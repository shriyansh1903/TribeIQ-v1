from src.repositories.base_repository import BaseRepository

class UsersRepository(BaseRepository):
    def __init__(self):
        super().__init__("users")

    def find_by_username(self, username: str):
        if self.collection is None:
            return None
        try:
            return self.collection.find_one({"username": username})
        except Exception:
            return None

    def increment_failed_attempts(self, username: str, lock_until=None):
        if self.collection is None:
            return
        try:
            update_data = {"$inc": {"failed_attempts": 1}}
            if lock_until:
                update_data["$set"] = {"locked_until": lock_until}
            self.collection.update_one({"username": username}, update_data)
        except Exception:
            pass

    def reset_failed_attempts(self, username: str):
        if self.collection is None:
            return
        try:
            self.collection.update_one(
                {"username": username}, 
                {"$set": {"failed_attempts": 0, "locked_until": None}}
            )
        except Exception:
            pass


class PropertiesRepository(BaseRepository):
    def __init__(self):
        super().__init__("properties")

class ResidentsRepository(BaseRepository):
    def __init__(self):
        super().__init__("residents")

class EventsRepository(BaseRepository):
    def __init__(self):
        super().__init__("events")

class CalendarEventsRepository(BaseRepository):
    def __init__(self):
        super().__init__("calendar_events")

class RecommendationsRepository(BaseRepository):
    def __init__(self):
        super().__init__("recommendations")

class VendorsRepository(BaseRepository):
    def __init__(self):
        super().__init__("vendors")

class MaterialsRepository(BaseRepository):
    def __init__(self):
        super().__init__("materials")

class StallsRepository(BaseRepository):
    def __init__(self):
        super().__init__("stalls")

class ExternalEventsRepository(BaseRepository):
    def __init__(self):
        super().__init__("external_events")

class SettingsRepository(BaseRepository):
    def __init__(self):
        super().__init__("settings")

class EventWorkspacesRepository(BaseRepository):
    def __init__(self):
        super().__init__("event_workspaces")
        self._ensure_indexes()

    def _ensure_indexes(self):
        if self.collection is not None:
            try:
                self.collection.create_index("workspace_id", unique=True)
                self.collection.create_index("event_id")
            except Exception:
                pass

    def find_by_workspace_id(self, workspace_id: str):
        if self.collection is None:
            return None
        try:
            return self.collection.find_one({"workspace_id": workspace_id})
        except Exception:
            return None

    def find_by_event_id(self, event_id: str):
        if self.collection is None:
            return None
        try:
            return self.collection.find_one({"event_id": str(event_id)})
        except Exception:
            return None


class TasksRepository(BaseRepository):
    def __init__(self):
        super().__init__("tasks")
        self._ensure_indexes()

    def _ensure_indexes(self):
        if self.collection is not None:
            try:
                self.collection.create_index("task_id", unique=True)
                self.collection.create_index("workspace_id")
                self.collection.create_index("assigned_user")
            except Exception:
                pass

    def find_by_task_id(self, task_id: str):
        if self.collection is None:
            return None
        try:
            return self.collection.find_one({"task_id": task_id})
        except Exception:
            return None

    def find_by_workspace(self, workspace_id: str):
        return self.find_all({"workspace_id": workspace_id})


class RunOfShowRepository(BaseRepository):
    def __init__(self):
        super().__init__("run_of_show")
        self._ensure_indexes()

    def _ensure_indexes(self):
        if self.collection is not None:
            try:
                self.collection.create_index("ros_id", unique=True)
                self.collection.create_index("workspace_id")
            except Exception:
                pass

    def find_by_workspace(self, workspace_id: str):
        if self.collection is None:
            return []
        try:
            return list(self.collection.find({"workspace_id": workspace_id}).sort("start_time", 1))
        except Exception:
            return []


