from server.config import settings
from server.lancedb_store import LanceDBStore
from server.source_items import SourceItemStore
from server.sources import SourceStore
from server.trash_db import TrashDB

from src.intent_recognition import IntentDetector
from src.saved_searches import SavedSearchManager


vector_store = LanceDBStore()
intent_detector = IntentDetector()
saved_search_manager = SavedSearchManager()

source_store = SourceStore(settings.BASE_DIR / "sources.db")
source_item_store = SourceItemStore(settings.BASE_DIR / "sources_items.db")
trash_db = TrashDB(settings.BASE_DIR / "trash.db")
