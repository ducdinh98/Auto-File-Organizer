import threading
from PIL import Image, ImageDraw, ImageEnhance
import pystray
from typing import Callable, Optional
from pathlib import Path
import sys

def get_resource_path(relative_path: str) -> Path:
    if hasattr(sys, "_MEIPASS"):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).resolve().parent
    return base_path / relative_path

def create_tray_image(is_active: bool = True) -> Image.Image:
    """Tạo biểu tượng thư mục đỏ cho System Tray từ logo thực tế."""
    logo_path = get_resource_path("assets/logo.png")
    if not logo_path.exists():
        logo_path = get_resource_path("logo.png")

    if logo_path.exists():
        try:
            img = Image.open(logo_path).convert("RGBA")
            img = img.resize((64, 64), Image.Resampling.LANCZOS)
            if is_active:
                draw = ImageDraw.Draw(img)
                # Chấm xanh Apple báo hiệu đang theo dõi tự động
                draw.ellipse([46, 6, 60, 20], fill=(48, 209, 88, 255), outline=(255, 255, 255, 255), width=2)
                return img
            else:
                gray = img.convert("LA").convert("RGBA")
                enhancer = ImageEnhance.Brightness(gray)
                return enhancer.enhance(0.7)
        except Exception:
            pass

    # Fallback vẽ biểu tượng nếu không tìm thấy file logo
    img = Image.new("RGBA", (64, 64), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    folder_color = (235, 60, 60, 255) if is_active else (100, 100, 100, 255)
    tab_color = (180, 40, 40, 255) if is_active else (70, 70, 70, 255)
    draw.rounded_rectangle([6, 12, 30, 26], radius=4, fill=tab_color)
    draw.rounded_rectangle([6, 20, 58, 54], radius=6, fill=folder_color)
    if is_active:
        draw.ellipse([44, 8, 58, 22], fill=(48, 209, 88, 255), outline=(255, 255, 255, 255), width=2)
    return img

class SystemTrayManager:
    def __init__(
        self,
        app_title: str = "Tự Động Sắp Xếp File",
        on_show_gui: Optional[Callable[[], None]] = None,
        on_toggle_auto: Optional[Callable[[], None]] = None,
        on_open_folder: Optional[Callable[[], None]] = None,
        on_quit: Optional[Callable[[], None]] = None,
        is_auto_active: bool = False
    ):
        self.app_title = app_title
        self.on_show_gui = on_show_gui
        self.on_toggle_auto = on_toggle_auto
        self.on_open_folder = on_open_folder
        self.on_quit = on_quit
        self.is_auto_active = is_auto_active
        self.icon: Optional[pystray.Icon] = None
        self._thread: Optional[threading.Thread] = None

    def _build_menu(self):
        auto_text = "🟢 Tự động: ĐANG BẬT" if self.is_auto_active else "⚪ Tự động: ĐANG TẮT"
        return pystray.Menu(
            pystray.MenuItem("📂 Mở giao diện", lambda icon, item: self.on_show_gui() if self.on_show_gui else None, default=True),
            pystray.MenuItem(auto_text, lambda icon, item: self.on_toggle_auto() if self.on_toggle_auto else None),
            pystray.MenuItem("📁 Mở thư mục theo dõi", lambda icon, item: self.on_open_folder() if self.on_open_folder else None),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("❌ Thoát hoàn toàn", lambda icon, item: self._quit())
        )

    def _quit(self):
        self.stop()
        if self.on_quit:
            self.on_quit()

    def update_state(self, is_active: bool):
        self.is_auto_active = is_active
        if self.icon:
            self.icon.icon = create_tray_image(is_active)
            self.icon.menu = self._build_menu()

    def notify(self, title: str, message: str):
        if self.icon:
            try:
                self.icon.notify(message, title)
            except Exception:
                pass

    def start(self):
        if self.icon is not None:
            return
        img = create_tray_image(self.is_auto_active)
        self.icon = pystray.Icon(
            "AutoFileOrganizer",
            img,
            self.app_title,
            self._build_menu()
        )
        self._thread = threading.Thread(target=self.icon.run, daemon=True)
        self._thread.start()

    def stop(self):
        if self.icon:
            try:
                self.icon.stop()
            except Exception:
                pass
            self.icon = None
