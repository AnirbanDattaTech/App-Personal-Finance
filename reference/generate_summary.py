#!/usr/bin/env python3
"""
generate_summary.py - Focused Project Context Generator for app-personal-finance

Generates 'instructions_code_details.txt' containing:
A. A focused file tree of the project structure (using proven logic).
B. Code details:
   - Full, whitespace/simple-comment-compressed code (preserving docstrings)
     for all relevant .py files (src, app, tests, streamlit, root, ref).
   - AI-generated summary + truncated snippet for files in reference/ (non-py) and
     essential config/metadata files (schema YAML, langgraph.json, pyproject.toml).
   - Head content for data/expenses.csv.

Excludes .git, cache dirs, build artifacts, env files etc. from tree and details.
Uses OpenAI API ONLY for summarizing specific non-Python files.
"""

import os
import logging
import re
from pathlib import Path
from dotenv import load_dotenv
from typing import List, TextIO, Set, Tuple
import pandas as pd
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
    # Assuming this script is in reference/
    SCRIPT_DIR = Path(__file__).resolve().parent
    ROOT_DIR = SCRIPT_DIR.parent
    REFERENCE_DIR = ROOT_DIR / "reference"
    OUTPUT_PATH = REFERENCE_DIR / "instructions_code_details.txt"

    # Define directories containing files needed for context details (Section 3)
    CONTEXT_DIRS_DETAILS: Set[Path] = {
        ROOT_DIR / "assistant" / "finance-assistant" / "src",
        ROOT_DIR / "assistant" / "finance-assistant" / "app",
        ROOT_DIR / "assistant" / "finance-assistant" / "tests",
        ROOT_DIR / "streamlit",
        ROOT_DIR / "metadata",
        ROOT_DIR / "reference",
        ROOT_DIR # Scan root for top-level files
    }
    # Define specific essential non-Python files relative to ROOT_DIR for details
    ESSENTIAL_NON_PY_FILES: Set[Path] = {
        ROOT_DIR / "assistant" / "finance-assistant" / "langgraph.json",
        ROOT_DIR / "assistant" / "finance-assistant" / "pyproject.toml",
        ROOT_DIR / "metadata" / "expenses_metadata_detailed.yaml",
    }
    # Specific data files to handle specially for details
    DATA_FILES_TO_INCLUDE: Set[Path] = {
        ROOT_DIR / "data" / "expenses.csv"
    }

    logger.info(f"Root directory set to: {ROOT_DIR}")

except Exception as e:
    logger.exception(f"Error setting up script paths: {e}")
    raise SystemExit("Could not determine project structure paths.") from e

# --- Exclusion Lists ---
# Directories excluded from BOTH Tree (Section 2) and Details (Section 3)
# Based on previous successful exclusion + adding langgraph_api, egg-info, .git
EXCLUDED_DIRS_HARD: Set[str] = {
    '.git', '__pycache__', '.vscode', '.idea', '.venv', 'venv',
    '.mypy_cache', '.pytest_cache', 'node_modules', 'build', 'dist',
    '.langgraph_api', 'agent.egg-info', # Added based on discussion
    '.github' # Usually excluded unless workflow files needed later
}
# Files excluded from Section 3 details ONLY
EXCLUDED_FILES_DETAILS: Set[str] = {
    '.env', '.log', '.gitignore', '.DS_Store', 'Thumbs.db',
    'LICENSE', 'Makefile', '.codespellignore',
    'generate_summary.py', 'generate_summary1.py',
    'instructions_code_details.txt', 'agentic_ai_guidelines.txt',
    'agentic_ai_guidelines.md', 'instructions_agentic_ai.txt',
    'requirements.txt', 'requirements-v2.0.txt'
}
# Extensions excluded from Section 3 details ONLY
EXCLUDED_EXTENSIONS_DETAILS: Set[str] = {
    '.pyc', '.log', '.env', '.db', '.db-journal', '.pckl',
    '.lock', '.svg', '.png', '.jpg', '.jpeg', '.gif', '.ico',
    '.zip', '.tar', '.gz', '.pdf', '.docx', '.xlsx',
    '.css', '.md',
}

# --- OpenAI Setup ---
try:
    # (OpenAI client setup - same as before)
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key: raise ValueError("OPENAI_API_KEY not found.")
    client = OpenAI(api_key=openai_api_key)
    logger.info("OpenAI client initialized.")
except Exception as e:
    logger.exception(f"Failed to initialize OpenAI client: {e}")
    raise SystemExit("OpenAI client initialization failed.") from e


# --- Tree Generation Function (Copied VERBATIM from generate_summary1.py) ---
# Uses its own internal exclusion lists from that script for correctness
def generate_folder_tree_v1(target_path: Path, output_file: Path) -> None:
    """
    Generates a folder tree structure and saves it to a file.
    Uses logic from generate_summary1.py.

    Args:
        target_path (Path): The root directory to generate the tree from.
        output_file (Path): The file path to save the tree structure.
    """
    logger.info(f"Generating folder tree (v1 logic) for: {target_path}")
    # Define exclusions specific to this tree function, matching generate_summary1.py logic
    # Added .langgraph_api, agent.egg-info, .git based on discussion
    EXCLUDED_DIRS_TREE = {'.git', '__pycache__', '.vscode', '.idea', '.venv', 'venv',
                         '.mypy_cache', '.pytest_cache', '.github',
                         '.langgraph_api', 'agent.egg-info'}
    EXCLUDED_FILES_TREE = {'.env', '.log', '.gitignore'} # Simplified list matching original

    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            for root, dirs, files in os.walk(target_path, topdown=True):
                # Filter directories based on the TREE exclusion list
                dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS_TREE]
                level = root.replace(str(target_path), '').count(os.sep)
                indent = ' ' * 4 * level

                # Write directory name
                if root == str(target_path):
                     # Use the actual directory name, not the full path
                    f.write(f'{target_path.name}/\n')
                else:
                    f.write(f'{indent}{os.path.basename(root)}/\n')

                subindent = ' ' * 4 * (level + 1)
                # Write file names, sorting for consistency
                for file in sorted(files, key=str.lower):
                    # Apply file exclusion specific to the tree if needed
                    if file not in EXCLUDED_FILES_TREE:
                         f.write(f'{subindent}{file}\n')
        logger.info(f"Folder tree (v1 logic) successfully written to {output_file}")
    except Exception as e:
        logger.exception(f"Error generating folder tree (v1 logic): {e}")
        # Write error to file if possible
        try:
            with open(output_file, 'w', encoding='utf-8') as f_err:
                f_err.write(f"# Error generating folder tree: {e}\n")
        except Exception:
            pass # Ignore error writing the error


# --- Helper Functions for Section 3 (Content Details - Unchanged from last version) ---

def get_target_files(root_dir: Path, context_dirs: Set[Path], essential_non_py: Set[Path], data_files: Set[Path]) -> List[Path]:
    """Finds all files to be included in Section 3 (details)."""
    target_files: Set[Path] = set()
    logger.info("Starting discovery of target files for Section 3 details...")
    all_scanned_items: Set[Path] = set()
    # Scan context directories
    for scan_dir in context_dirs:
        if scan_dir.is_dir():
            logger.info(f"Scanning directory for details: {scan_dir.relative_to(root_dir).as_posix()}")
            try:
                for item in scan_dir.rglob('*'):
                    if any(part in EXCLUDED_DIRS_HARD for part in item.relative_to(root_dir).parts): continue
                    if item.is_file(): all_scanned_items.add(item)
            except Exception as e: logger.error(f"Error scanning directory {scan_dir}: {e}")
        elif scan_dir == root_dir:
             try:
                 for item in root_dir.glob('*'):
                     if any(part in EXCLUDED_DIRS_HARD for part in item.relative_to(root_dir).parts): continue
                     if item.is_file(): all_scanned_items.add(item)
             except Exception as e: logger.error(f"Error scanning root directory {root_dir}: {e}")
        else: logger.warning(f"Directory specified for scanning not found or invalid: {scan_dir}")
    # Add essential and data files
    all_scanned_items.update(essential_non_py)
    all_scanned_items.update(data_files)
    # Filter
    for item in all_scanned_items:
         if not item.is_file(): continue
         relative_path = item.relative_to(root_dir)
         if any(part in EXCLUDED_DIRS_HARD for part in relative_path.parts): continue
         if item.name in EXCLUDED_FILES_DETAILS: continue
         if item.suffix.lower() in EXCLUDED_EXTENSIONS_DETAILS:
             if item not in essential_non_py and item not in data_files and not (item.is_relative_to(REFERENCE_DIR) and item.suffix.lower() not in ['.zip','.gz']): # Allow text files in reference
                 continue
         target_files.add(item)
    sorted_files = sorted(list(target_files), key=lambda p: str(p).lower())
    logger.info(f"Found {len(sorted_files)} target files for Section 3 details after filtering.")
    return sorted_files

def read_file_content(file_path: Path, is_csv: bool = False, csv_head_rows: int = 5) -> str:
    """Reads the content of a text file or head of CSV."""
    # (Content unchanged from previous version)
    logger.debug(f"Reading content from: {file_path}")
    try:
        if not file_path.is_file():
             logger.warning(f"File not found during read attempt: {file_path}")
             return "File not found."
        if is_csv:
            try:
                df = pd.read_csv(file_path, nrows=csv_head_rows, on_bad_lines='skip')
                logger.info(f"Read head ({csv_head_rows} rows) of CSV: {file_path.name}")
                return df.to_string(index=False)
            except pd.errors.EmptyDataError:
                logger.warning(f"CSV file is empty: {file_path}")
                return "CSV file is empty."
            except Exception as e_csv:
                 logger.error(f"Error reading CSV {file_path}: {e_csv}", exc_info=False)
                 return f"Unable to read CSV due to error: {type(e_csv).__name__}"
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            logger.info(f"Read {len(content)} characters from: {file_path.name}")
            return content
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}", exc_info=False)
        return f"Unable to read file due to error: {type(e).__name__}"

def compress_python_code(code: str) -> str:
    """Compresses Python code: removes whitespace/simple comments, keeps docstrings."""
    # (Content unchanged from previous version)
    if not code or code.strip() == "": return ""
    lines = code.splitlines()
    compressed_lines = []
    in_docstring = False
    docstring_char = None
    for line in lines:
        stripped_line = line.strip()
        is_docstring_line = False
        if '"""' in stripped_line or "'''" in stripped_line:
            potential_char = '"""' if '"""' in stripped_line else "'''"
            if stripped_line.count(potential_char) % 2 != 0:
                 if not in_docstring:
                     if stripped_line.startswith(potential_char):
                         in_docstring = True
                         docstring_char = potential_char
                         is_docstring_line = True
                 elif docstring_char and stripped_line.endswith(docstring_char):
                     in_docstring = False
                     docstring_char = None
                     is_docstring_line = True
            elif in_docstring: is_docstring_line = True
            elif stripped_line.startswith(potential_char) and stripped_line.endswith(potential_char) and len(stripped_line) >= len(potential_char)*2:
                 is_docstring_line = True
        if is_docstring_line or in_docstring:
             compressed_lines.append(line)
             continue
        if not stripped_line: continue
        if stripped_line.startswith('#'): continue
        indent_level = len(line) - len(line.lstrip(' '))
        compressed_lines.append(' ' * indent_level + stripped_line)
    final_lines = []
    last_line_blank = True
    for line in compressed_lines:
        is_blank = not line.strip()
        if is_blank and last_line_blank: continue
        final_lines.append(line)
        last_line_blank = is_blank
    return "\n".join(final_lines)


@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
def summarize_content(content: str, file_path_str: str, model: str = "gpt-4o", max_input_tokens: int = 8000) -> str:
    """Summarizes content using the OpenAI API (for specific non-Python files)."""
    # (Content unchanged from previous version)
    logger.info(f"Requesting summary for essential/reference file: {file_path_str} using {model}")
    if not content or content.strip() == "" or content.startswith(("Unable to read", "File not found", "CSV file is empty.")):
        logger.warning(f"Skipping summary for empty or unreadable file: {file_path_str}")
        return "Content empty or unreadable, summary skipped."
    try:
        try: encoding = tiktoken.encoding_for_model(model)
        except KeyError: encoding = tiktoken.get_encoding("cl100k_base")
        tokens = encoding.encode(content)
        if len(tokens) > max_input_tokens:
            logger.warning(f"Content for {file_path_str} too long ({len(tokens)} tokens), truncating.")
            content = encoding.decode(tokens[:max_input_tokens]) + "\n... [TRUNCATED]"
        logger.debug(f"Sending {len(encoding.encode(content))} tokens to OpenAI for {file_path_str}.")
        response = client.chat.completions.create(
            model=model,
            messages=[{
                "role": "system",
                "content": "You are a skilled technical assistant. Provide a concise summary (max 50 words) of the provided configuration, metadata, or reference file's primary purpose and key content/structure."
            }, {
                "role": "user",
                "content": f"Summarize the file content from '{file_path_str}' in no more than 50 words:\n\n```\n{content}\n```"
            }],
            temperature=0.2, max_tokens=100, timeout=60
        )
        summary = response.choices[0].message.content.strip()
        logger.info(f"Summary received for: {file_path_str}")
        return summary
    except Exception as e:
        logger.error(f"OpenAI API error during summarization for {file_path_str}: {e}", exc_info=True)
        return "Summary could not be generated due to API error."

def format_detailed_block(fpath: Path, summary: str, code_or_snippet: str, root_dir: Path) -> str:
    """Formats the file details block for Section 3."""
    # (Content unchanged from previous version)
    relative_path = fpath.relative_to(root_dir)
    file_ext = fpath.suffix.lower()
    marker = "#PY " if file_ext == '.py' else "#FILE "
    block_lines = [
        f"{marker}File: {fpath.name}",
        f"@path: {relative_path.as_posix()}",
        f"@summary: {summary}",
        f"@code:",
        f"{code_or_snippet}"
    ]
    return "\n".join(block_lines)

# --- Main Execution Flow ---
def main() -> None:
    """Main function"""
    logger.info("--- Starting Focused Project Context Generation ---")
    # Create a temporary file path for the tree
    TREE_TEMP_PATH = REFERENCE_DIR / "_temp_tree.txt"
    try:
        REFERENCE_DIR.mkdir(parents=True, exist_ok=True)

        # --- Generate Tree FIRST using V1 logic ---
        logger.info("--- Generating Section 2 (Tree) using v1 logic ---")
        # Generate tree to a temporary file
        generate_folder_tree_v1(ROOT_DIR, TREE_TEMP_PATH)
        # Read the generated tree content
        tree_content = TREE_TEMP_PATH.read_text(encoding='utf-8') if TREE_TEMP_PATH.exists() else "# Error: Tree file not generated."
        logger.info("--- Finished Section 2 (Tree) generation ---")

        # --- Prepare Section 3 Details ---
        logger.info("--- Generating Section 3 (Details) content ---")
        target_files = get_target_files(ROOT_DIR, CONTEXT_DIRS_DETAILS, ESSENTIAL_NON_PY_FILES, DATA_FILES_TO_INCLUDE)
        section_3a_content = ["# --- 3A. .py files (Full Compressed Code) ---"]
        section_3b_content = ["# --- 3B. Non-.py files (Summaries + Snippets/Head) ---"]

        if not target_files:
            logger.warning("No target files found to process for details.")
            section_3a_content.append("\n# (No relevant Python files found)")
            section_3b_content.append("\n# (No relevant non-Python files found)")
        else:
            logger.info(f"Processing {len(target_files)} target files for details...")
            python_files = sorted([f for f in target_files if f.suffix.lower() == '.py'], key=lambda p: str(p).lower())
            non_python_files = sorted([f for f in target_files if f.suffix.lower() != '.py'], key=lambda p: str(p).lower())

            # Process Python files
            if not python_files: section_3a_content.append("\n# (No relevant Python files found)")
            for i, fpath in enumerate(python_files):
                rel_path_str = str(fpath.relative_to(ROOT_DIR).as_posix())
                logger.info(f"Processing PY file {i+1}/{len(python_files)}: {rel_path_str}")
                content = read_file_content(fpath)
                if content.startswith(("Unable to read", "File not found")):
                    code_output, summary = content, f"Note: {content}"
                else:
                    code_output = compress_python_code(content)
                    summary = "Full Python code (compressed) included below."
                block = format_detailed_block(fpath, summary, code_output, ROOT_DIR)
                section_3a_content.append(f"\n{block}\n")
                logger.debug(f"Buffered block for PY: {rel_path_str}")

            # Process Non-Python files
            if not non_python_files: section_3b_content.append("\n# (No relevant non-Python files found)")
            else:
                 max_len_snippet = 1000
                 for i, fpath in enumerate(non_python_files):
                     rel_path_str = str(fpath.relative_to(ROOT_DIR).as_posix())
                     logger.info(f"Processing Non-PY file {i+1}/{len(non_python_files)}: {rel_path_str}")
                     is_csv = fpath in DATA_FILES_TO_INCLUDE
                     is_essential_config = fpath in ESSENTIAL_NON_PY_FILES
                     is_in_reference = REFERENCE_DIR.resolve() in fpath.resolve().parents
                     content = read_file_content(fpath, is_csv=is_csv, csv_head_rows=5)
                     summary, snippet_or_head = "", ""
                     if content.startswith(("Unable to read", "File not found", "CSV file is empty.")):
                         summary, snippet_or_head = f"Note: {content}", content
                     elif is_csv:
                         summary, snippet_or_head = "Head (first 5 rows) of the expenses CSV data.", content
                     elif is_essential_config or is_in_reference:
                         summary = summarize_content(content, rel_path_str)
                         snippet_or_head = content[:max_len_snippet] + ('\n[...]' if len(content) > max_len_snippet else '')
                     else: continue # Skip unexpected files
                     block = format_detailed_block(fpath, summary, snippet_or_head, ROOT_DIR)
                     section_3b_content.append(f"\n{block}\n")
                     logger.debug(f"Buffered block for Non-PY: {rel_path_str}")

        logger.info("--- Finished Section 3 (Details) content generation ---")

        # --- Write Final Output File ---
        logger.info(f"Writing final output to: {OUTPUT_PATH}")
        with open(OUTPUT_PATH, 'w', encoding='utf-8') as outfile:
            # Section 1
            outfile.write("# --- 1. File Description ---\n\n")
            outfile.write("This file provides context for LLM assistants about the 'app-personal-finance' project.\n")
            outfile.write("It includes:\n")
            outfile.write("A. A file tree showing the project structure (excluding specified cache/build/git dirs).\n")
            outfile.write("B. Details for key files:\n")
            outfile.write("   - Python (.py): Full, whitespace/comment-compressed code (docstrings preserved).\n")
            outfile.write("   - Essential Config/Metadata/Reference: AI summary + truncated snippet.\n")
            outfile.write("   - data/expenses.csv: Head rows only.\n")
            outfile.write("The goal is to provide meaningful context focusing on application logic, tests, essential configuration, and reference materials.\n")
            outfile.write("\n")

            # Section 2
            outfile.write("# --- 2. Folder and File structure tree ---\n\n")
            outfile.write(tree_content)
            outfile.write("\n")

            # Section 3
            outfile.write("# --- 3. Code file summary ---\n")
            outfile.write("\n".join(section_3a_content))
            outfile.write("\n") # Separator
            outfile.write("\n".join(section_3b_content))
            outfile.write("\n") # Ensure final newline

        logger.info(f"✅ Successfully generated combined context file: {OUTPUT_PATH}")

    except Exception as e:
        logger.exception(f"An critical error occurred during context generation: {e}")
        print(f"❌ Error generating context file. Check logs. Error: {e}")
    finally:
         # Clean up temporary tree file
         if TREE_TEMP_PATH.exists():
             try:
                 TREE_TEMP_PATH.unlink()
                 logger.info(f"Removed temporary tree file: {TREE_TEMP_PATH}")
             except OSError as e:
                 logger.error(f"Error removing temporary tree file {TREE_TEMP_PATH}: {e}")


    logger.info("--- Context Generation Complete ---")


if __name__ == "__main__":
    main()