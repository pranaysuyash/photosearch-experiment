import { useRef, useState } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Environment, Text, Image as DreiImage } from "@react-three/drei";
import { type Photo, api } from "../api";

interface MemoryMuseumProps {
    photos: Photo[];
    onClose: () => void;
    onPhotoSelect: (photo: Photo) => void;
}

function PhotoFrame({ photo, position, index, onSelect }: { photo: Photo, position: [number, number, number], index: number, onSelect: (p: Photo) => void }) {
    const [hovered, setHover] = useState(false);
    // Use low-res thumbnail for texture (size=300 from backend)
    const textureUrl = api.getImageUrl(photo.path, 300);
    
    // Simple oscillation
    const meshRef = useRef<any>(null);
    useFrame((state) => {
        if (!hovered && meshRef.current) {
            meshRef.current.position.y = position[1] + Math.sin(state.clock.elapsedTime + index) * 0.1;
        }
    });

    return (
        <group position={position} ref={meshRef}>
            <DreiImage 
                url={textureUrl}
                transparent 
                scale={[4, 3]} // 4:3 aspect ratio default
                opacity={1}
                side={2} // front side only?
                onPointerOver={() => { document.body.style.cursor = 'pointer'; setHover(true); }}
                onPointerOut={() => { document.body.style.cursor = 'auto'; setHover(false); }}
                onClick={() => onSelect(photo)}
            />
            {hovered && (
                <Text 
                    position={[0, -2, 0]} 
                    fontSize={0.3} 
                    color="white" 
                    anchorX="center" 
                    anchorY="middle"
                >
                    {photo.filename}
                </Text>
            )}
        </group>
    );
}

export function MemoryMuseum({ photos, onClose, onPhotoSelect }: MemoryMuseumProps) {
    // Generate a spiral layout
    const layoutPhotos = photos.slice(0, 50).map((photo, i) => {
        const angle = i * 0.5;
        const radius = 10 + i * 0.5;
        const x = Math.cos(angle) * radius;
        const z = Math.sin(angle) * radius;
        return { photo, position: [x, 0, z] as [number, number, number] };
    });

    return (
        <div className="fixed inset-0 z-50 bg-black/90">
            <button 
                onClick={onClose}
                className="absolute top-4 right-4 z-[60] px-4 py-2 bg-background/20 hover:bg-background/80 text-white rounded-full backdrop-blur transition-colors"
            >
                Exit 3D Mode
            </button>

            <Canvas camera={{ position: [0, 5, 20], fov: 60 }}>
                <color attach="background" args={['#050510']} />
                
                {/* Lighting */}
                <ambientLight intensity={0.5} />
                <pointLight position={[10, 10, 10]} />
                
                {/* Controls */}
                <OrbitControls 
                    enableDamping 
                    autoRotate={true}
                    autoRotateSpeed={0.5}
                    maxPolarAngle={Math.PI / 1.5}
                />
                
                {/* Environment - Stars? */}
                <Environment preset="night" />

                {/* Photos */}
                {layoutPhotos.map((item, i) => (
                    <PhotoFrame 
                        key={item.photo.path} 
                        photo={item.photo} 
                        position={item.position} 
                        index={i}
                        onSelect={onPhotoSelect}
                    />
                ))}
                
                {/* Floor Grid just for reference */}
                <gridHelper args={[100, 100, 0x333333, 0x111111]} position={[0, -2, 0]} />
            </Canvas>
            
            <div className="absolute bottom-10 left-0 right-0 text-center pointer-events-none text-white/50 text-sm">
                Drag to explore • Click to select
            </div>
        </div>
    );
}
