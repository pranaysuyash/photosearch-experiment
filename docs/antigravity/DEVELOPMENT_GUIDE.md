# Development Guide

**Created by:** Antigravity (AI Assistant)
**Date:** 2025-12-06
**Purpose:** Guide for development workflow, coding standards, and best practices

---

## Development Workflow

### For Each Task

#### 1. Pre-Implementation Phase
- [ ] Copy exact user request to task documentation
- [ ] State understanding of the task
- [ ] Outline approach and design decisions
- [ ] Note what could be done extra/differently
- [ ] Get user confirmation if needed

#### 2. Implementation Phase
- [ ] Create the Python file with clear module docstring
- [ ] Implement core functionality
- [ ] Add comprehensive error handling
- [ ] Add logging for debugging
- [ ] Create CLI interface for standalone testing
- [ ] Add type hints for clarity

#### 3. Testing Phase
- [ ] Test the module standalone
- [ ] Verify it can be imported by other modules
- [ ] Test edge cases (invalid inputs, missing files, etc.)
- [ ] Test error handling
- [ ] Verify logging works correctly

#### 4. Documentation Phase
- [ ] Update README with task completion details
- [ ] Document all functions with docstrings
- [ ] Add usage examples
- [ ] Note lessons learned
- [ ] Document future improvements
- [ ] Update FAQ if questions arose

---

## Coding Standards

### Python Style Guide
Follow PEP 8 with these specific guidelines:

#### File Structure
```python
"""
Module Name - Brief Description

This module provides functionality for [purpose].
Can be used standalone or imported by other modules.

Usage:
    python module_name.py [arguments]

    Or import:
    from module_name import function_name

Author: [Your name or "Generated"]
Date: YYYY-MM-DD
"""

# Standard library imports
import os
import sys
from pathlib import Path

# Third-party imports
import numpy as np
from PIL import Image

# Local imports
from config import get_api_key

# Constants
DEFAULT_SIZE = (224, 224)
SUPPORTED_FORMATS = ['.jpg', '.jpeg', '.png', '.webp']

# Main implementation
class ClassName:
    """Class docstring."""
    pass

def function_name(param: type) -> return_type:
    """
    Function docstring.

    Args:
        param: Description of parameter

    Returns:
        Description of return value

    Raises:
        ExceptionType: When this exception is raised
    """
    pass

# CLI interface
def main():
    """Main function for CLI usage."""
    pass

if __name__ == "__main__":
    main()
```

#### Naming Conventions
- **Files:** `snake_case.py`
- **Classes:** `PascalCase`
- **Functions:** `snake_case()`
- **Constants:** `UPPER_SNAKE_CASE`
- **Private functions:** `_leading_underscore()`

#### Type Hints
Always use type hints for function signatures:
```python
def process_image(
    image_path: str,
    size: tuple[int, int] = (224, 224)
) -> np.ndarray:
    """Process an image."""
    pass
```

#### Docstrings
Use Google-style docstrings:
```python
def search_similar(
    query: str,
    top_k: int = 10
) -> list[dict]:
    """
    Search for similar images using text query.

    Args:
        query: Text description to search for
        top_k: Number of results to return (default: 10)

    Returns:
        List of dictionaries containing:
            - path: Image file path
            - score: Similarity score (0-1)
            - metadata: Additional image metadata

    Raises:
        ValueError: If query is empty
        RuntimeError: If search index is not initialized

    Example:
        >>> results = search_similar("sunset beach", top_k=5)
        >>> print(results[0]['path'])
        '/path/to/image.jpg'
    """
    pass
```

---

## Error Handling

### Principles
1. **Fail gracefully** - Don't crash, provide useful error messages
2. **Log errors** - Always log what went wrong
3. **Provide context** - Include relevant information in error messages
4. **Recover when possible** - Use fallbacks and defaults

### Error Handling Pattern
```python
import logging

logger = logging.getLogger(__name__)

def risky_operation(param: str) -> dict:
    """
    Perform operation that might fail.

    Args:
        param: Input parameter

    Returns:
        Result dictionary

    Raises:
        ValueError: If param is invalid
        RuntimeError: If operation fails
    """
    # Validate inputs
    if not param:
        logger.error("Parameter cannot be empty")
        raise ValueError("Parameter cannot be empty")

    try:
        # Attempt operation
        result = perform_operation(param)
        logger.info(f"Operation successful for {param}")
        return result

    except ExternalAPIError as e:
        # Handle specific errors
        logger.error(f"API error: {e}")
        # Try fallback
        try:
            result = fallback_operation(param)
            logger.warning(f"Used fallback for {param}")
            return result
        except Exception as fallback_error:
            logger.error(f"Fallback also failed: {fallback_error}")
            raise RuntimeError(f"Operation failed: {e}") from e

    except Exception as e:
        # Catch-all for unexpected errors
        logger.exception(f"Unexpected error: {e}")
        raise
```

---

## Logging

### Setup
```python
import logging
from pathlib import Path

def setup_logging(log_file: str = "app.log", level: int = logging.INFO):
    """
    Configure logging for the application.

    Args:
        log_file: Path to log file
        level: Logging level (default: INFO)
    """
    # Create logs directory if needed
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Configure logging
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()  # Also print to console
        ]
    )
```

### Usage Levels
- **DEBUG:** Detailed information for debugging
- **INFO:** General information about program execution
- **WARNING:** Something unexpected but not critical
- **ERROR:** Error that prevented an operation
- **CRITICAL:** Serious error that may cause program to fail

### Example
```python
logger = logging.getLogger(__name__)

logger.debug(f"Processing image: {image_path}")
logger.info(f"Generated embedding with shape {embedding.shape}")
logger.warning(f"API rate limit approaching: {remaining_calls} calls left")
logger.error(f"Failed to load image: {error}")
logger.critical(f"Database connection lost")
```

---

## Testing Strategy

### Manual Testing
Each module should have a `main()` function for CLI testing:

```python
def main():
    """CLI interface for testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Module description")
    parser.add_argument("input", help="Input file or parameter")
    parser.add_argument("--option", default="default", help="Optional parameter")

    args = parser.parse_args()

    # Test the module
    result = main_function(args.input, option=args.option)
    print(f"Result: {result}")

if __name__ == "__main__":
    main()
```

### Test Cases to Consider
1. **Happy path** - Normal, expected usage
2. **Edge cases** - Empty inputs, very large inputs, special characters
3. **Error cases** - Invalid inputs, missing files, network errors
4. **Integration** - Can other modules import and use this?

---

## Module Design Principles

### 1. Single Responsibility
Each module should do one thing well.

**Good:**
```python
# image_loader.py - Only handles image loading
def load_image(path: str) -> Image:
    """Load an image from path."""
    pass
```

**Bad:**
```python
# utils.py - Does too many unrelated things
def load_image(path: str) -> Image:
    pass

def generate_embedding(image: Image) -> np.ndarray:
    pass

def search_database(query: str) -> list:
    pass
```

### 2. Clear Interfaces
Functions should have clear inputs and outputs.

**Good:**
```python
def resize_image(
    image: Image,
    size: tuple[int, int]
) -> Image:
    """Resize image to specified dimensions."""
    pass
```

**Bad:**
```python
def process(img, s):
    """Do something with image."""
    pass
```

### 3. Modularity
Modules should be importable and reusable.

**Good:**
```python
# Can be used standalone
if __name__ == "__main__":
    main()

# Can be imported
from image_loader import load_image
```

### 4. Configuration
Use configuration instead of hardcoding.

**Good:**
```python
from config import get_config

max_size = get_config("image.max_size")
```

**Bad:**
```python
max_size = 1024  # Hardcoded
```

---

## Dependency Management

### requirements.txt
Keep dependencies organized:

```txt
# Core dependencies
pillow>=10.0.0
numpy>=1.24.0
requests>=2.31.0

# AI/ML libraries
openai>=1.0.0
transformers>=4.30.0
sentence-transformers>=2.2.0

# Vector storage
faiss-cpu>=1.7.4

# Utilities
python-dotenv>=1.0.0
tqdm>=4.65.0
click>=8.1.0

# Development
pytest>=7.4.0
black>=23.0.0
mypy>=1.4.0
```

### Virtual Environment
Always use a virtual environment:

```bash
# Create
python -m venv venv

# Activate (Mac/Linux)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## Git Workflow

### Branch Strategy
Per user requirements:
- Create own branch for work
- Merge to main when complete and tested
- No breaking changes to existing code

```bash
# Create branch
git checkout -b feature/task-1-config

# Work on task
git add config.py
git commit -m "Add configuration management module"

# Test thoroughly
python config.py

# Merge to main if no conflicts
git checkout main
git merge feature/task-1-config

# Push to remote
git push origin main
```

### Commit Messages
Use clear, descriptive commit messages:

**Good:**
```
Add image loading module with URL support
Implement CLIP embedding generation
Fix error handling in vector store
```

**Bad:**
```
Update
Fix bug
Changes
```

---

## Documentation Standards

### README Updates
After each task, update README with:

1. **Task Summary**
   - What was implemented
   - What file was created/modified

2. **Usage Example**
   - How to use the module
   - CLI commands
   - Import examples

3. **What Worked**
   - Successful implementations
   - Good decisions

4. **What Didn't Work**
   - Challenges faced
   - Solutions found

5. **Future Improvements**
   - What could be better
   - Next steps

### Code Comments
- Comment **why**, not **what**
- Explain complex logic
- Note TODOs and FIXMEs

**Good:**
```python
# Use exponential backoff to avoid hitting rate limits
time.sleep(2 ** retry_count)
```

**Bad:**
```python
# Sleep for 2 seconds
time.sleep(2)
```

---

## Performance Considerations

### Optimization Guidelines
1. **Profile first** - Don't optimize prematurely
2. **Cache expensive operations** - API calls, embeddings
3. **Batch when possible** - Process multiple items together
4. **Use appropriate data structures** - NumPy for vectors
5. **Lazy loading** - Load data only when needed

### Example: Caching
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_embedding(image_hash: str) -> np.ndarray:
    """Get embedding with caching."""
    # Expensive operation only happens once per unique image
    return generate_embedding(image_hash)
```

---

## Security Best Practices

### API Keys
- Never commit API keys to git
- Use `.env` file (gitignored)
- Validate keys on startup
- Provide clear error messages for missing keys

### Input Validation
```python
def load_image(path: str) -> Image:
    """Load image with validation."""
    # Validate path
    if not path:
        raise ValueError("Path cannot be empty")

    # Check file exists
    if not Path(path).exists():
        raise FileNotFoundError(f"Image not found: {path}")

    # Validate extension
    ext = Path(path).suffix.lower()
    if ext not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported format: {ext}")

    # Load safely
    try:
        return Image.open(path)
    except Exception as e:
        raise RuntimeError(f"Failed to load image: {e}")
```

---

## Common Patterns

### Configuration Loading
```python
from pathlib import Path
from dotenv import load_dotenv
import os

def load_config():
    """Load configuration from environment."""
    # Load .env file
    env_path = Path(__file__).parent / ".env"
    load_dotenv(env_path)

    # Get required keys
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment")

    return {
        "api_key": api_key,
        "max_size": int(os.getenv("MAX_IMAGE_SIZE", "1024"))
    }
```

### Progress Tracking
```python
from tqdm import tqdm

def process_batch(image_paths: list[str]) -> list[dict]:
    """Process multiple images with progress bar."""
    results = []

    for path in tqdm(image_paths, desc="Processing images"):
        try:
            result = process_image(path)
            results.append(result)
        except Exception as e:
            logger.error(f"Failed to process {path}: {e}")
            continue

    return results
```

### Retry Logic
```python
import time
from functools import wraps

def retry(max_attempts: int = 3, delay: float = 1.0):
    """Decorator for retrying failed operations."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    logger.warning(f"Attempt {attempt + 1} failed: {e}")
                    time.sleep(delay * (2 ** attempt))
            return None
        return wrapper
    return decorator

@retry(max_attempts=3)
def call_api(endpoint: str) -> dict:
    """Call API with automatic retry."""
    pass
```

---

## Checklist for Each Task

Before marking a task as complete:

- [ ] Code is written and follows style guide
- [ ] Type hints are added
- [ ] Docstrings are comprehensive
- [ ] Error handling is implemented
- [ ] Logging is added
- [ ] CLI interface works
- [ ] Module can be imported
- [ ] Edge cases are tested
- [ ] README is updated
- [ ] No breaking changes to existing code
- [ ] Code is committed to git
- [ ] Tests pass

---

**Document Status:** Living Document - Updated as development practices evolve
**Next Review:** After Task 3 completion
