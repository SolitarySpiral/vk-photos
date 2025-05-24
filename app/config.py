import yaml
from pathlib import Path
import os
import sys
import subprocess

CONFIG_PATH = Path("vk-photos/config.yaml")

def load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}

def save_config(data: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f)

def load_token_from_config() -> str:
    return load_config().get("token", "")

def save_token_to_config(token: str) -> None:
    cfg = load_config()
    cfg["token"] = token
    save_config(cfg)

def load_download_dir_from_config() -> str:
    return load_config().get("download_dir", "")

def save_download_dir_to_config(path: str) -> None:
    cfg = load_config()
    cfg["download_dir"] = path
    save_config(cfg)

def open_folder(path):
    if sys.platform == "win32":
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:  # Linux
        subprocess.Popen(["xdg-open", path])