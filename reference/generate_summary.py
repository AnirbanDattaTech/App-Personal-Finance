#!/usr/bin/env python3
"""
generate_summary.py - Focused Project Context Generator for app-personal-finance

Generates 'instructions_code_details.txt' containing:
A. A file tree of the CORE project + test structure.
B. Code details:
   - Full code for essential .py files (agent source, streamlit source, tests).
   - AI-generated summary + truncated snippet for essential config/metadata
     files (schema YAML, langgraph.json).

Designed to provide meaningful context for LLM assistants, focusing on application
logic, essential configurations, and testing strategy.
Uses OpenAI API ONLY for summarizing essential non-Python files.
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from typing import List, TextIO, Set
# Note: Removed pandas import as we are excluding data/csv files now
# import pandas as pd
from openai import OpenAI
from tenacity import retry, wait_random_exponential, stop_after_attempt
import tiktoken

# --- Configuration ---
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(module)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# --- Path Definitions ---
try:
    SCRIPT_DIR = Path(__file__).resolve().parent
    ROOT_DIR = SCRIPT_DIR.parent
    REFERENCE_DIR = ROOT_DIR / "reference"
    OUTPUT_PATH = REFERENCE_DIR / "instructions_code_details.txt"

    # Define core directories containing essential code & tests
    CORE_DIRS_TO_SCAN: Set[Path] = {
        ROOT_DIR / "assistant" / "finance-assistant" / "src",
        ROOT_DIR / "assistant" / "finance-assistant" / "app",
        ROOT_DIR / "assistant" / "finance-assistant" / "tests", # Include tests
        ROOT_DIR / "streamlit",
        ROOT_DIR / "metadata" # Keep metadata directory for the YAML
    }
    # Define specific essential non-Python files relative to ROOT_DIR
    ESSENTIAL_FILES: Set[Path] = {
        ROOT_DIR / "assistant" / "finance-assistant" / "langgraph.json",
        ROOT_DIR / "metadata" / "expenses_metadata_detailed.yaml",
    }
    logger.info(f"Root directory set to: {ROOT_DIR}")
    logger.info(f"Core directories to scan: {[d.relative_to(ROOT_DIR) for d in CORE_DIRS_TO_SCAN]}")
    logger.info(f"Essential specific files: {[f.relative_to(ROOT_DIR) for f in ESSENTIAL_FILES]}")

except Exception as e:
    logger.exception(f"Error setting up script paths: {e}")
    raise SystemExit("Could not determine project structure paths.") from e

# --- Exclusion Lists (Applied during filtering) ---
# Focus on excluding files *within* the CORE_DIRS_TO_SCAN if needed,
# plus general non-code/binary types.
EXCLUDED_DIRS_GENERAL: Set[str] = {
    '__pycache__', '.mypy_cache', '.pytest_cache',
    '.git', '.vscode', '.idea', '.venv', 'venv', # General dev/tooling dirs
    'node_modules', 'build', 'dist', '*.egg-info' # Build artifacts
    # Note: Explicitly NOT excluding 'tests' here as it's in CORE_DIRS_TO_SCAN
}
EXCLUDED_FILES_GENERAL: Set[str] = {
    '.env', '.log', '.gitignore', '.DS_Store', 'Thumbs.db',
    'LICENSE', 'Makefile', # Tooling/Meta files
    'generate_summary.py', # Exclude self
    'instructions_code_details.txt', # Exclude output
    'agentic_ai_guidelines.txt', # Exclude guideline files
    'instructions_agentic_ai.txt'
}
# Exclude common binary/temporary/config extensions + database files
# Keep .json and .yaml as potentially essential config types
EXCLUDED_EXTENSIONS_GENERAL: Set[str] = {
    '.pyc', '.log', '.env', '.db', '.db-journal', '.pckl',
    '.lock', '.svg', '.png', '.jpg', '.jpeg', '.gif', '.ico',
    '.zip', '.tar', '.gz', '.pdf', '.docx', '.xlsx',
    '.csv', # Excluding data files now
    '.css', # Excluding stylesheets
    '.toml' # Excluding toml like pyproject.toml for now
}


# --- OpenAI Setup ---
try:
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY environment variable not found.")
    client = OpenAI(api_key=openai_api_key)
    logger.info("OpenAI client initialized.")
except ValueError as e:
    logger.error(f"OpenAI API Key Error: {e}")
    raise SystemExit("Missing OpenAI API Key.") from e
except Exception as e:
    logger.exception(f"Failed to initialize OpenAI client: {e}")
    raise SystemExit("OpenAI client initialization failed.") from e


# --- Helper Functions ---

def filter_relevant_items(items: List[Path], root_dir: Path) -> List[Path]:
    """Filters a list of paths based on exclusion rules."""
    filtered_items: List[Path] = []
    for item in items:
        relative_path = item.relative_to(root_dir)
        # Check if any part of the path is an excluded directory name
        if any(part in EXCLUDED_DIRS_GENERAL for part in relative_path.parts):
            continue
        # Check specific file name exclusions
        if item.name in EXCLUDED_FILES_GENERAL:
            continue
        # Check extension exclusions
        if item.suffix.lower() in EXCLUDED_EXTENSIONS_GENERAL:
            continue
        # If it passes all checks, keep it
        filtered_items.append(item)
    return filtered_items


def get_meaningful_context_files(root_dir: Path, core_dirs: Set[Path], essential_files: Set[Path]) -> List[Path]:
    """
    Finds essential Python files within core/test directories and specified essential files.

    Args:
        root_dir (Path): Project root directory.
        core_dirs (Set[Path]): Set of directories containing core source/test code.
        essential_files (Set[Path]): Set of specific essential non-Python config/metadata files.

    Returns:
        List[Path]: A list of Path objects for essential files for LLM context.
    """
    found_files: Set[Path] = set()
    logger.info("Starting discovery of meaningful context files...")

    # 1. Add specific essential files if they exist and pass filters
    for fpath in essential_files:
        if fpath.is_file():
             # Apply general filters even to essential files for safety
            if fpath.name not in EXCLUDED_FILES_GENERAL and \
               fpath.suffix.lower() not in EXCLUDED_EXTENSIONS_GENERAL and \
               not any(part in EXCLUDED_DIRS_GENERAL for part in fpath.relative_to(root_dir).parts):
                found_files.add(fpath)
                logger.debug(f"Included essential file: {fpath.relative_to(root_dir)}")
            else:
                 logger.warning(f"Specified essential file excluded by general rules: {fpath}")
        else:
            logger.warning(f"Essential file specified but not found: {fpath}")

    # 2. Scan core directories for ALL files initially
    all_items_in_core: List[Path] = []
    for core_dir in core_dirs:
        if core_dir.is_dir():
            logger.info(f"Scanning core/test directory: {core_dir.relative_to(root_dir)}")
            all_items_in_core.extend(list(core_dir.rglob('*')))
        else:
             logger.warning(f"Core directory specified but not found: {core_dir}")

    # 3. Filter the items found in core directories
    relevant_items_in_core = filter_relevant_items(all_items_in_core, root_dir)

    # 4. Add only Python files from the relevant items
    for item in relevant_items_in_core:
         if item.is_file() and item.suffix.lower() == '.py':
             found_files.add(item)
             logger.debug(f"Included core/test Python file: {item.relative_to(root_dir)}")

    sorted_files = sorted(list(found_files), key=lambda p: str(p).lower())
    logger.info(f"Found {len(sorted_files)} meaningful files for context.")
    return sorted_files


def read_file_content(file_path: Path) -> str:
    """Reads the content of a text file."""
    logger.debug(f"Reading content from: {file_path}")
    try:
        if not file_path.is_file():
             logger.warning(f"File not found during read attempt: {file_path}")
             return "File not found."
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            logger.info(f"Read {len(content)} characters from: {file_path.name}")
            return content
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}", exc_info=False)
        return f"Unable to read file due to error: {type(e).__name__}"

# Summarization Function (Retained for essential non-Python files)
@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
def summarize_content(content: str, file_path_str: str, model: str = "gpt-4o", max_input_tokens: int = 8000) -> str:
    """Summarizes content using the OpenAI API (for essential non-Python files)."""
    logger.info(f"Requesting summary for ESSENTIAL config/metadata: {file_path_str} using model {model}")
    # Basic checks moved here for clarity
    if not content or content.strip() == "" or content.startswith("Unable to read file") or content.startswith("File not found"):
        logger.warning(f"Skipping summary for empty or unreadable file: {file_path_str}")
        return "Content empty or unreadable, summary skipped."
    try:
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            logger.warning(f"Model '{model}' not found in tiktoken. Using 'cl100k_base'.")
            encoding = tiktoken.get_encoding("cl100k_base")

        tokens = encoding.encode(content)
        if len(tokens) > max_input_tokens:
            logger.warning(f"Content for {file_path_str} too long ({len(tokens)} tokens), truncating to {max_input_tokens}.")
            content = encoding.decode(tokens[:max_input_tokens]) + "\n... [TRUNCATED]"

        logger.debug(f"Sending {len(encoding.encode(content))} tokens to OpenAI for {file_path_str}.")

        response = client.chat.completions.create(
            model=model,
            messages=[{
                "role": "system",
                "content": "You are a highly skilled technical assistant. Your task is to provide a concise, accurate summary of the provided configuration or metadata file's primary purpose and key settings/structure in no more than 50 words."
            }, {
                "role": "user",
                "content": f"Summarize the following config/metadata file content from '{file_path_str}' in no more than 50 words:\n\n```\n{content}\n```"
            }],
            temperature=0.2,
            max_tokens=100,
            timeout=60
        )
        summary = response.choices[0].message.content.strip()
        logger.info(f"Summary received for: {file_path_str}")
        logger.debug(f"Summary for {file_path_str}: {summary}")
        return summary
    except Exception as e:
        logger.error(f"OpenAI API error during summarization for {file_path_str}: {e}", exc_info=True)
        return "Summary could not be generated due to API error."

# Formatting Function
def format_compressed_block(fpath: Path, summary: str, content: str, root_dir: Path) -> str:
    """
    Formats the file details into the compressed block structure.
    Includes full content for .py files and truncated content for essential others.

    Args:
        fpath (Path): The full path to the file.
        summary (str): The AI-generated summary (or placeholder for .py).
        content (str): The full file content (or read error message).
        root_dir (Path): The project root directory for relative path calculation.

    Returns:
        str: The formatted string block for the file.
    """
    relative_path = fpath.relative_to(root_dir)
    file_ext = fpath.suffix.lower()
    marker = "#PY " if file_ext == '.py' else "#FILE "

    # Define truncation length for essential non-Python files
    max_len_essential_other = 2000 # Allow more context for YAML/JSON config

    if content.startswith("Unable to read") or content.startswith("File not found"):
         code_output = content
         if summary.startswith("Content empty"):
             summary = f"Note: {content}"
    elif file_ext == '.py':
        code_output = content # Include full Python code
        summary = "Full Python code included below." # Override summary
    else: # Handle essential non-Python files (YAML, JSON)
        code_output = content[:max_len_essential_other] + ('\n[...]' if len(content) > max_len_essential_other else '')

    block_lines = [
        f"{marker}File: {fpath.name}",
        f"@path: {relative_path.as_posix()}",
        f"@summary: {summary}",
        f"@code:",
        f"{code_output}"
    ]
    return "\n".join(block_lines)

# Tree Generation Function
def generate_folder_tree(directory: Path, core_dirs: Set[Path], essential_files: Set[Path], outfile: TextIO) -> None:
    """
    Generates a text-based folder tree of CORE directories/files and writes it.

    Args:
        directory (Path): The root directory of the project.
        core_dirs (Set[Path]): Core directories to include in the tree.
        essential_files (Set[Path]): Specific essential files to include.
        outfile (TextIO): The open file handle to write the tree to.
    """
    logger.info(f"Generating focused folder tree starting from: {directory}")
    outfile.write(f"{directory.name}/\n")

    items_to_render: List[Path] = []
    
    # Add essential files first
    items_to_render.extend(essential_files)
    
    # Add files within core directories
    for core_dir in core_dirs:
        if core_dir.is_dir():
             # Add the directory itself relative to root
             # items_to_render.add(core_dir) # Adding dirs complicates sorting/display slightly
             for item in core_dir.rglob('*'):
                 items_to_render.append(item)

    # Filter and prepare for tree display
    tree_entries = set() # Use set to avoid duplicate paths if essential files are inside core dirs
    for item in items_to_render:
         # Basic filtering (redundant with get_meaningful_context_files but safe)
         if item.name in EXCLUDED_FILES_GENERAL or \
            item.suffix.lower() in EXCLUDED_EXTENSIONS_GENERAL or \
            any(part in EXCLUDED_DIRS_GENERAL for part in item.relative_to(directory).parts):
             continue
             
         # Ensure we only consider files or directories within the CORE_DIRS scope
         # or the explicitly listed ESSENTIAL_FILES
         is_essential = item in essential_files
         is_in_core_dir = any(item.is_relative_to(core_dir) for core_dir in core_dirs)

         if is_essential or (is_in_core_dir and (item.is_dir() or item.suffix == '.py')):
             tree_entries.add(item.relative_to(directory))

    # Build tree structure string
    processed_paths = set()
    output_lines = []

    for rel_path in sorted(list(tree_entries), key=lambda p: p.parts):
        # Add parent directories to the output if not already added
        for i in range(len(rel_path.parts) -1):
            parent_part = Path(*rel_path.parts[:i+1])
            if parent_part not in processed_paths:
                depth = len(parent_part.parts) -1
                indent = '    ' * (depth + 1)
                output_lines.append(f"{indent}{parent_part.name}/")
                processed_paths.add(parent_part)
                
        # Add the file or final directory itself
        depth = len(rel_path.parts) -1
        indent = '    ' * (depth + 1)
        if Path(directory / rel_path).is_dir(): # Check original path type
             # Add directory only if not already added via parent logic
             if rel_path not in processed_paths:
                 output_lines.append(f"{indent}{rel_path.name}/")
                 processed_paths.add(rel_path)
        else:
             output_lines.append(f"{indent}{rel_path.name}")
             processed_paths.add(rel_path) # Treat file path as processed

    # Write unique lines maintaining approximate order
    unique_lines = []
    seen = set()
    for line in output_lines:
        if line not in seen:
             unique_lines.append(line)
             seen.add(line)

    outfile.write("\n".join(unique_lines) + "\n")
    logger.info("Focused folder tree generation complete.")


# --- Main Execution Flow ---
def main() -> None:
    """Main function"""
    logger.info("--- Starting Focused Project Context Generation ---")
    try:
        REFERENCE_DIR.mkdir(parents=True, exist_ok=True)

        with open(OUTPUT_PATH, 'w', encoding='utf-8') as outfile:
            logger.info(f"Opened output file for writing: {OUTPUT_PATH}")

            outfile.write("# Focused Project Context: Core File Tree & Code Details\n")
            outfile.write("# Generated by: generate_summary.py\n")
            outfile.write("# Purpose: Provides meaningful context (core logic, essential config, tests) for LLM assistants.\n")
            outfile.write("# Includes full code for .py files and AI summaries + truncated snippets for essential config/metadata.\n")
            outfile.write("\n")

            logger.info("--- Generating Section A: Focused File Tree ---")
            outfile.write("# --- A. Project File Tree (Core Logic, Config, Tests) ---\n\n")
            # Pass core dirs and essential files to tree generator for focused output
            generate_folder_tree(ROOT_DIR, CORE_DIRS_TO_SCAN, ESSENTIAL_FILES, outfile)
            outfile.write("\n")
            logger.info("--- Finished Section A: Focused File Tree ---")

            logger.info("--- Generating Section B: Meaningful File Details ---")
            outfile.write("# --- B. File Details (Python Code + Essential Config/Metadata) ---\n")

            meaningful_files = get_meaningful_context_files(ROOT_DIR, CORE_DIRS_TO_SCAN, ESSENTIAL_FILES)

            if not meaningful_files:
                logger.warning("No meaningful context files found to process.")
                outfile.write("\n# (No meaningful files found based on inclusion/exclusion rules)\n")
            else:
                logger.info(f"Processing {len(meaningful_files)} meaningful files...")
                for i, fpath in enumerate(meaningful_files):
                    rel_path_str = str(fpath.relative_to(ROOT_DIR).as_posix())
                    logger.info(f"Processing file {i+1}/{len(meaningful_files)}: {rel_path_str}")

                    content = read_file_content(fpath)
                    summary = "" # Initialize

                    # --- Get summary ONLY for ESSENTIAL NON-PYTHON files ---
                    if fpath in ESSENTIAL_FILES and fpath.suffix.lower() != '.py':
                        if not (content.startswith("Unable to read") or content.startswith("File not found")):
                            summary = summarize_content(content, rel_path_str)
                        else:
                            summary = f"Note: {content}" # Use error as summary
                    # -----------------------------------------------------

                    compressed_block = format_compressed_block(fpath, summary, content, ROOT_DIR)
                    outfile.write(f"\n{compressed_block}\n")
                    logger.debug(f"Written context block for: {rel_path_str}")

            logger.info("--- Finished Section B: Meaningful File Details ---")

        logger.info(f"✅ Successfully generated focused context file: {OUTPUT_PATH}")

    except Exception as e:
        logger.exception(f"An error occurred during context generation: {e}")
        print(f"❌ Error generating context file. Check logs. Error: {e}")

    logger.info("--- Focused Context Generation Complete ---")


if __name__ == "__main__":
    main()