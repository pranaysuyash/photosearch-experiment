/**
 * Import Page
 *
 * Dedicated page for photo importing with wizard and quick import options.
 */
import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Download,
  FolderOpen,
  Cloud,
  HardDrive,
  Users,
  Zap,
  Plus
} from 'lucide-react';
import { ImportWizard } from '../components/import/ImportWizard';
import { glass } from '../design/glass';

export function Import() {
  const [showWizard, setShowWizard] = useState(false);

  const quickSources = [
    {
      icon: HardDrive,
      title: 'Local Folder',
      description: 'Import photos from a folder on your computer',
      action: 'Browse'
    },
    {
      icon: Cloud,
      title: 'Google Drive',
      description: 'Connect your Google Drive account',
      action: 'Connect'
    },
    {
      icon: Cloud,
      title: 'S3 Storage',
      description: 'Import from S3-compatible storage',
      action: 'Configure'
    }
  ];

  const features = [
    {
      icon: Zap,
      title: 'Smart Organization',
      description: 'Automatically organize by date, events, or preserve folders'
    },
    {
      icon: Users,
      title: 'Face Recognition',
      description: 'Detect and group faces automatically during import'
    },
    {
      icon: Download,
      title: 'Duplicate Detection',
      description: 'Skip or handle duplicates intelligently'
    }
  ];

  return (
    <div className="min-h-screen">
      {/* Header */}
      <div className="border-b border-white/10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center gap-3">
            <Download className="text-foreground" size={28} />
            <div>
              <h1 className="text-2xl font-bold text-foreground">Import Photos</h1>
              <p className="text-sm text-muted-foreground">
                Add photos to your library from various sources
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Main Import Button */}
        <div className="text-center mb-12">
          <div className="inline-flex flex-col items-center">
            <button
              onClick={() => setShowWizard(true)}
              className="btn-glass btn-glass--primary text-lg px-8 py-4 mb-4"
            >
              <Plus size={20} className="mr-2" />
              Start Import Wizard
            </button>
            <p className="text-sm text-muted-foreground max-w-md">
              Guided import process with organization rules and duplicate handling
            </p>
          </div>
        </div>

        {/* Quick Import Options */}
        <div className="mb-12">
          <h2 className="text-lg font-medium text-foreground mb-6">Quick Import</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {quickSources.map((source, index) => (
              <div
                key={index}
                className={`${glass.surface} rounded-xl p-6 border border-white/10 hover:border-white/20 transition-colors cursor-pointer group`}
                onClick={() => setShowWizard(true)}
              >
                <div className="flex items-center gap-4 mb-4">
                  <div className="w-12 h-12 rounded-full bg-white/10 flex items-center justify-center group-hover:bg-white/20 transition-colors">
                    <source.icon className="text-foreground" size={20} />
                  </div>
                  <div>
                    <h3 className="font-medium text-foreground group-hover:text-primary transition-colors">
                      {source.title}
                    </h3>
                    <div className="text-sm text-primary">{source.action} →</div>
                  </div>
                </div>
                <p className="text-sm text-muted-foreground">
                  {source.description}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Features */}
        <div className="mb-12">
          <h2 className="text-lg font-medium text-foreground mb-6">Import Features</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {features.map((feature, index) => (
              <div
                key={index}
                className={`${glass.surface} rounded-xl p-6 border border-white/10`}
              >
                <div className="flex items-start gap-4">
                  <div className="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center flex-shrink-0">
                    <feature.icon className="text-primary" size={18} />
                  </div>
                  <div>
                    <h3 className="font-medium text-foreground mb-2">{feature.title}</h3>
                    <p className="text-sm text-muted-foreground">{feature.description}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Getting Started */}
        <div className={`${glass.surface} rounded-xl p-8 border border-white/10 text-center`}>
          <h2 className="text-lg font-medium text-foreground mb-4">New to Living Museum?</h2>
          <p className="text-muted-foreground mb-6 max-w-2xl mx-auto">
            Get started quickly with our import wizard. It will guide you through connecting your sources,
            setting up organization rules, and importing your first photos.
          </p>
          <div className="flex items-center justify-center gap-4">
            <button
              onClick={() => setShowWizard(true)}
              className="btn-glass btn-glass--primary"
            >
              <Plus size={16} className="mr-2" />
              Start Importing
            </button>
            <Link
              to="/settings"
              className="btn-glass btn-glass--muted"
            >
              Configure Sources
            </Link>
          </div>
        </div>
      </div>

      {/* Import Wizard Modal */}
      <ImportWizard
        isOpen={showWizard}
        onClose={() => setShowWizard(false)}
        onComplete={() => {
          setShowWizard(false);
          // Optionally redirect to library
          window.location.href = '/';
        }}
      />
    </div>
  );
}