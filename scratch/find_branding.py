import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

search_terms = [
    "CodeIntel",
    "codeintel",
    "CODEINTEL",
    "Code Intel",
    "code intel",
    "Sajal Dwivedi",
    "Sajal Diwedi",
    "Sajal",
    "Sajaldwivedi",
    "sajaldwivedi",
]

pattern = re.compile("|".join(re.escape(t) for t in search_terms), re.IGNORECASE)

ignore_dirs = {'.git', 'node_modules', '__pycache__', '.pytest_cache', 'dist', 'build', '.venv', 'venv'}

matches = []
root_dir = r"c:\Users\saura\OneDrive\Desktop\CodeIntel-main"

for dirpath, dirnames, filenames in os.walk(root_dir):
    dirnames[:] = [d for d in dirnames if d not in ignore_dirs]
    for filename in filenames:
        if filename.endswith(('.pyc', '.png', '.jpg', '.jpeg', '.ico', '.tar', '.gz', '.zip', '.db')):
            continue
        filepath = os.path.join(dirpath, filename)
        if 'scratch' in filepath:
            continue
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                for line_idx, line in enumerate(lines, 1):
                    if pattern.search(line):
                        rel_path = os.path.relpath(filepath, root_dir)
                        matches.append((rel_path, line_idx, line.strip()))
        except Exception as e:
            pass

print(f"Total matches found: {len(matches)}\n")
for rel_path, line_idx, line in matches:
    print(f"{rel_path}:{line_idx}: {line}")
