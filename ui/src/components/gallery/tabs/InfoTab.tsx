import React from 'react';
import {
  ExternalLink,
  Star,
  StarOff,
  FolderPlus,
  Edit3,
  Hash,
  RotateCw,
  FlipHorizontal,
  FlipVertical,
  Trash2,
  Copy,
  Info,
} from 'lucide-react';
import { type Photo, api } from '../../../api'; // Type-only import
import { StarRating } from '../../rating/StarRating';
import { NotesEditor } from '../../notes/NotesEditor';
import { useToast } from '../../ui/useToast';

interface PhotoMetadata {
  image?: {
    width?: number;
    height?: number;
  };
  filesystem?: {
    size_human?: string;
    created?: string;
  };
}

interface InfoTabProps {
  photo: Photo;
  metadata: PhotoMetadata | null;
  isFavorited: boolean;
  rating?: number;
  note?: string;
  onToggleFavorite: () => void;
  onRotate: () => void;
  onFlip: (direction: 'horizontal' | 'vertical') => void;
  onEdit: () => void;
  onAddToAlbum: () => void;
  onAddToTags: () => void;
  onDelete: () => void;
}

export function InfoTab({
  photo,
  metadata,
  isFavorited,
  rating = 0,
  note = '',
  onToggleFavorite,
  onRotate,
  onFlip,
  onEdit,
  onAddToAlbum,
  onAddToTags,
  onDelete,
}: InfoTabProps) {
  const { showToast } = useToast();

  const originalOpenUrl = api.getFileUrl(photo.path);

  const copyPath = async () => {
    try {
      await navigator.clipboard.writeText(photo.path);
      showToast('Path copied to clipboard ✓', 'success');
    } catch {
      showToast('Failed to copy path', 'error');
    }
  };

  // Basic info calculation
  const dimensions =
    metadata?.image?.width && metadata?.image?.height
      ? `${metadata.image.width} × ${metadata.image.height}`
      : 'Unknown size';

  const fileSize = metadata?.filesystem?.size_human || 'Unknown size';
  const fileDate =
    metadata?.filesystem?.created?.split('T')[0] || 'Unknown date';

  return (
    <div className='flex flex-col gap-6 h-full text-white/90'>
      {/* 3.1 Icon-Only Button Bar */}
      <div className='flex flex-wrap items-center gap-2 p-3 bg-white/5 rounded-2xl border border-white/10 backdrop-blur-md'>
        <ControlButton
          onClick={() => window.open(originalOpenUrl, '_blank')}
          icon={ExternalLink}
          label='Open Original'
        />
        <ControlButton
          onClick={onToggleFavorite}
          icon={isFavorited ? StarOff : Star}
          label={isFavorited ? 'Unfavorite' : 'Favorite'}
          active={isFavorited}
          activeColor='text-yellow-400'
        />
        <ControlButton
          onClick={onAddToAlbum}
          icon={FolderPlus}
          label='Add to Album'
        />
        <ControlButton
          onClick={onEdit}
          icon={Edit3}
          label='Edit Photo'
          highlight
        />
        <ControlButton onClick={onAddToTags} icon={Hash} label='Manage Tags' />
        <div className='w-px h-6 bg-white/10 mx-1' /> {/* Separator */}
        <ControlButton onClick={onRotate} icon={RotateCw} label='Rotate 90°' />
        <ControlButton
          onClick={() => onFlip('horizontal')}
          icon={FlipHorizontal}
          label='Flip Horizontal'
        />
        <ControlButton
          onClick={() => onFlip('vertical')}
          icon={FlipVertical}
          label='Flip Vertical'
        />
        <div className='w-px h-6 bg-white/10 mx-1' /> {/* Separator */}
        <ControlButton
          onClick={onDelete}
          icon={Trash2}
          label='Move to Trash'
          variant='destructive'
        />
      </div>

      {/* Basic Metadata Card */}
      <div className='glass-surface p-4 rounded-xl space-y-3'>
        <h3 className='font-medium text-lg truncate' title={photo.filename}>
          {photo.filename}
        </h3>
        <div className='grid grid-cols-2 gap-y-2 text-sm text-white/60'>
          <div className='flex items-center gap-2'>
            <Info size={14} className='opacity-70' />
            <span>{dimensions}</span>
          </div>
          <div>{fileSize}</div>
          <div className='col-span-2'>{fileDate}</div>
        </div>
        <button
          onClick={copyPath}
          className='text-xs text-white/40 hover:text-white/80 transition-colors flex items-center gap-1.5 truncate max-w-full'
          title='Click to copy path'
        >
          <Copy size={12} />
          <span className='truncate'>{photo.path}</span>
        </button>
      </div>

      {/* Rating */}
      <div className='glass-surface p-4 rounded-xl'>
        <div className='flex items-center justify-between mb-2'>
          <span className='text-xs font-bold uppercase tracking-wider text-white/50'>
            Rating
          </span>
        </div>
        <StarRating
          photoPath={photo.path}
          initialRating={rating}
          showLabel
          size='md'
        />
      </div>

      {/* Smart Notes */}
      <div className='glass-surface p-4 rounded-xl'>
        <NotesEditor photoPath={photo.path} initialNote={note} showLabel />
      </div>
    </div>
  );
}

// Helper for Icon Buttons
interface ControlButtonProps {
  onClick: () => void;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  label: string;
  active?: boolean;
  activeColor?: string;
  highlight?: boolean;
  variant?: 'default' | 'destructive';
}

function ControlButton({
  onClick,
  icon: Icon,
  label,
  active,
  activeColor,
  highlight,
  variant = 'default',
}: ControlButtonProps) {
  const baseClass =
    'p-2 rounded-lg transition-all duration-200 flex items-center justify-center group relative';
  const variantClass =
    variant === 'destructive'
      ? 'hover:bg-red-500/20 text-red-300 hover:text-red-100'
      : highlight
      ? 'bg-white/10 hover:bg-white/20 text-white'
      : 'hover:bg-white/10 text-white/70 hover:text-white';

  return (
    <button
      onClick={onClick}
      className={`${baseClass} ${variantClass} ${active ? 'bg-white/15' : ''}`}
      aria-label={label}
      title={label}
    >
      <Icon size={18} className={active && activeColor ? activeColor : ''} />
      {/* Tooltip implementation could go here if using a Tooltip primitives,
                for now standard title attribute serves as basic tooltip */}
    </button>
  );
}
