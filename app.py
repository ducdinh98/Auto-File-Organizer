import os
import sys
import threading
import json
import urllib.request
import urllib.error
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from PIL import Image, ImageTk
import customtkinter as ctk

from organizer_core import FileOrganizer, DEFAULT_CATEGORIES
from watcher import DirectoryWatcher
from config_manager import load_config, save_config
from autostart_helper import set_autostart, check_autostart
from tray_helper import SystemTrayManager
from ai_classifier import AI_CATEGORIES, GEMINI_MODELS_PRIORITY

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


def get_resource_path(relative_path: str) -> Path:
    """Xác định đường dẫn tài nguyên tĩnh cho cả môi trường chạy trực tiếp và đóng gói PyInstaller."""
    if hasattr(sys, "_MEIPASS"):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).resolve().parent
    return base_path / relative_path


class FileOrganizerApp(ctk.CTk):
    def __init__(self, start_in_background: bool = False):
        super().__init__()

        self.title("Tự Động Sắp Xếp File Vào Thư Mục Con - Auto File Organizer")
        self.geometry("1080x880")
        self.minsize(980, 720)

        # Cấu hình biểu tượng cửa sổ (Window & Taskbar Icon)
        self._set_app_window_icon()

        # Cấu hình đã lưu (Mặc định enable_ai = False)
        self.config = load_config()
        self.selected_directory = self.config.get("watched_directory", "")
        self.current_plan = []
        self.is_processing = False
        self.is_scanning = False

        # Khởi tạo Watcher và Tray Manager
        self.watcher: DirectoryWatcher = None
        self.tray_manager = SystemTrayManager(
            app_title="Tự Động Sắp Xếp File",
            on_show_gui=self.show_window_from_tray,
            on_toggle_auto=self.toggle_auto_mode_from_tray,
            on_open_folder=self.open_current_directory,
            on_quit=self.quit_completely,
            is_auto_active=self.config.get("auto_mode", False)
        )
        self.tray_manager.start()

        self.init_ui()
        self.update_tree_theme(ctk.get_appearance_mode())

        self.protocol("WM_DELETE_WINDOW", self.on_window_close)

        if self.selected_directory and os.path.isdir(self.selected_directory):
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, self.selected_directory)
            self.trigger_scan_async()

        if self.config.get("auto_mode", False) and self.selected_directory:
            self.start_auto_watcher()

        if start_in_background:
            self.withdraw()

    def _set_app_window_icon(self):
        try:
            ico_path = get_resource_path("assets/logo.ico")
            if not ico_path.exists():
                ico_path = get_resource_path("logo.ico")
            if ico_path.exists():
                self.iconbitmap(str(ico_path))

            png_path = get_resource_path("assets/logo.png")
            if not png_path.exists():
                png_path = get_resource_path("logo.png")
            if png_path.exists():
                self._app_icon_tk = ImageTk.PhotoImage(file=str(png_path))
                self.iconphoto(False, self._app_icon_tk)
        except Exception as e:
            print(f"[Icon Error] Không thể gán icon cửa sổ: {e}")

    def init_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)  # Bảng danh sách co giãn tối đa

        # ========================================================
        # 1. HEADER (PHONG CÁCH APPLE MACOS)
        # ========================================================
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=24, pady=(14, 6), sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1)

        # Logo thương hiệu (Red Folder Logo)
        logo_png = get_resource_path("assets/logo.png")
        if not logo_png.exists():
            logo_png = get_resource_path("logo.png")

        if logo_png.exists():
            try:
                logo_img_pil = Image.open(logo_png)
                self.header_logo_ctk = ctk.CTkImage(
                    light_image=logo_img_pil,
                    dark_image=logo_img_pil,
                    size=(42, 42)
                )
                logo_lbl = ctk.CTkLabel(header_frame, image=self.header_logo_ctk, text="")
                logo_lbl.grid(row=0, column=0, padx=(0, 12), sticky="w")
            except Exception:
                logo_badge = ctk.CTkFrame(header_frame, width=38, height=38, corner_radius=10, fg_color="#E03E3E")
                logo_badge.grid(row=0, column=0, padx=(0, 12), sticky="w")
                logo_badge.grid_propagate(False)
                logo_lbl = ctk.CTkLabel(logo_badge, text="📁", font=ctk.CTkFont(size=18), text_color="#FFFFFF")
                logo_lbl.place(relx=0.5, rely=0.5, anchor="center")
        else:
            logo_badge = ctk.CTkFrame(header_frame, width=38, height=38, corner_radius=10, fg_color="#E03E3E")
            logo_badge.grid(row=0, column=0, padx=(0, 12), sticky="w")
            logo_badge.grid_propagate(False)
            logo_lbl = ctk.CTkLabel(logo_badge, text="📁", font=ctk.CTkFont(size=18), text_color="#FFFFFF")
            logo_lbl.place(relx=0.5, rely=0.5, anchor="center")

        # Tiêu đề & phụ đề
        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.grid(row=0, column=1, sticky="w")

        title_label = ctk.CTkLabel(
            title_box,
            text="Sắp Xếp File Tự Động",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold")
        )
        title_label.pack(anchor="w")

        subtitle_label = ctk.CTkLabel(
            title_box,
            text="Phân loại thông minh • Nhận diện thiết bị & EXIF • Trí tuệ nhân tạo (AI)",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#8E8E93"
        )
        subtitle_label.pack(anchor="w", pady=(1, 0))

        # Nút chuyển giao diện Sáng / Tối
        self.theme_switch = ctk.CTkSwitch(
            header_frame,
            text="Giao diện tối",
            command=self.toggle_theme,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            progress_color="#0A84FF"
        )
        if ctk.get_appearance_mode().lower() == "dark":
            self.theme_switch.select()
        else:
            self.theme_switch.deselect()
        self.theme_switch.grid(row=0, column=2, sticky="e")

        # ========================================================
        # 2. KHUNG CHỌN THƯ MỤC NGUỒN (SOURCE SELECTOR)
        # ========================================================
        control_card = ctk.CTkFrame(self, corner_radius=12, border_width=1, border_color=("#E5E5EA", "#2C2C32"))
        control_card.grid(row=1, column=0, padx=24, pady=(0, 6), sticky="ew")
        control_card.grid_columnconfigure(1, weight=1)

        folder_lbl = ctk.CTkLabel(
            control_card,
            text="Thư mục nguồn:",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=("#1D1D1F", "#E5E5EA")
        )
        folder_lbl.grid(row=0, column=0, padx=(16, 10), pady=10, sticky="w")

        self.path_entry = ctk.CTkEntry(
            control_card,
            placeholder_text="Chọn hoặc dán đường dẫn thư mục cần sắp xếp tại đây...",
            height=36,
            corner_radius=8,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            border_width=1,
            border_color=("#D1D1D6", "#3A3A42")
        )
        self.path_entry.grid(row=0, column=1, padx=(0, 10), pady=10, sticky="ew")
        self.path_entry.bind("<Return>", lambda e: self.trigger_scan_async())

        browse_btn = ctk.CTkButton(
            control_card,
            text="Duyệt Thư Mục...",
            width=135,
            height=36,
            corner_radius=8,
            command=self.browse_directory,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#0A84FF",
            hover_color="#0071E3",
            text_color="#FFFFFF"
        )
        browse_btn.grid(row=0, column=2, padx=(0, 8), pady=10, sticky="e")

        self.rescan_btn = ctk.CTkButton(
            control_card,
            text="Quét Lại",
            width=90,
            height=36,
            corner_radius=8,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color=("#E5E5EA", "#2A2A30"),
            hover_color=("#D1D1D6", "#383840"),
            text_color=("#1D1D1F", "#F5F5F7"),
            command=self.trigger_scan_async
        )
        self.rescan_btn.grid(row=0, column=3, padx=(0, 14), pady=10, sticky="e")

        # ========================================================
        # 3. TABVIEW CÀI ĐẶT THÔNG MINH (APPLE SETTINGS STYLE)
        # ========================================================
        self.settings_tabview = ctk.CTkTabview(
            self,
            height=138,
            corner_radius=12,
            border_width=1,
            border_color=("#E5E5EA", "#2C2C32"),
            segmented_button_selected_color="#0A84FF",
            segmented_button_selected_hover_color="#0071E3"
        )
        self.settings_tabview.grid(row=2, column=0, padx=24, pady=(0, 4), sticky="ew")

        tab_basic = self.settings_tabview.add("Cài Đặt Chung & Tự Động")
        tab_photo = self.settings_tabview.add("Phân Loại Ảnh & EXIF")
        tab_ai = self.settings_tabview.add("Phân Tích Nội Dung AI")

        # --- TAB 1: CÀI ĐẶT CHUNG & TỰ ĐỘNG ---
        tab_basic.grid_columnconfigure((0, 1), weight=1)

        self.match_existing_var = ctk.BooleanVar(value=self.config.get("match_existing_folders", True))
        self.match_check = ctk.CTkCheckBox(
            tab_basic,
            text="Tự khớp thư mục sẵn có trong thư mục mẹ (Ảnh, Docs, Video...)",
            variable=self.match_existing_var,
            command=self.on_setting_changed,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            checkmark_color="#FFFFFF",
            fg_color="#0A84FF"
        )
        self.match_check.grid(row=0, column=0, padx=14, pady=4, sticky="w")

        self.accent_name_var = ctk.BooleanVar(value=self.config.get("use_accent_names", True))
        self.accent_check = ctk.CTkCheckBox(
            tab_basic,
            text="Tên thư mục có dấu tiếng Việt ('Hình Ảnh' thay vì 'Hinh_Anh')",
            variable=self.accent_name_var,
            command=self.on_setting_changed,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            checkmark_color="#FFFFFF",
            fg_color="#0A84FF"
        )
        self.accent_check.grid(row=1, column=0, padx=14, pady=4, sticky="w")

        self.recursive_var = ctk.BooleanVar(value=self.config.get("recursive", False))
        self.recursive_check = ctk.CTkCheckBox(
            tab_basic,
            text="Quét đệ quy (quét cả các thư mục con bên trong)",
            variable=self.recursive_var,
            command=self.on_setting_changed,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            checkmark_color="#FFFFFF",
            fg_color="#0A84FF"
        )
        self.recursive_check.grid(row=2, column=0, padx=14, pady=4, sticky="w")

        self.auto_switch_var = ctk.BooleanVar(value=self.config.get("auto_mode", False))
        self.auto_switch = ctk.CTkSwitch(
            tab_basic,
            text="Tự động theo dõi thời gian thực (Watchdog)",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            variable=self.auto_switch_var,
            command=self.on_toggle_auto_switch,
            progress_color="#30D158"
        )
        self.auto_switch.grid(row=0, column=1, padx=14, pady=4, sticky="w")

        self.autostart_var = ctk.BooleanVar(value=check_autostart())
        self.autostart_check = ctk.CTkCheckBox(
            tab_basic,
            text="Khởi động cùng hệ điều hành Windows",
            variable=self.autostart_var,
            command=self.on_autostart_toggle,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            checkmark_color="#FFFFFF",
            fg_color="#0A84FF"
        )
        self.autostart_check.grid(row=1, column=1, padx=14, pady=4, sticky="w")

        self.tray_close_var = ctk.BooleanVar(value=self.config.get("minimize_to_tray_on_close", True))
        self.tray_close_check = ctk.CTkCheckBox(
            tab_basic,
            text="Thu nhỏ vào khay hệ thống (System Tray) khi đóng",
            variable=self.tray_close_var,
            command=self.save_current_settings,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            checkmark_color="#FFFFFF",
            fg_color="#0A84FF"
        )
        self.tray_close_check.grid(row=2, column=1, padx=14, pady=4, sticky="w")

        # --- TAB 2: PHÂN LOẠI ẢNH THEO THIẾT BỊ & EXIF ---
        tab_photo.grid_columnconfigure(0, weight=1)

        photo_top_bar = ctk.CTkFrame(tab_photo, fg_color="transparent")
        photo_top_bar.grid(row=0, column=0, padx=10, pady=(2, 4), sticky="ew")
        photo_top_bar.grid_columnconfigure(0, weight=1)

        has_photo_meta = self.config.get("enable_photo_meta", None)
        if has_photo_meta is None:
            has_photo_meta = (
                self.config.get("enable_device_categorize", False) or
                self.config.get("enable_lighting_categorize", False) or
                self.config.get("enable_focal_categorize", False)
            )
        self.photo_master_var = ctk.BooleanVar(value=has_photo_meta)
        self.photo_master_switch = ctk.CTkSwitch(
            photo_top_bar,
            text="Kích hoạt phân loại Ảnh & EXIF (Thiết Bị, Ánh Sáng, Tiêu Cự)",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            variable=self.photo_master_var,
            command=self.on_photo_master_switch_toggle,
            progress_color="#0A84FF"
        )
        self.photo_master_switch.grid(row=0, column=0, sticky="w")

        self.device_desc_lbl = ctk.CTkLabel(
            photo_top_bar,
            text="(Phân loại theo model thiết bị chụp, điều kiện ánh sáng, tiêu cự ống kính)",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#8E8E93"
        )
        self.device_desc_lbl.grid(row=0, column=1, sticky="e")

        self.photo_sub_frame = ctk.CTkFrame(
            tab_photo,
            corner_radius=8,
            fg_color=("#F2F2F7", "#19191C"),
            border_width=1,
            border_color=("#E5E5EA", "#2C2C32")
        )
        self.photo_sub_frame.grid(row=1, column=0, padx=10, pady=2, sticky="ew")

        self.device_cat_var = ctk.BooleanVar(value=self.config.get("enable_device_categorize", True))
        self.device_check = ctk.CTkCheckBox(
            self.photo_sub_frame,
            text="Theo Thiết Bị (iPhone, Redmi, Galaxy...)",
            variable=self.device_cat_var,
            command=self.on_setting_changed,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            checkmark_color="#FFFFFF",
            fg_color="#0A84FF"
        )
        self.device_check.pack(side="left", padx=(12, 16), pady=6)

        self.lighting_cat_var = ctk.BooleanVar(value=self.config.get("enable_lighting_categorize", False))
        self.lighting_check = ctk.CTkCheckBox(
            self.photo_sub_frame,
            text="Theo Ánh Sáng (Đủ Sáng / Thiếu Sáng)",
            variable=self.lighting_cat_var,
            command=self.on_setting_changed,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            checkmark_color="#FFFFFF",
            fg_color="#0A84FF"
        )
        self.lighting_check.pack(side="left", padx=(0, 16), pady=6)

        self.focal_cat_var = ctk.BooleanVar(value=self.config.get("enable_focal_categorize", False))
        self.focal_check = ctk.CTkCheckBox(
            self.photo_sub_frame,
            text="Theo Tiêu Cự (24mm, 56mm, Tele...)",
            variable=self.focal_cat_var,
            command=self.on_setting_changed,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            checkmark_color="#FFFFFF",
            fg_color="#0A84FF"
        )
        self.focal_check.pack(side="left", padx=(0, 12), pady=6)

        photo_hint = ctk.CTkLabel(
            tab_photo,
            text="Nhận diện ngữ cảnh thông minh: Khi đang ở trong thư mục máy (hoặc ánh sáng), tool tự nhận diện và chỉ tạo thư mục tiêu cự tại chỗ mà không lặp lại tên thiết bị.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#8E8E93"
        )
        photo_hint.grid(row=2, column=0, padx=10, pady=(4, 0), sticky="w")

        # --- TAB 3: PHÂN TÍCH NỘI DUNG AI ---
        tab_ai.grid_columnconfigure(0, weight=1)

        ai_top_bar = ctk.CTkFrame(tab_ai, fg_color="transparent")
        ai_top_bar.grid(row=0, column=0, padx=10, pady=(2, 4), sticky="ew")
        ai_top_bar.grid_columnconfigure(0, weight=1)

        self.enable_ai_var = ctk.BooleanVar(value=self.config.get("enable_ai", False))
        self.ai_switch = ctk.CTkSwitch(
            ai_top_bar,
            text="Kích hoạt AI nhận diện nội dung (Người, Xe cộ, Động vật, Phong cảnh, Đồ ăn...)",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            variable=self.enable_ai_var,
            command=self.on_ai_switch_toggle,
            progress_color="#BF5AF2"
        )
        self.ai_switch.grid(row=0, column=0, sticky="w")

        self.ai_video_var = ctk.BooleanVar(value=self.config.get("ai_categorize_video", True))
        self.ai_video_check = ctk.CTkCheckBox(
            ai_top_bar,
            text="Phân tích cả Video",
            variable=self.ai_video_var,
            command=self.on_setting_changed,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            checkmark_color="#FFFFFF",
            fg_color="#BF5AF2"
        )
        self.ai_video_check.grid(row=0, column=1, sticky="e")

        self.ai_details_frame = ctk.CTkFrame(tab_ai, fg_color="transparent")
        self.ai_details_frame.grid(row=1, column=0, padx=10, pady=2, sticky="ew")
        self.ai_details_frame.grid_columnconfigure(1, weight=1)

        engine_box = ctk.CTkFrame(self.ai_details_frame, fg_color="transparent")
        engine_box.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 4))

        engine_lbl = ctk.CTkLabel(
            engine_box,
            text="Mô hình AI:",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
        )
        engine_lbl.pack(side="left", padx=(0, 10))

        self.ai_engine_var = ctk.StringVar(value=self.config.get("ai_engine", "offline"))
        self.engine_segmented = ctk.CTkSegmentedButton(
            engine_box,
            values=["AI Offline (Nội bộ máy - Tốc độ cao, Không mạng)", "Cloud AI (Google Gemini - Đa mô hình tự luân chuyển)"],
            command=self.on_engine_selected,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            selected_color="#BF5AF2",
            selected_hover_color="#AF52DE"
        )
        if self.ai_engine_var.get() == "cloud":
            self.engine_segmented.set("Cloud AI (Google Gemini - Đa mô hình tự luân chuyển)")
        else:
            self.engine_segmented.set("AI Offline (Nội bộ máy - Tốc độ cao, Không mạng)")
        self.engine_segmented.pack(side="left")

        # Ô nhập API Key của Cloud AI
        self.api_key_box = ctk.CTkFrame(self.ai_details_frame, fg_color="transparent")
        self.api_key_box.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(2, 0))
        self.api_key_box.grid_columnconfigure(1, weight=1)

        api_lbl = ctk.CTkLabel(
            self.api_key_box,
            text="Gemini API Key:",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
        )
        api_lbl.grid(row=0, column=0, padx=(0, 8), sticky="w")

        self.api_key_entry = ctk.CTkEntry(
            self.api_key_box,
            placeholder_text="Dán API Key (bắt đầu bằng AIzaSy... nhận miễn phí tại aistudio.google.com)...",
            height=28,
            show="•",
            corner_radius=6,
            font=ctk.CTkFont(family="Segoe UI", size=11)
        )
        self.api_key_entry.insert(0, self.config.get("gemini_api_key", ""))
        self.api_key_entry.grid(row=0, column=1, padx=(0, 8), sticky="ew")
        self.api_key_entry.bind("<FocusOut>", lambda e: self.save_current_settings())

        self.show_key_var = ctk.BooleanVar(value=False)
        self.show_key_btn = ctk.CTkButton(
            self.api_key_box,
            text="Hiện",
            width=55,
            height=28,
            corner_radius=6,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color=("#D1D1D6", "#3A3A42"),
            hover_color=("#C7C7CC", "#4A4A52"),
            text_color=("#1D1D1F", "#F5F5F7"),
            command=self.toggle_show_api_key
        )
        self.show_key_btn.grid(row=0, column=2, padx=(0, 6), sticky="e")

        self.test_api_btn = ctk.CTkButton(
            self.api_key_box,
            text="Kiểm Tra",
            width=85,
            height=28,
            corner_radius=6,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#0A84FF",
            hover_color="#0071E3",
            text_color="#FFFFFF",
            command=self.test_gemini_api_key
        )
        self.test_api_btn.grid(row=0, column=3, sticky="e")

        # ========================================================
        # 4. THANH TRẠNG THÁI & CHIPS HOẠT ĐỘNG (MACOS STATUS STRIP)
        # ========================================================
        status_strip = ctk.CTkFrame(self, fg_color="transparent")
        status_strip.grid(row=3, column=0, padx=26, pady=(2, 4), sticky="ew")
        status_strip.grid_columnconfigure(0, weight=1)

        self.summary_label = ctk.CTkLabel(
            status_strip,
            text="● Chọn thư mục nguồn để quét và xem trước danh sách file.",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#8E8E93",
            anchor="w"
        )
        self.summary_label.grid(row=0, column=0, sticky="w")

        chips_frame = ctk.CTkFrame(status_strip, fg_color="transparent")
        chips_frame.grid(row=0, column=1, sticky="e")

        self.auto_chip = ctk.CTkLabel(
            chips_frame,
            text="● Tự động: TẮT",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#8E8E93"
        )
        self.auto_chip.pack(side="left", padx=8)

        self.photo_chip = ctk.CTkLabel(
            chips_frame,
            text="● Ảnh & EXIF: TẮT",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#8E8E93"
        )
        self.photo_chip.pack(side="left", padx=8)

        self.ai_chip = ctk.CTkLabel(
            chips_frame,
            text="● AI: TẮT",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#8E8E93"
        )
        self.ai_chip.pack(side="left", padx=8)

        # ========================================================
        # 5. BẢNG XEM TRƯỚC (PREVIEW TABLE - MACOS FINDER STYLE)
        # ========================================================
        preview_container = ctk.CTkFrame(
            self,
            corner_radius=12,
            border_width=1,
            border_color=("#E5E5EA", "#2C2C32"),
            fg_color=("#FFFFFF", "#1E1E24")
        )
        preview_container.grid(row=4, column=0, padx=24, pady=4, sticky="nsew")
        preview_container.grid_columnconfigure(0, weight=1)
        preview_container.grid_rowconfigure(0, weight=1)

        tree_frame = ctk.CTkFrame(preview_container, corner_radius=8, fg_color="transparent")
        tree_frame.grid(row=0, column=0, padx=12, pady=12, sticky="nsew")
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)

        self.style = ttk.Style()
        self.style.theme_use("clam")

        # 1. Loại bỏ hoàn toàn viền trắng bao quanh bảng
        self.style.layout("Treeview", [('Treeview.treearea', {'sticky': 'nswe'})])

        # 2. Loại bỏ hoàn toàn viền trắng ở thanh tiêu đề cột
        self.style.layout("Treeview.Heading", [
            ('Treeheading.cell', {'sticky': 'nswe'}),
            ('Treeheading.padding', {'sticky': 'nswe', 'children': [
                ('Treeheading.image', {'side': 'right', 'sticky': ''}),
                ('Treeheading.text', {'sticky': 'we'})
            ]})
        ])

        columns = ("name", "ext", "size", "category", "target")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("name", text="Tên Tệp Tin", anchor="w")
        self.tree.heading("ext", text="Định Dạng", anchor="center")
        self.tree.heading("size", text="Kích Thước", anchor="e")
        self.tree.heading("category", text="Phân Loại Chi Tiết", anchor="w")
        self.tree.heading("target", text="Thư Mục Đích Đến", anchor="w")

        # Cấu hình độ rộng và co giãn tự động để vừa khít màn hình, không bị thừa thanh cuộn ngang
        self.tree.column("name", width=240, minwidth=140, anchor="w", stretch=True)
        self.tree.column("ext", width=80, minwidth=60, anchor="center", stretch=False)
        self.tree.column("size", width=85, minwidth=70, anchor="e", stretch=False)
        self.tree.column("category", width=220, minwidth=140, anchor="w", stretch=True)
        self.tree.column("target", width=320, minwidth=180, anchor="w", stretch=True)

        # Thanh cuộn dọc CustomTkinter phong cách Apple siêu mỏng, không viền, không nút tam giác Win32
        self.tree_scroll_y = ctk.CTkScrollbar(
            tree_frame,
            orientation="vertical",
            command=self.tree.yview,
            width=10,
            corner_radius=5,
            fg_color="transparent",
            button_color=("#D1D1D6", "#3A3A42"),
            button_hover_color=("#AEAEB2", "#4E4E58")
        )
        self.tree.configure(yscrollcommand=self.tree_scroll_y.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree_scroll_y.grid(row=0, column=1, sticky="ns", padx=(4, 0))

        # ========================================================
        # 6. TIẾN TRÌNH & NÚT THỰC HIỆN (APPLE FLOATING DOCK)
        # ========================================================
        bottom_card = ctk.CTkFrame(
            self,
            corner_radius=12,
            border_width=1,
            border_color=("#E5E5EA", "#2C2C32"),
            fg_color=("#FFFFFF", "#1E1E24")
        )
        bottom_card.grid(row=5, column=0, padx=24, pady=(2, 14), sticky="ew")
        bottom_card.grid_columnconfigure(1, weight=1)

        self.progress_bar = ctk.CTkProgressBar(bottom_card, height=6, corner_radius=3, progress_color="#0A84FF")
        self.progress_bar.set(0)
        self.progress_bar.grid(row=0, column=0, columnspan=3, padx=16, pady=(10, 4), sticky="ew")

        self.status_label = ctk.CTkLabel(
            bottom_card,
            text="● Sẵn sàng.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#8E8E93",
            anchor="w"
        )
        self.status_label.grid(row=1, column=0, columnspan=3, padx=16, pady=(0, 4), sticky="w")

        action_box = ctk.CTkFrame(bottom_card, fg_color="transparent")
        action_box.grid(row=2, column=0, columnspan=3, padx=16, pady=(0, 10), sticky="ew")
        action_box.grid_columnconfigure(1, weight=1)

        self.open_folder_btn = ctk.CTkButton(
            action_box,
            text="Mở Thư Mục Này",
            width=140,
            height=38,
            corner_radius=8,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color=("#E5E5EA", "#2A2A30"),
            hover_color=("#D1D1D6", "#383840"),
            text_color=("#1D1D1F", "#F5F5F7"),
            command=self.open_current_directory
        )
        self.open_folder_btn.grid(row=0, column=0, sticky="w")

        self.start_btn = ctk.CTkButton(
            action_box,
            text="Sắp Xếp File Ngay",
            height=38,
            width=200,
            corner_radius=8,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color="#30D158",
            hover_color="#28B84D",
            text_color="#FFFFFF",
            command=self.start_manual_organize
        )
        self.start_btn.grid(row=0, column=2, sticky="e")

        self.update_ai_visibility_ui()
        self.update_photo_meta_visibility_ui()

    # ========================================================
    # XỬ LÝ GIAO DIỆN & TRẠNG THÁI
    # ========================================================
    def update_status_chips(self):
        # Auto chip
        if self.auto_switch_var.get():
            self.auto_chip.configure(text="● Tự động: BẬT", text_color="#30D158")
        else:
            self.auto_chip.configure(text="● Tự động: TẮT", text_color="#8E8E93")

        # Photo chip
        if self.photo_master_var.get() and (self.device_cat_var.get() or self.lighting_cat_var.get() or self.focal_cat_var.get()):
            extra = []
            if self.device_cat_var.get():
                extra.append("Thiết bị")
            if self.lighting_cat_var.get():
                extra.append("Ánh sáng")
            if self.focal_cat_var.get():
                extra.append("Tiêu cự")
            sub_txt = f" ({', '.join(extra)})" if extra else ""
            self.photo_chip.configure(text=f"● Ảnh & EXIF: BẬT{sub_txt}", text_color="#0A84FF")
        else:
            self.photo_chip.configure(text="● Ảnh & EXIF: TẮT", text_color="#8E8E93")

        # AI chip
        if self.enable_ai_var.get():
            eng = "Cloud" if self.ai_engine_var.get() == "cloud" else "Offline"
            self.ai_chip.configure(text=f"● AI: BẬT ({eng})", text_color="#BF5AF2")
        else:
            self.ai_chip.configure(text="● AI: TẮT", text_color="#8E8E93")

    def update_photo_meta_visibility_ui(self):
        is_on = self.photo_master_var.get()
        state = "normal" if is_on else "disabled"
        self.device_check.configure(state=state)
        self.lighting_check.configure(state=state)
        self.focal_check.configure(state=state)
        if is_on:
            self.device_desc_lbl.configure(text="✨ Đang bật phân loại ảnh nâng cao (EXIF & Thiết bị)")
        else:
            self.device_desc_lbl.configure(text="(Phân loại theo model thiết bị chụp, điều kiện ánh sáng, tiêu cự ống kính)")
        self.update_status_chips()

    def on_photo_master_switch_toggle(self):
        self.update_photo_meta_visibility_ui()
        self.save_current_settings()
        self.trigger_scan_async()
        if self.auto_switch_var.get():
            self.start_auto_watcher()

    def update_ai_visibility_ui(self):
        ai_enabled = self.enable_ai_var.get()
        is_cloud = self.ai_engine_var.get() == "cloud"

        if ai_enabled:
            self.engine_segmented.configure(state="normal")
            self.ai_video_check.configure(state="normal")
            if is_cloud:
                self.api_key_box.grid()
                self.api_key_entry.configure(state="normal")
                self.test_api_btn.configure(state="normal")
                self.show_key_btn.configure(state="normal")
            else:
                self.api_key_box.grid_remove()
        else:
            self.engine_segmented.configure(state="disabled")
            self.ai_video_check.configure(state="disabled")
            self.api_key_box.grid_remove()
        self.update_status_chips()

    def on_ai_switch_toggle(self):
        self.update_ai_visibility_ui()
        self.save_current_settings()
        self.trigger_scan_async()
        if self.auto_switch_var.get():
            self.start_auto_watcher()

    def on_engine_selected(self, value: str):
        if "Cloud" in value:
            self.ai_engine_var.set("cloud")
        else:
            self.ai_engine_var.set("offline")
        self.update_ai_visibility_ui()
        self.save_current_settings()
        self.trigger_scan_async()
        if self.auto_switch_var.get():
            self.start_auto_watcher()

    def toggle_show_api_key(self):
        if self.show_key_var.get():
            self.api_key_entry.configure(show="•")
            self.show_key_btn.configure(text="👁️ Hiện")
            self.show_key_var.set(False)
        else:
            self.api_key_entry.configure(show="")
            self.show_key_btn.configure(text="🔒 Ẩn")
            self.show_key_var.set(True)

    def test_gemini_api_key(self):
        key = self.api_key_entry.get().strip()
        if not key:
            messagebox.showwarning("Thiếu API Key", "Vui lòng nhập Google Gemini API Key trước khi kiểm tra!")
            return

        self.test_api_btn.configure(text="⏳ Đang test...", state="disabled")

        def _test():
            candidate_models = GEMINI_MODELS_PRIORITY
            success_model = None
            last_error = ""
            quota_hit_models = []

            for model in candidate_models:
                try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
                    payload = {
                        "contents": [{"parts": [{"text": "Hello, respond with OK"}]}],
                        "generationConfig": {"maxOutputTokens": 5}
                    }
                    req = urllib.request.Request(
                        url,
                        data=json.dumps(payload).encode("utf-8"),
                        headers={"Content-Type": "application/json"}
                    )
                    with urllib.request.urlopen(req, timeout=6) as resp:
                        if resp.status == 200:
                            success_model = model
                            break
                except urllib.error.HTTPError as e:
                    last_error = e.read().decode("utf-8", errors="ignore")
                    if e.code == 429:
                        quota_hit_models.append(model)
                        continue
                    elif e.code in [404, 503]:
                        continue
                    else:
                        break
                except Exception as e:
                    last_error = str(e)
                    break

            if success_model:
                quota_note = ""
                if quota_hit_models:
                    quota_note = f"\n(Lưu ý: Các model {', '.join(quota_hit_models)} đang tạm chạm hạn mức RPM và đã được tự động bỏ qua để chuyển sang model này.)"

                self.after(0, lambda: messagebox.showinfo(
                    "Thành công!",
                    f"🎉 Kết nối Google Gemini API thành công!\n\n"
                    f"🔹 Đang kết nối mô hình: {success_model}\n"
                    f"✨ Cơ chế Tự Động Luân Chuyển Model (Auto-Failover): ĐÃ BẬT!\n"
                    f"Ứng dụng sẽ tự động chuyển đổi thông minh giữa hơn 12 mô hình (Flash Lite, Flash 3.x, Flash 2.x...) khi có model chạm hạn mức RPM.{quota_note}"
                ))
            else:
                hint = ""
                if not key.startswith("AIzaSy"):
                    hint = "\n\n💡 LƯU Ý: Khóa API chuẩn của Google AI Studio thường bắt đầu bằng chữ 'AIzaSy...'. Khóa bạn đang nhập có vẻ chưa đúng định dạng. Bạn có thể lấy khóa miễn phí tại: https://aistudio.google.com/app/apikey"

                self.after(0, lambda: messagebox.showerror(
                    "Kiểm tra thất bại",
                    f"Không thể kết nối đến Gemini với khóa này.\n\nChi tiết lỗi từ Google:\n{last_error[:300]}{hint}"
                ))

            self.after(0, lambda: self.test_api_btn.configure(text="🔍 Kiểm Tra Kết Nối", state="normal"))

        threading.Thread(target=_test, daemon=True).start()

    # ========================================================
    # XỬ LÝ THEO DÕI TỰ ĐỘNG & SYSTEM TRAY
    # ========================================================
    def on_toggle_auto_switch(self):
        is_on = self.auto_switch_var.get()
        if is_on:
            dir_path = self.path_entry.get().strip()
            if not dir_path or not os.path.isdir(dir_path):
                messagebox.showwarning("Chưa chọn thư mục", "Vui lòng chọn thư mục mẹ hợp lệ trước khi bật chế độ tự động!")
                self.auto_switch_var.set(False)
                return
            self.start_auto_watcher()
        else:
            self.stop_auto_watcher()
        self.save_current_settings()

    def toggle_auto_mode_from_tray(self):
        new_val = not self.auto_switch_var.get()
        self.auto_switch_var.set(new_val)
        self.on_toggle_auto_switch()

    def start_auto_watcher(self):
        dir_path = self.path_entry.get().strip()
        if not dir_path or not os.path.isdir(dir_path):
            return

        self.selected_directory = dir_path

        if self.watcher:
            self.watcher.stop()

        photo_on = self.photo_master_var.get()
        self.watcher = DirectoryWatcher(
            directory=self.selected_directory,
            match_existing=self.match_existing_var.get(),
            use_accent=self.accent_name_var.get(),
            enable_ai=self.enable_ai_var.get(),
            ai_engine=self.ai_engine_var.get(),
            gemini_api_key=self.api_key_entry.get().strip(),
            ai_categorize_video=self.ai_video_var.get(),
            enable_device_categorize=self.device_cat_var.get() if photo_on else False,
            enable_lighting_categorize=self.lighting_cat_var.get() if photo_on else False,
            enable_focal_categorize=self.focal_cat_var.get() if photo_on else False,
            on_organized_cb=self._on_file_auto_organized
        )
        success = self.watcher.start()

        if success:
            short_dir = os.path.basename(self.selected_directory) or self.selected_directory
            ai_tag = " [AI ON]" if self.enable_ai_var.get() else ""
            self.auto_status_badge.configure(
                text=f"🟢 ĐANG THEO DÕI: [{short_dir}]{ai_tag} (Tự sắp xếp khi có file mới)",
                text_color="#28a745"
            )
            self.tray_manager.update_state(is_active=True)
            self.tray_manager.notify(
                "Đã bật tự động sắp xếp",
                f"Đang theo dõi thư mục: {self.selected_directory}\nBất kỳ file nào copy vào sẽ được tự động gom vào thư mục con."
            )
        else:
            self.auto_status_badge.configure(text="⚠️ Không thể theo dõi thư mục", text_color="red")
            self.auto_switch_var.set(False)

    def stop_auto_watcher(self):
        if self.watcher:
            self.watcher.stop()
            self.watcher = None
        self.auto_status_badge.configure(text="⚪ Chế độ tự động đang TẮT", text_color="gray")
        self.tray_manager.update_state(is_active=False)

    def _on_file_auto_organized(self, filename: str, target_folder: str):
        self.after(0, lambda: self._handle_auto_organized_ui(filename, target_folder))

    def _handle_auto_organized_ui(self, filename: str, target_folder: str):
        msg = f"Tự động chuyển: {filename} ➔ {target_folder}/"
        self.status_label.configure(text=f"⚡ {msg}")
        self.tray_manager.notify("Tự động sắp xếp thành công", f"File '{filename}' đã được chuyển vào '{target_folder}'.")
        self.trigger_scan_async()

    def on_autostart_toggle(self):
        enable = self.autostart_var.get()
        set_autostart(enable)
        self.save_current_settings()

    def save_current_settings(self):
        self.config["watched_directory"] = self.path_entry.get().strip()
        self.config["auto_mode"] = self.auto_switch_var.get()
        self.config["autostart_with_windows"] = self.autostart_var.get()
        self.config["minimize_to_tray_on_close"] = self.tray_close_var.get()
        self.config["match_existing_folders"] = self.match_existing_var.get()
        self.config["use_accent_names"] = self.accent_name_var.get()
        self.config["enable_ai"] = self.enable_ai_var.get()
        self.config["ai_engine"] = self.ai_engine_var.get()
        self.config["gemini_api_key"] = self.api_key_entry.get().strip()
        self.config["ai_categorize_video"] = self.ai_video_var.get()
        self.config["enable_photo_meta"] = self.photo_master_var.get()
        self.config["enable_device_categorize"] = self.device_cat_var.get()
        self.config["enable_lighting_categorize"] = self.lighting_cat_var.get()
        self.config["enable_focal_categorize"] = self.focal_cat_var.get()
        save_config(self.config)

    def on_setting_changed(self):
        self.save_current_settings()
        self.trigger_scan_async()
        if self.auto_switch_var.get():
            self.start_auto_watcher()

    def on_window_close(self):
        self.save_current_settings()
        if self.tray_close_var.get() or self.auto_switch_var.get():
            self.withdraw()
            self.tray_manager.notify(
                "Ứng dụng đang chạy ngầm",
                "Phần mềm đang tiếp tục theo dõi thư mục ở khay hệ thống (System Tray). Bấm đúp vào biểu tượng để mở lại."
            )
        else:
            self.quit_completely()

    def show_window_from_tray(self):
        self.after(0, self._restore_window)

    def _restore_window(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def quit_completely(self):
        self.save_current_settings()
        if self.watcher:
            self.watcher.stop()
        self.tray_manager.stop()
        self.destroy()
        sys.exit(0)

    # ========================================================
    # QUÉT & XEM TRƯỚC (ASYNC PREVIEW SCAN)
    # ========================================================
    def trigger_scan_async(self):
        if self.is_scanning:
            return
        dir_path = self.path_entry.get().strip()
        if not dir_path or not os.path.isdir(dir_path):
            self.summary_label.configure(text="⚠️ Vui lòng chọn đường dẫn thư mục hợp lệ.")
            self.tree.delete(*self.tree.get_children())
            self.current_plan = []
            return

        self.is_scanning = True
        self.rescan_btn.configure(state="disabled", text="⏳ Đang quét...")
        self.status_label.configure(text="Đang quét thư mục...")

        threading.Thread(target=self._run_scan_thread, args=(dir_path,), daemon=True).start()

    def _run_scan_thread(self, dir_path: str):
        photo_on = self.photo_master_var.get()
        organizer = FileOrganizer(
            parent_dir=dir_path,
            match_existing_folders=self.match_existing_var.get(),
            use_accent_folder=self.accent_name_var.get(),
            recursive=self.recursive_var.get(),
            enable_ai=self.enable_ai_var.get(),
            ai_engine=self.ai_engine_var.get(),
            gemini_api_key=self.api_key_entry.get().strip(),
            ai_categorize_video=self.ai_video_var.get(),
            enable_device_categorize=self.device_cat_var.get() if photo_on else False,
            enable_lighting_categorize=self.lighting_cat_var.get() if photo_on else False,
            enable_focal_categorize=self.focal_cat_var.get() if photo_on else False
        )

        def status_cb(msg):
            self.after(0, lambda: self.status_label.configure(text=msg))

        plan = organizer.scan_files(status_callback=status_cb)
        self.after(0, lambda: self._update_scan_results(plan, dir_path))

    def _update_scan_results(self, plan: list, dir_path: str):
        self.is_scanning = False
        self.rescan_btn.configure(state="normal", text="Quét Lại")
        self.current_plan = plan
        self.selected_directory = dir_path

        self.tree.delete(*self.tree.get_children())

        cat_counts = {}
        for i, item in enumerate(self.current_plan):
            cat = item["target_folder_name"]
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
            tag = "even" if i % 2 == 0 else "odd"
            self.tree.insert("", "end", values=(
                item["file_name"],
                item["ext"],
                item["formatted_size"],
                item.get("category_label", "Chuẩn"),
                item["target_folder_name"]
            ), tags=(tag,))

        total_files = len(self.current_plan)
        if total_files == 0:
            self.summary_label.configure(
                text="● Thư mục đã ngăn nắp và sạch sẽ (Hiện không có tệp tin lẻ nào cần sắp xếp).",
                text_color="#30D158"
            )
            self.status_label.configure(text="● Sẵn sàng.")
            self.start_btn.configure(state="disabled")
        else:
            cat_summary = ", ".join([f"{k}: {v}" for k, v in cat_counts.items()])
            active_modes = []
            if self.photo_master_var.get():
                if self.device_cat_var.get():
                    active_modes.append("Thiết bị")
                if self.lighting_cat_var.get():
                    active_modes.append("Ánh sáng")
                if self.focal_cat_var.get():
                    active_modes.append("Tiêu cự")
            if self.enable_ai_var.get():
                active_modes.append("AI")

            mode_text = f" [Bộ lọc: {', '.join(active_modes)}]" if active_modes else ""
            self.summary_label.configure(
                text=f"● Có {total_files} tệp tin cần sắp xếp{mode_text}: {cat_summary}",
                text_color="#F5F5F7" if ctk.get_appearance_mode().lower() == "dark" else "#1D1D1F"
            )
            self.status_label.configure(text=f"● Sẵn sàng sắp xếp {total_files} tệp tin.")
            self.start_btn.configure(state="normal")

        self.progress_bar.set(0)

    # ========================================================
    # THAO TÁC SẮP XẾP FILE
    # ========================================================
    def start_manual_organize(self):
        if not self.current_plan:
            messagebox.showwarning("Thông báo", "Không có file nào để sắp xếp!")
            return

        if self.is_processing or self.is_scanning:
            return

        confirm = messagebox.askyesno(
            "Xác nhận sắp xếp",
            f"Bạn có chắc muốn chuyển toàn bộ {len(self.current_plan)} file vào các thư mục con tương ứng không?"
        )
        if not confirm:
            return

        self.is_processing = True
        self.start_btn.configure(state="disabled", text="Đang di chuyển...")
        self.rescan_btn.configure(state="disabled")

        threading.Thread(target=self._run_manual_thread, daemon=True).start()

    def _run_manual_thread(self):
        photo_on = self.photo_master_var.get()
        organizer = FileOrganizer(
            parent_dir=self.selected_directory,
            match_existing_folders=self.match_existing_var.get(),
            use_accent_folder=self.accent_name_var.get(),
            recursive=self.recursive_var.get(),
            enable_ai=self.enable_ai_var.get(),
            ai_engine=self.ai_engine_var.get(),
            gemini_api_key=self.api_key_entry.get().strip(),
            ai_categorize_video=self.ai_video_var.get(),
            enable_device_categorize=self.device_cat_var.get() if photo_on else False,
            enable_lighting_categorize=self.lighting_cat_var.get() if photo_on else False,
            enable_focal_categorize=self.focal_cat_var.get() if photo_on else False
        )

        def progress_cb(current, total, msg):
            progress_ratio = current / total
            self.after(0, lambda: self._update_progress(progress_ratio, current, total, msg))

        success_count, error_count, errors = organizer.execute_organize(
            self.current_plan,
            progress_callback=progress_cb
        )

        self.after(0, lambda: self._finish_manual_organize(success_count, error_count, errors))

    def _update_progress(self, ratio, current, total, msg):
        self.progress_bar.set(ratio)
        self.status_label.configure(text=f"[{current}/{total}] {msg}")

    def _finish_manual_organize(self, success_count, error_count, errors):
        self.is_processing = False
        self.start_btn.configure(state="normal", text="Sắp Xếp File Ngay")
        self.rescan_btn.configure(state="normal")
        self.progress_bar.set(1.0)

        self.trigger_scan_async()

        if error_count == 0:
            messagebox.showinfo(
                "Hoàn tất thành công!",
                f"🎉 Đã sắp xếp thành công toàn bộ {success_count} file vào đúng các thư mục con!"
            )
        else:
            err_details = "\n".join(errors[:5])
            if len(errors) > 5:
                err_details += f"\n... và còn {len(errors) - 5} lỗi khác."
            messagebox.showwarning(
                "Hoàn tất có cảnh báo",
                f"Đã chuyển thành công: {success_count} file.\n"
                f"Số file lỗi: {error_count} file.\n\nChi tiết:\n{err_details}"
            )

    def browse_directory(self):
        selected = filedialog.askdirectory(title="Chọn Thư Mục Mẹ Cần Sắp Xếp File")
        if selected:
            self.selected_directory = selected
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, selected)
            self.save_current_settings()
            self.trigger_scan_async()
            if self.auto_switch_var.get():
                self.start_auto_watcher()

    def open_current_directory(self):
        dir_path = self.path_entry.get().strip()
        if dir_path and os.path.isdir(dir_path):
            os.startfile(dir_path)
        else:
            messagebox.showwarning("Thông báo", "Vui lòng chọn thư mục hợp lệ trước!")

    def update_tree_theme(self, mode: str):
        if mode.lower() == "dark":
            bg = "#1E1E24"
            row_alt = "#25252C"
            fg = "#F5F5F7"
            header_bg = "#18181B"
            header_fg = "#8E8E93"
            selected_bg = "#0A84FF"
            scrollbar_thumb = "#3A3A42"
            scrollbar_active = "#4E4E58"
        else:
            bg = "#FFFFFF"
            row_alt = "#F7F7FA"
            fg = "#1D1D1F"
            header_bg = "#F2F2F7"
            header_fg = "#6E6E73"
            selected_bg = "#0071E3"
            scrollbar_thumb = "#D1D1D6"
            scrollbar_active = "#AEAEB2"

        self.style.theme_use("clam")

        # 1. Loại bỏ hoàn toàn viền trắng bao quanh bảng
        self.style.layout("Treeview", [('Treeview.treearea', {'sticky': 'nswe'})])

        # 2. Loại bỏ hoàn toàn viền trắng ở thanh tiêu đề cột
        self.style.layout("Treeview.Heading", [
            ('Treeheading.cell', {'sticky': 'nswe'}),
            ('Treeheading.padding', {'sticky': 'nswe', 'children': [
                ('Treeheading.image', {'side': 'right', 'sticky': ''}),
                ('Treeheading.text', {'sticky': 'we'})
            ]})
        ])

        # Cấu hình Bảng Treeview phẳng phong cách macOS Finder
        self.style.configure(
            "Treeview",
            background=bg,
            foreground=fg,
            fieldbackground=bg,
            rowheight=32,
            font=("Segoe UI", 10),
            borderwidth=0,
            relief="flat"
        )
        self.style.configure(
            "Treeview.Heading",
            font=("Segoe UI", 10, "bold"),
            background=header_bg,
            foreground=header_fg,
            relief="flat",
            borderwidth=0
        )
        self.style.map(
            "Treeview.Heading",
            background=[("active", header_bg)]
        )
        self.style.map(
            "Treeview",
            background=[("selected", selected_bg)],
            foreground=[("selected", "#FFFFFF")]
        )

        # Cập nhật màu sắc thanh cuộn CustomTkinter
        if hasattr(self, "tree_scroll_y") and self.tree_scroll_y:
            self.tree_scroll_y.configure(
                button_color=scrollbar_thumb,
                button_hover_color=scrollbar_active
            )

        # Zebra striping
        self.tree.tag_configure("even", background=bg)
        self.tree.tag_configure("odd", background=row_alt)

    def toggle_theme(self):
        if self.theme_switch.get() == 1:
            ctk.set_appearance_mode("Dark")
            self.update_tree_theme("Dark")
        else:
            ctk.set_appearance_mode("Light")
            self.update_tree_theme("Light")


if __name__ == "__main__":
    start_background = "--background" in sys.argv or "-b" in sys.argv
    app = FileOrganizerApp(start_in_background=start_background)
    app.mainloop()
