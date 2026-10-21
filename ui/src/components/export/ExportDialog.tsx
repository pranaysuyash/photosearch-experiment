/**
 * Export Dialog Component
 *
 * Provides options for exporting photos with various formats and settings.
 */
import React, { useState, useEffect } from 'react';
import {
  X,
  Download,
  Link,
  Copy,
  Calendar,
  Eye,
  Lock,
  Check,
  CheckCircle,
  AlertCircle,
} from 'lucide-react';
import { api, type ExportOptions } from '../api';
import { glass } from '@/design/glass';
import { useModalBehavior } from '../../hooks/useModalBehavior';

interface ExportDialogProps {
  isOpen: boolean;
  onClose: () => void;
  photoPaths: string[];
}

interface ExportPreset {
  id: string;
  name: string;
  description: string;
  options: ExportOptions;
}

interface ShareLink {
  share_id: string;
  share_url: string;
  expiration: string;
}

export function ExportDialog({
  isOpen,
  onClose,
  photoPaths,
}: ExportDialogProps) {
  const [activeTab, setActiveTab] = useState<'export' | 'share'>('export');
  const [presets, setPresets] = useState<ExportPreset[]>([]);
  const [selectedPreset, setSelectedPreset] = useState<string>('');
  const [includeMetadata, setIncludeMetadata] = useState(true);
  const [includeThumbnails, setIncludeThumbnails] = useState(false);
  const [maxResolution, setMaxResolution] = useState<number | null>(null);
  const [blurFaces, setBlurFaces] = useState(false);
  const [blurStrength, setBlurStrength] = useState(10);
  const [isExporting, setIsExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [exportSuccess, setExportSuccess] = useState(false);
  const [shareLink, setShareLink] = useState<ShareLink | null>(null);
  const [isCreatingShare, setIsCreatingShare] = useState(false);
  const [shareError, setShareError] = useState<string | null>(null);
  const [expirationHours, setExpirationHours] = useState(24);
  const [password, setPassword] = useState('');
  const [usePassword, setUsePassword] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [copied, setCopied] = useState(false);

  // Load export presets
  useEffect(() => {
    if (isOpen) {
      loadPresets();
    }
  }, [isOpen]);

  const loadPresets = async () => {
    try {
      const loadedPresets = await api.getExportPresets();
      setPresets(loadedPresets);
      if (loadedPresets.length > 0) {
        setSelectedPreset(loadedPresets[0].id);
      }
    } catch (error) {
      console.error('Failed to load export presets:', error);
      // Default to some presets if API fails
      setPresets([
        {
          id: 'high_quality',
          name: 'High Quality',
          description: 'Full resolution with metadata',
          options: {
            format: 'zip',
            include_metadata: true,
            include_thumbnails: false,
            max_resolution: undefined,
          },
        },
      ]);
    }
  };

  const handlePresetChange = (presetId: string) => {
    setSelectedPreset(presetId);
    const preset = presets.find((p) => p.id === presetId);
    if (preset) {
      setIncludeMetadata(preset.options.include_metadata ?? true);
      setIncludeThumbnails(preset.options.include_thumbnails ?? false);
      setMaxResolution(preset.options.max_resolution ?? null);
    }
  };

  const handleExport = async () => {
    if (photoPaths.length === 0) return;

    setIsExporting(true);
    setExportError(null);
    setExportSuccess(false);

    try {
      // Prepare export options
      const exportOptions: ExportOptions = {
        format: 'zip',
        include_metadata: includeMetadata,
        include_thumbnails: includeThumbnails,
        max_resolution: maxResolution || undefined,
        blur_faces: blurFaces,
        blur_strength: blurStrength,
        password_protect: usePassword,
        password: usePassword ? password : undefined,
      };

      // Validate blur strength if blur is enabled
      if (blurFaces && (blurStrength < 1 || blurStrength > 50)) {
        throw new Error('Blur strength must be between 1 and 50');
      }

      // The export endpoint returns the finished zip in one response, so
      // progress is an honest indeterminate state — no fake percentages.
      const blob = await api.exportPhotos(photoPaths, exportOptions);

      // Save the zip to disk
      const url = window.URL.createObjectURL(new Blob([blob]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute(
        'download',
        `photos_export_${photoPaths.length}_files.zip`
      );
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      // Show success state
      setExportSuccess(true);

      setTimeout(() => {
        setIsExporting(false);
        onClose();
      }, 2000);
    } catch (error) {
      console.error('Export failed:', error);
      const errorMessage =
        error instanceof Error
          ? error.message
          : 'Export failed. Please try again.';
      setExportError(errorMessage);
      setIsExporting(false);
    }
  };

  const createShareLink = async () => {
    if (photoPaths.length === 0) return;

    setIsCreatingShare(true);
    setShareError(null);
    try {
      const result = await api.createShareLink(
        photoPaths,
        expirationHours,
        usePassword ? password : undefined
      );
      setShareLink(result);
    } catch (error) {
      console.error('Failed to create share link:', error);
      const errorMessage =
        error instanceof Error
          ? error.message
          : 'Failed to create share link. Please try again.';
      setShareError(errorMessage);
    } finally {
      setIsCreatingShare(false);
    }
  };

  const copyShareLink = () => {
    if (shareLink?.share_url) {
      navigator.clipboard.writeText(shareLink.share_url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const panelRef = useModalBehavior(isOpen, onClose);

  if (!isOpen) return null;

  return (
    <div className='fixed inset-0 z-[1400] flex items-center justify-center p-4'>
      <div
        className='absolute inset-0 bg-black/80 backdrop-blur-sm'
        onClick={() => {
          // Don't close mid-export from a stray backdrop click.
          if (!isExporting) onClose();
        }}
      />

      <div
        ref={panelRef}
        role='dialog'
        aria-modal='true'
        aria-label='Export photos'
        className={`relative w-full max-w-2xl ${glass.surface} ${glass.surfaceStrong} rounded-2xl border border-white/10 shadow-2xl overflow-hidden`}
      >
        {/* Header */}
        <div className='flex items-center justify-between px-6 py-4 border-b border-white/10'>
          <div className='flex items-center gap-3'>
            <h3 className='text-xl font-semibold text-foreground'>
              {activeTab === 'export' ? 'Export Photos' : 'Share Photos'}
            </h3>
            <span className='text-xs text-muted-foreground bg-white/10 px-2 py-1 rounded-full'>
              {photoPaths.length} selected
            </span>
          </div>
          <button
            onClick={onClose}
            className='btn-glass btn-glass--muted w-9 h-9 p-0 justify-center'
            aria-label='Close export dialog'
          >
            <X size={16} />
          </button>
        </div>

        {/* Tabs */}
        <div className='flex border-b border-white/10' role='tablist' aria-label='Export or share'>
          <button
            className={`flex-1 py-3 text-center text-sm font-medium ${
              activeTab === 'export'
                ? 'text-foreground border-b-2 border-primary'
                : 'text-muted-foreground hover:text-foreground'
            }`}
            onClick={() => setActiveTab('export')}
            role='tab'
            aria-selected={activeTab === 'export'}
          >
            Export
          </button>
          <button
            className={`flex-1 py-3 text-center text-sm font-medium ${
              activeTab === 'share'
                ? 'text-foreground border-b-2 border-primary'
                : 'text-muted-foreground hover:text-foreground'
            }`}
            onClick={() => setActiveTab('share')}
            role='tab'
            aria-selected={activeTab === 'share'}
          >
            Share
          </button>
        </div>

        {/* Content */}
        <div className='p-6'>
          {activeTab === 'export' ? (
            <div className='space-y-6'>
              <div>
                <h4 className='font-medium text-foreground mb-3'>
                  Export Options
                </h4>

                {/* Preset Selection */}
                <div className='mb-4'>
                  <label htmlFor='ed-export-preset' className='block text-sm font-medium text-foreground mb-2'>
                    Export Preset
                  </label>
                  <select
                    id='ed-export-preset'
                    value={selectedPreset}
                    onChange={(e) => handlePresetChange(e.target.value)}
                    className='w-full px-3 py-2 rounded-lg border border-white/10 bg-white/5 text-foreground'
                  >
                    {presets.map((preset) => (
                      <option key={preset.id} value={preset.id}>
                        {preset.name} - {preset.description}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Options */}
                <div className='space-y-3'>
                  <label className='flex items-center gap-3'>
                    <input
                      type='checkbox'
                      checked={includeMetadata}
                      onChange={(e) => setIncludeMetadata(e.target.checked)}
                      className='w-4 h-4 rounded border-white/10 bg-white/5 text-primary'
                    />
                    <div className='font-medium text-foreground'>
                      Include metadata
                      <div className='font-normal text-xs text-muted-foreground'>
                        Include JSON files with photo information
                      </div>
                    </div>
                  </label>

                  <label className='flex items-center gap-3'>
                    <input
                      type='checkbox'
                      checked={includeThumbnails}
                      onChange={(e) => setIncludeThumbnails(e.target.checked)}
                      className='w-4 h-4 rounded border-white/10 bg-white/5 text-primary'
                    />
                    <div className='font-medium text-foreground'>
                      Include thumbnails
                      <div className='font-normal text-xs text-muted-foreground'>
                        Include small preview images
                      </div>
                    </div>
                  </label>

                  <label className='flex items-center gap-3'>
                    <input
                      type='checkbox'
                      checked={blurFaces}
                      onChange={(e) => setBlurFaces(e.target.checked)}
                      className='w-4 h-4 rounded border-white/10 bg-white/5 text-primary'
                    />
                    <div className='font-medium text-foreground'>
                      Blur faces
                      <div className='font-normal text-xs text-muted-foreground'>
                        Blur detected faces for privacy
                      </div>
                    </div>
                  </label>

                  {blurFaces && (
                    <div className='ml-7 space-y-2'>
                      <label className='block text-sm font-medium text-foreground'>
                        Blur strength: {blurStrength}
                      </label>
                      <input
                        type='range'
                        min='1'
                        max='50'
                        value={blurStrength}
                        onChange={(e) =>
                          setBlurStrength(parseInt(e.target.value))
                        }
                        className='w-full'
                      />
                      <div className='text-xs text-muted-foreground'>
                        Lower = lighter blur, Higher = stronger blur
                      </div>
                    </div>
                  )}

                  <div>
                    <label htmlFor='ed-max-resolution' className='block text-sm font-medium text-foreground mb-2'>
                      Max Resolution (pixels)
                    </label>
                    <select
                      id='ed-max-resolution'
                      value={maxResolution || ''}
                      onChange={(e) =>
                        setMaxResolution(
                          e.target.value ? parseInt(e.target.value) : null
                        )
                      }
                      className='w-full px-3 py-2 rounded-lg border border-white/10 bg-white/5 text-foreground'
                    >
                      <option value=''>Original size</option>
                      <option value='800'>800px</option>
                      <option value='1200'>1200px</option>
                      <option value='1920'>1920px</option>
                      <option value='2560'>2560px</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* Export Error */}
              {exportError && (
                <div className='rounded-lg border border-red-500/50 bg-red-500/10 p-4'>
                  <div className='flex items-start gap-3'>
                    <AlertCircle
                      size={18}
                      className='flex-shrink-0 text-red-500 mt-0.5'
                    />
                    <div className='flex-1 min-w-0'>
                      <p className='text-sm font-medium text-red-700'>
                        Export Failed
                      </p>
                      <p className='text-sm text-red-600 mt-1'>{exportError}</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Export Success */}
              {exportSuccess && (
                <div className='rounded-lg border border-green-500/50 bg-green-500/10 p-4'>
                  <div className='flex items-center gap-3'>
                    <CheckCircle
                      size={18}
                      className='flex-shrink-0 text-green-500'
                    />
                    <div>
                      <p className='text-sm font-medium text-green-700'>
                        Export Complete!
                      </p>
                      <p className='text-sm text-green-600 mt-1'>
                        Your photos will download shortly.
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Export Status */}
              {isExporting ? (
                <div className='space-y-4'>
                  <div className='text-center' role='status' aria-live='polite'>
                    {exportSuccess ? (
                      <div className='text-4xl mb-2' aria-hidden='true'>
                        ✓
                      </div>
                    ) : (
                      <div
                        className='w-10 h-10 mx-auto mb-3 border-[3px] border-primary/30 border-t-primary rounded-full animate-spin'
                        aria-hidden='true'
                      />
                    )}
                    <div className='text-sm font-medium text-foreground'>
                      {exportSuccess ? 'Export complete!' : 'Preparing your zip…'}
                    </div>
                    <div className='text-xs text-muted-foreground mt-1'>
                      {exportSuccess
                        ? 'Download started'
                        : 'Large exports can take a little while'}
                    </div>
                  </div>
                </div>
              ) : (
                <button
                  onClick={handleExport}
                  disabled={
                    isCreatingShare || photoPaths.length === 0 || isExporting
                  }
                  className='btn-glass btn-glass--primary w-full text-sm py-3 flex items-center justify-center gap-2'
                >
                  <Download size={16} />
                  Export {photoPaths.length} Photo
                  {photoPaths.length !== 1 ? 's' : ''}
                </button>
              )}
            </div>
          ) : (
            <div className='space-y-6'>
              {/* Share Error */}
              {shareError && (
                <div className='rounded-lg border border-red-500/50 bg-red-500/10 p-4'>
                  <div className='flex items-start gap-3'>
                    <AlertCircle
                      size={18}
                      className='flex-shrink-0 text-red-500 mt-0.5'
                    />
                    <div className='flex-1 min-w-0'>
                      <p className='text-sm font-medium text-red-700'>
                        Failed to Create Share Link
                      </p>
                      <p className='text-sm text-red-600 mt-1'>{shareError}</p>
                    </div>
                  </div>
                </div>
              )}

              <div>
                <h4 className='font-medium text-foreground mb-3'>
                  Share Options
                </h4>

                <div className='space-y-4'>
                  <div>
                    <label htmlFor='ed-link-expiration' className='block text-sm font-medium text-foreground mb-2'>
                      Link Expiration
                    </label>
                    <select
                      id='ed-link-expiration'
                      value={expirationHours}
                      onChange={(e) =>
                        setExpirationHours(parseInt(e.target.value))
                      }
                      className='w-full px-3 py-2 rounded-lg border border-white/10 bg-white/5 text-foreground'
                    >
                      <option value={1}>1 hour</option>
                      <option value={6}>6 hours</option>
                      <option value={24}>24 hours (1 day)</option>
                      <option value={168}>168 hours (1 week)</option>
                      <option value={720}>720 hours (1 month)</option>
                    </select>
                  </div>

                  <div>
                    <label className='flex items-center gap-3'>
                      <input
                        type='checkbox'
                        checked={usePassword}
                        onChange={(e) => setUsePassword(e.target.checked)}
                        className='w-4 h-4 rounded border-white/10 bg-white/5 text-primary'
                      />
                      <div className='font-medium text-foreground'>
                        Add Password Protection
                        <div className='font-normal text-xs text-muted-foreground'>
                          Require password to access shared photos
                        </div>
                      </div>
                    </label>

                    {usePassword && (
                      <div className='mt-2 flex items-center gap-2'>
                        <div className='relative flex-1'>
                          <input
                            type={showPassword ? 'text' : 'password'}
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder='Enter password'
                            className='w-full px-3 py-2 pr-10 rounded-lg border border-white/10 bg-white/5 text-foreground'
                          />
                          <button
                            type='button'
                            onClick={() => setShowPassword(!showPassword)}
                            className='absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground'
                          >
                            {showPassword ? (
                              <Eye size={16} />
                            ) : (
                              <Lock size={16} />
                            )}
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {shareLink ? (
                <div className='space-y-4'>
                  <div>
                    <div className='text-sm font-medium text-foreground mb-1'>
                      Share Link
                    </div>
                    <div className='relative'>
                      <input
                        type='text'
                        value={shareLink.share_url}
                        readOnly
                        className='w-full px-3 py-2 pr-10 rounded-lg border border-white/10 bg-white/5 text-foreground'
                      />
                      <button
                        onClick={copyShareLink}
                        className='absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground'
                      >
                        {copied ? <Check size={16} /> : <Copy size={16} />}
                      </button>
                    </div>
                  </div>

                  <div className='text-xs text-muted-foreground'>
                    <div className='flex items-center gap-1'>
                      <Calendar size={12} />
                      Expires: {new Date(shareLink.expiration).toLocaleString()}
                    </div>
                  </div>

                  <div className='flex gap-2'>
                    <button
                      onClick={copyShareLink}
                      className='btn-glass btn-glass--primary flex-1 text-sm py-2 flex items-center justify-center gap-2'
                    >
                      <Copy size={14} />
                      {copied ? 'Copied!' : 'Copy Link'}
                    </button>
                    <button
                      onClick={() => {
                        setShareLink(null);
                        setPassword('');
                      }}
                      className='btn-glass btn-glass--muted text-sm py-2 px-4'
                    >
                      Create New
                    </button>
                  </div>
                </div>
              ) : (
                <button
                  onClick={createShareLink}
                  disabled={isCreatingShare || photoPaths.length === 0}
                  className='btn-glass btn-glass--primary w-full text-sm py-3 flex items-center justify-center gap-2'
                >
                  {isCreatingShare ? (
                    <div className='w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin' />
                  ) : (
                    <>
                      <Link size={16} />
                      Create Share Link
                    </>
                  )}
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
