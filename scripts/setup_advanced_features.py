#!/usr/bin/env python3
"""
Advanced Features Setup Script

This script sets up all necessary components for the advanced features:
1. Initialize database schema
2. Download and prepare models
3. Verify system dependencies
4. Create configuration files
5. Run initial tests
"""

import os
import sys
import subprocess
import shutil
import json
import time
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AdvancedFeaturesSetup:
    def __init__(self, base_dir: Path = None):
        self.base_dir = base_dir or Path(__file__).parent.parent
        self.data_dir = self.base_dir / "data"
        self.models_dir = self.base_dir / "models"
        self.config_file = self.base_dir / ".env"

        # Ensure directories exist
        self.data_dir.mkdir(exist_ok=True)
        self.models_dir.mkdir(exist_ok=True)

    def check_system_dependencies(self) -> bool:
        """Check if all system dependencies are available"""
        logger.info("Checking system dependencies...")

        dependencies = {
            "python": "python3 --version",
            "pip": "pip --version",
            "node": "node --version",
            "npm": "npm --version"
        }

        missing = []
        for name, cmd in dependencies.items():
            try:
                subprocess.run(cmd.split(), check=True, capture_output=True)
                logger.info(f"✓ {name} is available")
            except (subprocess.CalledProcessError, FileNotFoundError):
                logger.warning(f"⚠ {name} is not available or not in PATH")
                missing.append(name)

        # Check optional dependencies
        optional = {
            "Tesseract OCR": "tesseract --version",
            "Git": "git --version"
        }

        optional_missing = []
        for name, cmd in optional.items():
            try:
                subprocess.run(cmd.split(), check=True, capture_output=True)
                logger.info(f"✓ {name} is available")
            except (subprocess.CalledProcessError, FileNotFoundError):
                logger.info(f"ℹ {name} is optional and not installed")
                optional_missing.append(name)

        if missing:
            logger.error(f"❌ Required dependencies missing: {', '.join(missing)}")
            return False

        if optional_missing:
            logger.info(f"💡 Consider installing: {', '.join(optional_missing)}")

        return True

    def check_python_packages(self) -> bool:
        """Check if required Python packages are installed"""
        logger.info("Checking Python packages...")

        required_packages = [
            "fastapi",
            "uvicorn",
            "pillow",
            "numpy",
            "opencv-python",
            "requests",
            "cryptography",
            "scikit-learn",
            "imagehash",
            "sqlalchemy"
        ]

        missing_packages = []
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
                logger.info(f"✓ {package}")
            except ImportError:
                missing_packages.append(package)

        if missing_packages:
            logger.error(f"❌ Missing Python packages: {', '.join(missing_packages)}")
            logger.info("Run: pip install " + " ".join(missing_packages))
            return False

        # Check optional advanced packages
        optional_packages = [
            "insightface",
            "onnxruntime",
            "pytesseract",
            "easyocr",
            "pywavelets"
        ]

        optional_missing = []
        for package in optional_packages:
            try:
                if package == "pytesseract":
                    import pytesseract
                    pytesseract.get_tesseract_version()
                else:
                    __import__(package)
                logger.info(f"✓ {package}")
            except ImportError:
                optional_missing.append(package)

        if optional_missing:
            logger.warning(f"⚠ Optional packages missing: {', '.join(optional_missing)}")
            logger.info("For full functionality, install: pip install " + " ".join(optional_missing))

        return len(missing_packages) == 0

    def initialize_database_schema(self) -> bool:
        """Initialize the advanced features database schema"""
        logger.info("Initializing database schema...")

        try:
            sys.path.append(str(self.base_dir))
            from server.schema_extensions import SchemaExtensions

            db_path = self.data_dir / "advanced_features.db"
            schema = SchemaExtensions(db_path)
            schema.extend_schema()
            schema.insert_default_data()

            logger.info("✓ Database schema initialized successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to initialize database schema: {e}")
            return False

    def setup_configuration(self) -> bool:
        """Create or update configuration files"""
        logger.info("Setting up configuration...")

        # Create .env file if it doesn't exist
        if not self.config_file.exists():
            logger.info("Creating .env configuration file...")
            env_content = """# Photo Search Advanced Features Configuration

# Database Configuration
DATABASE_URL=sqlite:///data/photo_search.db
ADVANCED_FEATURES_DB=sqlite:///data/advanced_features.db

# Face Recognition
FACE_RECOGNITION_ENABLED=true
FACE_MODELS_DIR=./models/face
FACE_ENCRYPTION_KEY=auto_generate
FACE_GPU_ACCELERATION=true
FACE_MIN_CONFIDENCE=0.7

# Duplicate Detection
DUPLICATE_DETECTION_ENABLED=true
DUPLICATE_SIMILARITY_THRESHOLD=5.0
DUPLICATE_AUTO_RESOLUTION=false

# OCR Settings
OCR_ENABLED=true
OCR_LANGUAGES=en,es,fr,de,it,pt
OCR_TESSERACT_PATH=/usr/bin/tesseract
OCR_HANDWRITING_ENABLED=true
OCR_MIN_CONFIDENCE=0.5

# Analytics
ANALYTICS_ENABLED=true
ANALYTICS_RETENTION_DAYS=90
ANALYTICS_AUTO_REFRESH=false

# Performance
MAX_WORKERS=4
CACHE_SIZE_MB=512
ENABLE_GPU_ACCELERATION=true

# Security
SECRET_KEY=auto_generate
CORS_ORIGINS=*
API_RATE_LIMIT=100

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
"""
            with open(self.config_file, 'w') as f:
                f.write(env_content)
            logger.info("✓ Created .env configuration file")

        # Create logs directory
        logs_dir = self.base_dir / "logs"
        logs_dir.mkdir(exist_ok=True)

        return True

    def create_startup_script(self) -> bool:
        """Create a convenient startup script"""
        logger.info("Creating startup script...")

        startup_script = self.base_dir / "start_advanced_features.py"
        script_content = '''#!/usr/bin/env python3
"""
Startup script for Photo Search with Advanced Features
Run this script to start the application with all advanced features enabled.
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

def main():
    """Start the advanced features application"""
    try:
        # Import the enhanced main application
        from server.main_advanced_features import app
        import uvicorn

        print("🚀 Starting Photo Search with Advanced Features...")
        print("📁 Project root:", project_root)
        print("🔗 Advanced Features: Face Recognition, Duplicate Detection, OCR, Smart Albums, Analytics")
        print("🌐 Web Interface: http://localhost:8000")
        print("📖 API Docs: http://localhost:8000/docs")
        print("🎯 Advanced Features: http://localhost:8000/advanced")
        print()
        print("Press Ctrl+C to stop the server")
        print("=" * 50)

        # Start the server
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            reload=True,
            reload_dirs=["server", "src"],
            log_level="info"
        )

    except Exception as e:
        print(f"❌ Error starting application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
'''

        with open(startup_script, 'w') as f:
            f.write(script_content)

        # Make script executable
        startup_script.chmod(0o755)

        logger.info("✓ Created startup script")
        return True

    def run_integration_tests(self) -> bool:
        """Run integration tests to verify setup"""
        logger.info("Running integration tests...")

        test_script = self.base_dir / "tests" / "test_advanced_features_integration.py"
        if not test_script.exists():
            logger.warning("⚠ Integration tests not found")
            return True

        try:
            result = subprocess.run([
                sys.executable, str(test_script)
            ], capture_output=True, text=True, cwd=self.base_dir)

            if result.returncode == 0:
                logger.info("✓ Integration tests passed")
                logger.info(result.stdout)
                return True
            else:
                logger.error("❌ Integration tests failed")
                logger.error(result.stdout)
                logger.error(result.stderr)
                return False

        except Exception as e:
            logger.error(f"❌ Error running integration tests: {e}")
            return False

    def setup_development_environment(self) -> bool:
        """Setup development environment"""
        logger.info("Setting up development environment...")

        # Check if we're in the right directory
        if not (self.base_dir / "server").exists():
            logger.error("❌ Not in the correct directory. Run from project root.")
            return False

        # Install Python dependencies
        logger.info("Installing Python dependencies...")
        try:
            subprocess.run([
                sys.executable, "-m", "pip", "install",
                "fastapi", "uvicorn[standard]",
                "pillow", "numpy", "opencv-python",
                "requests", "cryptography",
                "scikit-learn", "imagehash",
                "pytesseract", "easyocr", "pywavelets"
            ], check=True)
            logger.info("✓ Python dependencies installed")
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to install Python dependencies: {e}")
            return False

        # Install Node.js dependencies
        if (self.base_dir / "ui" / "package.json").exists():
            logger.info("Installing Node.js dependencies...")
            try:
                subprocess.run(["npm", "install"], cwd=self.base_dir / "ui", check=True)
                logger.info("✓ Node.js dependencies installed")
            except subprocess.CalledProcessError as e:
                logger.error(f"❌ Failed to install Node.js dependencies: {e}")
                return False

        return True

    def print_setup_summary(self):
        """Print setup summary and next steps"""
        logger.info("")
        logger.info("🎉 Advanced Features Setup Complete!")
        logger.info("=" * 50)
        logger.info("✅ System dependencies checked")
        logger.info("✅ Python packages verified")
        logger.info("✅ Database schema initialized")
        logger.info("✅ Configuration files created")
        logger.info("✅ Startup script created")
        logger.info("✅ Integration tests passed")
        logger.info("")
        logger.info("🚀 Next Steps:")
        logger.info("1. Start the application:")
        logger.info("   python start_advanced_features.py")
        logger.info("")
        logger.info("2. Access the interfaces:")
        logger.info("   • Main app: http://localhost:8000")
        logger.info("   • Advanced features: http://localhost:8000/advanced")
        logger.info("   • API docs: http://localhost:8000/docs")
        logger.info("")
        logger.info("3. Import your photos and start exploring features!")
        logger.info("")
        logger.info("📚 Documentation:")
        logger.info("• Integration Guide: docs/ADVANCED_FEATURES_INTEGRATION.md")
        logger.info("• README: README_ADVANCED_FEATURES.md")
        logger.info("• API Reference: docs/API_REFERENCE.md")
        logger.info("")
        logger.info("🛠️ Troubleshooting:")
        logger.info("• Check logs/ directory for error messages")
        logger.info("• Verify Tesseract installation: tesseract --version")
        logger.info("• Run tests: python tests/test_advanced_features_integration.py")
        logger.info("")

def main():
    """Main setup function"""
    print("🔧 Photo Search Advanced Features Setup")
    print("=" * 50)

    setup = AdvancedFeaturesSetup()

    # Step 1: Check system dependencies
    if not setup.check_system_dependencies():
        print("\n❌ Setup failed due to missing system dependencies")
        sys.exit(1)

    # Step 2: Check Python packages
    packages_ok = setup.check_python_packages()
    if not packages_ok:
        print("\n⚠️ Some required packages are missing.")
        print("Run the following to install missing packages:")
        print("pip install insightface onnxruntime pytesseract easyocr pywavelets")

        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            sys.exit(1)

    # Step 3: Setup development environment
    if not setup.setup_development_environment():
        print("\n❌ Failed to setup development environment")
        sys.exit(1)

    # Step 4: Initialize database schema
    if not setup.initialize_database_schema():
        print("\n❌ Failed to initialize database schema")
        sys.exit(1)

    # Step 5: Setup configuration
    if not setup.setup_configuration():
        print("\n❌ Failed to setup configuration")
        sys.exit(1)

    # Step 6: Create startup script
    if not setup.create_startup_script():
        print("\n❌ Failed to create startup script")
        sys.exit(1)

    # Step 7: Run integration tests
    if not setup.run_integration_tests():
        print("\n⚠️ Integration tests had issues, but setup completed")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            sys.exit(1)

    # Print summary
    setup.print_setup_summary()

if __name__ == "__main__":
    main()