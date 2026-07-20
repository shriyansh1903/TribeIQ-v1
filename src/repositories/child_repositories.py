from src.repositories.base_repository import BaseRepository

class UsersRepository(BaseRepository):
    def __init__(self):
        super().__init__("users")

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
