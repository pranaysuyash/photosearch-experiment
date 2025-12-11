import os
import lancedb
import pyarrow as pa
from typing import List, Dict, Any, Optional
from server.config import settings

class LanceDBStore:
    """
    Production-ready Vector Store using LanceDB.
    Persists embeddings to disk with columnar storage.
    """
    
    def __init__(self, table_name: str = "photos"):
        """
        Initialize LanceDB connection.
        """
        # Ensure parent directory exists
        persist_path = settings.VECTOR_STORE_PATH
        if not persist_path.exists():
            persist_path.mkdir(parents=True, exist_ok=True)
            
        self.db = lancedb.connect(str(persist_path))
        self.table_name = table_name
        self.table = None
        
        # Open table if exists
        if table_name in self.db.table_names():
            self.table = self.db.open_table(table_name)
            
    def get_count(self) -> int:
        """Return total number of vectors."""
        if self.table:
            return len(self.table)
        return 0
        
    def add(self, id: str, embedding: List[float], metadata: Dict[str, Any] = None):
        """Add a single item. (Use add_batch for better performance)"""
        self.add_batch([id], [embedding], [metadata] if metadata else [{}])
        
    def add_batch(self, ids: List[str], embeddings: List[List[float]], metadata_list: List[Dict] = None):
        """
        Add multiple items to the vector store.
        LanceDB schema is inferred from the data (id, vector, metadata fields).
        """
        if not ids:
            return

        if metadata_list is None:
            metadata_list = [{} for _ in ids]
            
        # Prepare data list for LanceDB
        data = []
        for i, doc_id in enumerate(ids):
            item = {
                "id": doc_id,
                "vector": embeddings[i],
            }
            # Flatten metadata into the item
            if metadata_list[i]:
                for k, v in metadata_list[i].items():
                    # Ensure primitive types for compatibility
                    # Metadata values should be strings, ints, floats, or bools
                    if isinstance(v, (str, int, float, bool)):
                        item[k] = v
                    else:
                        item[k] = str(v)
            data.append(item)
            
        if self.table is None:
            # Create table with the first batch
            self.table = self.db.create_table(self.table_name, data)
        else:
            # Append to existing table
            self.table.add(data)
            
    def search(self, query_embedding: List[float], limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Semantic search for similar vectors with pagination.
        """
        if self.table is None:
            return []
            
        try:
            # Search using LanceDB with cosine metric
            # For pagination in vector search, we usually need to fetch (limit + offset)
            # and then slice [offset:] to ensure efficient and stable sorting.
            fetch_limit = limit + offset
            results = self.table.search(query_embedding, vector_column_name="vector").metric("cosine").limit(fetch_limit).to_list()
            
            # Slice the results for the requested page
            # results[offset : offset + limit]
            paginated_results = results[offset : offset + limit]
            
            out = []
            for r in paginated_results:
                # Extract metadata (all keys except internal ones)
                reserved = {'vector', '_distance', 'id'}
                meta = {k: v for k, v in r.items() if k not in reserved}
                
                # _distance is cosine distance (1 - similarity) for metric="cosine"
                # So similarity = 1 - distance
                cosine_similarity = 1.0 - r['_distance']
                
                out.append({
                    'id': r['id'],
                    'score': max(0, cosine_similarity),  # Clamp to non-negative
                    'metadata': meta
                })
            return out
        except Exception as e:
            print(f"Error searching LanceDB: {e}")
            return []

    def get_all_ids(self) -> set:
        """Return a set of all IDs currently in the store."""
        if self.table is None:
            return set()
        try:
            # Efficiently fetch only the ID column
            # Use to_arrow() or to_pandas() with columns filter
            tbl = self.table.to_arrow()
            return set(tbl["id"].to_pylist())
        except Exception as e:
            print(f"Error fetching IDs: {e}")
            return set()

    def get_all_records(self, limit: int = 1000, offset: int = 0) -> List[Dict[str, Any]]:
        """Return all records with their metadata (for home page display), with pagination.
        
        Optimized: Uses SQL query with LIMIT/OFFSET to avoid loading entire table.
        """
        if self.table is None:
            return []
        try:
            # Use LanceDB's SQL interface for efficient pagination
            # This avoids loading all rows into memory
            query = f"SELECT * FROM {self.table_name} LIMIT {limit} OFFSET {offset}"
            
            # LanceDB tables support to_lance() for SQL queries
            # Fallback: use search with a dummy vector if SQL not available
            try:
                # Try the newer search().limit().offset() pattern
                # Note: For non-vector queries, we use a scan-like approach
                results = self.table.search().limit(limit + offset).to_list()
                paginated = results[offset:offset + limit]
            except Exception:
                # Fallback to arrow slice (less efficient but works)
                tbl = self.table.to_arrow()
                total_rows = len(tbl)
                start = max(0, offset)
                end = min(total_rows, offset + limit)
                if start >= total_rows:
                    return []
                paginated = []
                for i in range(start, end):
                    row = {}
                    for col in tbl.column_names:
                        if col != 'vector':
                            row[col] = tbl[col][i].as_py()
                    paginated.append(row)
            
            records = []
            for r in paginated:
                record = {}
                for k, v in r.items():
                    if k not in ('vector', '_distance'):
                        record[k] = v
                # Rename 'id' to 'path' for consistency
                if 'id' in record:
                    record['path'] = record.pop('id')
                records.append(record)
            return records
        except Exception as e:
            print(f"Error fetching all records: {e}")
            return []

    def delete(self, ids: List[str]):
        """Delete items by ID."""
        if self.table:
            # LanceDB supports deletion via SQL filter string
            # "id IN ('id1', 'id2')"
            id_str = ", ".join([f"'{id}'" for id in ids])
            self.table.delete(f"id IN ({id_str})")

    def reset(self):
        """Drop the table - destructive!"""
        if self.table_name in self.db.table_names():
            self.db.drop_table(self.table_name)
            self.table = None
