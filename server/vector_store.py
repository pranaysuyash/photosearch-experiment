import numpy as np
import pickle
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

class VectorStore:
    """
    Simple in-memory vector store with persistence to disk.
    Uses numpy for efficient cosine similarity calculations.
    """
    
    def __init__(self):
        """Initialize empty vector store."""
        self.ids: List[str] = []
        self.embeddings: Optional[np.ndarray] = None
        self.metadata: List[Dict[str, Any]] = []
        
    def add(self, id: str, embedding: List[float], metadata: Dict[str, Any] = None):
        """
        Add a vector to the store.
        
        Args:
            id: Unique identifier for the item (e.g., file path)
            embedding: Vector embedding (list of floats)
            metadata: Associated metadata dictionary
        """
        if metadata is None:
            metadata = {}
            
        self.ids.append(id)
        self.metadata.append(metadata)
        
        # Convert to numpy array and normalize immediately for faster search later
        # (Normalization makes cosine similarity equivalent to dot product)
        vector = np.array(embedding, dtype=np.float32)
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
            
        if self.embeddings is None:
            self.embeddings = np.array([vector], dtype=np.float32)
        else:
            self.embeddings = np.vstack([self.embeddings, vector])
            
    def search(self, query_embedding: List[float], limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for similar vectors.
        
        Args:
            query_embedding: Query vector
            limit: Maximum number of results
            
        Returns:
            List of results with keys: id, score, metadata
        """
        if self.embeddings is None or len(self.embeddings) == 0:
            return []
            
        # Prepare query vector
        query = np.array(query_embedding, dtype=np.float32)
        norm = np.linalg.norm(query)
        if norm > 0:
            query = query / norm
            
        # Compute cosine similarity (dot product of normalized vectors)
        scores = np.dot(self.embeddings, query)
        
        # Get top k indices
        # argsort returns lowest to highest, so we take last 'limit' and reverse
        top_k_indices = np.argsort(scores)[-limit:][::-1]
        
        results = []
        for idx in top_k_indices:
            results.append({
                'id': self.ids[idx],
                'score': float(scores[idx]),
                'metadata': self.metadata[idx]
            })
            
        return results
        
    def save(self, path: str):
        """Save index to disk."""
        data = {
            'ids': self.ids,
            'embeddings': self.embeddings,
            'metadata': self.metadata
        }
        try:
            with open(path, 'wb') as f:
                pickle.dump(data, f)
            logger.info(f"Vector store saved to {path} ({len(self.ids)} items)")
        except Exception as e:
            logger.error(f"Failed to save vector store: {e}")
            raise
            
    def load(self, path: str):
        """Load index from disk."""
        path_obj = Path(path)
        if not path_obj.exists():
            logger.warning(f"Vector store not found at {path}, starting empty.")
            return

        try:
            with open(path, 'rb') as f:
                data = pickle.load(f)
            
            self.ids = data['ids']
            self.embeddings = data['embeddings']
            self.metadata = data['metadata']
            logger.info(f"Vector store loaded from {path} ({len(self.ids)} items)")
        except Exception as e:
            logger.error(f"Failed to load vector store: {e}")
            raise
