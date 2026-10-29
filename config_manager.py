import json
import os
from pathlib import Path
from typing import Dict, Any

import sys

def get_config_file() -> Path:
    """Xác định đường dẫn file config.json cho ứng dụng Portable."""
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        config_path = exe_dir / "config.json"
        try:
            test_file = exe_dir / ".write_test"
            test_file.touch()
            test_file.unlink()
            return config_path
        except Exception:
            fallback_dir = Path.home() / ".sapxepfile"
            fallback_dir.mkdir(parents=True, exist_ok=True)
            return fallback_dir / "config.json"
    else:
        return Path(__file__).resolve().parent / "config.json"

DEFAULT_CONFIG: Dict[str, Any] = {
    "watched_directory": "",
    "auto_mode": False,
    "autostart_with_windows": False,
    "minimize_to_tray_on_close": True,
    "match_existing_folders": True,
    "use_accent_names": True,
    "recursive": False,
    # Cấu hình AI (Mặc định tắt, ưu tiên phân loại tệp trước)
    "enable_ai": False,
    "ai_engine": "offline",  # "offline" hoặc "cloud"
    "gemini_api_key": "",
    "ai_categorize_video": True,
    # Cấu hình phân loại ảnh theo Thiết Bị & Thông Số Chụp
    "enable_device_categorize": False,
    "enable_lighting_categorize": False,
    "enable_focal_categorize": False
}

def load_config() -> Dict[str, Any]:
    """Tải cấu hình từ config.json, nếu chưa có thì tạo mới."""
    config_file = get_config_file()
    if not config_file.exists():
        save_config(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            for k, v in DEFAULT_CONFIG.items():
                if k not in data:
                    data[k] = v
            return data
    except Exception as e:
        print(f"Lỗi khi đọc config.json: {e}")
        return dict(DEFAULT_CONFIG)

def save_config(config: Dict[str, Any]) -> bool:
    """Lưu cấu hình vào file config.json."""
    config_file = get_config_file()
    try:
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Lỗi khi lưu config.json: {e}")
        return False
