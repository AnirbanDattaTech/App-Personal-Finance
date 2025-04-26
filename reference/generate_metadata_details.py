#!/usr/bin/env python3
"""
generate_metadata_details.py

Reads specified metadata files (YAML and JSON) from the 'metadata/' directory,
includes the head of CSV files found in the 'data/' directory,
and compiles their content into a single text file
'reference/instructions_metadata.txt' for LLM context.
"""

import logging
from pathlib import Path
import json
import yaml # Requires PyYAML to be installed (pip install pyyaml)
import pandas as pd # Required for reading CSV head
from typing import Optional, List

# --- Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(module)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

try:
    # Assuming this script is in reference/
    SCRIPT_DIR = Path(__file__).resolve().parent
    ROOT_DIR = SCRIPT_DIR.parent
    REFERENCE_DIR = ROOT_DIR / "reference"
    METADATA_DIR = ROOT_DIR / "metadata"
    DATA_DIR = ROOT_DIR / "data" # Define data directory path
    OUTPUT_PATH = REFERENCE_DIR / "instructions_metadata.txt"

    # Define the specific metadata files to include
    YAML_METADATA_PATH = METADATA_DIR / "expenses_metadata_detailed.yaml"
    JSON_METADATA_PATH = METADATA_DIR / "expense_metadata.json" # Phase 1 metadata

    # Number of rows to show from CSV files
    CSV_HEAD_ROWS = 5

    logger.info(f"Root directory: {ROOT_DIR}")
    logger.info(f"Metadata directory: {METADATA_DIR}")
    logger.info(f"Data directory: {DATA_DIR}")
    logger.info(f"Output file path: {OUTPUT_PATH}")

except Exception as e:
    logger.exception(f"Error setting up script paths: {e}")
    raise SystemExit("Could not determine project structure paths.") from e

# --- Helper Functions ---

def read_file_content(file_path: Path) -> Optional[str]:
    """Reads the entire content of a given text file (non-CSV)."""
    logger.debug(f"Attempting to read text file: {file_path.relative_to(ROOT_DIR)}")
    if not file_path.is_file():
        logger.error(f"File not found: {file_path}")
        return None
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        logger.info(f"Successfully read {len(content)} characters from {file_path.name}")
        return content
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}", exc_info=True)
        return None

def read_csv_head(file_path: Path, num_rows: int) -> Optional[str]:
    """Reads the head of a CSV file using pandas."""
    logger.debug(f"Attempting to read head of CSV: {file_path.relative_to(ROOT_DIR)}")
    if not file_path.is_file():
        logger.error(f"CSV file not found: {file_path}")
        return None
    try:
        df = pd.read_csv(file_path, nrows=num_rows, on_bad_lines='skip')
        logger.info(f"Successfully read head ({len(df)} rows) of CSV: {file_path.name}")
        if df.empty:
             return "(CSV file is empty)"
        return df.to_string(index=False)
    except pd.errors.EmptyDataError:
        logger.warning(f"CSV file is empty: {file_path}")
        return "(CSV file is empty)"
    except Exception as e:
        logger.error(f"Error reading CSV file {file_path}: {e}", exc_info=True)
        return f"# ERROR: Could not read CSV head from {file_path.name} due to {type(e).__name__}\n"


def find_csv_files(directory: Path) -> List[Path]:
    """Finds all .csv files directly within the specified directory."""
    csv_files: List[Path] = []
    if not directory.is_dir():
        logger.warning(f"Data directory not found: {directory}")
        return csv_files
    try:
        csv_files = sorted(list(directory.glob('*.csv')))
        logger.info(f"Found {len(csv_files)} CSV files in {directory.name}/: {[f.name for f in csv_files]}")
    except Exception as e:
        logger.error(f"Error searching for CSV files in {directory}: {e}")
    return csv_files

# --- Main Execution ---

def main() -> None:
    """
    Reads metadata files and CSV heads, generates the consolidated instructions_metadata.txt file.
    """
    logger.info(f"--- Starting Metadata & Data Head Consolidation for {OUTPUT_PATH.name} ---")

    try:
        REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Ensured reference directory exists: {REFERENCE_DIR}")
    except Exception as e:
        logger.error(f"Could not create reference directory {REFERENCE_DIR}: {e}")
        return

    # Read metadata content
    yaml_content = read_file_content(YAML_METADATA_PATH)
    json_content = read_file_content(JSON_METADATA_PATH)

    # Find and read CSV file heads
    csv_files_in_data_dir = find_csv_files(DATA_DIR)
    csv_head_contents = {}
    for csv_file in csv_files_in_data_dir:
        head_content = read_csv_head(csv_file, CSV_HEAD_ROWS)
        if head_content is not None:
            csv_head_contents[csv_file] = head_content

    # Write to the output file
    try:
        with open(OUTPUT_PATH, 'w', encoding='utf-8') as outfile:
            logger.info(f"Opened output file for writing: {OUTPUT_PATH}")

            # --- Header Section ---
            outfile.write("# Metadata and Data Sample Context for LLM Assistant\n\n")
            outfile.write("This file contains the content of key metadata files and the head rows of key data files\n")
            outfile.write("used in the 'app-personal-finance' project.\n\n")
            outfile.write("-" * 70)
            outfile.write("\n\n")

            # --- YAML Metadata Section ---
            outfile.write(f"# --- Content from: {YAML_METADATA_PATH.relative_to(ROOT_DIR).as_posix()} ---\n\n")
            if yaml_content is not None:
                outfile.write(yaml_content)
                logger.info(f"Wrote content from {YAML_METADATA_PATH.name}")
            else:
                outfile.write(f"# ERROR: Could not read content from {YAML_METADATA_PATH.name}\n")
                logger.error(f"Failed to write content for {YAML_METADATA_PATH.name} as it could not be read.")
            outfile.write("\n\n")
            outfile.write("-" * 70)
            outfile.write("\n\n")

            # --- JSON Metadata Section ---
            outfile.write(f"# --- Content from: {JSON_METADATA_PATH.relative_to(ROOT_DIR).as_posix()} ---\n\n")
            if json_content is not None:
                try:
                    parsed_json = json.loads(json_content)
                    outfile.write(json.dumps(parsed_json, indent=4))
                except json.JSONDecodeError:
                    logger.warning(f"Could not parse JSON from {JSON_METADATA_PATH.name}, writing raw content.")
                    outfile.write(json_content)
                logger.info(f"Wrote content from {JSON_METADATA_PATH.name}")
            else:
                outfile.write(f"# ERROR: Could not read content from {JSON_METADATA_PATH.name}\n")
                logger.error(f"Failed to write content for {JSON_METADATA_PATH.name} as it could not be read.")
            outfile.write("\n\n")
            outfile.write("-" * 70)
            outfile.write("\n\n")

            # --- CSV Data Head Section ---
            outfile.write(f"# --- Data Samples (Top {CSV_HEAD_ROWS} Rows) from CSV files in {DATA_DIR.relative_to(ROOT_DIR).as_posix()}/ ---\n\n")
            if not csv_head_contents:
                 outfile.write("# (No CSV files found or readable in the data directory)\n")
            else:
                for csv_file, head_content in csv_head_contents.items():
                     outfile.write(f"# --- Head of: {csv_file.relative_to(ROOT_DIR).as_posix()} ---\n\n")
                     outfile.write(head_content)
                     outfile.write("\n\n")
                     logger.info(f"Wrote head content from {csv_file.name}")

            outfile.write("\n") # Final newline

        logger.info(f"✅ Successfully generated metadata & data sample context file: {OUTPUT_PATH}")

    except Exception as e:
        logger.exception(f"An critical error occurred during file generation: {e}")
        print(f"❌ Error generating context file. Check logs. Error: {e}")

    logger.info("--- Metadata & Data Head Consolidation Complete ---")


if __name__ == "__main__":
    # Ensure PyYAML and Pandas are installed
    try:
        import yaml
        import pandas
    except ImportError as import_err:
        print(f"Error: Missing required library - {import_err.name}")
        print("Please install required libraries using:")
        print("pip install pyyaml pandas")
        exit(1)

    main()