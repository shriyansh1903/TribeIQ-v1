from typing import Any, Dict, List, Optional
from bson import ObjectId
from src.database import db_manager

class BaseRepository:
    def __init__(self, collection_name: str):
        self.collection_name = collection_name

    @property
    def collection(self):
        return db_manager.get_collection(self.collection_name)

    def insert(self, data: Dict[str, Any]) -> str:
        if self.collection is None:
            return ""
        try:
            result = self.collection.insert_one(data)
            return str(result.inserted_id)
        except Exception:
            return ""

    def find_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        if self.collection is None:
            return None
        # Try finding by ObjectId or by string representation
        try:
            res = self.collection.find_one({"_id": ObjectId(doc_id)})
            if res:
                return res
        except Exception:
            pass
        try:
            return self.collection.find_one({"_id": doc_id})
        except Exception:
            return None

    def find_all(self, query: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        if self.collection is None:
            return []
        query_filter = query or {}
        try:
            return list(self.collection.find(query_filter))
        except Exception:
            return []

    def update(self, doc_id: str, data: Dict[str, Any]) -> bool:
        if self.collection is None:
            return False
        # Try both ObjectId and string
        criteria = {"_id": doc_id}
        try:
            if self.collection.count_documents({"_id": ObjectId(doc_id)}) > 0:
                criteria = {"_id": ObjectId(doc_id)}
        except Exception:
            pass
            
        try:
            result = self.collection.update_one(criteria, {"$set": data})
            return result.modified_count > 0
        except Exception:
            return False

    def delete(self, doc_id: str) -> bool:
        if self.collection is None:
            return False
        criteria = {"_id": doc_id}
        try:
            if self.collection.count_documents({"_id": ObjectId(doc_id)}) > 0:
                criteria = {"_id": ObjectId(doc_id)}
        except Exception:
            pass
            
        try:
            result = self.collection.delete_one(criteria)
            return result.deleted_count > 0
        except Exception:
            return False
