/**
 * Version Stack Viewer Component
 *
 * Displays all versions of a photo in a vertical stack with the ability to switch between versions
 * and see edit history.
 */
import React, { useState, useEffect } from 'react';
import { 
  Image, 
  History, 
  Edit3, 
  Copy, 
  RotateCw,
  Eye,
  EyeOff,
  Lock,
  Globe,
  Settings,
  X,
  Check,
  AlertCircle,
  MoreHorizontal
} from 'lucide-react';
import { api } from '../../api';
import { glass } from '../../design/glass';

interface PhotoVersion {
  id: string;
  version_path: string;
  version_type: 'original' | 'edit' | 'variant' | 'derivative';
  version_name: string | null;
  version_description: string | null;
  edit_instructions: Record<string, any>;
  created_at: string;
  updated_at: string;
  parent_version_id: string | null;
}

interface VersionStack {
  id: string;
  original_path: string;
  version_count: number;
  created_at: string;
  updated_at: string;
  versions: PhotoVersion[];
}

interface VersionStackViewerProps {
  photoPath: string;
  onVersionChange?: (path: string) => void;
}

export function VersionStackViewer({ photoPath, onVersionChange }: VersionStackViewerProps) {
  const [versionStack, setVersionStack] = useState<VersionStack | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);
  const [showMetadata, setShowMetadata] = useState(false);

  useEffect(() => {
    loadVersionStack();
  }, [photoPath]);

  const loadVersionStack = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await api.getPhotoVersions(photoPath);
      setVersionStack(response);
    } catch (err) {
      console.error('Failed to load version stack:', err);
      setError('Failed to load version stack');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className={`${glass.surface} rounded-xl border border-white/10 p-4`}>
        <div className="flex items-center justify-center h-24">
          <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`${glass.surface} rounded-xl border border-white/10 p-4`}>
        <div className="text-destructive flex items-center gap-2">
          <AlertCircle size={16} />
          {error}
        </div>
      </div>
    );
  }

  if (!versionStack || versionStack.versions.length <= 1) {
    return (
      <div className={`${glass.surface} rounded-xl border border-white/10 p-4`}>
        <div className="text-muted-foreground text-center py-8">
          <History size={32} className="mx-auto mb-2 opacity-50" />
          <p>No alternate versions available</p>
          <p className="text-xs mt-1">This photo has no edited or derived versions</p>
        </div>
      </div>
    );
  }

  // Sort versions: original first, then by creation date
  const sortedVersions = [...versionStack.versions].sort((a, b) => {
    if (a.version_type === 'original') return -1;
    if (b.version_type === 'original') return 1;
    return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
  });

  const handleSelectVersion = (versionPath: string) => {
    if (onVersionChange) {
      onVersionChange(versionPath);
    }
  };

  const getEditInstructionSummary = (instructions: Record<string, any>): string => {
    if (!instructions || Object.keys(instructions).length === 0) {
      return 'No edits applied';
    }

    const changes = [];
    if (instructions.brightness) changes.push(`Brightness: ${instructions.brightness}`);
    if (instructions.contrast) changes.push(`Contrast: ${instructions.contrast}`);
    if (instructions.saturation) changes.push(`Saturation: ${instructions.saturation}`);
    if (instructions.rotation) changes.push(`Rotation: ${instructions.rotation}°`);
    if (instructions.flip_horizontal) changes.push('Horiz. Flip');
    if (instructions.flip_vertical) changes.push('Vert. Flip');
    if (instructions.crop) changes.push('Cropped');

    if (changes.length === 0) return 'Edits applied';
    return changes.slice(0, 2).join(', ') + (changes.length > 2 ? ', ...' : '');
  };

  return (
    <div className={`${glass.surface} rounded-xl border border-white/10 overflow-hidden`}>
      <div className="flex items-center justify-between p-3 border-b border-white/10">
        <div className="flex items-center gap-2">
          <History size={16} className="text-foreground" />
          <span className="text-sm font-medium text-foreground">Version Stack</span>
          <span className="text-xs text-muted-foreground">({versionStack.version_count} versions)</span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setShowMetadata(!showMetadata)}
            className="btn-glass btn-glass--muted w-8 h-8 p-0 flex items-center justify-center"
            title={showMetadata ? 'Hide metadata' : 'Show metadata'}
          >
            <Settings size={14} />
          </button>
          <button
            onClick={() => setExpanded(!expanded)}
            className="btn-glass btn-glass--muted w-8 h-8 p-0 flex items-center justify-center"
            title={expanded ? 'Collapse' : 'Expand'}
          >
            {expanded ? <X size={14} /> : <MoreHorizontal size={14} />}
          </button>
        </div>
      </div>

      {expanded ? (
        <div className="max-h-80 overflow-y-auto">
          <div className="space-y-1 p-2">
            {sortedVersions.map((version, index) => (
              <div 
                key={version.id}
                onClick={() => handleSelectVersion(version.version_path)}
                className={`flex items-center gap-3 p-2 rounded-lg cursor-pointer transition-colors ${
                  photoPath === version.version_path
                    ? 'bg-primary/20 border border-primary/30'
                    : 'hover:bg-white/5 border border-transparent'
                }`}
              >
                <div className="relative">
                  <img
                    src={api.getImageUrl(version.version_path, 60)}
                    alt={`Version ${index + 1}`}
                    className="w-12 h-12 object-cover rounded border border-white/10"
                  />
                  {version.version_type === 'original' && (
                    <div className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-blue-500 flex items-center justify-center">
                      <Lock size={10} className="text-white" />
                    </div>
                  )}
                </div>
                
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-foreground truncate">
                      {version.version_name || `Version ${index + 1}`}
                    </span>
                    <span className={`text-xs px-1.5 py-0.5 rounded-full ${
                      version.version_type === 'original' 
                        ? 'bg-blue-500/20 text-blue-400' 
                        : version.version_type === 'edit'
                        ? 'bg-green-500/20 text-green-400'
                        : version.version_type === 'variant'
                        ? 'bg-purple-500/20 text-purple-400'
                        : 'bg-orange-500/20 text-orange-400'
                    }`}>
                      {version.version_type}
                    </span>
                  </div>
                  
                  <div className="text-xs text-muted-foreground truncate">
                    {getEditInstructionSummary(version.edit_instructions)}
                  </div>
                  
                  <div className="text-xs text-muted-foreground">
                    {new Date(version.created_at).toLocaleDateString()}
                  </div>
                  
                  {showMetadata && version.version_description && (
                    <div className="text-xs text-muted-foreground mt-1 italic">
                      {version.version_description}
                    </div>
                  )}
                </div>
                
                {photoPath === version.version_path && (
                  <Check size={16} className="text-primary flex-shrink-0" />
                )}
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="p-3">
          <div className="flex gap-2 overflow-x-auto pb-1">
            {sortedVersions.map((version, index) => (
              <div 
                key={version.id}
                onClick={() => handleSelectVersion(version.version_path)}
                className={`flex-shrink-0 relative group cursor-pointer ${
                  photoPath === version.version_path ? 'ring-2 ring-primary rounded' : ''
                }`}
                title={version.version_name || `Version ${index + 1}`}
              >
                <img
                  src={api.getImageUrl(version.version_path, 80)}
                  alt={`Version ${index + 1}`}
                  className="w-16 h-16 object-cover rounded border border-white/10"
                />
                
                {version.version_type === 'original' && (
                  <div className="absolute top-1 left-1 w-4 h-4 rounded-full bg-blue-500 flex items-center justify-center">
                    <Lock size={8} className="text-white" />
                  </div>
                )}
                
                <div className="absolute bottom-0 left-0 right-0 bg-black/70 text-white text-xs px-1 py-0.5 truncate">
                  {version.version_name || `V${index + 1}`}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Stack Info */}
      <div className={`${glass.surfaceStrong} p-3 border-t border-white/10 text-xs text-muted-foreground`}>
        <div className="flex justify-between">
          <span>Original:</span>
          <span className="truncate ml-2">{versionStack.original_path.split('/').pop()}</span>
        </div>
        <div className="flex justify-between mt-1">
          <span>Created:</span>
          <span>{new Date(versionStack.created_at).toLocaleDateString()}</span>
        </div>
      </div>
    </div>
  );
}

export default VersionStackViewer;