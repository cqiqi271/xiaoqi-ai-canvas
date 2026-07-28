import json
from pathlib import Path

import main as _main

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "project-config.json"

DEFAULT_CONFIG = {
    "project_name": "Infinite Canvas",
    "home_url": "http://127.0.0.1:3011/",
    "version_url": "",
    "update_notes_url": "",
    "tree_url": "",
    "mirror_home_url": "",
    "mirror_version_url": "",
    "mirror_update_notes_url": "",
    "mirror_tree_url": "",
}


def load_config() -> dict:
    try:
        if CONFIG_PATH.exists():
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {**DEFAULT_CONFIG, **data}
    except Exception:
        pass
    return dict(DEFAULT_CONFIG)


CONFIG = load_config()

# Override runtime URLs without editing the upstream main.py.
_main.GITHUB_REPO_URL = str(CONFIG.get("home_url") or "").strip() or _main.GITHUB_REPO_URL
_main.GITHUB_VERSION_URL = str(CONFIG.get("version_url") or "").strip() or _main.GITHUB_VERSION_URL
_main.GITHUB_TREE_URL = str(CONFIG.get("tree_url") or "").strip() or _main.GITHUB_TREE_URL
_main.GITHUB_UPDATE_NOTES_URL = str(CONFIG.get("update_notes_url") or "").strip() or _main.GITHUB_UPDATE_NOTES_URL
_main.MODELSCOPE_REPO_URL = str(CONFIG.get("mirror_home_url") or "").strip() or _main.MODELSCOPE_REPO_URL
_main.MODELSCOPE_VERSION_URL = str(CONFIG.get("mirror_version_url") or "").strip() or _main.MODELSCOPE_VERSION_URL
_main.MODELSCOPE_UPDATE_NOTES_URL = str(CONFIG.get("mirror_update_notes_url") or "").strip() or _main.MODELSCOPE_UPDATE_NOTES_URL
_main.MODELSCOPE_TREE_URL = str(CONFIG.get("mirror_tree_url") or "").strip() or _main.MODELSCOPE_TREE_URL

# Keep the update UI labels readable and stable.
_main.UPDATE_SOURCE_LABELS = {
    "github": str(CONFIG.get("project_name") or "Infinite Canvas").strip(),
    "modelscope": "Backup Update Source",
}

app = _main.app
