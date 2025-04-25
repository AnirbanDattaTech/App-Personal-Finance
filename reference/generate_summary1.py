#!/usr/bin/env python3
"""
generate_summary.py - Combined documentation generator for app-personal-finance
Combines functionality from:
- generate_code_details.py
- generate_code_details_compressed.py 
- generate_tree.py
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from typing import List
import pandas as pd
from openai import OpenAI
from tenacity import retry, wait_random_exponential, stop_after_attempt
import tiktoken

# --- Configuration ---
load_dotenv()
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
REFERENCE_DIR = ROOT_DIR / "reference"

# File paths
CODE_DETAILS_PATH = REFERENCE_DIR / "instruction_code_details.txt"
COMPRESSED_PATH = REFERENCE_DIR / "instruction_code_details_compressed.txt"
TREE_PATH = REFERENCE_DIR / "instruction_file_tree.txt"

# Exclusion lists (combined from original scripts)
EXCLUDED_DIRS = {'.git', '__pycache__', '.vscode', '.idea', '.venv', 'venv', 
                '.mypy_cache', '.pytest_cache', '.git', '.vscode', '.idea', 'venv', '.github'}
EXCLUDED_FILES = {'.env', '.log', '.gitignore', '.env', '.gitignore'}
EXCLUDED_EXTENSIONS = {'.pyc', '.log', '.env', '.db', '.codespellignore'}

# OpenAI setup
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- Shared Functions from generate_code_details.py ---
def get_all_relevant_files(directory: Path) -> List[Path]:
    files = []
    for root, dirs, filenames in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for fname in filenames:
            fpath = Path(root) / fname
            if (fpath.suffix.lower() not in EXCLUDED_EXTENSIONS and 
                fpath.name not in EXCLUDED_FILES):
                files.append(fpath)
    return files

def read_file_content(file_path: Path) -> str:
    try:
        if file_path.suffix.lower() == '.csv':
            df = pd.read_csv(file_path)
            return df.head().to_string(index=False)
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logging.error(f"Error reading file {file_path}: {e}")
        return "Unable to read file."

@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
def summarize_content(content: str, model: str = "gpt-4o") -> str:
    try:
        encoding = tiktoken.encoding_for_model(model)
        tokens = encoding.encode(content)
        if len(tokens) > 12000:
            content = encoding.decode(tokens[:8000])
        response = client.chat.completions.create(
            model=model,
            messages=[{
                "role": "system",
                "content": "You are an assistant that summarizes code files."
            }, {
                "role": "user",
                "content": f"Summarize the following file in no more than 50 words:\n\n{content}"
            }],
            temperature=0.3,
            max_tokens=100
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"OpenAI API error: {e}")
        return "Summary could not be generated."

# --- Compression Logic from generate_code_details_compressed.py ---
def compress_code_details():
    current_block = []
    in_code_block = False
    file_ext = None
    
    with open(CODE_DETAILS_PATH, 'r', encoding='utf-8') as infile, \
         open(COMPRESSED_PATH, 'w', encoding='utf-8') as outfile:
        
        for line in infile:
            line = line.strip()
            
            if line.startswith("File: "):
                if current_block:
                    _write_compressed_block(current_block, file_ext, outfile)
                    current_block = []
                current_block.append(f"# {line[6:]}")
            
            elif line.startswith("Location: "):
                path = line[10:]
                file_ext = Path(path).suffix.lower()
                current_block.append(f"@path: {path}")
            
            elif line.startswith("Summary: "):
                current_block.append(f"@summary: {line[9:]}")
            
            elif line == 'Code: """':
                in_code_block = True
                code_lines = []
            
            elif line == '"""' and in_code_block:
                in_code_block = False
                code = '\n'.join(code_lines)
                truncated = code[:6000] + ('[...]' if len(code) > 6000 else '') \
                    if file_ext == '.py' else code[:300] + ('[...]' if len(code) > 300 else '')
                current_block.append(f"@code:\n{truncated}")
            
            elif in_code_block:
                code_lines.append(line)
        
        if current_block:
            _write_compressed_block(current_block, file_ext, outfile)

def _write_compressed_block(block: list, ext: str, outfile):
    compressed = '\n'.join(block)
    marker = "#PY " if ext == '.py' else "#FILE "
    outfile.write(f"\n{compressed.replace('# ', marker)}\n")

# --- Tree Generation from generate_tree.py ---
def generate_folder_tree():
    with open(TREE_PATH, 'w', encoding='utf-8') as f:
        for root, dirs, files in os.walk(ROOT_DIR, topdown=True):
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
            level = root.replace(str(ROOT_DIR), '').count(os.sep)
            indent = ' ' * 4 * level
            
            if root == str(ROOT_DIR):
                f.write(f'{ROOT_DIR.name}/\n')
            else:
                f.write(f'{indent}{os.path.basename(root)}/\n')
            
            subindent = ' ' * 4 * (level + 1)
            for file in files:
                if file not in EXCLUDED_FILES:
                    f.write(f'{subindent}{file}\n')

# --- Main Execution Flow ---
def main():
    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
    
    # Step 1: Generate code details
    with open(CODE_DETAILS_PATH, 'w', encoding='utf-8') as out:
        out.write("# instruction_code_details.txt\n\"\"\"\nDescribes the functionality of each file...\n\"\"\"\n\n")
        for fpath in get_all_relevant_files(ROOT_DIR):
            rel_path = fpath.relative_to(ROOT_DIR)
            content = read_file_content(fpath)
            summary = summarize_content(content if fpath.suffix == '.py' else content[:1000])
            out.write(f"File: {fpath.name}\nLocation: {rel_path}\nSummary: {summary}\nCode: \"\"\"\n{content}\n\"\"\"\n\n")
    
    # Step 2: Compress code details
    compress_code_details()
    
    # Step 3: Generate folder tree
    generate_folder_tree()
    
    print(f"✅ Summary files generated in {REFERENCE_DIR}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()