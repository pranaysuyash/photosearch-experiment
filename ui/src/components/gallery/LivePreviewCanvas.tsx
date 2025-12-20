import React, { useEffect, useRef, useState } from 'react';
import { api } from '../../api';
import { cn } from '../../lib/utils';

interface EditSettings {
    brightness: number;
    contrast: number;
    saturation: number;
    rotation: number;
    flipH: boolean;
    flipV: boolean;
    crop?: { x: number; y: number; width: number; height: number };
}

interface LivePreviewCanvasProps {
    photoPath: string;
    settings: EditSettings;
    className?: string;
}

export function LivePreviewCanvas({ photoPath, settings, className }: LivePreviewCanvasProps) {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const [image, setImage] = useState<HTMLImageElement | null>(null);
    const [loading, setLoading] = useState(true);

    // Load image
    useEffect(() => {
        let active = true;
        setLoading(true);

        // Use high res for preview but maybe not full original if huge? 
        // For now use a reasonable size like 1600px
        const url = api.getImageUrl(photoPath, 1600);

        const img = new Image();
        img.crossOrigin = 'anonymous';
        img.src = url;
        img.onload = () => {
            if (active) {
                setImage(img);
                setLoading(false);
            }
        };

        return () => { active = false; };
    }, [photoPath]);

    // Apply filters and draw
    useEffect(() => {
        if (!image || !canvasRef.current || !containerRef.current) return;

        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        // Dimensions: Fit image into container while maintaining aspect ratio
        const containerWidth = containerRef.current.clientWidth;
        const containerHeight = containerRef.current.clientHeight;

        // Calculate scale to fit
        // We actually want the canvas to be the size of the *displayed* image
        // But filters operate on pixels. 
        // Strategy: Set canvas to native image resolution (or capped), then CSS scales it down.

        // For performance, let's limit canvas size to 2048px max dimension
        const maxDim = 2048;
        let width = image.width;
        let height = image.height;

        if (width > maxDim || height > maxDim) {
            const ratio = Math.min(maxDim / width, maxDim / height);
            width *= ratio;
            height *= ratio;
        }

        // Handles rotation 90/270 which swaps dimensions
        const isRotated90 = settings.rotation % 180 !== 0;
        canvas.width = isRotated90 ? height : width;
        canvas.height = isRotated90 ? width : height;

        // Drawing context setup
        ctx.save();
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Transform Origin Center
        ctx.translate(canvas.width / 2, canvas.height / 2);

        // Rotation
        ctx.rotate((settings.rotation * Math.PI) / 180);

        // Flip
        ctx.scale(settings.flipH ? -1 : 1, settings.flipV ? -1 : 1);

        // Draw Image (Centered)
        // Draw the image at its scaled size
        ctx.drawImage(image, -width / 2, -height / 2, width, height);

        ctx.restore();

        // Apply Filters (Brightness, Contrast, Saturation)
        // We get the ImageData and manipulate pixels
        // NOTE: This can be slow for large images. 
        // Optimization: CSS filters on the canvas element?
        // Using ImageData gives us exact control to match the backend (if backend uses similar logic).
        // CSS filters are faster for preview.
        // Let's use ImageData for accuracy if it matches `PhotoEditor.tsx` logic.
        // `PhotoEditor.tsx` used manual pixel manipulation.

        if (settings.brightness !== 0 || settings.contrast !== 0 || settings.saturation !== 0) {
            const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
            const data = imageData.data;

            const b = settings.brightness; // -100 to 100
            const c = settings.contrast; // -100 to 100
            const s = settings.saturation; // -100 to 100

            // Pre-calculate factors
            const brightnessOffset = b * 2.55; // simple brightness
            const contrastFactor = (259 * (c + 255)) / (255 * (259 - c));
            const saturationFactor = (s + 100) / 100;

            for (let i = 0; i < data.length; i += 4) {
                let r = data[i];
                let g = data[i + 1];
                let bVal = data[i + 2];

                // Brightness
                r += brightnessOffset;
                g += brightnessOffset;
                bVal += brightnessOffset;

                // Contrast
                r = contrastFactor * (r - 128) + 128;
                g = contrastFactor * (g - 128) + 128;
                bVal = contrastFactor * (bVal - 128) + 128;

                // Saturation
                if (s !== 0) {
                    const gray = 0.2989 * r + 0.5870 * g + 0.1140 * bVal;
                    r = gray + saturationFactor * (r - gray);
                    g = gray + saturationFactor * (g - gray);
                    bVal = gray + saturationFactor * (bVal - gray);
                }

                data[i] = Math.max(0, Math.min(255, r));
                data[i + 1] = Math.max(0, Math.min(255, g));
                data[i + 2] = Math.max(0, Math.min(255, bVal));
            }

            ctx.putImageData(imageData, 0, 0);
        }

    }, [image, settings]);

    return (
        <div ref={containerRef} className={cn("w-full h-full flex items-center justify-center overflow-hidden", className)}>
            {loading && <div className="text-white/50">Loading preview...</div>}
            <canvas
                ref={canvasRef}
                className="max-w-full max-h-full object-contain shadow-2xl"
            />
        </div>
    );
}
