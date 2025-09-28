import json
from pathlib import Path

def save_state(results, path: Path):
    with open(path, "w") as f: json.dump(results, f, indent=2)

def load_state(path: Path):
    if not path.exists(): return None
    with open(path) as f: return json.load(f)
