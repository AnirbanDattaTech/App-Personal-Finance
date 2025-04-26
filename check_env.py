# check_env.py
import sys
import os
import importlib.util

print(f"--- Python Executable ---")
print(sys.executable) # Shows which python is running this script
print("-" * 25)

print("\n--- sys.path ---")
for p in sys.path:
    print(p) # Shows where Python looks for modules
print("-" * 25)

print("\n--- Checking Pandas Import ---")
try:
    spec = importlib.util.find_spec("pandas")
    if spec is not None:
        print(f"Pandas found at: {spec.origin}")
        import pandas as pd
        print(f"Pandas successfully imported. Version: {pd.__version__}")
    else:
        print("Pandas specification NOT found by importlib.")
except ImportError:
    print("Pandas import FAILED.")
except Exception as e:
    print(f"An unexpected error occurred during pandas check: {e}")
print("-" * 25)

print("\n--- PATH Environment Variable ---")
path_var = os.environ.get('PATH', '')
path_list = path_var.split(os.pathsep)
print("Entries in PATH:")
for entry in path_list:
    print(entry)
print("-" * 25)

print("\n--- Checking if genai paths are in PATH ---")
genai_scripts = r"E:\Code\venv\conda\genai\Scripts"
genai_lib_bin = r"E:\Code\venv\conda\genai\Library\bin" # Common on Windows
genai_base = r"E:\Code\venv\conda\genai"

if any(p.lower().startswith(genai_scripts.lower()) for p in path_list):
     print(f"✅ Found path starting with: {genai_scripts}")
else:
     print(f"❌ Did NOT find expected Scripts path starting with: {genai_scripts}")

if any(p.lower().startswith(genai_lib_bin.lower()) for p in path_list):
     print(f"✅ Found path starting with: {genai_lib_bin}")
else:
     print(f"❌ Did NOT find expected Library\\bin path starting with: {genai_lib_bin}")

if any(p.lower().startswith(genai_base.lower()) for p in path_list if not p.lower().startswith(genai_scripts.lower()) and not p.lower().startswith(genai_lib_bin.lower())):
     print(f"✅ Found other path starting with: {genai_base}")
else:
     print(f"❌ Did NOT find other base path starting with: {genai_base}")