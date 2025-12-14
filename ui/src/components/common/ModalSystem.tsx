/**
 * Modal System Component
 *
 * Manages and displays various types of dialogs and modals
 */

import { useState, useEffect } from 'react';
import './ModalSystem.css';

interface DialogItem {
  id: string;
  type: 'confirmation' | 'error' | 'progress' | 'input' | 'info';
  title: string;
  message: string;
  options?: string[];
  progress?: number;
  created_at?: string;
  status?: string;
}

const ModalSystem: React.FC = () => {
  const [dialogs, setDialogs] = useState<DialogItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  interface ModalStats {
    active_dialogs?: number;
    total_dialogs?: number;
    closed_dialogs?: number;
  }
  const [stats, setStats] = useState<ModalStats | null>(null);
  const [newDialog, setNewDialog] = useState<{
    type: DialogItem['type'];
    title: string;
    message: string;
    options: string[];
  }>({
    type: 'confirmation',
    title: '',
    message: '',
    options: ['Yes', 'No'],
  });

  // Fetch active dialogs on mount
  const fetchDialogs = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch('/api/dialogs/active');
      if (!response.ok) {
        throw new Error('Failed to fetch dialogs');
      }

      const data = await response.json();
      setDialogs(data.dialogs || []);

      // Fetch statistics
      const statsResponse = await fetch('/api/dialogs/stats');
      if (statsResponse.ok) {
        const statsData = await statsResponse.json();
        setStats(statsData.stats);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      console.error('Error fetching dialogs:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDialogs();

    // Set up polling for active dialogs
    const interval = setInterval(fetchDialogs, 5000);
    return () => clearInterval(interval);
  }, []);

  // Create a new dialog
  const createDialog = async () => {
    try {
      setError(null);

      const response = await fetch('/api/dialogs/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          dialog_type: newDialog.type,
          title: newDialog.title,
          message: newDialog.message,
          options: newDialog.options,
          user_id: 'system',
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to create dialog');
      }

      const result = await response.json();
      console.log('Dialog created:', result);

      // Reset form and refresh
      setNewDialog({
        type: 'confirmation',
        title: '',
        message: '',
        options: ['Yes', 'No'],
      });
      fetchDialogs();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      console.error('Error creating dialog:', err);
    }
  };

  // Handle dialog action
  const handleDialogAction = async (dialogId: string, action: string) => {
    try {
      const response = await fetch(`/api/dialogs/${dialogId}/action`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          action: action,
          user_id: 'system',
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to record action');
      }

      // Close the dialog
      await fetch(`/api/dialogs/${dialogId}/close`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          action: action,
          user_id: 'system',
        }),
      });

      fetchDialogs();
    } catch (err) {
      console.error('Error handling dialog action:', err);
    }
  };

  // Dismiss a dialog
  const dismissDialog = async (dialogId: string) => {
    try {
      const response = await fetch(`/api/dialogs/${dialogId}/dismiss`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: 'system',
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to dismiss dialog');
      }

      fetchDialogs();
    } catch (err) {
      console.error('Error dismissing dialog:', err);
    }
  };

  // Create specific dialog types
  const createConfirmation = () => {
    setNewDialog({
      type: 'confirmation',
      title: 'Confirm Action',
      message: 'Are you sure you want to perform this action?',
      options: ['Yes', 'No'],
    });
  };

  const createError = () => {
    setNewDialog({
      type: 'error',
      title: 'Error',
      message: 'An error occurred while processing your request.',
      options: ['OK'],
    });
  };

  const createProgress = () => {
    setNewDialog({
      type: 'progress',
      title: 'Processing',
      message: 'Please wait while we process your request...',
      options: [],
    });
  };

  const createInput = () => {
    setNewDialog({
      type: 'input',
      title: 'Input Required',
      message: 'Please enter the required information:',
      options: [],
    });
  };

  if (loading) {
    return <div className='loading'>Loading dialogs...</div>;
  }

  if (error) {
    return <div className='error'>Error: {error}</div>;
  }

  return (
    <div className='modal-system'>
      <div className='header'>
        <h2>Modal System</h2>
        <div className='controls'>
          <button onClick={fetchDialogs} className='refresh-btn'>
            Refresh
          </button>
        </div>
      </div>

      {stats && (
        <div className='stats'>
          <div className='stat-item'>
            <span className='stat-label'>Active Dialogs:</span>
            <span className='stat-value'>{stats.active_dialogs}</span>
          </div>
          <div className='stat-item'>
            <span className='stat-label'>Total Dialogs:</span>
            <span className='stat-value'>{stats.total_dialogs}</span>
          </div>
          <div className='stat-item'>
            <span className='stat-label'>Closed Dialogs:</span>
            <span className='stat-value'>{stats.closed_dialogs}</span>
          </div>
        </div>
      )}

      <div className='dialog-creator'>
        <h3>Create New Dialog</h3>
        <div className='creator-controls'>
          <button onClick={createConfirmation} className='create-btn'>
            Confirmation
          </button>
          <button onClick={createError} className='create-btn'>
            Error
          </button>
          <button onClick={createProgress} className='create-btn'>
            Progress
          </button>
          <button onClick={createInput} className='create-btn'>
            Input
          </button>
        </div>

        <div className='dialog-form'>
          <div className='form-group'>
            <label htmlFor='dialog-type-select'>Type:</label>
            <select
              id='dialog-type-select'
              value={newDialog.type}
              onChange={(e) =>
                setNewDialog({
                  ...newDialog,
                  type: e.target.value as DialogItem['type'],
                })
              }
              aria-label='Dialog type'
              title='Dialog type'
            >
              <option value='confirmation'>Confirmation</option>
              <option value='error'>Error</option>
              <option value='progress'>Progress</option>
              <option value='input'>Input</option>
              <option value='info'>Info</option>
            </select>
          </div>

          <div className='form-group'>
            <label>Title:</label>
            <input
              type='text'
              value={newDialog.title}
              onChange={(e) =>
                setNewDialog({ ...newDialog, title: e.target.value })
              }
              placeholder='Dialog title'
            />
          </div>

          <div className='form-group'>
            <label>Message:</label>
            <textarea
              value={newDialog.message}
              onChange={(e) =>
                setNewDialog({ ...newDialog, message: e.target.value })
              }
              placeholder='Dialog message'
            />
          </div>

          <div className='form-group'>
            <label>Options (comma separated):</label>
            <input
              type='text'
              value={newDialog.options.join(', ')}
              onChange={(e) =>
                setNewDialog({
                  ...newDialog,
                  options: e.target.value.split(',').map((o) => o.trim()),
                })
              }
              placeholder='Option 1, Option 2'
            />
          </div>

          <button onClick={createDialog} className='create-dialog-btn'>
            Create Dialog
          </button>
        </div>
      </div>

      <div className='active-dialogs'>
        <h3>Active Dialogs ({dialogs.length})</h3>

        {dialogs.length === 0 ? (
          <div className='empty-state'>
            <p>No active dialogs.</p>
            <p>Create a new dialog to see it here.</p>
          </div>
        ) : (
          <div className='dialogs-list'>
            {dialogs.map((dialog) => (
              <div key={dialog.id} className='dialog-item'>
                <div className={`dialog-header dialog-type-${dialog.type}`}>
                  <h4>{dialog.title}</h4>
                  <span className='dialog-type'>{dialog.type}</span>
                  <button
                    className='dismiss-btn'
                    onClick={() => dismissDialog(dialog.id)}
                  >
                    ×
                  </button>
                </div>

                <div className='dialog-content'>
                  <p>{dialog.message}</p>

                  {dialog.type === 'progress' && (
                    <div className='progress-container'>
                      <div
                        className={`progress-bar score-fill-${
                          Math.round(
                            Math.max(0, Math.min(100, dialog.progress || 0)) /
                              10
                          ) * 10
                        }`}
                      />
                      <span className='progress-text'>
                        {dialog.progress || 0}%
                      </span>
                    </div>
                  )}

                  {dialog.options && dialog.options.length > 0 && (
                    <div className='dialog-actions'>
                      {dialog.options.map((option: string, index: number) => (
                        <button
                          key={index}
                          onClick={() => handleDialogAction(dialog.id, option)}
                          className='action-btn'
                        >
                          {option}
                        </button>
                      ))}
                    </div>
                  )}

                  <div className='dialog-meta'>
                    <span>
                      Created:{' '}
                      {dialog.created_at
                        ? new Date(dialog.created_at).toLocaleString()
                        : ''}
                    </span>
                    <span>Status: {dialog.status}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default ModalSystem;
