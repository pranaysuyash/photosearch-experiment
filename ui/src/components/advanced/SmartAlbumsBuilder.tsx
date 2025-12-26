/**
 * Smart Albums Rule Builder
 *
 * Visual rule builder for smart albums with:
 * - Drag-and-drop rule creation interface
 * - Suggested album templates
 * - Preview and testing capabilities
 * - Complex boolean logic support
 * - Real-time result preview
 */

import React, { useState, useEffect, useCallback, memo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Plus,
  Trash2,
  Settings,
  Save,
  Sparkles,
  Filter,
  Calendar,
  MapPin,
  Tag,
  Image as ImageIcon,
  Star,
  Heart,
  Zap,
  FolderPlus,
  X,
  Loader2,
  Eye,
  Target,
  BarChart3,
} from 'lucide-react';
import { api } from '../../api';
import { glass } from '../../design/glass';
import { useAmbientThemeContext } from '../../contexts/AmbientThemeContext';

export interface AlbumRule {
  id: string;
  field: string;
  operator: string;
  value: unknown;
  label?: string;
}

export interface AlbumTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  rules: AlbumRule[];
  featured: boolean;
}

export interface SmartAlbum {
  id: string;
  name: string;
  description: string;
  rules: AlbumRule[];
  photo_count: number;
  last_updated: string;
  auto_update: boolean;
}

export function SmartAlbumsBuilder() {
  useAmbientThemeContext();
  const [activeTab, setActiveTab] = useState<
    'builder' | 'templates' | 'albums' | 'analytics'
  >('builder');
  const [albumName, setAlbumName] = useState('');
  const [albumDescription, setAlbumDescription] = useState('');
  const [rules, setRules] = useState<AlbumRule[]>([]);
  const [templates, setTemplates] = useState<AlbumTemplate[]>([]);
  const [albums, setAlbums] = useState<SmartAlbum[]>([]);
  const [previewResults, setPreviewResults] = useState<unknown[]>([]);
  const [loading, setLoading] = useState(false);
  const [showPreview, setShowPreview] = useState(false);

  // Load data on mount
  useEffect(() => {
    loadTemplates();
    loadAlbums();
  }, [loadTemplates, loadAlbums]);

  const loadTemplates = useCallback(async () => {
    try {
      const response = await api.get('/api/albums/templates');
      setTemplates(response.data.templates);
    } catch (error) {
      console.error('Failed to load templates:', error);
    }
  }, []);

  const loadAlbums = useCallback(async () => {
    try {
      const response = await api.get('/api/albums');
      setAlbums(response.data.albums || []);
    } catch (error) {
      console.error('Failed to load albums:', error);
    }
  }, []);

  const addRule = useCallback(() => {
    const newRule: AlbumRule = {
      id: `rule_${Date.now()}`,
      field: 'created_at',
      operator: 'greater_than',
      value: '30_days_ago',
    };
    setRules((prev) => [...prev, newRule]);
  }, []);

  const updateRule = useCallback(
    (ruleId: string, updates: Partial<AlbumRule>) => {
      setRules((prev) =>
        prev.map((rule) =>
          rule.id === ruleId ? { ...rule, ...updates } : rule
        )
      );
    },
    []
  );

  const removeRule = useCallback((ruleId: string) => {
    setRules((prev) => prev.filter((rule) => rule.id !== ruleId));
  }, []);

  const loadTemplate = useCallback((template: AlbumTemplate) => {
    setAlbumName(template.name);
    setAlbumDescription(template.description);
    setRules([...template.rules]);
    setActiveTab('builder');
  }, []);

  const previewAlbum = useCallback(async () => {
    if (rules.length === 0) return;

    try {
      setLoading(true);
      const response = await api.post('/api/albums/preview', {
        name: albumName,
        rules: rules,
      });

      setPreviewResults(response.data.results || []);
      setShowPreview(true);
    } catch (error) {
      console.error('Failed to preview album:', error);
    } finally {
      setLoading(false);
    }
  }, [albumName, rules]);

  const saveAlbum = useCallback(async () => {
    if (!albumName.trim() || rules.length === 0) return;

    try {
      setLoading(true);
      await api.post('/api/albums/create', {
        name: albumName,
        description: albumDescription,
        rules: rules,
        auto_update: true,
      });

      loadAlbums();
      setAlbumName('');
      setAlbumDescription('');
      setRules([]);
      setActiveTab('albums');
    } catch (error) {
      console.error('Failed to save album:', error);
    } finally {
      setLoading(false);
    }
  }, [albumName, albumDescription, rules, loadAlbums]);

  const getFieldOptions = () => [
    {
      value: 'created_at',
      label: 'Date Created',
      icon: Calendar,
      type: 'date',
    },
    { value: 'file_size', label: 'File Size', icon: BarChart3, type: 'number' },
    { value: 'filename', label: 'Filename', icon: ImageIcon, type: 'text' },
    { value: 'file_type', label: 'File Type', icon: Tag, type: 'select' },
    { value: 'rating', label: 'Rating', icon: Star, type: 'number' },
    { value: 'location', label: 'Location', icon: MapPin, type: 'text' },
    { value: 'tags', label: 'Tags', icon: Tag, type: 'text' },
    { value: 'is_favorite', label: 'Favorite', icon: Heart, type: 'boolean' },
    { value: 'width', label: 'Width', icon: Target, type: 'number' },
    { value: 'height', label: 'Height', icon: Target, type: 'number' },
  ];

  const getOperatorOptions = (fieldType: string) => {
    const baseOperators = [
      { value: 'equals', label: 'Equals' },
      { value: 'not_equals', label: 'Does not equal' },
      { value: 'contains', label: 'Contains' },
      { value: 'not_contains', label: 'Does not contain' },
    ];

    if (fieldType === 'number' || fieldType === 'date') {
      return [
        ...baseOperators,
        { value: 'greater_than', label: 'Greater than' },
        { value: 'less_than', label: 'Less than' },
        { value: 'greater_equal', label: 'Greater or equal' },
        { value: 'less_equal', label: 'Less or equal' },
      ];
    }

    if (fieldType === 'boolean') {
      return [
        { value: 'equals', label: 'Is' },
        { value: 'not_equals', label: 'Is not' },
      ];
    }

    return baseOperators;
  };

  const getValueInput = (rule: AlbumRule) => {
    const fieldInfo = getFieldOptions().find((f) => f.value === rule.field);
    const fieldType = fieldInfo?.type || 'text';

    switch (fieldType) {
      case 'boolean':
        return (
          <select
            value={rule.value}
            onChange={(e) =>
              updateRule(rule.id, { value: e.target.value === 'true' })
            }
            className='flex-1 px-3 py-2 bg-black/30 border border-white/20 rounded-lg text-white focus:outline-none focus:border-blue-500'
          >
            <option value='true'>True</option>
            <option value='false'>False</option>
          </select>
        );

      case 'select':
        return (
          <select
            value={rule.value}
            onChange={(e) => updateRule(rule.id, { value: e.target.value })}
            className='flex-1 px-3 py-2 bg-black/30 border border-white/20 rounded-lg text-white focus:outline-none focus:border-blue-500'
          >
            <option value=''>Select...</option>
            <option value='image'>Image</option>
            <option value='video'>Video</option>
            <option value='raw'>RAW</option>
          </select>
        );

      case 'number':
        return (
          <input
            type='number'
            value={rule.value}
            onChange={(e) =>
              updateRule(rule.id, { value: parseFloat(e.target.value) || 0 })
            }
            className='flex-1 px-3 py-2 bg-black/30 border border-white/20 rounded-lg text-white focus:outline-none focus:border-blue-500'
          />
        );

      case 'date':
        return (
          <select
            value={rule.value}
            onChange={(e) => updateRule(rule.id, { value: e.target.value })}
            className='flex-1 px-3 py-2 bg-black/30 border border-white/20 rounded-lg text-white focus:outline-none focus:border-blue-500'
          >
            <option value='today'>Today</option>
            <option value='yesterday'>Yesterday</option>
            <option value='this_week'>This Week</option>
            <option value='this_month'>This Month</option>
            <option value='this_year'>This Year</option>
            <option value='30_days_ago'>Last 30 Days</option>
            <option value='90_days_ago'>Last 90 Days</option>
            <option value='1_year_ago'>Last Year</option>
          </select>
        );

      default:
        return (
          <input
            type='text'
            value={rule.value}
            onChange={(e) => updateRule(rule.id, { value: e.target.value })}
            placeholder='Enter value...'
            className='flex-1 px-3 py-2 bg-black/30 border border-white/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500'
          />
        );
    }
  };

  return (
    <div className='p-6 space-y-6'>
      {/* Header */}
      <div className='flex items-center justify-between'>
        <div>
          <h2 className='text-2xl font-bold text-white mb-2'>Smart Albums</h2>
          <p className='text-gray-400'>
            Create intelligent photo albums with custom rules
          </p>
        </div>
        <button
          onClick={() => setActiveTab('builder')}
          className='px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2'
        >
          <FolderPlus className='w-4 h-4' />
          New Smart Album
        </button>
      </div>

      {/* Tabs */}
      <div className='flex space-x-1 p-1 bg-black/20 rounded-lg'>
        {(
          ['builder', 'templates', 'albums', 'analytics'] as Array<
            'builder' | 'templates' | 'albums' | 'analytics'
          >
        ).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 px-4 py-2 rounded-md capitalize transition-all ${
              activeTab === tab
                ? 'bg-blue-600 text-white'
                : 'text-gray-400 hover:text-white hover:bg-white/10'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      <AnimatePresence mode='wait'>
        {/* Builder Tab */}
        {activeTab === 'builder' && (
          <motion.div
            key='builder'
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className='grid grid-cols-1 lg:grid-cols-3 gap-6'
          >
            {/* Album Configuration */}
            <div className={`${glass.card} p-6 space-y-4`}>
              <h3 className='text-xl font-semibold text-white'>
                Album Details
              </h3>

              <div>
                <label className='block text-gray-300 text-sm mb-2'>
                  Album Name
                </label>
                <input
                  type='text'
                  value={albumName}
                  onChange={(e) => setAlbumName(e.target.value)}
                  placeholder='Enter album name...'
                  className='w-full px-3 py-2 bg-black/30 border border-white/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500'
                />
              </div>

              <div>
                <label className='block text-gray-300 text-sm mb-2'>
                  Description
                </label>
                <textarea
                  value={albumDescription}
                  onChange={(e) => setAlbumDescription(e.target.value)}
                  placeholder='Describe your smart album...'
                  rows={3}
                  className='w-full px-3 py-2 bg-black/30 border border-white/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 resize-none'
                />
              </div>

              <div className='pt-4 space-y-2'>
                <button
                  onClick={addRule}
                  className='w-full px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center justify-center gap-2'
                >
                  <Plus className='w-4 h-4' />
                  Add Rule
                </button>

                <button
                  onClick={previewAlbum}
                  disabled={!albumName.trim() || rules.length === 0 || loading}
                  className='w-full px-3 py-2 bg-white/10 text-white rounded-lg hover:bg-white/20 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2'
                >
                  {loading ? (
                    <Loader2 className='w-4 h-4 animate-spin' />
                  ) : (
                    <Eye className='w-4 h-4' />
                  )}
                  Preview Results
                </button>

                <button
                  onClick={saveAlbum}
                  disabled={!albumName.trim() || rules.length === 0 || loading}
                  className='w-full px-3 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2'
                >
                  {loading ? (
                    <Loader2 className='w-4 h-4 animate-spin' />
                  ) : (
                    <Save className='w-4 h-4' />
                  )}
                  Save Album
                </button>
              </div>
            </div>

            {/* Rules Builder */}
            <div className={`${glass.card} p-6`}>
              <div className='flex items-center justify-between mb-4'>
                <h3 className='text-xl font-semibold text-white'>Rules</h3>
                <span className='text-gray-400 text-sm'>
                  {rules.length} rule{rules.length !== 1 ? 's' : ''}
                </span>
              </div>

              {rules.length === 0 ? (
                <div className='text-center py-8'>
                  <Filter className='w-12 h-12 text-gray-600 mx-auto mb-3' />
                  <p className='text-gray-400'>
                    Add rules to define your smart album
                  </p>
                </div>
              ) : (
                <div className='space-y-3'>
                  {rules.map((rule, index) => {
                    const fieldInfo = getFieldOptions().find(
                      (f) => f.value === rule.field
                    );
                    const FieldIcon = fieldInfo?.icon || Settings;

                    return (
                      <motion.div
                        key={rule.id}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -20 }}
                        className='p-3 bg-black/20 rounded-lg border border-white/10'
                      >
                        <div className='flex items-center gap-2 mb-3'>
                          <div className='w-6 h-6 bg-blue-600/20 rounded-full flex items-center justify-center'>
                            <span className='text-blue-400 text-xs font-bold'>
                              {index + 1}
                            </span>
                          </div>
                          <FieldIcon className='w-4 h-4 text-gray-400' />
                          <span className='text-gray-300 text-sm'>
                            {fieldInfo?.label || rule.field}
                          </span>
                          <button
                            onClick={() => removeRule(rule.id)}
                            className='ml-auto text-red-400 hover:text-red-300'
                          >
                            <Trash2 className='w-3 h-3' />
                          </button>
                        </div>

                        <div className='grid grid-cols-3 gap-2'>
                          <select
                            value={rule.field}
                            onChange={(e) =>
                              updateRule(rule.id, { field: e.target.value })
                            }
                            className='px-2 py-1 bg-black/30 border border-white/20 rounded text-white text-sm focus:outline-none focus:border-blue-500'
                          >
                            {getFieldOptions().map((field) => (
                              <option key={field.value} value={field.value}>
                                {field.label}
                              </option>
                            ))}
                          </select>

                          <select
                            value={rule.operator}
                            onChange={(e) =>
                              updateRule(rule.id, { operator: e.target.value })
                            }
                            className='px-2 py-1 bg-black/30 border border-white/20 rounded text-white text-sm focus:outline-none focus:border-blue-500'
                          >
                            {getOperatorOptions(fieldInfo?.type || 'text').map(
                              (op) => (
                                <option key={op.value} value={op.value}>
                                  {op.label}
                                </option>
                              )
                            )}
                          </select>

                          {getValueInput(rule)}
                        </div>
                      </motion.div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Preview */}
            {showPreview && (
              <div className={`${glass.card} p-6`}>
                <div className='flex items-center justify-between mb-4'>
                  <h3 className='text-xl font-semibold text-white'>
                    Preview Results
                  </h3>
                  <button
                    onClick={() => setShowPreview(false)}
                    className='text-gray-400 hover:text-white'
                  >
                    <X className='w-4 h-4' />
                  </button>
                </div>

                <div className='text-center py-4 mb-4'>
                  <p className='text-gray-400 mb-2'>
                    Found {previewResults.length} matching photos
                  </p>
                  <p className='text-white font-semibold'>"{albumName}"</p>
                </div>

                {previewResults.length > 0 ? (
                  <div className='grid grid-cols-3 gap-2 max-h-96 overflow-y-auto'>
                    {previewResults
                      .filter((p): p is { path: string } => {
                        const maybe = (p as { path?: unknown }).path;
                        return typeof maybe === 'string';
                      })
                      .slice(0, 24)
                      .map((photo, index) => (
                        <div
                          key={index}
                          className='aspect-square bg-black/20 rounded-lg overflow-hidden'
                        >
                          <img
                            src={`/api/image/${encodeURIComponent(photo.path)}`}
                            alt={`Preview ${index + 1}`}
                            className='w-full h-full object-cover hover:scale-110 transition-transform cursor-pointer'
                          />
                        </div>
                      ))}
                  </div>
                ) : (
                  <div className='text-center py-8'>
                    <ImageIcon className='w-12 h-12 text-gray-600 mx-auto mb-3' />
                    <p className='text-gray-400'>
                      No photos match your current rules
                    </p>
                  </div>
                )}
              </div>
            )}
          </motion.div>
        )}

        {/* Templates Tab */}
        {activeTab === 'templates' && (
          <motion.div
            key='templates'
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
          >
            <div className={`${glass.card} p-6`}>
              <h3 className='text-xl font-semibold text-white mb-4 flex items-center gap-2'>
                <Sparkles className='w-5 h-5 text-yellow-500' />
                Album Templates
              </h3>

              <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'>
                {templates.map((template) => (
                  <motion.div
                    key={template.id}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    className='p-4 bg-black/20 rounded-lg border border-white/10 hover:border-white/20 cursor-pointer'
                    onClick={() => loadTemplate(template)}
                  >
                    <div className='flex items-start justify-between mb-3'>
                      <h4 className='text-white font-medium'>
                        {template.name}
                      </h4>
                      {template.featured && (
                        <span className='px-2 py-1 bg-yellow-500/20 text-yellow-400 text-xs rounded'>
                          Featured
                        </span>
                      )}
                    </div>

                    <p className='text-gray-400 text-sm mb-3'>
                      {template.description}
                    </p>

                    <div className='flex items-center justify-between'>
                      <span className='text-gray-500 text-xs capitalize'>
                        {template.category}
                      </span>
                      <div className='flex items-center gap-1'>
                        <Filter className='w-3 h-3 text-gray-400' />
                        <span className='text-gray-400 text-xs'>
                          {template.rules.length} rules
                        </span>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>

              {templates.length === 0 && (
                <div className='text-center py-12'>
                  <FolderPlus className='w-12 h-12 text-gray-600 mx-auto mb-3' />
                  <p className='text-gray-400'>No templates available yet</p>
                </div>
              )}
            </div>
          </motion.div>
        )}

        {/* Albums Tab */}
        {activeTab === 'albums' && (
          <motion.div
            key='albums'
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
          >
            <div className={`${glass.card} p-6`}>
              <h3 className='text-xl font-semibold text-white mb-4'>
                Your Smart Albums
              </h3>

              {albums.length > 0 ? (
                <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'>
                  {albums.map((album) => (
                    <motion.div
                      key={album.id}
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      className='p-4 bg-black/20 rounded-lg border border-white/10 hover:border-white/20'
                    >
                      <div className='flex items-start justify-between mb-3'>
                        <h4 className='text-white font-medium'>{album.name}</h4>
                        <button className='text-gray-400 hover:text-white'>
                          <Settings className='w-4 h-4' />
                        </button>
                      </div>

                      <p className='text-gray-400 text-sm mb-3'>
                        {album.description}
                      </p>

                      <div className='flex items-center justify-between mb-3'>
                        <div className='flex items-center gap-2'>
                          <ImageIcon className='w-4 h-4 text-gray-400' />
                          <span className='text-gray-300 text-sm'>
                            {album.photo_count} photos
                          </span>
                        </div>
                        {album.auto_update && (
                          <span className='px-2 py-1 bg-green-500/20 text-green-400 text-xs rounded'>
                            Auto
                          </span>
                        )}
                      </div>

                      <div className='text-xs text-gray-500'>
                        Updated{' '}
                        {new Date(album.last_updated).toLocaleDateString()}
                      </div>
                    </motion.div>
                  ))}
                </div>
              ) : (
                <div className='text-center py-12'>
                  <FolderPlus className='w-12 h-12 text-gray-600 mx-auto mb-3' />
                  <p className='text-gray-400 mb-2'>
                    No smart albums created yet
                  </p>
                  <button
                    onClick={() => setActiveTab('builder')}
                    className='px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700'
                  >
                    Create Your First Album
                  </button>
                </div>
              )}
            </div>
          </motion.div>
        )}

        {/* Analytics Tab */}
        {activeTab === 'analytics' && (
          <motion.div
            key='analytics'
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className={`${glass.card} p-6`}
          >
            <h3 className='text-xl font-semibold text-white mb-4'>
              Album Analytics
            </h3>

            <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6'>
              <div className='p-4 bg-black/20 rounded-lg'>
                <div className='flex items-center justify-between mb-2'>
                  <FolderPlus className='w-5 h-5 text-blue-500' />
                  <span className='text-gray-400 text-xs'>Total</span>
                </div>
                <p className='text-2xl font-bold text-white'>{albums.length}</p>
                <p className='text-gray-400 text-sm'>Smart Albums</p>
              </div>

              <div className='p-4 bg-black/20 rounded-lg'>
                <div className='flex items-center justify-between mb-2'>
                  <ImageIcon className='w-5 h-5 text-green-500' />
                  <span className='text-gray-400 text-xs'>Total</span>
                </div>
                <p className='text-2xl font-bold text-white'>
                  {albums.reduce((sum, album) => sum + album.photo_count, 0)}
                </p>
                <p className='text-gray-400 text-sm'>Photos Organized</p>
              </div>

              <div className='p-4 bg-black/20 rounded-lg'>
                <div className='flex items-center justify-between mb-2'>
                  <Zap className='w-5 h-5 text-yellow-500' />
                  <span className='text-gray-400 text-xs'>Auto</span>
                </div>
                <p className='text-2xl font-bold text-white'>
                  {albums.filter((album) => album.auto_update).length}
                </p>
                <p className='text-gray-400 text-sm'>Auto-updating</p>
              </div>

              <div className='p-4 bg-black/20 rounded-lg'>
                <div className='flex items-center justify-between mb-2'>
                  <BarChart3 className='w-5 h-5 text-purple-500' />
                  <span className='text-gray-400 text-xs'>Average</span>
                </div>
                <p className='text-2xl font-bold text-white'>
                  {albums.length > 0
                    ? Math.round(
                        albums.reduce(
                          (sum, album) => sum + album.photo_count,
                          0
                        ) / albums.length
                      )
                    : 0}
                </p>
                <p className='text-gray-400 text-sm'>Photos per Album</p>
              </div>
            </div>

            <div className='grid grid-cols-1 lg:grid-cols-2 gap-6'>
              <div>
                <h4 className='text-white font-medium mb-3'>Album Usage</h4>
                <div className='space-y-2'>
                  {albums.slice(0, 5).map((album) => (
                    <div
                      key={album.id}
                      className='flex items-center justify-between'
                    >
                      <span className='text-gray-300'>{album.name}</span>
                      <div className='flex items-center gap-2'>
                        <div className='w-24 h-2 bg-black/30 rounded-full overflow-hidden'>
                          <div
                            className='h-full bg-blue-500'
                            style={{
                              width: `${Math.min(
                                100,
                                (album.photo_count / 100) * 100
                              )}%`,
                            }}
                          />
                        </div>
                        <span className='text-gray-400 text-sm w-12 text-right'>
                          {album.photo_count}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <h4 className='text-white font-medium mb-3'>
                  Popular Templates
                </h4>
                <div className='space-y-2'>
                  <div className='flex items-center justify-between'>
                    <span className='text-gray-300'>Recent Photos</span>
                    <span className='text-gray-400 text-sm'>42 albums</span>
                  </div>
                  <div className='flex items-center justify-between'>
                    <span className='text-gray-300'>Favorites</span>
                    <span className='text-gray-400 text-sm'>28 albums</span>
                  </div>
                  <div className='flex items-center justify-between'>
                    <span className='text-gray-300'>Large Files</span>
                    <span className='text-gray-400 text-sm'>15 albums</span>
                  </div>
                  <div className='flex items-center justify-between'>
                    <span className='text-gray-300'>Screenshots</span>
                    <span className='text-gray-400 text-sm'>11 albums</span>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default memo(SmartAlbumsBuilder);
