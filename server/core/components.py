from server.config import settings

from src.code_splitting import CodeSplittingConfig, LazyLoadPerformanceTracker
from src.face_clustering import FaceClusterer
from src.modal_system import ModalSystem
from src.ocr_search import OCRSearch
from src.tauri_integration import TauriIntegration
from src.video_analysis import VideoAnalyzer


# Initialize Face Clustering with explicit paths
face_clusterer = FaceClusterer(
    db_path=str(settings.FACE_CLUSTERS_DB_PATH),
    models_dir=str(settings.BASE_DIR / "models"),
)

# Initialize OCR Search
ocr_search = OCRSearch()

# Initialize Modal System
modal_system = ModalSystem()

# Initialize Code Splitting
code_splitting_config = CodeSplittingConfig()
lazy_load_tracker = LazyLoadPerformanceTracker()

# Initialize Tauri Integration
tauri_integration = TauriIntegration()

# Initialize Video Analyzer
video_analyzer = VideoAnalyzer(
    db_path=str(settings.BASE_DIR / "video_analysis.db"),
    cache_dir=str(settings.BASE_DIR / "cache" / "video"),
)
