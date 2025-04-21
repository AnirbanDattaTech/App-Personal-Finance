#!/usr/bin/env python3
"""
Compresses instruction_code_details.txt into a more LLM-efficient format by:
1. Removing redundant labels (File/Location/Summary headers)
2. Truncating non-Python code to 300 characters
3. Using compact Markdown-style headers
4. Aggressive whitespace reduction
"""

import re
from pathlib import Path

def compress_file(input_path: Path, output_path: Path) -> None:
    current_block = []
    in_code_block = False
    file_ext = None
    
    with open(input_path, 'r', encoding='utf-8') as infile, \
         open(output_path, 'w', encoding='utf-8') as outfile:
        
        for line in infile:
            line = line.strip()
            
            # Detect section start
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
                
                # Apply truncation rules
                if file_ext == '.py':
                    truncated = code[:6000] + ('[...]' if len(code) > 6000 else '')
                else:
                    truncated = code[:300] + ('[...]' if len(code) > 300 else '')
                
                current_block.append(f"@code:\n{truncated}")
            
            elif in_code_block:
                code_lines.append(line)
        
        # Write final block
        if current_block:
            _write_compressed_block(current_block, file_ext, outfile)

def _write_compressed_block(block: list, ext: str, outfile):
    # Join with minimal delimiters
    compressed = '\n'.join(block)
    
    # Add type-specific markers
    if ext == '.py':
        compressed = compressed.replace("# ", "#PY ")
    else:
        compressed = compressed.replace("# ", "#FILE ")
    
    outfile.write(f"\n{compressed}\n")

if __name__ == "__main__":
    input_file = Path(__file__).parent.parent / "reference" / "instruction_code_details.txt"
    output_file = input_file.parent / "instruction_code_details_compressed.txt"
    
    compress_file(input_file, output_file)
    print(f"✅ Compressed file created: {output_file}")