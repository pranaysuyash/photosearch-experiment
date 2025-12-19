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
  Unlock,
  Check
} from 'lucide-react';
import { api } from '../api';
import { glass } from '../design/glass';

interface ExportDialogProps {
  isOpen: boolean;
  onClose: () => void;
  photoPaths: string[];
}

interface ExportPreset {
  id: string;
  name: string;
  description: string;
  options: any;
}

interface ShareLink {
  share_id: string;
  share_url: string;
  expiration: string;
}

export function ExportDialog({ isOpen, onClose, photoPaths }: ExportDialogProps) {
  const [activeTab, setActiveTab] = useState<'export' | 'share'>('export');
  const [presets, setPresets] = useState<ExportPreset[]>([]);
  const [selectedPreset, setSelectedPreset] = useState<string>('');
  const [includeMetadata, setIncludeMetadata] = useState(true);
  const [includeThumbnails, setIncludeThumbnails] = useState(false);
  const [maxResolution, setMaxResolution] = useState<number | null>(null);
  const [isExporting, setIsExporting] = useState(false);
  const [exportProgress, setExportProgress] = useState(0);
  const [shareLink, setShareLink] = useState<ShareLink | null>(null);
  const [isCreatingShare, setIsCreatingShare] = useState(false);
  const [expirationHours, setExpirationHours] = useState(24);
  const [password, setPassword] = useState('');
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
            max_resolution: null
          }
        }
      ]);
    }
  };

  const handlePresetChange = (presetId: string) => {
    setSelectedPreset(presetId);
    const preset = presets.find(p => p.id === presetId);
    if (preset) {
      setIncludeMetadata(preset.options.include_metadata);
      setIncludeThumbnails(preset.options.include_thumbnails);
      setMaxResolution(preset.options.max_resolution);
    }
  };

  const handleExport = async () => {
    if (photoPaths.length === 0) return;

    setIsExporting(true);
    setExportProgress(0); // Reset progress

    try {
      // Simulate progress
      for (let i = 0; i <= 100; i += 10) {
        setExportProgress(i);
        await new Promise(resolve => setTimeout(resolve, 100));
      }

      // Prepare export options
      const exportOptions = {
        format: 'zip',
        include_metadata: includeMetadata,
        include_thumbnails: includeThumbnails,
        max_resolution: maxResolution,
        rename_pattern: null,
        password_protect: false,
        password: null
      };

      // Actually perform the export
      await api.exportPhotos(photoPaths, exportOptions);

      // Reset and close after successful export
      setExportProgress(100);
      setTimeout(() => {
        setIsExporting(false);
        setExportProgress(0);
        onClose();
      }, 1000);
    } catch (error) {
      console.error('Export failed:', error);
      setIsExporting(false);
      setExportProgress(0);
    }
  };

  const createShareLink = async () => {
    if (photoPaths.length === 0) return;

    setIsCreatingShare(true);
    try {
      const result = await api.createShareLink(
        photoPaths,
        expirationHours,
        password || undefined
      );
      setShareLink(result);
    } catch (error) {
      console.error('Failed to create share link:', error);
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

  if (!isOpen) return null;

  const selectedPresetData = presets.find(p => p.id === selectedPreset);

  return (
    <div className="fixed inset-0 z-[1400] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={onClose} />

      <div className={`relative w-full max-w-2xl ${glass.surface} ${glass.surfaceStrong} rounded-2xl border border-white/10 shadow-2xl overflow-hidden`}>
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/10">
          <div className="flex items-center gap-3">
            <h3 className="text-xl font-semibold text-foreground">
              {activeTab === 'export' ? 'Export Photos' : 'Share Photos'}
            </h3>
            <span className="text-xs text-muted-foreground bg-white/10 px-2 py-1 rounded-full">
              {photoPaths.length} selected
            </span>
          </div>
          <button
            onClick={onClose}
            className="btn-glass btn-glass--muted w-9 h-9 p-0 justify-center"
            aria-label="Close export dialog"
          >
            <X size={16} />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-white/10">
          <button
            className={`flex-1 py-3 text-center text-sm font-medium ${
              activeTab === 'export'
                ? 'text-foreground border-b-2 border-primary'
                : 'text-muted-foreground hover:text-foreground'
            }`}
            onClick={() => setActiveTab('export')}
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
          >
            Share
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {activeTab === 'export' ? (
            <div className="space-y-6">
              <div>
                <h4 className="font-medium text-foreground mb-3">Export Options</h4>
                
                {/* Preset Selection */}
                <div className="mb-4">
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Export Preset
                  </label>
                  <select
                    value={selectedPreset}
                    onChange={(e) => handlePresetChange(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-white/10 bg-white/5 text-foreground"
                  >
                    {presets.map(preset => (
                      <option key={preset.id} value={preset.id}>
                        {preset.name} - {preset.description}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Options */}
                <div className="space-y-3">
                  <label className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      checked={includeMetadata}
                      onChange={(e) => setIncludeMetadata(e.target.checked)}
                      className="w-4 h-4 rounded border-white/10 bg-white/5 text-primary"
                    />
                    <div>
                      <div className="font-medium text-foreground">Include metadata</div>
                      <div className="text-xs text-muted-foreground">Include JSON files with photo information</div>
                    </div>
                  </label>

                  <label className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      checked={includeThumbnails}
                      onChange={(e) => setIncludeThumbnails(e.target.checked)}
                      className="w-4 h-4 rounded border-white/10 bg-white/5 text-primary"
                    />
                    <div>
                      <div className="font-medium text-foreground">Include thumbnails</div>
                      <div className="text-xs text-muted-foreground">Include small preview images</div>
                    </div>
                  </label>

                  <div>
                    <label className="block text-sm font-medium text-foreground mb-2">
                      Max Resolution (pixels)
                    </label>
                    <select
                      value={maxResolution || ''}
                      onChange={(e) => setMaxResolution(e.target.value ? parseInt(e.target.value) : null)}
                      className="w-full px-3 py-2 rounded-lg border border-white/10 bg-white/5 text-foreground"
                    >
                      <option value="">Original size</option>
                      <option value="800">800px</option>
                      <option value="1200">1200px</option>
                      <option value="1920">1920px</option>
                      <option value="2560">2560px</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* Export Status */}
              {isExporting ? (
                <div className="space-y-4">
                  <div className="text-center">
                    <div className="text-4xl font-bold text-foreground mb-2">
                      {exportProgress}%
                    </div>
                    <div className="text-sm text-muted-foreground">
                      Exporting your photos...
                    </div>
                  </div>

                  <div className="w-full bg-white/10 rounded-full h-3">
                    <div
                      className="bg-primary h-3 rounded-full transition-all duration-300"
                      style={{ width: `${exportProgress}%` }}
                    />
                  </div>
                </div>
              ) : (
                <button
                  onClick={handleExport}
                  disabled={isCreatingShare || photoPaths.length === 0}
                  className="btn-glass btn-glass--primary w-full text-sm py-3 flex items-center justify-center gap-2"
                >
                  <Download size={16} />
                  Export {photoPaths.length} Photos
                </button>
              )}
            </div>
          ) : (
            <div className="space-y-6">
              <div>
                <h4 className="font-medium text-foreground mb-3">Share Options</h4>
                
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-2">
                      Link Expiration
                    </label>
                    <select
                      value={expirationHours}
                      onChange={(e) => setExpirationHours(parseInt(e.target.value))}
                      className="w-full px-3 py-2 rounded-lg border border-white/10 bg-white/5 text-foreground"
                    >
                      <option value={1}>1 hour</option>
                      <option value={6}>6 hours</option>
                      <option value={24}>24 hours (1 day)</option>
                      <option value={168}>168 hours (1 week)</option>
                      <option value={720}>720 hours (1 month)</option>
                    </select>
                  </div>

                  <div>
                    <label className="flex items-center gap-3">
                      <input
                        type="checkbox"
                        checked={!!password}
                        onChange={(e) => setPassword(e.target.checked ? '' : '')}
                        className="w-4 h-4 rounded border-white/10 bg-white/5 text-primary"
                      />
                      <div>
                        <div className="font-medium text-foreground">Add Password Protection</div>
                        <div className="text-xs text-muted-foreground">Require password to access shared photos</div>
                      </div>
                    </label>

                    {password !== undefined && (
                      <div className="mt-2 flex items-center gap-2">
                        <div className="relative flex-1">
                          <input
                            type={showPassword ? "text" : "password"}
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="Enter password"
                            className="w-full px-3 py-2 pr-10 rounded-lg border border-white/10 bg-white/5 text-foreground"
                          />
                          <button
                            type="button"
                            onClick={() => setShowPassword(!showPassword)}
                            className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                          >
                            {showPassword ? <Eye size={16} /> : <Lock size={16} />}
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {shareLink ? (
                <div className="space-y-4">
                  <div>
                    <div className="text-sm font-medium text-foreground mb-1">Share Link</div>
                    <div className="relative">
                      <input
                        type="text"
                        value={shareLink.share_url}
                        readOnly
                        className="w-full px-3 py-2 pr-10 rounded-lg border border-white/10 bg-white/5 text-foreground"
                      />
                      <button
                        onClick={copyShareLink}
                        className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                      >
                        {copied ? <Check size={16} /> : <Copy size={16} />}
                      </button>
                    </div>
                  </div>

                  <div className="text-xs text-muted-foreground">
                    <div className="flex items-center gap-1">
                      <Calendar size={12} />
                      Expires: {new Date(shareLink.expiration).toLocaleString()}
                    </div>
                  </div>

                  <div className="flex gap-2">
                    <button
                      onClick={copyShareLink}
                      className="btn-glass btn-glass--primary flex-1 text-sm py-2 flex items-center justify-center gap-2"
                    >
                      <Copy size={14} />
                      {copied ? 'Copied!' : 'Copy Link'}
                    </button>
                    <button
                      onClick={() => {
                        setShareLink(null);
                        setPassword('');
                      }}
                      className="btn-glass btn-glass--muted text-sm py-2 px-4"
                    >
                      Create New
                    </button>
                  </div>
                </div>
              ) : (
                <button
                  onClick={createShareLink}
                  disabled={isCreatingShare || photoPaths.length === 0}
                  className="btn-glass btn-glass--primary w-full text-sm py-3 flex items-center justify-center gap-2"
                >
                  {isCreatingShare ? (
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
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