/**
 * Privacy Dashboard Component - Phase 8
 *
 * Comprehensive privacy controls and transparency interface.
 * Provides GDPR-compliant privacy management with user-friendly controls.
 *
 * Features:
 * - Consent management with clear explanations
 * - Data export and portability (GDPR Article 20)
 * - Right to be forgotten implementation (GDPR Article 17)
 * - Privacy audit logs and transparency
 * - Data processing transparency
 * - Privacy settings and preferences
 */

import React, { useState, useEffect, useCallback } from 'react';
import { apiFetch } from '@/api';
import {
  Shield,
  Download,
  Trash2,
  Eye,
  FileText,
  Clock,
  CheckCircle,
  XCircle,
  AlertTriangle,
  User,
  Lock,
  RefreshCw
} from 'lucide-react';
import { useModalBehavior } from '../../hooks/useModalBehavior';

interface ConsentStatus {
  [key: string]: {
    granted: boolean;
    description: string;
  };
}

interface PrivacyDashboardData {
  user_id: string;
  consents: Array<{
    consent_type: string;
    status: string;
    granted_at: string | null;
    expires_at: string | null;
    purpose: string;
  }>;
  recent_actions: Array<{
    action: string;
    resource_type: string;
    timestamp: string;
    details: string;
  }>;
  export_requests: Array<{
    request_id: string;
    requested_at: string;
    status: string;
    export_types: string;
  }>;
  privacy_rights: {
    right_to_access: string;
    right_to_rectification: string;
    right_to_erasure: string;
    right_to_portability: string;
    right_to_object: string;
  };
}

export const PrivacyDashboard: React.FC = () => {
  const [dashboardData, setDashboardData] = useState<PrivacyDashboardData | null>(null);
  const [consentStatus, setConsentStatus] = useState<ConsentStatus>({});
  const [loading, setLoading] = useState(true);
  const [exportLoading, setExportLoading] = useState(false);
  const [selectedExportTypes, setSelectedExportTypes] = useState<string[]>(['consent', 'audit_logs']);
  const [showExportModal, setShowExportModal] = useState(false);
  const [showAnonymizeModal, setShowAnonymizeModal] = useState(false);
  const [anonymizePersonId, setAnonymizePersonId] = useState('');
  const [anonymizeReason, setAnonymizeReason] = useState('');

  const closeAnonymize = () => {
    setShowAnonymizeModal(false);
    setAnonymizePersonId('');
    setAnonymizeReason('');
  };

  const exportPanelRef = useModalBehavior(showExportModal, () => setShowExportModal(false));
  const anonymizePanelRef = useModalBehavior(showAnonymizeModal, closeAnonymize);

  // Fetch privacy dashboard data
  const fetchDashboardData = useCallback(async () => {
    try {
      const response = await apiFetch('/api/privacy/dashboard');
      if (response.ok) {
        const data = await response.json();
        setDashboardData(data);
      }
    } catch (error) {
      console.error('Failed to fetch privacy dashboard:', error);
    }
  }, []);

  // Fetch consent status
  const fetchConsentStatus = useCallback(async () => {
    try {
      const response = await apiFetch('/api/privacy/consent/status');
      if (response.ok) {
        const data = await response.json();
        setConsentStatus(data.consent_status);
      }
    } catch (error) {
      console.error('Failed to fetch consent status:', error);
    }
  }, []);

  // Load data on mount
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([fetchDashboardData(), fetchConsentStatus()]);
      setLoading(false);
    };
    loadData();
  }, [fetchDashboardData, fetchConsentStatus]);

  // Grant consent
  const grantConsent = async (consentType: string) => {
    try {
      // First request consent
      const requestResponse = await apiFetch('/api/privacy/consent/request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          consent_type: consentType,
          purpose: getConsentPurpose(consentType),
          legal_basis: 'consent'
        })
      });

      if (requestResponse.ok) {
        const requestData = await requestResponse.json();

        // Then grant the consent
        const grantResponse = await apiFetch(`/api/privacy/consent/${requestData.consent_id}/grant`, {
          method: 'POST'
        });

        if (grantResponse.ok) {
          await fetchConsentStatus();
        }
      }
    } catch (error) {
      console.error('Failed to grant consent:', error);
    }
  };

  // Withdraw consent
  const withdrawConsent = async (consentType: string) => {
    try {
      const response = await apiFetch(`/api/privacy/consent/${consentType}/withdraw`, {
        method: 'POST'
      });

      if (response.ok) {
        await fetchConsentStatus();
      }
    } catch (error) {
      console.error('Failed to withdraw consent:', error);
    }
  };

  // Request data export
  const requestDataExport = async () => {
    setExportLoading(true);
    try {
      const response = await apiFetch('/api/privacy/export/request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          export_types: selectedExportTypes,
          include_biometric_data: false
        })
      });

      if (response.ok) {
        await fetchDashboardData();
        setShowExportModal(false);
      }
    } catch (error) {
      console.error('Failed to request data export:', error);
    } finally {
      setExportLoading(false);
    }
  };

  // Anonymize person data
  const anonymizePersonData = async () => {
    if (!anonymizePersonId || !anonymizeReason) return;

    const confirmed = window.confirm(
      `Permanently anonymize person "${anonymizePersonId}"? Their face data and identifying metadata will be irreversibly removed.`
    );
    if (!confirmed) return;

    try {
      const response = await apiFetch('/api/privacy/anonymize/person', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          person_id: anonymizePersonId,
          reason: anonymizeReason
        })
      });

      if (response.ok) {
        setShowAnonymizeModal(false);
        setAnonymizePersonId('');
        setAnonymizeReason('');
        await fetchDashboardData();
      }
    } catch (error) {
      console.error('Failed to anonymize person data:', error);
    }
  };

  // Get consent purpose description
  const getConsentPurpose = (consentType: string): string => {
    const purposes: { [key: string]: string } = {
      face_recognition: 'We detect and recognize faces in your photos for organization and search',
      facial_attributes: 'We analyze facial attributes like age and emotion for enhanced search',
      face_clustering: 'We group similar faces together to identify people in your photos',
      video_processing: 'We process faces in your videos for timeline analysis and highlights',
      data_analytics: 'We analyze your photo collection to provide insights and recommendations',
      biometric_storage: 'We store biometric face data for accurate recognition across sessions'
    };
    return purposes[consentType] || 'Data processing for photo organization';
  };

  // Get consent status icon
  const getConsentIcon = (granted: boolean) => {
    return granted ?
      <CheckCircle className="w-5 h-5 text-green-600" /> :
      <XCircle className="w-5 h-5 text-red-600" />;
  };

  // Format date
  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleDateString();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex items-center space-x-2">
          <RefreshCw className="w-5 h-5 animate-spin" />
          <span>Loading privacy dashboard…</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold flex items-center space-x-2">
            <Shield className="w-6 h-6 text-blue-600" />
            <span>Privacy Dashboard</span>
          </h2>
          <p className="text-gray-600">
            Manage your privacy settings and data processing preferences
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={() => setShowExportModal(true)}
            className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            <Download className="w-4 h-4" />
            <span>Export Data</span>
          </button>

          <button
            onClick={() => setShowAnonymizeModal(true)}
            className="flex items-center space-x-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
          >
            <Trash2 className="w-4 h-4" />
            <span>Anonymize Data</span>
          </button>
        </div>
      </div>

      {/* Consent Management */}
      <div className="bg-white rounded-lg shadow-sm border p-6">
        <div className="flex items-center space-x-2 mb-4">
          <Lock className="w-5 h-5 text-green-600" />
          <h3 className="text-lg font-semibold">Consent Management</h3>
        </div>

        <div className="space-y-4">
          {Object.entries(consentStatus).map(([consentType, status]) => (
            <div key={consentType} className="flex items-center justify-between p-4 border rounded-lg">
              <div className="flex-1">
                <div className="flex items-center space-x-3">
                  {getConsentIcon(status.granted)}
                  <div>
                    <h4 className="font-medium capitalize">
                      {consentType.replace(/_/g, ' ')}
                    </h4>
                    <p className="text-sm text-gray-600">{status.description}</p>
                  </div>
                </div>
              </div>

              <div className="flex items-center space-x-2">
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                  status.granted
                    ? 'bg-green-100 text-green-800'
                    : 'bg-red-100 text-red-800'
                }`}>
                  {status.granted ? 'Granted' : 'Not Granted'}
                </span>

                {status.granted ? (
                  <button
                    onClick={() => withdrawConsent(consentType)}
                    className="px-3 py-1 bg-red-100 text-red-700 rounded hover:bg-red-200 text-sm"
                  >
                    Withdraw
                  </button>
                ) : (
                  <button
                    onClick={() => grantConsent(consentType)}
                    className="px-3 py-1 bg-green-100 text-green-700 rounded hover:bg-green-200 text-sm"
                  >
                    Grant
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Privacy Rights */}
      {dashboardData && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Your Rights */}
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <div className="flex items-center space-x-2 mb-4">
              <User className="w-5 h-5 text-blue-600" />
              <h3 className="text-lg font-semibold">Your Privacy Rights</h3>
            </div>

            <div className="space-y-3">
              {Object.entries(dashboardData.privacy_rights).map(([right, description]) => (
                <div key={right} className="flex items-start space-x-3">
                  <CheckCircle className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                  <div>
                    <h4 className="font-medium capitalize text-sm">
                      {right.replace(/_/g, ' ')}
                    </h4>
                    <p className="text-xs text-gray-600">{description}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Recent Activity */}
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <div className="flex items-center space-x-2 mb-4">
              <Clock className="w-5 h-5 text-purple-600" />
              <h3 className="text-lg font-semibold">Recent Privacy Activity</h3>
            </div>

            <div className="space-y-3 max-h-64 overflow-y-auto">
              {dashboardData.recent_actions.length > 0 ? (
                dashboardData.recent_actions.map((action, index) => (
                  <div key={index} className="flex items-start space-x-3 p-3 bg-gray-50 rounded-lg">
                    <Eye className="w-4 h-4 text-gray-600 mt-0.5 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium">{action.action}</p>
                      <p className="text-xs text-gray-600">{action.resource_type}</p>
                      <p className="text-xs text-gray-500">{formatDate(action.timestamp)}</p>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-sm text-gray-500">No recent privacy activity</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Export Requests */}
      {dashboardData && dashboardData.export_requests.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <div className="flex items-center space-x-2 mb-4">
            <FileText className="w-5 h-5 text-orange-600" />
            <h3 className="text-lg font-semibold">Data Export Requests</h3>
          </div>

          <div className="space-y-3">
            {dashboardData.export_requests.map((request) => (
              <div key={request.request_id} className="flex items-center justify-between p-3 border rounded-lg">
                <div>
                  <p className="font-medium">Export Request</p>
                  <p className="text-sm text-gray-600">
                    Types: {JSON.parse(request.export_types).join(', ')}
                  </p>
                  <p className="text-xs text-gray-500">
                    Requested: {formatDate(request.requested_at)}
                  </p>
                </div>

                <div className="flex items-center space-x-2">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                    request.status === 'completed'
                      ? 'bg-green-100 text-green-800'
                      : request.status === 'processing'
                      ? 'bg-yellow-100 text-yellow-800'
                      : 'bg-gray-100 text-gray-800'
                  }`}>
                    {request.status}
                  </span>

                  {request.status === 'completed' && (
                    <button
                      onClick={() => window.open(`/api/privacy/export/${request.request_id}/download`)}
                      className="px-3 py-1 bg-blue-100 text-blue-700 rounded hover:bg-blue-200 text-sm"
                    >
                      Download
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Export Modal */}
      {showExportModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div
            ref={exportPanelRef}
            role="dialog"
            aria-modal="true"
            aria-label="Export your data"
            className="bg-white rounded-lg p-6 w-full max-w-md"
          >
            <h3 className="text-lg font-semibold mb-4">Export Your Data</h3>

            <div className="space-y-3 mb-4">
              <p className="text-sm text-gray-600">
                Select the types of data you want to export:
              </p>

              {['consent', 'audit_logs', 'face_data', 'privacy_settings'].map((type) => (
                <label key={type} className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    checked={selectedExportTypes.includes(type)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedExportTypes([...selectedExportTypes, type]);
                      } else {
                        setSelectedExportTypes(selectedExportTypes.filter(t => t !== type));
                      }
                    }}
                    className="rounded"
                  />
                  <span className="text-sm capitalize">{type.replace(/_/g, ' ')}</span>
                </label>
              ))}
            </div>

            <div className="flex items-center justify-end space-x-3">
              <button
                onClick={() => setShowExportModal(false)}
                className="px-4 py-2 text-gray-600 hover:text-gray-800"
              >
                Cancel
              </button>
              <button
                onClick={requestDataExport}
                disabled={exportLoading || selectedExportTypes.length === 0}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {exportLoading ? 'Requesting…' : 'Request Export'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Anonymize Modal */}
      {showAnonymizeModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div
            ref={anonymizePanelRef}
            role="dialog"
            aria-modal="true"
            aria-label="Anonymize person"
            className="bg-white rounded-lg p-6 w-full max-w-md"
          >
            <h3 className="text-lg font-semibold mb-4 flex items-center space-x-2">
              <AlertTriangle className="w-5 h-5 text-red-600" />
              <span>Anonymize Person Data</span>
            </h3>

            <div className="space-y-4 mb-4">
              <div>
                <label htmlFor="pd-anonymize-person-id" className="block text-sm font-medium mb-1">Person ID</label>
                <input
                  id="pd-anonymize-person-id"
                  type="text"
                  value={anonymizePersonId}
                  onChange={(e) => setAnonymizePersonId(e.target.value)}
                  placeholder="Enter person/cluster ID"
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label htmlFor="pd-anonymize-reason" className="block text-sm font-medium mb-1">Reason</label>
                <textarea
                  id="pd-anonymize-reason"
                  value={anonymizeReason}
                  onChange={(e) => setAnonymizeReason(e.target.value)}
                  placeholder="Reason for anonymization (required for audit)"
                  rows={3}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm text-red-800">
                  <strong>Warning:</strong> This action will permanently anonymize all data
                  associated with this person. This cannot be undone.
                </p>
              </div>
            </div>

            <div className="flex items-center justify-end space-x-3">
              <button
                onClick={closeAnonymize}
                className="px-4 py-2 text-gray-600 hover:text-gray-800"
              >
                Cancel
              </button>
              <button
                onClick={anonymizePersonData}
                disabled={!anonymizePersonId || !anonymizeReason}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
              >
                Anonymize Data
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
