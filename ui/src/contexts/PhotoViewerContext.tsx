import React, {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
} from 'react';
import type { Photo } from '../api';
import { PhotoDetail } from '../components/gallery/PhotoDetail';

/* eslint-disable react-refresh/only-export-components */
interface PhotoViewerContextValue {
  isOpen: boolean;
  open: (photos: Photo[], index: number) => void;
  openForPhoto: (photos: Photo[], photo: Photo) => void;
  close: () => void;
}

const PhotoViewerContext = createContext<PhotoViewerContextValue | null>(null);

export function PhotoViewerProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [currentIndex, setCurrentIndex] = useState<number | null>(null);

  const close = useCallback(() => {
    setCurrentIndex(null);
    setPhotos([]);
  }, []);

  const open = useCallback((nextPhotos: Photo[], index: number) => {
    setPhotos(nextPhotos);
    setCurrentIndex(index);
  }, []);

  const openForPhoto = useCallback(
    (nextPhotos: Photo[], photo: Photo) => {
      const idx = nextPhotos.findIndex((p) => p.path === photo.path);
      if (idx >= 0) open(nextPhotos, idx);
      else open([photo], 0);
    },
    [open]
  );

  const value = useMemo<PhotoViewerContextValue>(
    () => ({
      isOpen: currentIndex !== null,
      open,
      openForPhoto,
      close,
    }),
    [close, currentIndex, open, openForPhoto]
  );

  return (
    <PhotoViewerContext.Provider value={value}>
      {children}
      <PhotoDetail
        photos={photos}
        currentIndex={currentIndex}
        onNavigate={setCurrentIndex}
        onClose={close}
      />
    </PhotoViewerContext.Provider>
  );
}

export function usePhotoViewer() {
  const ctx = useContext(PhotoViewerContext);
  if (!ctx) {
    throw new Error('usePhotoViewer must be used within a PhotoViewerProvider');
  }
  return ctx;
}
