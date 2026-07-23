from typing import List, Dict, Any, Optional
from src.repositories.base_repository import BaseRepository

class BusinessGraphRepository(BaseRepository):
    """
    Data access repository for Business Graph relationships stored in MongoDB 'business_graph'.
    Inherits from BaseRepository and provides indexed relationship queries.
    """
    def __init__(self):
        super().__init__("business_graph")
        self._ensure_indexes()

    def _ensure_indexes(self):
        if self.collection is not None:
            try:
                self.collection.create_index("edge_id", unique=True)
                self.collection.create_index("source_id")
                self.collection.create_index("target_id")
                self.collection.create_index("relationship")
                self.collection.create_index([("source_id", 1), ("relationship", 1), ("target_id", 1)], unique=True)
            except Exception:
                pass

    def find_relationships(self, query_filter: Dict[str, Any]) -> List[Dict[str, Any]]:
        return self.find_all(query_filter)

    def find_by_edge_id(self, edge_id: str) -> Optional[Dict[str, Any]]:
        if self.collection is None:
            return None
        try:
            return self.collection.find_one({"edge_id": edge_id})
        except Exception:
            return None
