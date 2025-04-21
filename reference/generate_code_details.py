#!/usr/bin/env python3
"""
generate_code_details.py

Summarizes each relevant file in the 'app-personal-finance' project using GPT-4o and writes the result to
'reference/instruction_code_details.txt' in a structured format.

Handles:
- .py files → full code
- .csv files → top 5 rows
- Other files → first 1000 characters
- Skips .env, .log, .db, __pycache__, .git, etc.

Requirements:
- Python 3.8+
- openai>=1.0.0
- python-dotenv
- tqdm
- tenacity
- tiktoken
- pandas
"""

import os
import logging
import time
from pathlib import Path
from dotenv import load_dotenv
from typing import List
import pandas as pd
from openai import OpenAI
from tenacity import retry, wait_random_exponential, stop_after_attempt
import tiktoken

# Load environment variables
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Define paths
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
REFERENCE_DIR = ROOT_DIR / "reference"
OUTPUT_FILE = REFERENCE_DIR / "instruction_code_details.txt"

# Define exclusions
EXCLUDED_DIRS = {'.git', '__pycache__', '.vscode', '.idea', '.venv', 'venv', '.mypy_cache', '.pytest_cache'}
EXCLUDED_FILES = {'.env', '.log', '.gitignore'}
EXCLUDED_EXTENSIONS = {'.pyc', '.log', '.env', '.db'}

def get_all_relevant_files(directory: Path) -> List[Path]:
    files = []
    for root, dirs, filenames in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for fname in filenames:
            fpath = Path(root) / fname
            if (
                fpath.suffix.lower() not in EXCLUDED_EXTENSIONS and
                fpath.name not in EXCLUDED_FILES
            ):
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
        logger.error(f"Error reading file {file_path}: {e}")
        return "Unable to read file."

def count_tokens(text: str, model: str = "gpt-4o") -> int:
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))

def truncate_for_summary(text: str, model: str = "gpt-4o", max_tokens: int = 8000) -> str:
    encoding = tiktoken.encoding_for_model(model)
    tokens = encoding.encode(text)
    return encoding.decode(tokens[:max_tokens])

@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
def summarize_content(content: str, model: str = "gpt-4o") -> str:
    try:
        if count_tokens(content, model) > 12000:
            content = truncate_for_summary(content, model)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an assistant that summarizes code files."},
                {"role": "user", "content": f"Summarize the following file in no more than 50 words:\n\n{content}"}
            ],
            temperature=0.3,
            max_tokens=100
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        return "Summary could not be generated due to an error."

def main() -> None:
    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
    files = get_all_relevant_files(ROOT_DIR)

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as out:
        out.write("# instruction_code_details.txt\n")
        out.write("\"\"\"\nDescribes the functionality of each file in the ROOT project directory and its sub directories, their path relative to ROOT, and their code for .py files and relevant snippets for non .py files. Purpose is to set the context of the project.\n\"\"\"\n\n")

        for fpath in files:
            rel_path = fpath.relative_to(ROOT_DIR)
            ftype = fpath.suffix.lower()
            filename = fpath.name

            logger.info(f"Processing {rel_path}")

            code_content = read_file_content(fpath)
            summary_input = code_content if ftype == '.py' else code_content[:1000]
            summary = summarize_content(summary_input)

            out.write(f"File: {filename}\n")
            out.write(f"Location: {rel_path}\n")
            out.write(f"Summary: {summary}\n")
            out.write(f"Code: \"\"\"\n{code_content}\n\"\"\"\n\n")

        logger.info(f"✅ Summaries written to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
