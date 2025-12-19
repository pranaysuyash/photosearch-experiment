/**
 * Bulk Actions with Undo Component
 *
 * Provides safe bulk operations with undo capability for photo management.
 */
import React, { useState, useEffect, useCallback } from 'react';
import { 
  Undo2, 
  Trash2, 
  Star, 
  Plus, 
  X, 
  Check, 
  AlertTriangle,
  Clock,
  RotateCcw,
  AlertCircle
} from 'lucide-react';
import { api } from '../api';
import { glass } from '../design/glass';

interface BulkAction {
  id: string;
  action_type: string;
  user_id: string;
  affected_paths: string[];
  operation_data: Record<string, any>;
  status: string;
  created_at: string;
  undone_at?: string;
}

interface BulkActionHistoryProps {
  userId: string;
  onUndoAction: (actionId: string) => void;
}

export function BulkActionsHistory({ userId, onUndoAction }: BulkActionHistoryProps) {
  const [history, setHistory] = useState<BulkAction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedAction, setExpandedAction] = useState<string | null>(null);

  useEffect(() => {
    loadHistory();
  }, [userId]);

  const loadHistory = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await api.getBulkActionHistory(userId);
      setHistory(response.actions || []);
    } catch (err) {
      console.error('Failed to load bulk action history:', err);
      setError('Failed to load action history');
    } finally {
      setLoading(false);
    }
  };

  const handleUndo = async (actionId: string) => {
    try {
      await api.undoBulkAction(actionId);
      // Update local state to reflect undone action
      setHistory(history.map(action => 
        action.id === actionId ? { ...action, status: 'undone' } : action
      ));
      
      if (onUndoAction) {
        onUndoAction(actionId);
      }
    } catch (err) {
      console.error('Failed to undo action:', err);
      setError('Failed to undo action');
    }
  };

  const canUndoAction = async (actionId: string): Promise<boolean> => {
    try {
      const response = await api.canUndoBulkAction(actionId);
      return response.can_undo;
    } catch (err) {
      console.error('Failed to check if action can be undone:', err);
      return false;
    }
  };

  const getActionIcon = (actionType: string) => {
    switch (actionType) {
      case 'delete': return <Trash2 size={16} className="text-red-400" />;
      case 'favorite': return <Star size={16} className="text-yellow-400" />;
      case 'tag_add': return <Plus size={16} className="text-green-400" />;
      case 'tag_remove': return <X size={16} className="text-red-400" />;
      case 'move': return <AlertCircle size={16} className="text-blue-400" />;
      case 'copy': return <Copy size={16} className="text-blue-400" />;
      default: return <AlertCircle size={16} className="text-muted-foreground" />;
    }
  };

  const getActionLabel = (actionType: string) => {
    const labels: Record<string, string> = {
      delete: 'Deleted',
      favorite: 'Favorited',
      tag_add: 'Added tags to',
      tag_remove: 'Removed tags from',
      move: 'Moved',
      copy: 'Copied'
    };
    return labels[actionType] || actionType;
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

  if (error) {
    return (
      <div className={`${glass.surface} rounded-xl border border-white/10 p-6`}>
        <div className="text-destructive">{error}</div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-foreground flex items-center gap-2">
          <Clock size={18} />
          Recent Actions
        </h3>
        <button
          onClick={loadHistory}
          className="btn-glass btn-glass--muted text-sm px-3 py-1.5 flex items-center gap-1"
        >
          <RotateCcw size={14} />
          Refresh
        </button>
      </div>

      {history.length === 0 ? (
        <div className={`${glass.surface} rounded-xl border border-white/10 p-8 text-center`}>
          <Clock size={48} className="mx-auto text-muted-foreground mb-4" />
          <h4 className="font-medium text-foreground mb-2">No Recent Actions</h4>
          <p className="text-sm text-muted-foreground">
            Bulk operations will appear here for undo capability.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {history.map((action) => (
            <div 
              key={action.id} 
              className={`${glass.surfaceStrong} rounded-xl border border-white/10 p-4`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3 flex-1">
                  <div className={`p-2 rounded-lg ${
                    action.status === 'undone' 
                      ? 'bg-destructive/20 text-destructive' 
                      : 'bg-primary/10 text-primary'
                  }`}>
                    {getActionIcon(action.action_type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-foreground">
                        {getActionLabel(action.action_type)}
                      </span>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        action.status === 'undone' 
                          ? 'bg-destructive/20 text-destructive' 
                          : 'bg-primary/20 text-primary'
                      }`}>
                        {action.status === 'undone' ? 'Undone' : 'Completed'}
                      </span>
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {action.affected_paths.length} {action.affected_paths.length === 1 ? 'photo' : 'photos'}
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      {new Date(action.created_at).toLocaleString()}
                    </div>
                  </div>
                </div>
                
                <div className="flex items-center gap-2">
                  {action.status !== 'undone' && (
                    <button
                      onClick={() => handleUndo(action.id)}
                      disabled={isUndoing}
                      className="btn-glass btn-glass--primary text-xs px-3 py-1.5 flex items-center gap-1"
                    >
                      <Undo2 size={12} />
                      Undo
                    </button>
                  )}
                  
                  <button
                    onClick={() => setExpandedAction(expandedAction === action.id ? null : action.id)}
                    className="btn-glass btn-glass--muted w-8 h-8 p-0 flex items-center justify-center"
                  >
                    {expandedAction === action.id ? <X size={14} /> : <AlertTriangle size={14} />}
                  </button>
                </div>
              </div>
              
              {expandedAction === action.id && (
                <div className={`${glass.surface} rounded-lg border border-white/5 mt-3 p-3`}>
                  <h4 className="font-medium text-foreground mb-2">Affected Photos</h4>
                  <div className="space-y-1 max-h-32 overflow-y-auto">
                    {action.affected_paths.slice(0, 10).map((path, idx) => (
                      <div key={idx} className="text-xs text-muted-foreground truncate">
                        {path.split('/').pop()}
                      </div>
                    ))}
                    {action.affected_paths.length > 10 && (
                      <div className="text-xs text-muted-foreground">
                        ...and {action.affected_paths.length - 10} more
                      </div>
                    )}
                  </div>
                  
                  <div className="mt-3 pt-3 border-t border-white/5">
                    <div className="text-xs text-muted-foreground">
                      Action ID: {action.id.substring(0, 8)}
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function BulkActionsPanel() {
  const [showHistory, setShowHistory] = useState(false);
  const [recentAction, setRecentAction] = useState<BulkAction | null>(null);
  const [showUndoToast, setShowUndoToast] = useState(false);

  // Listen for bulk actions via context or event system
  useEffect(() => {
    const handleBulkAction = (action: BulkAction) => {
      setRecentAction(action);
      setShowUndoToast(true);
      
      // Auto-hide the toast after 5 seconds if not interacted with
      setTimeout(() => {
        setShowUndoToast(false);
      }, 5000);
    };

    // In a real app, this would be an event listener
    // For now, we'll just simulate it
    // window.addEventListener('bulk-action-completed', handleBulkAction);

    return () => {
      // window.removeEventListener('bulk-action-completed', handleBulkAction);
    };
  }, []);

  const handleUndoRecent = async () => {
    if (!recentAction) return;
    
    try {
      await api.undoBulkAction(recentAction.id);
      setRecentAction(null);
      setShowUndoToast(false);
    } catch (err) {
      console.error('Failed to undo recent action:', err);
    }
  };

  return (
    <div className="relative">
      {/* Undo Toast for Recent Actions */}
      {showUndoToast && recentAction && (
        <div className={`${glass.surfaceStrong} fixed bottom-4 right-4 z-[1600] border border-white/10 rounded-xl shadow-2xl max-w-sm w-full`}>
          <div className="p-4">
            <div className="flex items-start gap-3">
              <div className="p-2 rounded-lg bg-primary/10 text-primary flex-shrink-0">
                <Undo2 size={20} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-medium text-foreground">
                  {recentAction.action_type === 'delete' ? 'Photos Deleted' : 'Operation Completed'}
                </div>
                <div className="text-sm text-muted-foreground mt-1">
                  {recentAction.affected_paths.length} photo{recentAction.affected_paths.length !== 1 ? 's' : ''} affected
                </div>
              </div>
              <button
                onClick={() => setShowUndoToast(false)}
                className="btn-glass btn-glass--muted w-8 h-8 p-0 flex items-center justify-center flex-shrink-0"
              >
                <X size={16} />
              </button>
            </div>
            
            <div className="flex gap-2 mt-3">
              <button
                onClick={handleUndoRecent}
                className="btn-glass btn-glass--primary flex-1 text-sm py-2"
              >
                <Undo2 size={14} className="mr-1" />
                Undo Action
              </button>
              <button
                onClick={() => {
                  setShowUndoToast(false);
                  setRecentAction(null);
                }}
                className="btn-glass btn-glass--muted text-sm py-2 px-4"
              >
                Dismiss
              </button>
            </div>
          </div>
        </div>
      )}

      {/* History Modal */}
      {showHistory && (
        <div className="fixed inset-0 z-[1500] flex items-center justify-center p-4">
          <div 
            className="absolute inset-0 bg-black/80 backdrop-blur-sm" 
            onClick={() => setShowHistory(false)} 
          />
          
          <div className={`${glass.surface} ${glass.surfaceStrong} rounded-2xl border border-white/10 shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden`}>
            <div className="flex items-center justify-between p-6 border-b border-white/10">
              <h3 className="text-xl font-semibold text-foreground flex items-center gap-2">
                <Clock size={24} />
                Action History
              </h3>
              <button
                onClick={() => setShowHistory(false)}
                className="btn-glass btn-glass--muted w-10 h-10 p-0 flex items-center justify-center"
              >
                <X size={20} />
              </button>
            </div>
            
            <div className="p-6 overflow-y-auto max-h-[calc(90vh-150px)]">
              <BulkActionsHistory 
                userId="current_user_id" 
                onUndoAction={(actionId) => {
                  // Refresh any affected UI
                }} 
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}