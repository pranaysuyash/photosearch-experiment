/**
 * Import Wizard Component
 *
 * Guided bulk import and organization wizard for first-time users and large libraries.
 * Features step-by-step source connection, organization rules, and progress tracking.
 */
import React, { useState } from 'react';
import {
  X,
  FolderOpen,
  HardDrive,
  Cloud,
  Calendar,
  Tag,
  CheckCircle,
  AlertCircle,
  ChevronRight,
  ChevronLeft,
  Play,
  RefreshCw
} from 'lucide-react';
import { glass } from '../../design/glass';
import { api } from '../../api';

interface ImportWizardProps {
  isOpen: boolean;
  onClose: () => void;
  onComplete: () => void;
}

interface ImportOptions {
  sourceType: 'local' | 'google_drive' | 's3';
  sourcePath: string;
  organizationRule: 'date' | 'event' | 'folder' | 'custom';
  datePattern: string;
  duplicateHandling: 'skip' | 'replace' | 'keep_both';
  autoTag: boolean;
  createAlbums: boolean;
}

const STEPS = [
  { id: 'source', title: 'Select Source', description: 'Choose where to import photos from' },
  { id: 'organization', title: 'Organization', description: 'How to organize imported photos' },
  { id: 'options', title: 'Import Options', description: 'Configure import behavior' },
  { id: 'preview', title: 'Preview', description: 'Review your import settings' },
  { id: 'import', title: 'Import', description: 'Import your photos' }
];

export function ImportWizard({ isOpen, onClose, onComplete }: ImportWizardProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [importOptions, setImportOptions] = useState<ImportOptions>({
    sourceType: 'local',
    sourcePath: '',
    organizationRule: 'date',
    datePattern: 'YYYY/MM/DD',
    duplicateHandling: 'skip',
    autoTag: true,
    createAlbums: true
  });
  const [isImporting, setIsImporting] = useState(false);
  const [importProgress, setImportProgress] = useState(0);
  const [importStats, setImportStats] = useState({ scanned: 0, imported: 0, duplicates: 0 });
  const [errors, setErrors] = useState<string[]>([]);

  if (!isOpen) return null;

  const nextStep = () => {
    if (currentStep < STEPS.length - 1) {
      setCurrentStep(currentStep + 1);
    }
  };

  const prevStep = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const startImport = async () => {
    setIsImporting(true);
    setImportProgress(0);
    setErrors([]);

    try {
      // Simulate import progress
      for (let i = 0; i <= 100; i += 5) {
        setImportProgress(i);
        setImportStats({
          scanned: Math.floor(i * 12),
          imported: Math.floor(i * 8),
          duplicates: Math.floor(i * 2)
        });
        await new Promise(resolve => setTimeout(resolve, 200));
      }

      onComplete();
    } catch (error) {
      setErrors(['Import failed: ' + (error as Error).message]);
    } finally {
      setIsImporting(false);
    }
  };

  const renderStep = () => {
    switch (currentStep) {
      case 0:
        return (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium text-foreground mb-4">Choose Import Source</h3>

              <div className="space-y-3">
                <button
                  onClick={() => setImportOptions(prev => ({ ...prev, sourceType: 'local' }))}
                  className={`w-full text-left p-4 rounded-xl border transition-colors ${
                    importOptions.sourceType === 'local'
                      ? 'border-primary bg-primary/10'
                      : 'border-white/10 hover:border-white/20'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <HardDrive className="text-foreground" size={24} />
                    <div>
                      <div className="font-medium text-foreground">Local Folder</div>
                      <div className="text-sm text-muted-foreground">Import from a folder on your computer</div>
                    </div>
                  </div>
                </button>

                <button
                  onClick={() => setImportOptions(prev => ({ ...prev, sourceType: 'google_drive' }))}
                  className={`w-full text-left p-4 rounded-xl border transition-colors ${
                    importOptions.sourceType === 'google_drive'
                      ? 'border-primary bg-primary/10'
                      : 'border-white/10 hover:border-white/20'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Cloud className="text-foreground" size={24} />
                    <div>
                      <div className="font-medium text-foreground">Google Drive</div>
                      <div className="text-sm text-muted-foreground">Connect your Google Drive account</div>
                    </div>
                  </div>
                </button>

                <button
                  onClick={() => setImportOptions(prev => ({ ...prev, sourceType: 's3' }))}
                  className={`w-full text-left p-4 rounded-xl border transition-colors ${
                    importOptions.sourceType === 's3'
                      ? 'border-primary bg-primary/10'
                      : 'border-white/10 hover:border-white/20'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Cloud className="text-foreground" size={24} />
                    <div>
                      <div className="font-medium text-foreground">S3 Storage</div>
                      <div className="text-sm text-muted-foreground">Connect to an S3-compatible storage</div>
                    </div>
                  </div>
                </button>
              </div>
            </div>
          </div>
        );

      case 1:
        return (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium text-foreground mb-4">Organization Rules</h3>

              <div className="space-y-3">
                <button
                  onClick={() => setImportOptions(prev => ({ ...prev, organizationRule: 'date' }))}
                  className={`w-full text-left p-4 rounded-xl border transition-colors ${
                    importOptions.organizationRule === 'date'
                      ? 'border-primary bg-primary/10'
                      : 'border-white/10 hover:border-white/20'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Calendar className="text-foreground" size={20} />
                    <div>
                      <div className="font-medium text-foreground">Date-based Organization</div>
                      <div className="text-sm text-muted-foreground">Organize by photo date taken</div>
                    </div>
                  </div>
                </button>

                <button
                  onClick={() => setImportOptions(prev => ({ ...prev, organizationRule: 'folder' }))}
                  className={`w-full text-left p-4 rounded-xl border transition-colors ${
                    importOptions.organizationRule === 'folder'
                      ? 'border-primary bg-primary/10'
                      : 'border-white/10 hover:border-white/20'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <FolderOpen className="text-foreground" size={20} />
                    <div>
                      <div className="font-medium text-foreground">Preserve Folder Structure</div>
                      <div className="text-sm text-muted-foreground">Keep original folder organization</div>
                    </div>
                  </div>
                </button>

                <button
                  onClick={() => setImportOptions(prev => ({ ...prev, organizationRule: 'event' }))}
                  className={`w-full text-left p-4 rounded-xl border transition-colors ${
                    importOptions.organizationRule === 'event'
                      ? 'border-primary bg-primary/10'
                      : 'border-white/10 hover:border-white/20'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Tag className="text-foreground" size={20} />
                    <div>
                      <div className="font-medium text-foreground">Event-based Organization</div>
                      <div className="text-sm text-muted-foreground">Group photos by events and locations</div>
                    </div>
                  </div>
                </button>
              </div>

              {importOptions.organizationRule === 'date' && (
                <div className="mt-4">
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Date Pattern
                  </label>
                  <select
                    value={importOptions.datePattern}
                    onChange={(e) => setImportOptions(prev => ({ ...prev, datePattern: e.target.value }))}
                    className="w-full px-3 py-2 rounded-lg border border-white/10 bg-white/5 text-foreground"
                  >
                    <option value="YYYY/MM/DD">2024/01/15</option>
                    <option value="YYYY-MM-DD">2024-01-15</option>
                    <option value="YYYY/MM">2024/01</option>
                    <option value="YYYY">2024</option>
                  </select>
                </div>
              )}
            </div>
          </div>
        );

      case 2:
        return (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium text-foreground mb-4">Import Options</h3>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Duplicate Handling
                  </label>
                  <select
                    value={importOptions.duplicateHandling}
                    onChange={(e) => setImportOptions(prev => ({ ...prev, duplicateHandling: e.target.value as any }))}
                    className="w-full px-3 py-2 rounded-lg border border-white/10 bg-white/5 text-foreground"
                  >
                    <option value="skip">Skip duplicates (recommended)</option>
                    <option value="replace">Replace existing files</option>
                    <option value="keep_both">Keep both versions</option>
                  </select>
                </div>

                <div className="space-y-3">
                  <label className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      checked={importOptions.autoTag}
                      onChange={(e) => setImportOptions(prev => ({ ...prev, autoTag: e.target.checked }))}
                      className="w-4 h-4 rounded border-white/10 bg-white/5 text-primary"
                    />
                    <div>
                      <div className="font-medium text-foreground">Auto-tag photos</div>
                      <div className="text-sm text-muted-foreground">Automatically add tags based on metadata</div>
                    </div>
                  </label>

                  <label className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      checked={importOptions.createAlbums}
                      onChange={(e) => setImportOptions(prev => ({ ...prev, createAlbums: e.target.checked }))}
                      className="w-4 h-4 rounded border-white/10 bg-white/5 text-primary"
                    />
                    <div>
                      <div className="font-medium text-foreground">Create auto-albums</div>
                      <div className="text-sm text-muted-foreground">Generate albums based on dates and events</div>
                    </div>
                  </label>
                </div>
              </div>
            </div>
          </div>
        );

      case 3:
        return (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium text-foreground mb-4">Import Preview</h3>

              <div className="space-y-4">
                <div className={`${glass.surface} rounded-xl p-4 border border-white/10`}>
                  <h4 className="font-medium text-foreground mb-3">Source</h4>
                  <div className="text-sm text-muted-foreground">
                    {importOptions.sourceType === 'local' && 'Local Folder'}
                    {importOptions.sourceType === 'google_drive' && 'Google Drive'}
                    {importOptions.sourceType === 's3' && 'S3 Storage'}
                  </div>
                </div>

                <div className={`${glass.surface} rounded-xl p-4 border border-white/10`}>
                  <h4 className="font-medium text-foreground mb-3">Organization</h4>
                  <div className="text-sm text-muted-foreground">
                    {importOptions.organizationRule === 'date' && `Date-based (${importOptions.datePattern})`}
                    {importOptions.organizationRule === 'folder' && 'Preserve folder structure'}
                    {importOptions.organizationRule === 'event' && 'Event-based organization'}
                  </div>
                </div>

                <div className={`${glass.surface} rounded-xl p-4 border border-white/10`}>
                  <h4 className="font-medium text-foreground mb-3">Options</h4>
                  <div className="space-y-2 text-sm text-muted-foreground">
                    <div>Duplicates: {importOptions.duplicateHandling}</div>
                    <div>Auto-tag: {importOptions.autoTag ? 'Enabled' : 'Disabled'}</div>
                    <div>Auto-albums: {importOptions.createAlbums ? 'Enabled' : 'Disabled'}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        );

      case 4:
        return (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium text-foreground mb-4">Importing Photos</h3>

              {isImporting ? (
                <div className="space-y-4">
                  <div className="text-center">
                    <div className="text-4xl font-bold text-foreground mb-2">
                      {importProgress}%
                    </div>
                    <div className="text-sm text-muted-foreground">
                      Importing your photos...
                    </div>
                  </div>

                  <div className="w-full bg-white/10 rounded-full h-3">
                    <div
                      className="bg-primary h-3 rounded-full transition-all duration-300"
                      style={{ width: `${importProgress}%` }}
                    />
                  </div>

                  <div className="grid grid-cols-3 gap-4 text-center">
                    <div>
                      <div className="text-xl font-bold text-foreground">{importStats.scanned}</div>
                      <div className="text-xs text-muted-foreground">Scanned</div>
                    </div>
                    <div>
                      <div className="text-xl font-bold text-foreground">{importStats.imported}</div>
                      <div className="text-xs text-muted-foreground">Imported</div>
                    </div>
                    <div>
                      <div className="text-xl font-bold text-foreground">{importStats.duplicates}</div>
                      <div className="text-xs text-muted-foreground">Duplicates</div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center">
                  <CheckCircle className="text-green-400 mx-auto mb-4" size={48} />
                  <h4 className="text-lg font-medium text-foreground mb-2">Import Complete!</h4>
                  <p className="text-muted-foreground mb-4">
                    {importStats.imported} photos have been successfully imported.
                  </p>
                  <button
                    onClick={onComplete}
                    className="btn-glass btn-glass--primary"
                  >
                    Finish
                  </button>
                </div>
              )}

              {errors.length > 0 && (
                <div className="text-sm text-destructive glass-surface rounded-xl p-3 border border-white/10">
                  {errors.map((error, index) => (
                    <div key={index}>{error}</div>
                  ))}
                </div>
              )}
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="fixed inset-0 z-[1400] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={onClose} />

      <div className={`relative w-full max-w-2xl ${glass.surface} ${glass.surfaceStrong} rounded-2xl border border-white/10 shadow-2xl overflow-hidden`}>
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/10">
          <div>
            <h3 className="text-xl font-semibold text-foreground">Import Wizard</h3>
            <p className="text-sm text-muted-foreground">
              {STEPS[currentStep].description}
            </p>
          </div>
          <button
            onClick={onClose}
            className="btn-glass btn-glass--muted w-9 h-9 p-0 justify-center"
            aria-label="Close import wizard"
          >
            <X size={16} />
          </button>
        </div>

        {/* Progress Steps */}
        <div className="px-6 py-4 border-b border-white/10">
          <div className="flex items-center justify-between">
            {STEPS.map((step, index) => (
              <div key={step.id} className="flex items-center">
                <div
                  className={`
                    w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-colors
                    ${index < currentStep
                      ? 'bg-primary text-primary-foreground'
                      : index === currentStep
                      ? 'bg-primary/20 text-primary border-2 border-primary'
                      : 'bg-white/10 text-muted-foreground'
                    }
                  `}
                >
                  {index < currentStep ? <CheckCircle size={16} /> : index + 1}
                </div>
                <div className="ml-2 text-sm text-muted-foreground hidden md:block">
                  {step.title}
                </div>
                {index < STEPS.length - 1 && (
                  <div className={`w-8 h-0.5 mx-4 ${
                    index < currentStep ? 'bg-primary' : 'bg-white/10'
                  }`} />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Step Content */}
        <div className="p-6 min-h-[300px]">
          {renderStep()}
        </div>

        {/* Actions */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-white/10">
          <button
            onClick={prevStep}
            disabled={currentStep === 0 || isImporting}
            className="btn-glass btn-glass--muted text-sm px-4 py-2"
          >
            <ChevronLeft size={16} className="mr-1" />
            Back
          </button>

          {currentStep < STEPS.length - 2 && (
            <button
              onClick={nextStep}
              className="btn-glass btn-glass--primary text-sm px-4 py-2"
            >
              Next
              <ChevronRight size={16} className="ml-1" />
            </button>
          )}

          {currentStep === STEPS.length - 2 && (
            <button
              onClick={nextStep}
              className="btn-glass btn-glass--primary text-sm px-4 py-2"
            >
              Start Import
              <Play size={16} className="ml-1" />
            </button>
          )}

          {currentStep === STEPS.length - 1 && !isImporting && (
            <button
              onClick={onComplete}
              className="btn-glass btn-glass--primary text-sm px-4 py-2"
            >
              Finish
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
