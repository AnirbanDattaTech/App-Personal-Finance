# config/settings.py
"""
Loads configuration from .env and config.yaml, providing centralized access.
"""

import os
import yaml
import logging
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Path Setup ---
try:
    # Project root is the parent directory of this 'config' directory
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    CONFIG_FILE_PATH = Path(__file__).parent / "config.yaml"
    ENV_PATH = PROJECT_ROOT / ".env"
    logger.debug(f"Project Root determined as: {PROJECT_ROOT}")
    logger.debug(f"Config file path: {CONFIG_FILE_PATH}")
    logger.debug(f"Env file path: {ENV_PATH}")
except Exception as e:
    logger.error(f"Error determining project paths: {e}", exc_info=True)
    raise SystemExit("Could not determine project structure paths.") from e

# --- Load .env File (for secrets) ---
if ENV_PATH.is_file():
    load_dotenv(dotenv_path=ENV_PATH)
    logger.info(f"Loaded environment variables from: {ENV_PATH}")
else:
    logger.warning(f".env file not found at {ENV_PATH}. Secret keys (like API keys) might be missing.")

# --- Load config.yaml File ---
_config: Dict[str, Any] = {}
if CONFIG_FILE_PATH.is_file():
    try:
        with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
            _config = yaml.safe_load(f)
            if not isinstance(_config, dict):
                logger.error(f"Invalid YAML structure in {CONFIG_FILE_PATH}. Expected a dictionary.")
                _config = {} # Reset to empty dict on error
            else:
                 logger.info(f"Loaded configuration settings from {CONFIG_FILE_PATH}")
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML file {CONFIG_FILE_PATH}: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Unexpected error loading {CONFIG_FILE_PATH}: {e}", exc_info=True)
else:
    logger.error(f"Configuration file not found: {CONFIG_FILE_PATH}. Using default fallbacks.")

# --- Define Accessible Settings ---

# Secrets (from .env)
GOOGLE_API_KEY: Optional[str] = os.getenv("GOOGLE_API_KEY")
# Add other secrets as needed, e.g., OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Database Settings (from config.yaml, with fallbacks)
_db_config = _config.get("database", {})
DB_DIRECTORY: str = _db_config.get("directory", "data")
ACTIVE_DB_FILENAME: str = _db_config.get("active_db", "expenses.db") # Default fallback
DB_FULL_PATH: Path = PROJECT_ROOT / DB_DIRECTORY / ACTIVE_DB_FILENAME
DB_URI: str = f"sqlite:///{DB_FULL_PATH.resolve()}"

# LLM Settings (from config.yaml, with fallbacks)
_llm_config = _config.get("llm", {})
LLM_DEFAULT_MODEL: str = _llm_config.get("default_model", "gemini-1.5-flash-latest") # Default fallback
# Future: LLM_PROVIDER = _llm_config.get("provider", "google")

# Path Settings (from config.yaml, with fallbacks)
_paths_config = _config.get("paths", {})
METADATA_FILENAME: str = _paths_config.get("metadata_file", "metadata/expenses_metadata_detailed.yaml") # Default fallback
METADATA_FULL_PATH: Path = PROJECT_ROOT / METADATA_FILENAME

# --- Log Loaded Configuration ---
logger.info(f"Active Database Path: {DB_FULL_PATH}")
logger.info(f"Default LLM Model: {LLM_DEFAULT_MODEL}")
logger.info(f"Metadata File Path: {METADATA_FULL_PATH}")
if not GOOGLE_API_KEY:
    logger.warning("GOOGLE_API_KEY is not set in environment variables.")

# --- Optional: Add validation logic here if needed ---
# e.g., check if DB_FULL_PATH exists, if METADATA_FULL_PATH exists

# --- Make settings easily importable ---
# You can import specific variables like `from config.settings import DB_URI, LLM_DEFAULT_MODEL`
# Or potentially create a settings object/dataclass later if preferred