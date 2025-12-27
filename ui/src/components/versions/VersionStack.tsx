/**
 * Version Stack Component
 *
 * Displays a stack of related photo versions (original + edited copies).
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  Layers,
  X,
  Eye,
  FileText,
  MoreHorizontal,
} from 'lucide-react';
import { api } from '../../api';
import { glass } from '../../design/glass';

interface PhotoVersion {
  id: string;
  original_path: string;
  version_path: string;
  version_type: 'original' | 'edited' | 'variant';
  version_name?: string;
  version_description?: string;
  created_at: string;
  updated_at: string;
  editing_instructions?: string;
}

interface VersionStackProps {
  photoPath: string;
  onVersionSelect?: (path: string) => void;
}

export function VersionStack({ photoPath, onVersionSelect }: VersionStackProps) {
  const [versions, setVersions] = useState<PhotoVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);

  // Load version stack
  const loadVersionStack = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const stack: PhotoVersion[] = await api.getVersionStack(photoPath);
      setVersions(stack);
    } catch (err) {
      console.error('Failed to load version stack:', err);
      setError('Failed to load version stack');
    } finally {
      setLoading(false);
    }
  }, [photoPath]);

  useEffect(() => {
    loadVersionStack();
  }, [loadVersionStack]);

  const handleSelectVersion = (versionPath: string) => {
    if (onVersionSelect) {
      onVersionSelect(versionPath);
    }
  };

  if (loading) {
    return (
      <div className={`${glass.surfaceStrong} rounded-xl border border-white/10 p-3`}>
        <div className="flex items-center gap-2 mb-2">
          <Layers size={16} className="text-muted-foreground" />
          <span className="text-sm font-medium text-foreground">Versions</span>
        </div>
        <div className="text-xs text-muted-foreground">Loading versions...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`${glass.surfaceStrong} rounded-xl border border-white/10 p-3`}>
        <div className="flex items-center gap-2 mb-2">
          <Layers size={16} className="text-muted-foreground" />
          <span className="text-sm font-medium text-foreground">Versions</span>
        </div>
        <div className="text-xs text-destructive">{error}</div>
      </div>
    );
  }

  if (versions.length <= 1) {
    return null; // Don't show if there's only 1 version (the original itself)
  }

  // Find the original in the stack
  const originalVersion = versions.find(v => v.version_type === 'original') || versions[0];
  const editedVersions = versions.filter(v => v.version_type !== 'original');

  return (
    <div className={`${glass.surfaceStrong} rounded-xl border border-white/10 overflow-hidden`}>
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-white/10">
        <div className="flex items-center gap-2">
          <Layers size={16} className="text-muted-foreground" />
          <span className="text-sm font-medium text-foreground">Version Stack</span>
        </div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="btn-glass btn-glass--muted w-8 h-8 p-0 justify-center"
          title={expanded ? 'Collapse' : 'Expand'}
        >
          <MoreHorizontal size={14} />
        </button>
      </div>

      {/* Collapsed view - show latest version */}
      {!expanded && (
        <div className="p-3">
          <div className="flex items-center gap-3">
            <div className="relative">
              <img
                src={api.getImageUrl(originalVersion.version_path, 80)}
                alt="Original"
                className="w-16 h-16 object-cover rounded border border-white/10"
              />
              {originalVersion.version_type === 'original' && (
                <div className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-blue-500 flex items-center justify-center">
                  <FileText size={10} className="text-white" />
                </div>
              )}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-foreground truncate">
                {originalVersion.version_name || originalVersion.version_path.split('/').pop()}
              </div>
              <div className="text-xs text-muted-foreground">
                {editedVersions.length} edit{editedVersions.length !== 1 ? 's' : ''}
              </div>
              <div className="text-xs text-muted-foreground truncate">
                {originalVersion.version_description || 'Original photo'}
              </div>
            </div>
            <button
              onClick={() => handleSelectVersion(originalVersion.version_path)}
              className="btn-glass btn-glass--primary text-xs px-2 py-1 flex items-center gap-1"
            >
              <Eye size={12} />
              View
            </button>
          </div>
        </div>
      )}

      {/* Expanded view - show all versions */}
      {expanded && (
        <div className="p-3 space-y-3">
          <div className="space-y-2 max-h-60 overflow-y-auto">
            {versions.map(version => (
              <div
                key={version.id}
                className={`flex items-center gap-3 p-2 rounded-lg border ${
                  photoPath === version.version_path
                    ? 'border-primary bg-primary/10'
                    : 'border-white/10 hover:border-white/20'
                }`}
              >
                <img
                  src={api.getImageUrl(version.version_path, 80)}
                  alt={`Version ${version.id}`}
                  className="w-12 h-12 object-cover rounded border border-white/10"
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <div className="text-sm font-medium text-foreground truncate">
                      {version.version_name || version.version_path.split('/').pop()}
                    </div>
                    {version.version_type === 'original' && (
                      <span className="text-xs px-1.5 py-0.5 rounded-full bg-blue-500/20 text-blue-400">
                        Original
                      </span>
                    )}
                  </div>
                  {version.version_description && (
                    <div className="text-xs text-muted-foreground truncate">
                      {version.version_description}
                    </div>
                  )}
                  <div className="text-xs text-muted-foreground">
                    {new Date(version.created_at).toLocaleDateString()}
                  </div>
                </div>
                <button
                  onClick={() => handleSelectVersion(version.version_path)}
                  className="btn-glass btn-glass--muted w-8 h-8 p-0 justify-center"
                  title="View this version"
                >
                  <Eye size={14} />
                </button>
              </div>
            ))}
          </div>

          <div className="flex justify-end">
            <button
              onClick={() => setExpanded(false)}
              className="btn-glass btn-glass--muted text-xs px-2 py-1 flex items-center gap-1"
            >
              <X size={12} />
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
