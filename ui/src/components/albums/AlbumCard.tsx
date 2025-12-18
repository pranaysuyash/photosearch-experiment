import { motion } from 'framer-motion';
import { Folder, Zap, Image as ImageIcon } from 'lucide-react';
import { api, type Album } from '../../api';
import SecureLazyImage from '../gallery/SecureLazyImage';

interface AlbumCardProps {
  album: Album;
  onClick: () => void;
}

export function AlbumCard({ album, onClick }: AlbumCardProps) {
  const coverUrl = album.cover_photo_path
    ? api.getImageUrl(album.cover_photo_path, 400)
    : null;

  return (
    <motion.button
      onClick={onClick}
      className='relative group w-full aspect-square overflow-hidden rounded-2xl glass-panel hover:scale-[1.02] transition-all duration-200'
      whileHover={{ y: -4 }}
      whileTap={{ scale: 0.98 }}
    >
      {/* Cover Photo Background */}
      <div className='absolute inset-0'>
        {coverUrl ? (
          <SecureLazyImage
            path={album.cover_photo_path!}
            size={400}
            alt={album.name}
            className='w-full h-full object-cover'
          />
        ) : (
          <div className='w-full h-full bg-gradient-to-br from-white/5 to-white/10 flex items-center justify-center'>
            <Folder size={64} className='text-white/20' />
          </div>
        )}
        {/* Gradient overlay */}
        <div className='absolute inset-0 bg-gradient-to-t from-black/80 via-black/40 to-transparent' />
      </div>

      {/* Content */}
      <div className='relative h-full flex flex-col justify-between p-4'>
        {/* Top: Smart Album Badge */}
        <div className='flex justify-between items-start'>
          {album.is_smart && (
            <div className='px-2 py-1 rounded-lg bg-yellow-500/20 backdrop-blur-sm border border-yellow-400/30'>
              <div className='flex items-center gap-1'>
                <Zap size={12} className='text-yellow-400' />
                <span className='text-xs font-medium text-yellow-300'>
                  Smart
                </span>
              </div>
            </div>
          )}
          <div className='flex-1' /> {/* Spacer */}
        </div>

        {/* Bottom: Album Info */}
        <div className='space-y-1'>
          {/* Photo Count Badge */}
          <div className='flex items-center gap-1.5 mb-2'>
            <div className='px-2 py-1 rounded-lg bg-white/10 backdrop-blur-sm border border-white/20'>
              <div className='flex items-center gap-1.5'>
                <ImageIcon size={12} className='text-white/80' />
                <span className='text-xs font-medium text-white/90'>
                  {album.photo_count.toLocaleString()}
                </span>
              </div>
            </div>
          </div>

          {/* Album Name */}
          <h3 className='text-lg font-semibold text-white line-clamp-2 text-left'>
            {album.name}
          </h3>

          {/* Description */}
          {album.description && (
            <p className='text-sm text-white/60 line-clamp-2 text-left'>
              {album.description}
            </p>
          )}
        </div>
      </div>

      {/* Hover Effect Overlay */}
      <div className='absolute inset-0 border-2 border-white/0 group-hover:border-white/20 rounded-2xl transition-colors duration-200 pointer-events-none' />
    </motion.button>
  );
}
