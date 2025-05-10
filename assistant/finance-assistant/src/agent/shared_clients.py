# src/agent/shared_clients.py
"""
Initializes and provides shared clients and configurations
(LLM, Database Engine, Schema Metadata) by loading config relative to project root.
Relies on standard package structure, not sys.path manipulation in server.py.
"""

import os
import json
import yaml
import logging
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, Engine
from langchain_google_genai import ChatGoogleGenerativeAI

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Path Setup (Relative to this file) ---
try:
    # src/agent/shared_clients.py -> src/agent -> src -> finance-assistant -> assistant -> app-personal-finance
    CURRENT_FILE_DIR = Path(__file__).resolve().parent
    AGENT_DIR = CURRENT_FILE_DIR
    SRC_DIR = AGENT_DIR.parent
    FINANCE_ASSISTANT_DIR = SRC_DIR.parent
    ASSISTANT_DIR = FINANCE_ASSISTANT_DIR.parent
    PROJECT_ROOT = ASSISTANT_DIR.parent

    CONFIG_DIR = PROJECT_ROOT / "config"
    CONFIG_FILE_PATH = CONFIG_DIR / "config.yaml"
    ENV_PATH = PROJECT_ROOT / ".env"
    DATA_DIR = PROJECT_ROOT / "data"
    METADATA_DIR = PROJECT_ROOT / "metadata"

    logger.debug(f"Project Root determined as: {PROJECT_ROOT}")
    logger.debug(f"Config directory: {CONFIG_DIR}")
    logger.debug(f"Env file path: {ENV_PATH}")

except Exception as e:
    logger.error(f"Error determining project paths from shared_clients.py: {e}", exc_info=True)
    raise SystemExit("Could not determine project structure paths.") from e

# --- Load .env File ---
config_loaded_flags = {"env": False, "yaml": False}
if ENV_PATH.is_file():
    load_dotenv(dotenv_path=ENV_PATH)
    logger.info(f"Loaded environment variables from: {ENV_PATH}")
    config_loaded_flags["env"] = True
else:
    logger.warning(f".env file not found at {ENV_PATH}. Secret keys might be missing.")

# --- Load config.yaml File ---
_config = {}
if CONFIG_FILE_PATH.is_file():
    try:
        with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
            _config = yaml.safe_load(f)
            if not isinstance(_config, dict):
                logger.error(f"Invalid YAML structure in {CONFIG_FILE_PATH}. Expected a dictionary.")
                _config = {}
            else:
                 logger.info(f"Loaded configuration settings from {CONFIG_FILE_PATH}")
                 config_loaded_flags["yaml"] = True
    except Exception as e:
        logger.error(f"Error loading or parsing {CONFIG_FILE_PATH}: {e}", exc_info=True)
else:
    logger.error(f"Configuration file not found: {CONFIG_FILE_PATH}. Using default fallbacks.")

# --- Extract Settings ---
# Secrets
GOOGLE_API_KEY: str | None = os.getenv("GOOGLE_API_KEY")

# Database
_db_config = _config.get("database", {})
DB_DIRECTORY_NAME: str = _db_config.get("directory", "data")
ACTIVE_DB_FILENAME: str = _db_config.get("active_db", "expenses.db")
DB_FULL_PATH: Path | None = PROJECT_ROOT / DB_DIRECTORY_NAME / ACTIVE_DB_FILENAME if PROJECT_ROOT else None
DB_URI: str | None = f"sqlite:///{DB_FULL_PATH.resolve()}" if DB_FULL_PATH and DB_FULL_PATH.exists() else None

# LLM
_llm_config = _config.get("llm", {})
LLM_DEFAULT_MODEL: str = _llm_config.get("default_model", "gemini-1.5-flash-latest")

# Paths
_paths_config = _config.get("paths", {})
METADATA_FILENAME: str = _paths_config.get("metadata_file", "metadata/expenses_metadata_detailed.yaml")
METADATA_FULL_PATH: Path | None = PROJECT_ROOT / METADATA_FILENAME if PROJECT_ROOT else None

# --- Initialize Database Engine ---
engine: Engine | None = None
if DB_URI is None:
     logger.error("Database engine cannot be initialized: DB_URI is None (check config.yaml and file existence).")
elif DB_FULL_PATH and not DB_FULL_PATH.exists():
     logger.error(f"Database engine cannot be initialized: Database file not found at {DB_FULL_PATH}")
else:
    try:
        engine = create_engine(DB_URI)
        logger.info(f"Database engine created for: {DB_URI}")
        with engine.connect() as conn: logger.info("Database connection test successful.")
    except Exception as e:
        logger.error(f"Failed to create database engine or connect to {DB_URI}: {e}", exc_info=True)
        engine = None

# --- Initialize LLM (Gemini) ---
LLM: ChatGoogleGenerativeAI | None = None
if not GOOGLE_API_KEY:
    logger.error("LLM cannot be initialized: GOOGLE_API_KEY not found.")
elif not LLM_DEFAULT_MODEL:
    logger.error("LLM cannot be initialized: LLM_DEFAULT_MODEL not set.")
else:
    try:
        LLM = ChatGoogleGenerativeAI(
            model=LLM_DEFAULT_MODEL,
            google_api_key=GOOGLE_API_KEY,
            temperature=0.1,
            convert_system_message_to_human=True
        )
        logger.info(f"ChatGoogleGenerativeAI model initialized ({LLM_DEFAULT_MODEL}).")
    except Exception as e:
        logger.error(f"Failed to initialize ChatGoogleGenerativeAI ({LLM_DEFAULT_MODEL}): {e}", exc_info=True)
        LLM = None

# --- Load Schema Metadata ---
SCHEMA_METADATA: str = ""
if METADATA_FULL_PATH is None:
     logger.error("Schema metadata cannot be loaded: METADATA_FULL_PATH is None.")
elif not METADATA_FULL_PATH.is_file():
    logger.error(f"Schema metadata file not found: {METADATA_FULL_PATH}. Using fallback.")
    SCHEMA_METADATA = """Fallback Schema: Table: expenses. Columns: id, date, year, month, week, day_of_week, account, category, sub_category, type, user, amount."""
else:
    try:
        with open(METADATA_FULL_PATH, 'r', encoding='utf-8') as f:
            metadata_content = yaml.safe_load(f)
            SCHEMA_METADATA = json.dumps(metadata_content, indent=2)
            logger.info(f"Successfully loaded schema metadata from {METADATA_FULL_PATH}")
    except Exception as e:
        logger.error(f"Failed to load or parse metadata YAML from {METADATA_FULL_PATH}: {e}", exc_info=True)
        SCHEMA_METADATA = """Fallback Schema: Table: expenses. Columns: id, date, year, month, week, day_of_week, account, category, sub_category, type, user, amount."""

# --- Final Check Logging ---
if engine is None: logger.warning("Database engine initialization failed.")
if LLM is None: logger.warning("LLM initialization failed.")
if not SCHEMA_METADATA or "Fallback Schema" in SCHEMA_METADATA: logger.warning("Schema metadata missing or using fallback.")