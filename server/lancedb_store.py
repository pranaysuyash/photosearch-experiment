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
            
    def search(self, query_embedding: List[float], limit: int = 20) -> List[Dict[str, Any]]:
        """
        Semantic search for similar vectors.
        """
        if self.table is None:
            return []
            
        try:
            # Search using LanceDB with cosine metric
            # Using metric="cosine" gives us cosine distance (1 - cosine_similarity)
            results = self.table.search(query_embedding, vector_column_name="vector").metric("cosine").limit(limit).to_list()
            
            out = []
            for r in results:
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
