import yaml
from pathlib import Path
from typing import Dict, Any

def load_config() -> Dict[str, Any]:
    config_path = Path(__file__).parent.parent / "config" / "config.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

def load_taxonomies() -> Dict[str, Any]:
    taxonomies_path = Path(__file__).parent.parent / "config" / "taxonomies.yaml"
    with open(taxonomies_path, "r") as f:
        return yaml.safe_load(f)

if __name__ == "__main__":
    config = load_config()
    taxonomies = load_taxonomies()
    print("Config loaded successfully.")
