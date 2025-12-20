/**
 * Duplicates Page - Review and Manage Duplicate Photos
 *
 * Displays duplicate photo groups and allows users to resolve them.
 * Uses the glass design system consistent with the rest of the app.
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  Copy,
  X,
  Check,
  Trash2,
  Download,
  AlertTriangle,
  Clock,
  Image as ImageIcon,
  Search,
  RefreshCw,
  Loader2,
  ShieldCheck,
} from 'lucide-react';
import { api } from '../api';
import { glass } from '../design/glass';

interface DuplicateGroup {
  id: string;
  hash_type: string;
  files: string[];
  similarity_score?: number;
  created_at?: string;
  resolved_at?: string;
  resolution?: string;
}

interface DuplicateStats {
  total_groups: number;
  total_duplicate_files: number;
  potential_space_saved: number;
  md5_groups?: number;
  perceptual_groups?: number;
}

export function Duplicates() {
  const [groups, setGroups] = useState<DuplicateGroup[]>([]);
  const [stats, setStats] = useState<DuplicateStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedGroup, setSelectedGroup] = useState<string | null>(null);
  const [resolvingGroup, setResolvingGroup] = useState<string | null>(null);

  const fetchDuplicateGroups = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.getDuplicates({ limit: 200 });
      setGroups(response.groups || []);
    } catch (err: any) {
      console.error('Failed to fetch duplicate groups:', err);
      setError(err?.message || 'Failed to load duplicate groups');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchStats = useCallback(async () => {
    try {
      const response = await api.getDuplicateStats();
      setStats(response.stats || response);
    } catch (err) {
      console.error('Failed to fetch duplicate stats:', err);
    }
  }, []);

  useEffect(() => {
    fetchDuplicateGroups();
    fetchStats();
  }, [fetchDuplicateGroups, fetchStats]);

  const handleScan = async () => {
    try {
      setScanning(true);
      setError(null);
      const response = await api.scanDuplicates('exact', 1000);
      console.log('Duplicate scan completed:', response);

      // Refresh data after scan
      await fetchDuplicateGroups();
      await fetchStats();
    } catch (err) {
      console.error('Failed to scan for duplicates:', err);
      setError('Failed to scan for duplicates');
    } finally {
      setScanning(false);
    }
  };

  const handleResolveGroup = async (
    groupId: string,
    resolution: 'keep_all' | 'keep_selected' | 'delete_all',
    keepFiles?: string[]
  ) => {
    try {
      setResolvingGroup(groupId);
      await api.resolveDuplicateGroup(groupId, resolution, keepFiles);

      await fetchDuplicateGroups();
      await fetchStats();
    } catch (err: any) {
      console.error('Failed to resolve duplicate group:', err);
      setError(err?.message || 'Failed to resolve duplicate group');
    } finally {
      setResolvingGroup(null);
    }
  };

  const handleDeleteGroup = async (groupId: string) => {
    try {
      const confirmed = window.confirm(
        'Are you sure you want to delete this duplicate group? This action cannot be undone.'
      );
      if (!confirmed) return;

      await api.deleteDuplicateGroup(groupId);

      // Remove from local state
      setGroups(groups.filter((group) => group.id !== groupId));

      // Refresh stats
      await fetchStats();
    } catch (err) {
      console.error('Failed to delete duplicate group:', err);
      setError('Failed to delete duplicate group');
    }
  };

  const handleSelectGroup = (groupId: string) => {
    setSelectedGroup(groupId === selectedGroup ? null : groupId);
  };

  const filteredGroups = groups.filter((group) => {
    if (!searchTerm) return true;

    // Search in file paths
    return group.files.some((file) =>
      file.toLowerCase().includes(searchTerm.toLowerCase())
    );
  });

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className='min-h-screen'>
      {/* Header */}
      <div className='border-b border-white/10'>
        <div className='max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6'>
          <div className='flex items-center justify-between'>
            <div className='flex items-center gap-3'>
              <Copy className='text-foreground' size={28} />
              <div>
                <h1 className='text-2xl font-bold text-foreground'>
                  Duplicates
                </h1>
                <p className='text-sm text-muted-foreground'>
                  Review and manage duplicate photos
                </p>
              </div>
            </div>

            <div className='flex items-center gap-3'>
              <button
                onClick={handleScan}
                disabled={scanning}
                className={`btn-glass ${
                  scanning ? 'btn-glass--muted' : 'btn-glass--primary'
                } text-sm px-4 py-2`}
              >
                {scanning ? (
                  <div className='flex items-center gap-2'>
                    <RefreshCw size={16} className='animate-spin' />
                    Scanning...
                  </div>
                ) : (
                  <div className='flex items-center gap-2'>
                    <Search size={16} />
                    Scan for Duplicates
                  </div>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Stats and Search */}
      <div className='max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6'>
        <div className='grid grid-cols-1 md:grid-cols-5 gap-4 mb-6'>
          {/* Stats Cards */}
          {stats && (
            <>
              <div
                className={`${glass.surface} rounded-xl p-4 border border-white/10`}
              >
                <div className='flex items-center gap-3'>
                  <div className='w-10 h-10 rounded-full bg-blue-500/20 flex items-center justify-center'>
                    <Copy className='text-blue-400' size={18} />
                  </div>
                  <div>
                    <div className='text-2xl font-bold text-foreground'>
                      {stats.total_groups}
                    </div>
                    <div className='text-xs text-muted-foreground'>
                      Total Groups
                    </div>
                  </div>
                </div>
              </div>

              <div
                className={`${glass.surface} rounded-xl p-4 border border-white/10`}
              >
                <div className='flex items-center gap-3'>
                  <div className='w-10 h-10 rounded-full bg-green-500/20 flex items-center justify-center'>
                    <ImageIcon className='text-green-400' size={18} />
                  </div>
                  <div>
                    <div className='text-2xl font-bold text-foreground'>
                      {stats.total_duplicate_files}
                    </div>
                    <div className='text-xs text-muted-foreground'>
                      Duplicate Files
                    </div>
                  </div>
                </div>
              </div>

              <div
                className={`${glass.surface} rounded-xl p-4 border border-white/10`}
              >
                <div className='flex items-center gap-3'>
                  <div className='w-10 h-10 rounded-full bg-purple-500/20 flex items-center justify-center'>
                    <Download className='text-purple-400' size={18} />
                  </div>
                  <div>
                    <div className='text-2xl font-bold text-foreground'>
                      {formatFileSize(stats.potential_space_saved || 0)}
                    </div>
                    <div className='text-xs text-muted-foreground'>
                      Space Saved
                    </div>
                  </div>
                </div>
              </div>

              <div
                className={`${glass.surface} rounded-xl p-4 border border-white/10`}
              >
                <div className='flex items-center gap-3'>
                  <div className='w-10 h-10 rounded-full bg-orange-500/20 flex items-center justify-center'>
                    <Check className='text-orange-400' size={18} />
                  </div>
                  <div>
                    <div className='text-2xl font-bold text-foreground'>
                      {stats.md5_groups ?? 0}
                    </div>
                    <div className='text-xs text-muted-foreground'>
                      MD5 Groups
                    </div>
                  </div>
                </div>
              </div>

              <div
                className={`${glass.surface} rounded-xl p-4 border border-white/10`}
              >
                <div className='flex items-center gap-3'>
                  <div className='w-10 h-10 rounded-full bg-red-500/20 flex items-center justify-center'>
                    <AlertTriangle className='text-red-400' size={18} />
                  </div>
                  <div>
                    <div className='text-2xl font-bold text-foreground'>
                      {stats.perceptual_groups ?? 0}
                    </div>
                    <div className='text-xs text-muted-foreground'>
                      Perceptual Groups
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Search */}
        <div
          className={`${glass.surface} rounded-xl p-4 border border-white/10 mb-6`}
        >
          <div className='flex items-center gap-2'>
            <Search className='text-muted-foreground' size={16} />
            <input
              type='text'
              placeholder='Search duplicate groups...'
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className='flex-1 bg-transparent outline-none text-sm placeholder:text-muted-foreground'
            />
          </div>
        </div>

        {/* Error State */}
        {error && (
          <div className='mb-6 text-sm text-destructive glass-surface rounded-xl p-4 border border-white/10'>
            {error}
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className='flex items-center justify-center py-20'>
            <div className='flex items-center gap-3'>
              <RefreshCw
                size={20}
                className='animate-spin text-muted-foreground'
              />
              <span className='text-muted-foreground'>
                Loading duplicate groups...
              </span>
            </div>
          </div>
        )}

        {/* No Duplicates State */}
        {!loading && groups.length === 0 && (
          <div className='text-center py-20'>
            <Copy size={48} className='mx-auto text-muted-foreground mb-4' />
            <h3 className='text-lg font-medium text-foreground mb-2'>
              No Duplicates Found
            </h3>
            <p className='text-muted-foreground mb-6'>
              Start by scanning your photos for duplicates
            </p>
            <button
              onClick={handleScan}
              disabled={scanning}
              className='btn-glass btn-glass--primary'
            >
              <Search size={16} className='mr-2' />
              Scan for Duplicates
            </button>
          </div>
        )}

        {/* Duplicate Groups List */}
        {!loading && filteredGroups.length > 0 && (
          <div className='space-y-4'>
            {filteredGroups.map((group) => (
              <div
                key={group.id}
                className={`${glass.surface} rounded-xl border border-white/10 overflow-hidden hover:border-white/20 transition-colors`}
              >
                {/* Group Header */}
                <div
                  className='flex items-center justify-between p-4 cursor-pointer'
                  onClick={() => handleSelectGroup(group.id)}
                >
                  <div className='flex items-center gap-3'>
                    <div className='w-10 h-10 rounded-full bg-orange-500/20 flex items-center justify-center'>
                      <Copy size={18} className='text-orange-400' />
                    </div>
                    <div>
                      <div className='font-medium text-foreground'>
                        {group.files.length} duplicates
                      </div>
                      <div className='text-xs text-muted-foreground'>
                        {group.hash_type} hash • {group.files.length} files
                      </div>
                    </div>
                  </div>

                  <div className='flex items-center gap-3'>
                    <div className='text-xs text-muted-foreground flex items-center gap-1'>
                      <Clock size={12} />
                      {group.created_at ? new Date(group.created_at).toLocaleDateString() : 'Unknown date'}
                    </div>

                    {group.resolved_at ? (
                      <span className='text-xs px-2 py-1 rounded-full bg-green-500/20 text-green-400'>
                        Resolved
                      </span>
                    ) : (
                      <span className='text-xs px-2 py-1 rounded-full bg-yellow-500/20 text-yellow-400'>
                        Pending
                      </span>
                    )}

                    <button className='text-muted-foreground hover:text-foreground'>
                      {selectedGroup === group.id ? (
                        <X size={16} />
                      ) : (
                        <Copy size={16} />
                      )}
                    </button>
                  </div>
                </div>

                {/* Expanded Group Details */}
                {selectedGroup === group.id && (
                  <div className='border-t border-white/10 p-4'>
                    {/* File List */}
                    <div className='mb-4'>
                      <h4 className='text-sm font-medium text-foreground mb-2'>
                        Duplicate Files
                      </h4>
                      <div className='grid grid-cols-1 md:grid-cols-2 gap-3'>
                        {group.files.map((filePath, index) => (
                          <div
                            key={index}
                            className={`${glass.surfaceStrong} rounded-lg p-3 border border-white/5 flex items-center gap-3`}
                          >
                            <img
                              src={api.getImageUrl(filePath, 120)}
                              alt={`Duplicate ${index + 1}`}
                              className='w-16 h-16 object-cover rounded'
                              loading='lazy'
                            />
                            <div className='flex-1 min-w-0'>
                              <div className='text-sm font-medium text-foreground truncate'>
                                {filePath.split('/').pop()}
                              </div>
                              <div className='text-xs text-muted-foreground truncate'>
                                {filePath}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Action Buttons - Only show for unresolved groups */}
                    {!group.resolved_at && (
                      <div className='flex flex-wrap gap-2 pt-4 border-t border-white/10'>
                        <button
                          onClick={() =>
                            handleResolveGroup(
                              group.id,
                              'keep_all',
                              group.files
                            )
                          }
                          className='btn-glass btn-glass--muted text-xs px-3 py-1.5'
                          disabled={!!resolvingGroup}
                        >
                          <ShieldCheck size={12} className='mr-1' />
                          Keep All
                        </button>

                        <button
                          onClick={() =>
                            handleResolveGroup(group.id, 'keep_selected', [
                              group.files[0],
                            ])
                          }
                          className='btn-glass btn-glass--primary text-xs px-3 py-1.5'
                          disabled={!!resolvingGroup}
                        >
                          <Check size={12} className='mr-1' />
                          Keep First, discard rest
                        </button>

                        <button
                          onClick={() =>
                            handleResolveGroup(group.id, 'delete_all')
                          }
                          className='btn-glass btn-glass--danger text-xs px-3 py-1.5'
                          disabled={!!resolvingGroup}
                        >
                          <Trash2 size={12} className='mr-1' />
                          Delete all (manual cleanup)
                        </button>

                        <button
                          onClick={() => handleDeleteGroup(group.id)}
                          className='btn-glass btn-glass--muted text-xs px-3 py-1.5 ml-auto'
                        >
                          <Trash2 size={12} className='mr-1' />
                          Delete Group
                        </button>

                        {resolvingGroup === group.id && (
                          <div className='text-xs text-muted-foreground flex items-center gap-2 ml-auto'>
                            <Loader2 size={12} className='animate-spin' />{' '}
                            Resolving…
                          </div>
                        )}
                      </div>
                    )}

                    {/* Resolution Status - Show for resolved groups */}
                    {group.resolved_at && (
                      <div className='bg-green-500/10 border border-green-500/20 rounded-lg p-3 mt-3'>
                        <div className='flex items-center gap-2 text-green-400'>
                          <Check size={16} />
                          <span className='text-sm font-medium'>
                            Group resolved on{' '}
                            {new Date(group.resolved_at).toLocaleString()}
                          </span>
                        </div>
                        <div className='text-xs text-muted-foreground mt-1'>
                          Resolution: {group.resolution}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
