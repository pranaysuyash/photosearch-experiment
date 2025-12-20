import { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';

interface LazyImageProps {
  src: string;
  alt: string;
  className?: string;
  placeholder?: string;
  aspectRatio?: number;
  onLoad?: () => void;
  onError?: () => void;
  onLoadTime?: (loadTime: number) => void;
  objectFit?: 'cover' | 'contain' | 'fill' | 'none' | 'scale-down';
}

export function LazyImage({
  src,
  alt,
  className = '',
  placeholder,
  aspectRatio,
  onLoad,
  onError,
  onLoadTime,
  objectFit = 'cover',
}: LazyImageProps) {
  const [isLoaded, setIsLoaded] = useState(false);
  const [hasError, setHasError] = useState(false);
  const [isInView, setIsInView] = useState(false);
  const imgRef = useRef<HTMLImageElement>(null);
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const observerRef = useRef<IntersectionObserver | null>(null);
  const loadStartTimeRef = useRef<number>(0);

  useEffect(() => {
    const node = wrapperRef.current;
    if (!node) return;

    observerRef.current = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setIsInView(true);
            loadStartTimeRef.current = performance.now();
            observerRef.current?.disconnect();
          }
        });
      },
      { threshold: 0.1, rootMargin: '200px' }
    );

    observerRef.current.observe(node);

    return () => {
      observerRef.current?.disconnect();
    };
  }, []);

  const handleLoad = () => {
    const loadTime = performance.now() - loadStartTimeRef.current;
    onLoadTime?.(loadTime);
    setIsLoaded(true);
    onLoad?.();
  };

  const handleError = () => {
    setHasError(true);
    onError?.();
  };

  return (
    <div
      ref={wrapperRef}
      className={`relative overflow-hidden ${className}`}
      style={aspectRatio ? { aspectRatio } : undefined}
    >
      {/* Placeholder/Loading state */}
      {(!isLoaded || hasError) && (
        <div className='absolute inset-0 bg-muted animate-pulse flex items-center justify-center'>
          {placeholder ? (
            <img
              src={placeholder}
              alt=''
              className='w-full h-full object-cover opacity-50'
            />
          ) : (
            <div className='w-8 h-8 border-2 border-primary/30 border-t-primary rounded-full animate-spin' />
          )}
        </div>
      )}

      {/* Main image */}
      {isInView && (
        <motion.img
          ref={imgRef}
          src={src}
          alt={alt}
          className={`w-full h-full transition-opacity duration-300 ${isLoaded ? 'opacity-100' : 'opacity-0'
            }`}
          style={{ objectFit }}
          onLoad={handleLoad}
          onError={handleError}
          initial={{ opacity: 0 }}
          animate={{ opacity: isLoaded ? 1 : 0 }}
          transition={{ duration: 0.3 }}
        />
      )}
    </div>
  );
}
