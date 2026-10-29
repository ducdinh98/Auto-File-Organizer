import time
import shutil
from pathlib import Path
from typing import Callable, Optional, Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from organizer_core import FileOrganizer

class AutoFileHandler(FileSystemEventHandler):
    def __init__(
        self,
        organizer: FileOrganizer,
        on_file_organized: Optional[Callable[[str, str], None]] = None
    ):
        super().__init__()
        self.organizer = organizer
        self.on_file_organized = on_file_organized
        self.parent_dir = self.organizer.parent_dir.resolve()
        self.processing_files: Set[str] = set()

    def on_created(self, event):
        if not event.is_directory:
            self._handle_event_file(Path(event.src_path))

    def on_moved(self, event):
        if not event.is_directory:
            self._handle_event_file(Path(event.dest_path))

    def _handle_event_file(self, file_path: Path):
        file_path = file_path.resolve()

        # Chỉ xử lý các file nằm trực tiếp tại thư mục mẹ
        if file_path.parent != self.parent_dir:
            return

        # Bỏ qua các file tạm của Windows và trình duyệt
        fname = file_path.name
        if fname.startswith("~") or fname.startswith("."):
            return
        if file_path.suffix.lower() in [".tmp", ".crdownload", ".part", ".downloading", ".opdownload"]:
            return

        key = str(file_path)
        if key in self.processing_files:
            return

        self.processing_files.add(key)
        try:
            # Đợi file ghi xong hoàn toàn
            if not self._wait_file_ready(file_path):
                return

            if not file_path.exists():
                return

            subfolders = self.organizer.get_existing_subfolders()
            target_folder_name, cat_label = self.organizer.find_target_folder_name(file_path, subfolders)
            if not target_folder_name or target_folder_name == ".":
                return

            dest_dir = self.parent_dir / Path(target_folder_name)
            try:
                if file_path.parent.resolve() == dest_dir.resolve():
                    return
            except Exception:
                pass

            dest_dir.mkdir(parents=True, exist_ok=True)
            final_dest = self.organizer.get_unique_destination(dest_dir, file_path.name)
            shutil.move(str(file_path), str(final_dest))

            if self.on_file_organized:
                self.on_file_organized(file_path.name, target_folder_name)
        except Exception as e:
            print(f"[Watcher Error] Không thể di chuyển {file_path.name}: {e}")
        finally:
            self.processing_files.discard(key)

    def _wait_file_ready(self, file_path: Path, max_wait_sec: float = 15.0) -> bool:
        start_time = time.time()
        last_size = -1
        stable_count = 0

        while time.time() - start_time < max_wait_sec:
            if not file_path.exists():
                return False
            try:
                curr_size = file_path.stat().st_size
                with open(file_path, "ab"):
                    pass

                if curr_size == last_size:
                    stable_count += 1
                    if stable_count >= 2:
                        return True
                else:
                    stable_count = 0

                last_size = curr_size
            except (PermissionError, OSError):
                stable_count = 0

            time.sleep(0.5)

        return file_path.exists()


class DirectoryWatcher:
    """Quản lý tiến trình theo dõi thư mục ngầm có tích hợp AI."""
    def __init__(
        self,
        directory: str,
        match_existing: bool = True,
        use_accent: bool = True,
        enable_ai: bool = False,
        ai_engine: str = "offline",
        gemini_api_key: str = "",
        ai_categorize_video: bool = True,
        enable_device_categorize: bool = False,
        enable_lighting_categorize: bool = False,
        enable_focal_categorize: bool = False,
        on_organized_cb: Optional[Callable[[str, str], None]] = None
    ):
        self.directory = Path(directory)
        self.match_existing = match_existing
        self.use_accent = use_accent
        self.enable_ai = enable_ai
        self.ai_engine = ai_engine
        self.gemini_api_key = gemini_api_key
        self.ai_categorize_video = ai_categorize_video
        self.enable_device_categorize = enable_device_categorize
        self.enable_lighting_categorize = enable_lighting_categorize
        self.enable_focal_categorize = enable_focal_categorize
        self.on_organized_cb = on_organized_cb
        self.observer: Optional[Observer] = None
        self.is_running = False

    def start(self) -> bool:
        if not self.directory.exists() or not self.directory.is_dir():
            return False

        if self.is_running:
            self.stop()

        organizer = FileOrganizer(
            parent_dir=str(self.directory),
            match_existing_folders=self.match_existing,
            use_accent_folder=self.use_accent,
            recursive=False,
            enable_ai=self.enable_ai,
            ai_engine=self.ai_engine,
            gemini_api_key=self.gemini_api_key,
            ai_categorize_video=self.ai_categorize_video,
            enable_device_categorize=self.enable_device_categorize,
            enable_lighting_categorize=self.enable_lighting_categorize,
            enable_focal_categorize=self.enable_focal_categorize
        )

        handler = AutoFileHandler(organizer, on_file_organized=self.on_organized_cb)
        self.observer = Observer()
        self.observer.schedule(handler, str(self.directory), recursive=False)
        self.observer.daemon = True
        self.observer.start()
        self.is_running = True
        return True

    def stop(self):
        if self.observer and self.is_running:
            try:
                self.observer.stop()
                self.observer.join(timeout=2.0)
            except Exception:
                pass
            self.observer = None
        self.is_running = False
