import os
import lancedb
import pyarrow as pa
from typing import List, Dict, Any, Optional, Tuple
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


class FaceEmbeddingStore(LanceDBStore):
    """
    Vector store for face embeddings using ArcFace (512-dim).
    
    Stores face embeddings alongside metadata for efficient
    similarity search and clustering operations.
    """
    
    def __init__(self):
        """Initialize face embedding store with dedicated table."""
        super().__init__(table_name="faces")
    
    def add_face(
        self, 
        face_id: str, 
        embedding: List[float], 
        image_path: str,
        bbox: str,  # JSON string: "[x, y, width, height]"
        confidence: float,
        cluster_id: Optional[int] = None,
        embedding_version: str = "arcface_r50_v1",
        age: Optional[int] = None,
        gender: Optional[str] = None
    ):
        """
        Add a single face embedding with metadata.
        
        Args:
            face_id: Unique identifier for this face
            embedding: 512-dim ArcFace embedding
            image_path: Path to source image
            bbox: JSON string of bounding box
            confidence: Detection confidence score
            cluster_id: Optional cluster assignment
            embedding_version: Model version for migration tracking
            age: Optional estimated age
            gender: Optional estimated gender ('M' or 'F')
        """
        metadata = {
            'image_path': image_path,
            'bbox': bbox,
            'confidence': confidence,
            'embedding_version': embedding_version,
        }
        if cluster_id is not None:
            metadata['cluster_id'] = cluster_id
        if age is not None:
            metadata['age'] = age
        if gender is not None:
            metadata['gender'] = gender
            
        self.add(face_id, embedding, metadata)
    
    def add_faces_batch(self, faces: List[Dict]):
        """
        Add multiple faces in a batch.
        
        Args:
            faces: List of dicts with keys:
                - face_id: str
                - embedding: List[float]
                - image_path: str
                - bbox: str
                - confidence: float
                - cluster_id: Optional[int]
                - embedding_version: str
        """
        if not faces:
            return
            
        ids = []
        embeddings = []
        metadata_list = []
        
        for face in faces:
            ids.append(face['face_id'])
            embeddings.append(face['embedding'])
            metadata_list.append({
                'image_path': face['image_path'],
                'bbox': face['bbox'],
                'confidence': face['confidence'],
                'embedding_version': face.get('embedding_version', 'arcface_r50_v1'),
                'cluster_id': face.get('cluster_id', -1),
                'age': face.get('age', -1),
                'gender': face.get('gender', ''),
            })
        
        self.add_batch(ids, embeddings, metadata_list)
    
    def find_similar_faces(
        self, 
        query_embedding: List[float], 
        limit: int = 20,
        min_confidence: float = 0.0
    ) -> List[Dict]:
        """
        Find faces similar to the query embedding.
        
        Args:
            query_embedding: 512-dim face embedding to search for
            limit: Maximum number of results
            min_confidence: Minimum detection confidence threshold
            
        Returns:
            List of similar faces with similarity scores
        """
        results = self.search(query_embedding, limit=limit)
        
        # Filter by confidence if specified
        if min_confidence > 0:
            results = [
                r for r in results 
                if r.get('metadata', {}).get('confidence', 0) >= min_confidence
            ]
        
        return results
    
    def get_faces_by_image(self, image_path: str) -> List[Dict]:
        """
        Get all faces detected in a specific image.
        
        Args:
            image_path: Path to the image
            
        Returns:
            List of face records from that image
        """
        if self.table is None:
            return []
            
        try:
            # Use SQL-like filter
            results = self.table.search().where(
                f"image_path = '{image_path}'"
            ).to_list()
            
            return [
                {
                    'id': r.get('id'),
                    'confidence': r.get('confidence'),
                    'bbox': r.get('bbox'),
                    'cluster_id': r.get('cluster_id'),
                }
                for r in results
            ]
        except Exception as e:
            print(f"Error getting faces for image: {e}")
            return []
    
    def update_cluster_ids(self, face_cluster_map: Dict[str, int]):
        """
        Update cluster IDs for multiple faces.
        
        Args:
            face_cluster_map: Dict mapping face_id -> cluster_id
        """
        # LanceDB doesn't support direct updates easily,
        # so we'd need to delete and re-add, or use a different approach
        # For now, log this as a TODO for the cluster assignment
        print(f"TODO: Update cluster IDs for {len(face_cluster_map)} faces")
    
    def get_all_embeddings_for_clustering(self) -> Tuple[List[str], Any]:
        """
        Get all face embeddings for clustering.
        
        Returns:
            Tuple of (face_ids, embeddings_array)
        """
        if self.table is None:
            return [], None
            
        try:
            import numpy as np
            
            # Fetch all records
            tbl = self.table.to_arrow()
            face_ids = tbl["id"].to_pylist()
            
            # Get vectors
            vectors = tbl["vector"].to_pylist()
            embeddings = np.array(vectors)
            
            return face_ids, embeddings
        except Exception as e:
            print(f"Error fetching embeddings for clustering: {e}")
            return [], None
    
    def get_face_count(self) -> int:
        """Return total number of faces stored."""
        return self.get_count()


# Convenience function to get singleton instances
_photo_store = None
_face_store = None

def get_photo_store() -> LanceDBStore:
    """Get singleton photo embedding store."""
    global _photo_store
    if _photo_store is None:
        _photo_store = LanceDBStore(table_name="photos")
    return _photo_store

def get_face_store() -> FaceEmbeddingStore:
    """Get singleton face embedding store."""
    global _face_store
    if _face_store is None:
        _face_store = FaceEmbeddingStore()
    return _face_store
