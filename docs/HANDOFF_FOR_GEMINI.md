# Handoff for Gemini: UI Search Toggle Implementation
**From:** Claude  
**Date:** 2025-12-08 01:00  
**Priority:** HIGH

---

## 🎯 Task: Add Search Mode Toggle to UI

User approved adding a toggle between Semantic and Metadata search in the UI.

---

## Files to Modify

### 1. `ui/src/api.ts`
**Add this method:**
```typescript
searchSemantic: async (query: string, limit: number = 50) => {
  const res = await axios.get(`${API_BASE}/search/semantic`, { 
    params: { query, limit } 
  });
  return res.data;
},
```

### 2. `ui/src/App.tsx`
**Add state for search mode:**
```typescript
const [searchMode, setSearchMode] = useState<'semantic' | 'metadata'>('semantic');
```

**Add toggle UI near search bar:**
```tsx
<div className="flex gap-2 text-xs">
  <button 
    onClick={() => setSearchMode('semantic')}
    className={searchMode === 'semantic' ? 'text-primary' : 'text-muted-foreground'}
  >
    🧠 Semantic
  </button>
  <button 
    onClick={() => setSearchMode('metadata')}
    className={searchMode === 'metadata' ? 'text-primary' : 'text-muted-foreground'}
  >
    📋 Metadata
  </button>
</div>
```

**Pass mode to PhotoGrid:**
```tsx
<PhotoGrid query={debouncedSearch} mode={searchMode} />
```

### 3. `ui/src/components/PhotoGrid.tsx`
**Accept mode prop and use correct API:**
```typescript
interface PhotoGridProps {
  query: string;
  mode?: 'semantic' | 'metadata';
}

// In the fetch function:
const results = mode === 'semantic' 
  ? await api.searchSemantic(query)
  : await api.search(query);
```

---

## Testing

1. Start server: `python server/main.py`
2. Start UI: `cd ui && npm run dev`
3. Open http://localhost:5173
4. Type a query, toggle between modes, verify results differ

---

## Bonus Ideas (If Time)

- [ ] Add loading indicator: "Generating embedding..." for semantic search
- [ ] Show badge on results: "🧠" or "📋" to indicate source
- [ ] Add keyboard shortcut: `Cmd+Shift+S` to toggle mode

---

**Gemini, you're cleared to proceed!**

*— Claude*
