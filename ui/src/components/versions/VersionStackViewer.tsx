/**
 * Version Stack Component
 *
 * Provides a UI for managing photo version stacks (originals and edited copies).
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  Layers,
  Edit3,
  Trash2,
  Eye,
  Download,
  MoreVertical,
} from 'lucide-react';
import { api } from '../api';
import { glass } from '../design/glass';

interface PhotoVersion {
  id: string;
  version_path: string;
  version_type: 'original' | 'edit' | 'variant' | 'derivative';
  version_name: string | null;
  version_description: string | null;
  created_at: string;
  updated_at: string;
  edit_instructions: Record<string, unknown> | null; // Contains edit operations applied to reach this version
  parent_version_id: string | null; // ID of parent version in the chain
  size_bytes: number;
  dimensions: { width: number; height: number };
  is_current: boolean; // Whether this is the currently viewed version
}

interface VersionStack {
  id: string;
  original_path: string;
  versions: PhotoVersion[];
  created_at: string;
  updated_at: string;
}

interface VersionStackProps {
  photoPath: string;
  currentVersionPath?: string;
  onVersionChange?: (versionPath: string) => void;
}

export function VersionStackViewer({
  photoPath,
  currentVersionPath,
  onVersionChange,
}: VersionStackProps) {
  const [versionStack, setVersionStack] = useState<VersionStack | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);
  const [showActions, setShowActions] = useState<string | null>(null);

  // Load the version stack for this photo
  const loadVersionStack = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const stack = await api.getVersionStack(photoPath);
      setVersionStack(stack);
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

  const handleVersionSelect = (versionPath: string) => {
    onVersionChange?.(versionPath);
  };

  const deleteVersion = async (versionId: string) => {
    if (
      !window.confirm(
        'Are you sure you want to delete this version? This cannot be undone.'
      )
    ) {
      return;
    }

    try {
      await api.deleteVersion(versionId);
      loadVersionStack(); // Refresh the stack
    } catch (err) {
      console.error('Failed to delete version:', err);
      setError('Failed to delete version');
    }
  };

  if (loading) {
    return (
      <div className={`${glass.surface} rounded-xl border border-white/10 p-4`}>
        <div className='flex items-center gap-2 mb-2'>
          <Layers size={16} className='text-muted-foreground' />
          <span className='text-sm font-medium text-foreground'>Versions</span>
        </div>
        <div className='flex items-center justify-center h-20'>
          <div className='w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin' />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`${glass.surface} rounded-xl border border-white/10 p-4`}>
        <div className='flex items-center gap-2 mb-2'>
          <Layers size={16} className='text-muted-foreground' />
          <span className='text-sm font-medium text-foreground'>Versions</span>
        </div>
        <div className='text-sm text-destructive'>{error}</div>
      </div>
    );
  }

  if (!versionStack || versionStack.versions.length <= 1) {
    return (
      <div className={`${glass.surface} rounded-xl border border-white/10 p-4`}>
        <div className='flex items-center gap-2 mb-2'>
          <Layers size={16} className='text-muted-foreground' />
          <span className='text-sm font-medium text-foreground'>Versions</span>
        </div>
        <div className='text-sm text-muted-foreground italic'>
          {versionStack?.versions.length === 1
            ? 'No edited versions yet'
            : 'No versions found for this photo'}
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

  // Find the current version in the stack
  const currentVersion =
    versionStack.versions.find((v) => v.version_path === currentVersionPath) ||
    versionStack.versions[0]; // Default to first version

  // Format file size
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div
      className={`${glass.surface} rounded-xl border border-white/10 overflow-hidden`}
    >
      {/* Header */}
      <div className='flex items-center justify-between p-3 border-b border-white/10'>
        <div className='flex items-center gap-2'>
          <Layers size={16} className='text-foreground' />
          <span className='text-sm font-medium text-foreground'>Versions</span>
        </div>
        <button
          onClick={() => setExpanded(!expanded)}
          className='btn-glass btn-glass--muted w-8 h-8 p-0 flex items-center justify-center'
          title={expanded ? 'Collapse' : 'Expand'}
        >
          <MoreVertical size={16} />
        </button>
      </div>

      {/* Current Version Preview */}
      {!expanded && (
        <div className='p-3'>
          <div className='flex items-center gap-3 mb-2'>
            <div className='relative'>
              <img
                src={api.getImageUrl(currentVersion.version_path, 80)}
                alt='Current version'
                className='w-16 h-16 object-cover rounded border border-white/10'
                loading='lazy'
              />
              {currentVersion.version_type === 'original' && (
                <div className='absolute -top-1 -right-1 w-5 h-5 rounded-full bg-blue-500 flex items-center justify-center'>
                  <Edit3 size={10} className='text-white' />
                </div>
              )}
            </div>
            <div className='flex-1 min-w-0'>
              <div className='flex items-center gap-2'>
                <div className='font-medium text-foreground truncate'>
                  {currentVersion.version_name || 'Current Version'}
                </div>
                <span
                  className={`text-xs px-1.5 py-0.5 rounded-full ${
                    currentVersion.version_type === 'original'
                      ? 'bg-blue-500/20 text-blue-400'
                      : currentVersion.version_type === 'edit'
                      ? 'bg-green-500/20 text-green-400'
                      : 'bg-purple-500/20 text-purple-400'
                  }`}
                >
                  {currentVersion.version_type === 'original'
                    ? 'Original'
                    : currentVersion.version_type === 'edit'
                    ? 'Edit'
                    : currentVersion.version_type === 'variant'
                    ? 'Variant'
                    : 'Derivative'}
                </span>
              </div>
              <div className='text-xs text-muted-foreground truncate'>
                {currentVersion.dimensions.width}×
                {currentVersion.dimensions.height} •{' '}
                {formatFileSize(currentVersion.size_bytes)}
              </div>
              {currentVersion.version_description && (
                <div className='text-xs text-muted-foreground truncate mt-1'>
                  {currentVersion.version_description}
                </div>
              )}
            </div>
          </div>

          <button
            onClick={() => handleVersionSelect(currentVersion.version_path)}
            className='btn-glass btn-glass--primary w-full text-sm py-1.5'
          >
            <Eye size={14} className='mr-1' />
            View This Version
          </button>
        </div>
      )}

      {/* Expanded View - Full Version Stack */}
      {expanded && (
        <div className='p-3 space-y-3 max-h-80 overflow-y-auto'>
          {sortedVersions.map((version, index) => (
            <div
              key={version.id}
              className={`p-3 rounded-lg border flex items-center gap-3 ${
                version.version_path === currentVersionPath
                  ? 'border-primary bg-primary/10'
                  : 'border-white/10 hover:border-white/20'
              }`}
            >
              <div className='relative'>
                <img
                  src={api.getImageUrl(version.version_path, 100)}
                  alt={`Version ${index + 1}`}
                  className='w-20 h-20 object-cover rounded border border-white/10'
                  loading='lazy'
                />
                {version.version_type === 'original' && (
                  <div className='absolute -top-1 -right-1 w-5 h-5 rounded-full bg-blue-500 flex items-center justify-center'>
                    <Edit3 size={10} className='text-white' />
                  </div>
                )}
              </div>

              <div className='flex-1 min-w-0'>
                <div className='flex items-center justify-between mb-1'>
                  <div className='font-medium text-foreground truncate'>
                    {version.version_name || `Version ${index + 1}`}
                  </div>
                  <div className='flex items-center gap-2'>
                    {version.is_current && (
                      <span className='text-xs px-1 py-0.5 rounded bg-green-500/20 text-green-400'>
                        Current
                      </span>
                    )}
                    <button
                      onClick={() =>
                        setShowActions(
                          showActions === version.id ? null : version.id
                        )
                      }
                      className='btn-glass btn-glass--muted w-8 h-8 p-0 flex items-center justify-center'
                    >
                      <MoreVertical size={14} />
                    </button>
                  </div>
                </div>

                <div className='flex items-center gap-4 text-xs text-muted-foreground mb-1'>
                  <span>{version.version_type}</span>
                  <span>
                    {new Date(version.created_at).toLocaleDateString()}
                  </span>
                  <span>{formatFileSize(version.size_bytes)}</span>
                </div>

                {version.version_description && (
                  <div className='text-xs text-muted-foreground line-clamp-2'>
                    {version.version_description}
                  </div>
                )}
              </div>

              <div className='flex flex-col gap-1'>
                <button
                  onClick={() => handleVersionSelect(version.version_path)}
                  className='btn-glass btn-glass--primary w-8 h-8 p-0 flex items-center justify-center'
                  title='View version'
                >
                  <Eye size={14} />
                </button>

                <button
                  onClick={() =>
                    window.open(api.getFileUrl(version.version_path), '_blank')
                  }
                  className='btn-glass btn-glass--muted w-8 h-8 p-0 flex items-center justify-center'
                  title='Download version'
                >
                  <Download size={14} />
                </button>
              </div>

              {/* Action menu for each version */}
              {showActions === version.id && (
                <div
                  className={`${glass.surfaceStrong} absolute right-24 top-3 z-10 border border-white/10 rounded-lg shadow-lg`}
                >
                  <button
                    onClick={() => handleVersionSelect(version.version_path)}
                    className='flex items-center gap-2 w-full px-3 py-2 text-xs hover:bg-white/5'
                  >
                    <Eye size={12} />
                    View
                  </button>
                  <button
                    onClick={() =>
                      window.open(
                        api.getFileUrl(version.version_path),
                        '_blank'
                      )
                    }
                    className='flex items-center gap-2 w-full px-3 py-2 text-xs hover:bg-white/5'
                  >
                    <Download size={12} />
                    Download
                  </button>
                  {version.version_type !== 'original' && (
                    <button
                      onClick={() => deleteVersion(version.id)}
                      className='flex items-center gap-2 w-full px-3 py-2 text-xs hover:bg-destructive/10 text-destructive'
                    >
                      <Trash2 size={12} />
                      Delete
                    </button>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Stack Stats */}
      <div
        className={`${glass.surfaceStrong} p-3 border-t border-white/10 text-xs text-muted-foreground`}
      >
        <div className='flex justify-between'>
          <span>
            {sortedVersions.length} version
            {sortedVersions.length !== 1 ? 's' : ''}
          </span>
          <span>
            {sortedVersions.filter((v) => v.version_type === 'original').length}{' '}
            original,{' '}
            {sortedVersions.filter((v) => v.version_type === 'edit').length}{' '}
            edited
          </span>
        </div>
      </div>
    </div>
  );
}
