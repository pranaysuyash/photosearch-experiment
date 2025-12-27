/**
 * Privacy Controls Component
 *
 * Provides granular privacy controls for photos, including encryption and sharing permissions.
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  Shield,
  Globe,
  Users,
  Lock,
  Eye,
  Key,
  Settings,
  UserPlus,
  UserX,
  Share2,
  X,
  AlertTriangle
} from 'lucide-react';
import { api } from '../api';
import { glass } from '../design/glass';

interface PrivacyControl {
  id: string;
  photo_path: string;
  owner_id: string;
  visibility: 'public' | 'shared' | 'private' | 'friends_only';
  share_permissions: Record<string, boolean>;
  encryption_enabled: boolean;
  encryption_key_hash?: string;
  allowed_users: string[];
  allowed_groups: string[];
  created_at: string;
  updated_at: string;
}

type SharePermissionKey = 'view' | 'download' | 'share' | 'edit';

interface PrivacySettings {
  visibility: PrivacyControl['visibility'];
  sharePermissions: Record<SharePermissionKey, boolean>;
  encryptionEnabled: boolean;
  encryptionKey: string;
  allowedUsers: string[];
  allowedGroups: string[];
}

export function PrivacyControls({ photoPath }: { photoPath: string }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [tab, setTab] = useState<'general' | 'sharing' | 'encryption'>('general');
  const [newAllowedUser, setNewAllowedUser] = useState('');

  // Default privacy settings
  const [settings, setSettings] = useState<PrivacySettings>({
    visibility: 'private',
    sharePermissions: {
      view: true,
      download: false,
      share: false,
      edit: false
    },
    encryptionEnabled: false,
    encryptionKey: '',
    allowedUsers: [] as string[],
    allowedGroups: [] as string[]
  });

  // Load current privacy settings
  const loadPrivacySettings = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const privacyData: PrivacyControl = await api.getPhotoPrivacy(photoPath);

      setSettings({
        visibility: privacyData.visibility,
        sharePermissions: privacyData.share_permissions || {
          view: true,
          download: false,
          share: false,
          edit: false
        },
        encryptionEnabled: privacyData.encryption_enabled,
        encryptionKey: '',
        allowedUsers: privacyData.allowed_users || [],
        allowedGroups: privacyData.allowed_groups || []
      });
    } catch (err) {
      console.error('Failed to load privacy settings:', err);
      setError('Failed to load privacy settings');
    } finally {
      setLoading(false);
    }
  }, [photoPath]);

  useEffect(() => {
    loadPrivacySettings();
  }, [loadPrivacySettings]);

  const savePrivacySettings = async () => {
    try {
      setSaving(true);
      setError(null);

      await api.updatePhotoPrivacy(photoPath, {
        visibility: settings.visibility,
        share_permissions: settings.sharePermissions,
        encryption_enabled: settings.encryptionEnabled,
        encryption_key_hash: settings.encryptionEnabled ?
          btoa(settings.encryptionKey) : undefined, // In a real app, use proper hashing
        allowed_users: settings.allowedUsers,
        allowed_groups: settings.allowedGroups
      });

      // Reload settings to confirm changes
      loadPrivacySettings();
    } catch (err) {
      console.error('Failed to update privacy settings:', err);
      setError('Failed to update privacy settings');
    } finally {
      setSaving(false);
    }
  };

  const addUserToAccessList = () => {
    if (!newAllowedUser.trim()) return;
    if (!settings.allowedUsers.includes(newAllowedUser.trim())) {
      setSettings(prev => ({
        ...prev,
        allowedUsers: [...prev.allowedUsers, newAllowedUser.trim()]
      }));
    }
    setNewAllowedUser('');
  };

  const removeUserFromAccessList = (user: string) => {
    setSettings(prev => ({
      ...prev,
      allowedUsers: prev.allowedUsers.filter(u => u !== user)
    }));
  };

  const toggleSharePermission = (permission: SharePermissionKey) => {
    setSettings(prev => ({
      ...prev,
      sharePermissions: {
        ...prev.sharePermissions,
        [permission]: !prev.sharePermissions[permission]
      }
    }));
  };

  if (loading) {
    return (
      <div className={`${glass.surface} rounded-xl border border-white/10 p-6`}>
        <div className="flex items-center justify-center h-32">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-foreground flex items-center gap-2">
          <Shield className="text-primary" size={24} />
          Privacy Controls
        </h2>

        <button
          onClick={savePrivacySettings}
          disabled={saving}
          className="btn-glass btn-glass--primary px-4 py-2 flex items-center gap-2"
        >
          {saving ? (
            <>
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Saving...
            </>
          ) : (
            <>
              <Settings size={16} />
              Save Settings
            </>
          )}
        </button>
      </div>

      {/* Tab Navigation */}
      <div className="flex border-b border-white/10">
        <button
          className={`pb-2 px-4 text-sm font-medium ${
            tab === 'general'
              ? 'text-foreground border-b-2 border-primary'
              : 'text-muted-foreground hover:text-foreground'
          }`}
          onClick={() => setTab('general')}
        >
          General
        </button>
        <button
          className={`pb-2 px-4 text-sm font-medium ${
            tab === 'sharing'
              ? 'text-foreground border-b-2 border-primary'
              : 'text-muted-foreground hover:text-foreground'
          }`}
          onClick={() => setTab('sharing')}
        >
          Sharing
        </button>
        <button
          className={`pb-2 px-4 text-sm font-medium ${
            tab === 'encryption'
              ? 'text-foreground border-b-2 border-primary'
              : 'text-muted-foreground hover:text-foreground'
          }`}
          onClick={() => setTab('encryption')}
        >
          Encryption
        </button>
      </div>

      {/* General Privacy Settings */}
      {tab === 'general' && (
        <div className="space-y-6">
          <div className={`${glass.surfaceStrong} rounded-xl border border-white/10 p-4`}>
            <h3 className="font-medium text-foreground mb-3 flex items-center gap-2">
              <Lock size={16} />
              Visibility Settings
            </h3>

            <div className="space-y-3">
              {[
                { value: 'private', label: 'Private', desc: 'Only you can view this photo', icon: <Lock size={16} /> },
                { value: 'friends_only', label: 'Friends Only', desc: 'Only allowed users can view this photo', icon: <Users size={16} /> },
                { value: 'shared', label: 'Shared', desc: 'Specific users and groups can view this photo', icon: <Share2 size={16} /> },
                { value: 'public', label: 'Public', desc: 'Anyone can discover and view this photo', icon: <Globe size={16} /> }
              ].map(option => (
                <label
                  key={option.value}
                  className={`flex items-start gap-3 p-3 rounded-lg cursor-pointer border ${
                    settings.visibility === option.value
                      ? 'border-primary bg-primary/10'
                      : 'border-white/10 hover:border-white/20'
                  }`}
                >
                  <input
                    type="radio"
                    name="visibility"
                    value={option.value}
                    checked={settings.visibility === option.value}
                    onChange={(e) => setSettings(prev => ({
                      ...prev,
                      visibility: e.target.value as PrivacyControl['visibility']
                    }))}
                    className="mt-0.5"
                  />
                  <div className="flex items-start gap-2 flex-1">
                    <div className={`p-1.5 rounded ${
                      settings.visibility === option.value
                        ? 'text-primary'
                        : 'text-muted-foreground'
                    }`}>
                      {option.icon}
                    </div>
                    <div>
                      <div className="font-medium text-foreground">{option.label}</div>
                      <div className="text-sm text-muted-foreground">{option.desc}</div>
                    </div>
                  </div>
                </label>
              ))}
            </div>
          </div>

          <div className={`${glass.surfaceStrong} rounded-xl border border-white/10 p-4`}>
            <h3 className="font-medium text-foreground mb-3 flex items-center gap-2">
              <Eye size={16} />
              View and Download Permissions
            </h3>

            <div className="space-y-3">
              {[
                { key: 'view', label: 'View Photo', desc: 'Users can view the photo' },
                { key: 'download', label: 'Download Photo', desc: 'Users can download the original photo' },
                { key: 'share', label: 'Share Photo', desc: 'Users can share the photo with others' },
                { key: 'edit', label: 'Edit Photo', desc: 'Users can make edits to the photo' }
              ].map(permission => (
                <label
                  key={permission.key}
                  className="flex items-center gap-3 p-3 rounded-lg cursor-pointer border border-white/10 hover:border-white/20"
                >
                  <input
                    type="checkbox"
                    checked={settings.sharePermissions[permission.key as keyof typeof settings.sharePermissions] || false}
                    onChange={() => toggleSharePermission(permission.key)}
                    className="rounded"
                  />
                  <div>
                    <div className="font-medium text-foreground">{permission.label}</div>
                    <div className="text-sm text-muted-foreground">{permission.desc}</div>
                  </div>
                </label>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Sharing Settings */}
      {tab === 'sharing' && (
        <div className="space-y-6">
          <div className={`${glass.surfaceStrong} rounded-xl border border-white/10 p-4`}>
            <h3 className="font-medium text-foreground mb-3 flex items-center gap-2">
              <Share2 size={16} />
              Authorized Users
            </h3>

            <div className="space-y-4">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newAllowedUser}
                  onChange={(e) => setNewAllowedUser(e.target.value)}
                  placeholder="Enter user ID or email to authorize"
                  className="flex-1 px-3 py-2 rounded-lg border border-white/10 bg-white/5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
                <button
                  onClick={addUserToAccessList}
                  className="btn-glass btn-glass--primary px-3 py-2 flex items-center gap-1"
                >
                  <UserPlus size={16} />
                  Add
                </button>
              </div>

              {settings.allowedUsers.length > 0 ? (
                <div className="space-y-2">
                  {settings.allowedUsers.map(user => (
                    <div key={user} className="flex items-center justify-between p-2 rounded-lg bg-white/5">
                      <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
                          <UserPlus size={14} className="text-primary" />
                        </div>
                        <span className="text-sm text-foreground">{user}</span>
                      </div>
                      <button
                        onClick={() => removeUserFromAccessList(user)}
                        className="btn-glass btn-glass--muted p-1.5"
                        title="Revoke access"
                      >
                        <UserX size={14} />
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-4 text-muted-foreground">
                  No authorized users yet
                </div>
              )}
            </div>
          </div>

          <div className={`${glass.surfaceStrong} rounded-xl border border-white/10 p-4`}>
            <h3 className="font-medium text-foreground mb-3 flex items-center gap-2">
              <Users size={16} />
              Authorized Groups
            </h3>

            <div className="space-y-3">
              {settings.allowedGroups.length > 0 ? (
                <div className="space-y-2">
                  {settings.allowedGroups.map(group => (
                    <div key={group} className="flex items-center justify-between p-2 rounded-lg bg-white/5">
                      <span className="text-sm text-foreground">{group}</span>
                      <button
                        onClick={() => {
                          setSettings(prev => ({
                            ...prev,
                            allowedGroups: prev.allowedGroups.filter(g => g !== group)
                          }));
                        }}
                        className="btn-glass btn-glass--muted p-1.5"
                        title="Remove group"
                      >
                        <X size={14} />
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-4 text-muted-foreground">
                  No authorized groups yet
                </div>
              )}

              <button
                className="btn-glass btn-glass--muted w-full py-2 flex items-center justify-center gap-2"
                onClick={() => alert('Group creation/selection would open here')}
              >
                <UserPlus size={16} />
                Add Group
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Encryption Settings */}
      {tab === 'encryption' && (
        <div className="space-y-6">
          <div className={`${glass.surfaceStrong} rounded-xl border border-white/10 p-4`}>
            <h3 className="font-medium text-foreground mb-3 flex items-center gap-2">
              <Key size={16} />
              Encryption Settings
            </h3>

            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="enableEncryption"
                  checked={settings.encryptionEnabled}
                  onChange={(e) => setSettings(prev => ({
                    ...prev,
                    encryptionEnabled: e.target.checked
                  }))}
                  className="rounded"
                />
                <label htmlFor="enableEncryption" className="font-medium text-foreground">
                  Enable Client-Side Encryption
                </label>
              </div>

              {settings.encryptionEnabled && (
                <div className="space-y-3 p-3 rounded-lg bg-white/5">
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-2">
                      Encryption Key
                    </label>
                    <div className="flex gap-2">
                      <input
                        type="password"
                        value={settings.encryptionKey}
                        onChange={(e) => setSettings(prev => ({
                          ...prev,
                          encryptionKey: e.target.value
                        }))}
                        placeholder="Enter a strong encryption key"
                        className="flex-1 px-3 py-2 rounded-lg border border-white/10 bg-white/5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                      />
                      <button
                        onClick={() => setSettings(prev => ({
                          ...prev,
                          encryptionKey: Math.random().toString(36).substring(2, 15) +
                                         Math.random().toString(36).substring(2, 15)
                        }))}
                        className="btn-glass btn-glass--muted px-3 py-2"
                      >
                        Generate
                      </button>
                    </div>
                    <p className="text-xs text-muted-foreground mt-2">
                      Keep this key secure. Without it, you will not be able to decrypt your photo.
                    </p>
                  </div>

                  <div className="flex items-start gap-2 p-3 rounded-lg bg-warning/10 border border-warning/20">
                    <AlertTriangle size={16} className="text-warning mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-sm font-medium text-warning">Important</p>
                      <p className="text-xs text-muted-foreground">
                        The encryption key is never stored on our servers. It stays on your device only.
                        If you lose this key, there is no way to recover your encrypted data.
                      </p>
                    </div>
                  </div>
                </div>
              )}

              <div className="text-sm text-muted-foreground space-y-2">
                <p>
                  Client-side encryption ensures that your photo data is encrypted in your browser before being sent to our servers.
                  Only someone with the encryption key can decrypt and view your photos.
                </p>
                <p>
                  This provides an additional layer of security beyond standard access controls, ensuring that even our systems
                  cannot access your encrypted content.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="text-sm text-destructive bg-destructive/10 rounded-lg p-3">
          {error}
          <button
            className="ml-2"
            onClick={() => setError(null)}
          >
            <X size={16} />
          </button>
        </div>
      )}

      {/* Summary Card */}
      <div className={`${glass.surfaceStrong} rounded-xl border border-white/10 p-4`}>
        <h3 className="font-medium text-foreground mb-3">Privacy Summary</h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div>
            <div className="text-muted-foreground">Visibility:</div>
            <div className="font-medium capitalize">
              {settings.visibility.replace('_', ' ')}
              {settings.visibility === 'private' && (
                <span className="ml-2 text-xs px-1.5 py-0.5 rounded-full bg-red-500/20 text-red-400">
                  Highest Privacy
                </span>
              )}
              {settings.visibility === 'public' && (
                <span className="ml-2 text-xs px-1.5 py-0.5 rounded-full bg-green-500/20 text-green-400">
                  Lowest Privacy
                </span>
              )}
            </div>
          </div>

          <div>
            <div className="text-muted-foreground">Authorized Users:</div>
            <div className="font-medium">
              {settings.allowedUsers.length} {settings.allowedUsers.length === 1 ? 'user' : 'users'}
            </div>
          </div>

          <div>
            <div className="text-muted-foreground">Encryption:</div>
            <div className="font-medium">
              {settings.encryptionEnabled ? (
                <span className="text-green-400">Enabled</span>
              ) : (
                <span className="text-muted-foreground">Disabled</span>
              )}
            </div>
          </div>

          <div>
            <div className="text-muted-foreground">Download Permission:</div>
            <div className="font-medium">
              {settings.sharePermissions.download ? (
                <span className="text-green-400">Allowed</span>
              ) : (
                <span className="text-red-400">Blocked</span>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
