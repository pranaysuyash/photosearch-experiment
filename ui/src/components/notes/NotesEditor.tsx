/**
 * Notes Editor Component
 *
 * Smart collapsible notes editor:
 * - Collapsed by default
 * - Shows [+] Add Note if no notes
 * - Shows truncated preview + [✏️][🗑️] if has notes
 * - Expands to full editor on click
 */
import React, { useState, useEffect } from 'react';
import { Edit3, Save, X, Trash2, Clock, Plus, ChevronDown, ChevronUp } from 'lucide-react';
import { api } from '../../api';
import { glass } from '../../design/glass';

interface NotesEditorProps {
  photoPath: string;
  initialNote?: string;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

export function NotesEditor({
  photoPath,
  initialNote = '',
  size = 'md',
  showLabel = true,
}: NotesEditorProps) {
  const [note, setNote] = useState(initialNote);
  const [isExpanded, setIsExpanded] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  // Keep local state in sync with prop changes
  useEffect(() => {
    setNote(initialNote);
  }, [initialNote]);

  // Load note when component mounts or photo changes
  useEffect(() => {
    const fetchNote = async () => {
      try {
        const fetched = await api.getPhotoNote(photoPath);
        setNote(fetched?.note || '');
        if (fetched?.updated_at) {
          setLastUpdated(fetched.updated_at);
        }
      } catch (err) {
        console.error('Failed to fetch photo note:', err);
      }
    };

    if (photoPath) {
      fetchNote();
    }
  }, [photoPath]);

  const handleEdit = () => {
    setIsExpanded(true);
    setIsEditing(true);
  };

  const handleSave = async () => {
    if (!isEditing) return;

    try {
      setIsLoading(true);
      setError(null);

      if (note.trim() === '') {
        const res = await api.deletePhotoNote(photoPath);
        setLastUpdated(res?.updated_at || new Date().toISOString());
      } else {
        const res = await api.setPhotoNote(photoPath, note.trim());
        setLastUpdated(res?.updated_at || new Date().toISOString());
      }

      setIsEditing(false);
      // Collapse after save if note is empty
      if (!note.trim()) {
        setIsExpanded(false);
      }
    } catch (err) {
      console.error('Failed to save photo note:', err);
      setError('Failed to save note');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancel = () => {
    setNote(initialNote);
    setIsEditing(false);
    // Collapse if canceling and no note exists
    if (!initialNote) {
      setIsExpanded(false);
    }
  };

  const handleDelete = async () => {
    try {
      setIsLoading(true);
      const res = await api.deletePhotoNote(photoPath);
      setNote('');
      setIsEditing(false);
      setIsExpanded(false);
      setLastUpdated(res?.updated_at || new Date().toISOString());
    } catch (err) {
      console.error('Failed to delete photo note:', err);
      setError('Failed to delete note');
    } finally {
      setIsLoading(false);
    }
  };

  const handleNoteChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setNote(e.target.value);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault();
      handleSave();
    }
  };

  const textSizeClass =
    size === 'sm' ? 'text-xs' : size === 'lg' ? 'text-lg' : 'text-sm';
  const textareaRows = size === 'sm' ? 2 : size === 'lg' ? 6 : 3;

  // Truncate preview to ~60 chars
  const notePreview = note.length > 60 ? note.substring(0, 60) + '...' : note;
  const hasNote = note.trim().length > 0;

  return (
    <div className="w-full">
      {/* Collapsed State Header - Always visible */}
      {!isExpanded && (
        <div
          className={`${glass.surfaceStrong} rounded-xl border border-white/10 p-3 cursor-pointer hover:bg-white/5 transition-colors`}
          onClick={hasNote ? () => setIsExpanded(true) : handleEdit}
        >
          <div className="flex items-center justify-between gap-2">
            <div className={`flex items-center gap-2 text-white/60 ${textSizeClass}`}>
              <Edit3 size={size === 'sm' ? 12 : 14} />
              <span className="uppercase tracking-wider font-medium">Notes</span>
            </div>

            {hasNote ? (
              <div className="flex items-center gap-1">
                <button
                  onClick={(e) => { e.stopPropagation(); handleEdit(); }}
                  className="btn-glass btn-glass--muted w-6 h-6 p-0 justify-center"
                  title="Edit note"
                >
                  <Edit3 size={12} />
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); handleDelete(); }}
                  className="btn-glass btn-glass--muted w-6 h-6 p-0 justify-center hover:bg-red-500/10 hover:text-red-400"
                  title="Delete note"
                >
                  <Trash2 size={12} />
                </button>
                <ChevronDown size={14} className="text-white/40 ml-1" />
              </div>
            ) : (
              <div className="flex items-center gap-1 text-white/50">
                <Plus size={14} />
                <span className={textSizeClass}>Add</span>
              </div>
            )}
          </div>

          {/* Preview text when collapsed with content */}
          {hasNote && (
            <div className={`mt-2 text-white/70 ${textSizeClass} line-clamp-2`}>
              {notePreview}
            </div>
          )}
        </div>
      )}

      {/* Expanded State */}
      {isExpanded && (
        <div className={`${glass.surfaceStrong} rounded-xl border border-white/10 p-3`}>
          {/* Header */}
          <div className="flex items-center justify-between gap-2 mb-2">
            <div className={`flex items-center gap-2 text-white/60 ${textSizeClass}`}>
              <Edit3 size={size === 'sm' ? 12 : 14} />
              <span className="uppercase tracking-wider font-medium">Notes</span>
            </div>

            <div className="flex items-center gap-1">
              {!isEditing && lastUpdated && (
                <div className="flex items-center gap-1 text-xs text-white/40 mr-2">
                  <Clock size={10} />
                  <span>{new Date(lastUpdated).toLocaleDateString()}</span>
                </div>
              )}
              <button
                onClick={() => { setIsExpanded(false); setIsEditing(false); }}
                className="btn-glass btn-glass--muted w-6 h-6 p-0 justify-center"
                title="Collapse"
              >
                <ChevronUp size={14} />
              </button>
            </div>
          </div>

          {isEditing ? (
            <>
              <textarea
                value={note}
                onChange={handleNoteChange}
                onKeyDown={handleKeyDown}
                placeholder="Add notes about this photo..."
                className={`w-full bg-transparent border border-white/10 rounded-lg p-2 text-foreground placeholder:text-muted-foreground resize-none focus:outline-none focus:ring-1 focus:ring-primary ${textSizeClass}`}
                rows={textareaRows}
                autoFocus
              />
              <div className="flex items-center justify-end gap-2 mt-2">
                <button
                  onClick={handleCancel}
                  disabled={isLoading}
                  className="btn-glass btn-glass--muted text-xs px-2 py-1"
                  title="Cancel"
                >
                  <X size={12} />
                </button>
                {hasNote && (
                  <button
                    onClick={handleDelete}
                    disabled={isLoading}
                    className="btn-glass btn-glass--muted text-xs px-2 py-1 hover:bg-red-500/10 hover:text-red-400"
                    title="Delete note"
                  >
                    <Trash2 size={12} />
                  </button>
                )}
                <button
                  onClick={handleSave}
                  disabled={isLoading || !note.trim()}
                  className="btn-glass btn-glass--primary text-xs px-3 py-1 flex items-center gap-1"
                >
                  {isLoading ? (
                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  ) : (
                    <>
                      <Save size={12} />
                      Save
                    </>
                  )}
                </button>
              </div>
              {error && (
                <div className="text-xs text-destructive mt-2">{error}</div>
              )}
            </>
          ) : (
            <>
              <div className={`whitespace-pre-wrap break-words text-foreground ${textSizeClass}`}>
                {note}
              </div>
              <div className="flex justify-end mt-2">
                <button
                  onClick={handleEdit}
                  className="btn-glass btn-glass--muted text-xs px-2 py-1 flex items-center gap-1"
                >
                  <Edit3 size={12} />
                  Edit
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

