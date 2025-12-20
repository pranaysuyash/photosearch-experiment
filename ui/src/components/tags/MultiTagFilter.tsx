/**
 * Multi-Tag Filtering Component
 *
 * Provides advanced tag filtering with AND/OR logic for photo searches.
 */
import React, { useState, useEffect } from 'react';
import {
  Tags,
  Plus,
  X,
  Search,
  Filter,
  CircleEllipsis,
  CircleCheck,
  CircleX,
  ArrowRightLeft,
  Hash,
  CheckCircle,
  MinusCircle,
} from 'lucide-react';
import { api } from '../api';
import { glass } from '../design/glass';

interface TagExpression {
  id: string;
  tag: string;
  operator: 'has' | 'not_has' | 'maybe_has'; // 'has' = include, 'not_has' = exclude, 'maybe_has' = optional
}

interface TagFilter {
  id: string;
  name: string;
  tag_expressions: TagExpression[];
  combination_operator: 'AND' | 'OR';
  created_at: string;
  updated_at: string;
}

interface MultiTagFilterProps {
  initialOperator?: 'AND' | 'OR';
  initialExpressions?: TagExpression[];
  onFilterChange: (tags: string[], operator: 'AND' | 'OR') => void;
  onSearch: (results: any[]) => void;
}

export function MultiTagFilter({
  initialOperator = 'OR',
  initialExpressions = [],
  onFilterChange,
  onSearch,
}: MultiTagFilterProps) {
  const [operator, setOperator] = useState<'AND' | 'OR'>(initialOperator);
  const [expressions, setExpressions] =
    useState<TagExpression[]>(initialExpressions);
  const [newTag, setNewTag] = useState('');
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedFilters, setSavedFilters] = useState<TagFilter[]>([]);
  const [showSavedFilters, setShowSavedFilters] = useState(false);

  // Load saved filters
  useEffect(() => {
    loadSavedFilters();
  }, []);

  const loadSavedFilters = async () => {
    try {
      const response = await api.getTagFilters();
      setSavedFilters(response.filters || []);
    } catch (err) {
      console.error('Failed to load saved filters:', err);
    }
  };

  const addTagExpression = () => {
    if (!newTag.trim()) return;

    const newExpression: TagExpression = {
      id: Date.now().toString(),
      tag: newTag.trim(),
      operator: 'has', // Default to 'has' (include)
    };

    setExpressions([...expressions, newExpression]);
    setNewTag('');
    setShowSuggestions(false);
  };

  const removeTagExpression = (id: string) => {
    setExpressions(expressions.filter((expr) => expr.id !== id));
  };

  const updateTagExpression = (id: string, updates: Partial<TagExpression>) => {
    setExpressions(
      expressions.map((expr) =>
        expr.id === id ? { ...expr, ...updates } : expr
      )
    );
  };

  const handleTagInput = async (value: string) => {
    setNewTag(value);

    if (value.length > 2) {
      try {
        const results = await api.searchTags(value);
        setSuggestions(results || []);
        setShowSuggestions(true);
      } catch (err) {
        console.error('Failed to search tags:', err);
        setSuggestions([]);
      }
    } else {
      setShowSuggestions(false);
    }
  };

  const applyFilter = async () => {
    if (expressions.length === 0) {
      // If no expressions, clear the filter
      onFilterChange([], operator);
      onSearch([]);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const tagList = expressions
        .filter((expr) => expr.operator !== 'not_has') // Only include 'has' and 'maybe_has' for search
        .map((expr) => expr.tag);

      if (tagList.length === 0) {
        onFilterChange([], operator);
        onSearch([]);
        return;
      }

      const excludeTags = expressions
        .filter((expr) => expr.operator === 'not_has')
        .map((expr) => expr.tag);

      // In a real implementation, we would call an API endpoint that supports
      // multi-tag filtering with the specified operator
      const response = await api.getPhotosByTags(
        tagList,
        operator,
        excludeTags
      );

      onFilterChange(tagList, operator);
      onSearch(response.photos || response || []);
    } catch (err) {
      console.error('Failed to apply filter:', err);
      setError('Failed to apply filter');
    } finally {
      setLoading(false);
    }
  };

  const saveFilter = async () => {
    if (expressions.length === 0) return;

    try {
      const filterName = prompt('Enter a name for this filter:');
      if (!filterName) return;

      const newFilter = await api.createTagFilter(
        filterName,
        expressions,
        operator
      );

      setSavedFilters([...savedFilters, newFilter]);
    } catch (err) {
      console.error('Failed to save filter:', err);
      setError('Failed to save filter');
    }
  };

  const loadFilter = (filter: TagFilter) => {
    setExpressions(filter.tag_expressions);
    setOperator(filter.combination_operator);
    setShowSavedFilters(false);
  };

  const clearFilter = () => {
    setExpressions([]);
    setNewTag('');
    onFilterChange([], operator);
    onSearch([]);
  };

  const operatorOptions = [
    {
      value: 'AND',
      label: 'All tags (AND)',
      desc: 'Photos must have ALL of these tags',
    },
    {
      value: 'OR',
      label: 'Any tag (OR)',
      desc: 'Photos can have ANY of these tags',
    },
  ];

  const operatorIcons = {
    AND: <CircleCheck size={16} />,
    OR: <ArrowRightLeft size={16} />,
  };

  return (
    <div
      className={`${glass.surfaceStrong} rounded-xl border border-white/10 p-4`}
    >
      <div className='flex items-center justify-between mb-4'>
        <div className='flex items-center gap-2'>
          <Tags size={20} className='text-foreground' />
          <h3 className='font-medium text-foreground'>Multi-Tag Filter</h3>
        </div>

        <div className='flex items-center gap-2'>
          <button
            onClick={saveFilter}
            disabled={expressions.length === 0}
            className='btn-glass btn-glass--muted text-xs px-2 py-1.5 flex items-center gap-1'
            title='Save this filter for later'
          >
            <Hash size={14} />
            Save
          </button>

          <button
            onClick={() => setShowSavedFilters(!showSavedFilters)}
            className='btn-glass btn-glass--muted text-xs px-2 py-1.5'
            title='Saved filters'
          >
            <CircleEllipsis size={14} />
          </button>
        </div>
      </div>

      {/* Operator Selection */}
      <div className='mb-4'>
        <label className='block text-sm font-medium text-foreground mb-2'>
          Combine tags with
        </label>
        <div className='grid grid-cols-2 gap-2'>
          {operatorOptions.map((option) => (
            <button
              key={option.value}
              onClick={() => setOperator(option.value as 'AND' | 'OR')}
              className={`p-3 rounded-lg border text-left ${
                operator === option.value
                  ? 'border-primary bg-primary/10 text-foreground'
                  : 'border-white/10 hover:border-white/20 text-muted-foreground'
              }`}
            >
              <div className='flex items-center gap-2 mb-1'>
                {operatorIcons[option.value as 'AND' | 'OR']}
                <span className='font-medium'>{option.label}</span>
              </div>
              <div className='text-xs'>{option.desc}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Tag Expression Builder */}
      <div className='mb-4'>
        <label className='block text-sm font-medium text-foreground mb-2'>
          Add Tags
        </label>

        <div className='flex gap-2 mb-3'>
          <div className='relative flex-1'>
            <input
              type='text'
              value={newTag}
              onChange={(e) => handleTagInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && newTag.trim()) {
                  e.preventDefault();
                  addTagExpression();
                } else if (e.key === 'Escape') {
                  setShowSuggestions(false);
                }
              }}
              placeholder='Type a tag...'
              className='w-full px-3 py-2 rounded-lg border border-white/10 bg-white/5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary'
            />

            {showSuggestions && suggestions.length > 0 && (
              <div
                className={`${glass.surfaceStrong} absolute z-10 mt-1 w-full border border-white/10 rounded-lg shadow-lg max-h-60 overflow-y-auto`}
              >
                {suggestions.map((suggestion, index) => (
                  <button
                    key={index}
                    onClick={() => {
                      setNewTag(suggestion);
                      setShowSuggestions(false);
                    }}
                    className='w-full text-left px-3 py-2 hover:bg-white/5 text-foreground truncate'
                  >
                    #{suggestion}
                  </button>
                ))}
              </div>
            )}
          </div>

          <button
            onClick={addTagExpression}
            disabled={!newTag.trim()}
            className='btn-glass btn-glass--primary px-3 py-2 flex items-center gap-1'
          >
            <Plus size={16} />
            Add
          </button>
        </div>

        {/* Current Expressions */}
        {expressions.length > 0 && (
          <div className='space-y-2'>
            {expressions.map((expr, index) => (
              <div
                key={expr.id}
                className='flex items-center gap-2 p-2 bg-white/5 rounded-lg'
              >
                <select
                  value={expr.operator}
                  onChange={(e) =>
                    updateTagExpression(expr.id, {
                      operator: e.target.value as any,
                    })
                  }
                  className='px-2 py-1 rounded border border-white/10 bg-white/5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary text-sm'
                >
                  <option value='has'>Include</option>
                  <option value='not_has'>Exclude</option>
                  <option value='maybe_has'>Optional</option>
                </select>

                <span className='text-foreground flex-1 text-sm'>
                  #{expr.tag}
                </span>

                <button
                  onClick={() => removeTagExpression(expr.id)}
                  className='btn-glass btn-glass--muted w-8 h-8 p-0 flex items-center justify-center'
                  title='Remove tag'
                >
                  <X size={14} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Filter Actions */}
      <div className='flex flex-wrap gap-2'>
        <button
          onClick={applyFilter}
          disabled={loading || expressions.length === 0}
          className='btn-glass btn-glass--primary flex items-center gap-2 px-3 py-2'
        >
          {loading ? (
            <div className='w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin' />
          ) : (
            <Search size={16} />
          )}
          Apply Filter
        </button>

        <button
          onClick={clearFilter}
          className='btn-glass btn-glass--muted flex items-center gap-2 px-3 py-2'
        >
          <X size={16} />
          Clear
        </button>
      </div>

      {/* Saved Filters Dropdown */}
      {showSavedFilters && (
        <div
          className={`${glass.surfaceStrong} absolute z-[1000] mt-1 w-64 border border-white/10 rounded-lg shadow-lg right-4 top-full`}
        >
          <div className='p-2 border-b border-white/10'>
            <div className='flex items-center justify-between'>
              <h4 className='text-sm font-medium text-foreground'>
                Saved Filters
              </h4>
              <button
                onClick={() => setShowSavedFilters(false)}
                className='btn-glass btn-glass--muted w-6 h-6 p-0'
              >
                <X size={12} />
              </button>
            </div>
          </div>

          {savedFilters.length === 0 ? (
            <div className='p-4 text-center text-sm text-muted-foreground'>
              No saved filters
            </div>
          ) : (
            <div className='max-h-60 overflow-y-auto'>
              {savedFilters.map((filter) => (
                <button
                  key={filter.id}
                  onClick={() => loadFilter(filter)}
                  className='w-full text-left px-3 py-2 hover:bg-white/5 text-foreground text-sm flex items-center justify-between'
                >
                  <span>{filter.name}</span>
                  <span className='text-xs text-muted-foreground'>
                    {filter.combination_operator} •{' '}
                    {filter.tag_expressions.length} tags
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className='mt-3 text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-lg p-3'>
          {error}
          <button className='ml-2' onClick={() => setError(null)}>
            <X size={16} />
          </button>
        </div>
      )}
    </div>
  );
}

export default MultiTagFilter;
