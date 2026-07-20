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
        result = self.collection.insert_one(data)
        return str(result.inserted_id)

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
        return self.collection.find_one({"_id": doc_id})

    def find_all(self, query: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        if self.collection is None:
            return []
        query_filter = query or {}
        return list(self.collection.find(query_filter))

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
            
        result = self.collection.update_one(criteria, {"$set": data})
        return result.modified_count > 0

    def delete(self, doc_id: str) -> bool:
        if self.collection is None:
            return False
        criteria = {"_id": doc_id}
        try:
            if self.collection.count_documents({"_id": ObjectId(doc_id)}) > 0:
                criteria = {"_id": ObjectId(doc_id)}
        except Exception:
            pass
            
        result = self.collection.delete_one(criteria)
        return result.deleted_count > 0
