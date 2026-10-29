import os
import re
import shutil
import unicodedata
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Callable

from ai_classifier import AIClassifier, AI_CATEGORIES
from photo_metadata import extract_photo_metadata

DEFAULT_CATEGORIES = {
    "Tai_Lieu": {
        "display_name": "Tài Liệu",
        "folder_name_no_accent": "Tai_Lieu",
        "extensions": {
            ".pdf", ".docx", ".doc", ".txt", ".xlsx", ".xls", ".pptx", ".ppt",
            ".csv", ".epub", ".odt", ".rtf", ".wps", ".tsv", ".md"
        },
        "keywords": ["tai lieu", "tài liệu", "document", "documents", "docs", "doc", "van ban", "văn bản", "word", "excel"]
    },
    "Hinh_Anh": {
        "display_name": "Hình Ảnh",
        "folder_name_no_accent": "Hinh_Anh",
        "extensions": {
            ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico",
            ".tiff", ".tif", ".heic", ".heif", ".raw", ".dng", ".cr2", ".nef", ".arw", ".psd", ".ai", ".eps", ".cdr"
        },
        "keywords": ["hinh anh", "hình ảnh", "anh", "ảnh", "images", "image", "pictures", "picture", "photos", "photo", "pic", "pics"]
    },
    "Video": {
        "display_name": "Video",
        "folder_name_no_accent": "Video",
        "extensions": {
            ".mp4", ".mkv", ".mov", ".avi", ".wmv", ".flv", ".webm", ".m4v",
            ".3gp", ".ts", ".mpeg", ".mpg"
        },
        "keywords": ["video", "videos", "phim", "clip", "clips", "movies", "movie"]
    },
    "Am_Thanh": {
        "display_name": "Âm Thanh",
        "folder_name_no_accent": "Am_Thanh",
        "extensions": {
            ".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma", ".opus",
            ".mid", ".midi"
        },
        "keywords": ["am thanh", "âm thanh", "nhac", "nhạc", "music", "audio", "sound", "sounds", "songs", "bai hat"]
    },
    "Nen_Va_CaiDat": {
        "display_name": "Nén & Cài Đặt",
        "folder_name_no_accent": "Nen_CaiDat",
        "extensions": {
            ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".iso",
            ".exe", ".msi", ".dmg", ".apk"
        },
        "keywords": ["nen", "nén", "zip", "rar", "cai dat", "cài đặt", "install", "installer", "setup", "software", "phan mem", "phần mềm", "archives"]
    },
    "Code_DuLieu": {
        "display_name": "Code & Dữ Liệu",
        "folder_name_no_accent": "Code_DuLieu",
        "extensions": {
            ".py", ".js", ".ts", ".html", ".css", ".json", ".xml", ".sql",
            ".java", ".cpp", ".c", ".h", ".cs", ".php", ".sh", ".bat", ".yaml", ".yml"
        },
        "keywords": ["code", "source", "script", "scripts", "lap trinh", "lập trình", "data", "du lieu", "dữ liệu"]
    },
    "Khac": {
        "display_name": "Khác",
        "folder_name_no_accent": "Khac",
        "extensions": set(),
        "keywords": ["khac", "khác", "other", "others", "misc"]
    }
}

# Từ khóa phụ ánh xạ cho thư mục AI
AI_SUBFOLDER_KEYWORDS = {
    "Con_Nguoi": ["nguoi", "người", "chan dung", "chân dung", "selfie", "people", "person", "portrait", "face", "mat"],
    "Dong_Vat": ["dong vat", "động vật", "thu cung", "thú cưng", "pet", "pets", "animal", "animals", "cho", "chó", "meo", "mèo", "cat", "dog"],
    "Phong_Canh": ["phong canh", "phong cảnh", "canh", "cảnh", "thien nhien", "thiên nhiên", "landscape", "scenery", "nature", "bien", "biển", "nui", "núi"],
    "Xe_Co": ["xe co", "xe cộ", "xe", "oto", "ô tô", "car", "cars", "vehicle", "vehicles", "xe may", "xe máy", "motorbike", "motorcycle", "xe dap", "xe đạp", "bike", "may bay", "máy bay", "airplane", "tau", "tàu", "boat", "ship", "truck", "xe tai", "xe tải"],
    "Do_An_Uong": ["do an", "đồ ăn", "mon an", "món ăn", "am thuc", "ẩm thực", "food", "drink", "drinks", "thuc uong"],
    "Tai_Lieu_Chup": ["tai lieu chup", "tài liệu chụp", "hoa don", "hóa đơn", "bill", "invoice", "receipt", "giay to", "giấy tờ"],
    "Screenshots": ["screenshot", "screenshots", "chup man hinh", "chụp màn hình", "capture", "meme", "memes"]
}


def normalize_text(text: str) -> str:
    """Loại bỏ dấu tiếng Việt và chuẩn hoá chuỗi để so sánh."""
    text = text.lower().strip()
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    text = text.replace('đ', 'd')
    for ch in "_-./\\+":
        text = text.replace(ch, " ")
    return " ".join(text.split())


def folder_matches_keywords(folder_name: str, keywords: List[str]) -> bool:
    norm_folder = normalize_text(folder_name)
    folder_tokens = set(norm_folder.split())

    for kw in keywords:
        norm_kw = normalize_text(kw)
        kw_tokens = set(norm_kw.split())

        if norm_folder == norm_kw:
            return True
        if norm_kw in norm_folder:
            return True
        if kw_tokens and kw_tokens.issubset(folder_tokens):
            return True
        if len(folder_tokens) == 1 and norm_folder in kw_tokens:
            return True

    return False


KNOWN_PHOTO_FOLDER_NAMES = {
    "hinh anh", "hinhanh", "anh", "photo", "photos", "image", "images",
    "picture", "pictures", "dcim", "camera", "hinh_anh", "album"
}

KNOWN_LIGHTING_NAMES = {
    "du sang", "du_sang", "thieu sang", "thieu_sang", "chua xac dinh", "chua_xac_dinh"
}

KNOWN_DEVICE_BRANDS = [
    "iphone", "ipad", "ipod", "apple", "samsung", "galaxy", "sony", "canon",
    "nikon", "fujifilm", "fuji", "pixel", "google", "xiaomi", "redmi", "oppo",
    "vivo", "huawei", "honor", "realme", "oneplus", "asus", "panasonic",
    "lumix", "leica", "olympus", "gopro", "dji", "hasselblad", "thiet bi khac", "thiet_bi_khac"
]


def get_path_hierarchy(path: Path) -> List[Path]:
    """Trả về danh sách gồm chính thư mục đó và toàn bộ các thư mục tổ tiên (từ gần đến xa)."""
    try:
        p = path.resolve()
        return [p] + list(p.parents)
    except Exception:
        return [path]


def is_in_photo_context(parent_dir: Path) -> bool:
    """
    Kiểm tra xem thư mục hiện tại có đang nằm trong một cấu trúc cây thư mục ảnh hay không.
    (Ví dụ: nằm trong 'Hình Ảnh', hoặc nằm trong thư mục thiết bị 'iPhone...', hoặc thư mục 'Đủ Sáng', v.v.)
    """
    for folder in get_path_hierarchy(parent_dir):
        norm_f = normalize_text(folder.name)
        if not norm_f:
            continue
        if norm_f in KNOWN_PHOTO_FOLDER_NAMES:
            return True
        for p_name in KNOWN_PHOTO_FOLDER_NAMES:
            if p_name in norm_f:
                return True
        if norm_f in KNOWN_LIGHTING_NAMES:
            return True
        for brand in KNOWN_DEVICE_BRANDS:
            if brand in norm_f:
                return True
        if re.search(r'\d+\s*mm', norm_f) and any(kw in norm_f for kw in ["goc", "tele", "chuan", "sieu"]):
            return True
    return False


def is_device_in_path(device_name: str, parent_dir: Path) -> bool:
    """Kiểm tra xem tên thiết bị này đã xuất hiện trong thư mục hiện tại hoặc các thư mục cha hay chưa."""
    norm_dev = normalize_text(device_name)
    if not norm_dev:
        return False

    dev_tokens = set(norm_dev.split())
    noise = {'4g', '5g', 'lte', 'wifi', 'photo', 'photos', 'anh', 'video', 'camera', 'hinh', 'youtube', 'work'}
    brands = {
        'apple', 'xiaomi', 'samsung', 'google', 'sony', 'canon', 'nikon',
        'fujifilm', 'oppo', 'vivo', 'realme', 'huawei', 'honor', 'asus',
        'oneplus', 'panasonic', 'motorola'
    }
    dev_core = dev_tokens - noise
    dev_without_brand = dev_core - brands

    for folder in get_path_hierarchy(parent_dir):
        norm_f = normalize_text(folder.name)
        if not norm_f:
            continue
        if norm_f == norm_dev:
            return True
        if len(norm_dev) >= 4 and len(norm_f) >= 4:
            if norm_dev in norm_f or norm_f in norm_dev:
                return True

        f_tokens = set(norm_f.split())
        f_core = f_tokens - noise
        f_without_brand = f_core - brands

        # So khớp cốt lõi model (ví dụ 'redmi note 17' với 'redmi note 17 4g')
        if dev_without_brand and f_without_brand:
            if dev_without_brand == f_without_brand:
                return True
            if dev_without_brand.issubset(f_core) or f_without_brand.issubset(dev_core):
                return True

        # Giao nhau của các từ nhận diện chính (ví dụ 'redmi', 'note', '17'...)
        common = dev_core & f_core
        if len(common) >= 2:
            return True

        # Nếu thư mục chính là thương hiệu độc lập (ví dụ folder 'iPhone', 'Redmi', 'Galaxy', 'Pixel'...)
        standalone_subbrands = {'iphone', 'ipad', 'pixel', 'galaxy', 'redmi', 'poco', 'xperia', 'lumix'}
        for sb in standalone_subbrands:
            if sb in norm_dev and sb in norm_f:
                return True

    return False


def is_lighting_in_path(lighting_name: str, parent_dir: Path) -> bool:
    """Kiểm tra xem điều kiện ánh sáng này đã xuất hiện trong thư mục hiện tại hoặc các thư mục cha hay chưa."""
    norm_lighting = normalize_text(lighting_name)
    if not norm_lighting:
        return False

    for folder in get_path_hierarchy(parent_dir):
        norm_f = normalize_text(folder.name)
        if norm_f == norm_lighting:
            return True
        if "du sang" in norm_lighting and any(k in norm_f for k in ["du sang", "du_sang", "daylight"]):
            return True
        if "thieu sang" in norm_lighting and any(k in norm_f for k in ["thieu sang", "thieu_sang", "lowlight", "night"]):
            return True
        if "chua xac dinh" in norm_lighting and "chua xac dinh" in norm_f:
            return True
    return False


def is_focal_in_path(focal_name: str, parent_dir: Path) -> bool:
    """Kiểm tra xem dải tiêu cự này đã xuất hiện trong thư mục hiện tại hoặc các thư mục cha hay chưa."""
    norm_focal = normalize_text(focal_name)
    if not norm_focal:
        return False

    mm_match = re.search(r'(\d+)\s*mm', norm_focal)
    target_mm = mm_match.group(1) if mm_match else None

    for folder in get_path_hierarchy(parent_dir):
        norm_f = normalize_text(folder.name)
        if norm_f == norm_focal:
            return True
        if target_mm:
            f_mm_match = re.search(r'(\d+)\s*mm', norm_f)
            if f_mm_match and f_mm_match.group(1) == target_mm:
                return True
    return False


def is_ai_category_in_path(ai_cat_key: str, ai_label: str, parent_dir: Path) -> bool:
    """Kiểm tra xem danh mục AI này đã xuất hiện trong thư mục hiện tại hoặc các thư mục cha hay chưa."""
    keywords = list(AI_SUBFOLDER_KEYWORDS.get(ai_cat_key, []))
    keywords.append(ai_label)
    norm_label = normalize_text(ai_label)

    for folder in get_path_hierarchy(parent_dir):
        norm_f = normalize_text(folder.name)
        if norm_f == norm_label or folder_matches_keywords(folder.name, keywords):
            return True
    return False


def format_file_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


class FileOrganizer:
    def __init__(
        self,
        parent_dir: str,
        match_existing_folders: bool = True,
        use_accent_folder: bool = True,
        recursive: bool = False,
        enable_ai: bool = False,
        ai_engine: str = "offline",
        gemini_api_key: str = "",
        ai_categorize_video: bool = True,
        enable_device_categorize: bool = False,
        enable_lighting_categorize: bool = False,
        enable_focal_categorize: bool = False
    ):
        self.parent_dir = Path(parent_dir)
        self.match_existing_folders = match_existing_folders
        self.use_accent_folder = use_accent_folder
        self.recursive = recursive
        self.enable_ai = enable_ai
        self.ai_engine = ai_engine
        self.gemini_api_key = gemini_api_key
        self.ai_categorize_video = ai_categorize_video
        self.enable_device_categorize = enable_device_categorize
        self.enable_lighting_categorize = enable_lighting_categorize
        self.enable_focal_categorize = enable_focal_categorize

        # Khởi tạo AI Classifier chỉ khi bật AI
        self.ai_classifier: Optional[AIClassifier] = None
        if self.enable_ai:
            try:
                self.ai_classifier = AIClassifier()
            except Exception as e:
                print(f"[Organizer] Không thể nạp AI: {e}")

    def get_existing_subfolders(self) -> List[Path]:
        if not self.parent_dir.exists() or not self.parent_dir.is_dir():
            return []
        try:
            return [p for p in self.parent_dir.iterdir() if p.is_dir()]
        except Exception:
            return []

    def find_target_folder_name(self, file_path: Path, existing_subfolders: List[Path]) -> Tuple[str, str]:
        """
        Xác định thư mục con đích đến:
        - Nếu bật Phân loại Ảnh theo Thiết bị / Ánh sáng / Tiêu cự: Trích xuất EXIF và ánh sáng.
        - Nếu bật AI và là Ảnh / Video: Phân tích nội dung ảnh/video bằng AI.
        - Ngược lại: Phân loại theo đuôi file thông thường.
        """
        ext = file_path.suffix.lower()
        image_exts = {
            ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".heic", ".heif",
            ".tif", ".tiff", ".raw", ".dng", ".cr2", ".nef", ".arw"
        }
        video_exts = {".mp4", ".mkv", ".mov", ".avi", ".wmv", ".flv", ".webm", ".3gp"}

        is_image = ext in image_exts
        is_video = ext in video_exts and self.ai_categorize_video

        # =========================================================================
        # 1. PHÂN LOẠI ẢNH THEO THIẾT BỊ / ÁNH SÁNG / TIÊU CỰ NẾU BẬT
        # =========================================================================
        if is_image and (self.enable_device_categorize or self.enable_lighting_categorize or self.enable_focal_categorize):
            meta = extract_photo_metadata(file_path, use_accent=self.use_accent_folder)
            parent_img_name = "Hình Ảnh" if self.use_accent_folder else "Hinh_Anh"

            path_parts = []
            label_parts = []
            in_photo_ctx = is_in_photo_context(self.parent_dir)
            dev_already_in_path = is_device_in_path(meta["device"], self.parent_dir)
            light_already_in_path = is_lighting_in_path(meta["lighting"], self.parent_dir)
            focal_already_in_path = is_focal_in_path(meta["focal_length"], self.parent_dir)

            # 1.0 Chỉ tạo thư mục gốc 'Hình Ảnh' nếu thư mục hiện tại chưa nằm trong ngữ cảnh ảnh
            # và chưa nằm trong bất kỳ thư mục thiết bị/ánh sáng/tiêu cự nào
            if not in_photo_ctx and not dev_already_in_path and not light_already_in_path and not focal_already_in_path:
                path_parts.append(parent_img_name)

            # 1.1 Phân loại theo thiết bị chụp
            if self.enable_device_categorize:
                if not dev_already_in_path:
                    matched_existing_device_folder = None
                    if self.match_existing_folders and existing_subfolders:
                        dev_norm = normalize_text(meta["device"])
                        for sub in existing_subfolders:
                            sub_norm = normalize_text(sub.name)
                            if dev_norm == sub_norm or (len(dev_norm) >= 4 and dev_norm in sub_norm):
                                matched_existing_device_folder = sub.name
                                break

                    dev_folder = matched_existing_device_folder if matched_existing_device_folder else meta["device"]
                    path_parts.append(dev_folder)
                    label_parts.append(meta["device"])
                elif not (self.enable_lighting_categorize or self.enable_focal_categorize):
                    # Nếu chỉ bật mỗi phân loại thiết bị mà thiết bị đã khớp sẵn trong đường dẫn
                    label_parts.append(meta["device"])

            # 1.2 Phân tích nội dung AI nếu kết hợp bật
            if self.enable_ai and self.ai_classifier is not None:
                try:
                    ai_cat_key = self.ai_classifier.classify_file(file_path, engine=self.ai_engine, api_key=self.gemini_api_key)
                except Exception:
                    ai_cat_key = "Khac"
                ai_info = AI_CATEGORIES.get(ai_cat_key, AI_CATEGORIES["Khac"])
                ai_sub_name = ai_info["label"] if self.use_accent_folder else ai_info["folder"]

                if not is_ai_category_in_path(ai_cat_key, ai_info["label"], self.parent_dir):
                    path_parts.append(ai_sub_name)
                    label_parts.append(ai_info["label"])
                else:
                    label_parts.append(ai_info["label"])

            # 1.3 Phân loại theo điều kiện ánh sáng (Đủ Sáng / Thiếu Sáng)
            if self.enable_lighting_categorize:
                if not light_already_in_path:
                    matched_light = None
                    if self.match_existing_folders and existing_subfolders:
                        light_norm = normalize_text(meta["lighting"])
                        for sub in existing_subfolders:
                            if normalize_text(sub.name) == light_norm:
                                matched_light = sub.name
                                break
                    light_folder = matched_light if matched_light else meta["lighting"]
                    path_parts.append(light_folder)
                    label_parts.append(meta["lighting"])
                elif not self.enable_focal_categorize and not path_parts:
                    label_parts.append(meta["lighting"])

            # 1.4 Phân loại theo tiêu cự (Focal Length)
            if self.enable_focal_categorize:
                if not focal_already_in_path:
                    matched_focal = None
                    if self.match_existing_folders and existing_subfolders:
                        focal_norm = normalize_text(meta["focal_length"])
                        for sub in existing_subfolders:
                            if normalize_text(sub.name) == focal_norm:
                                matched_focal = sub.name
                                break
                    focal_folder = matched_focal if matched_focal else meta["focal_length"]
                    path_parts.append(focal_folder)
                    label_parts.append(meta["focal_length"])
                elif not path_parts:
                    label_parts.append(meta["focal_length"])

            # Nếu tất cả tiêu chí đã khớp với cây thư mục hiện tại
            if not path_parts:
                display_label = " | ".join(label_parts) if label_parts else "Đúng vị trí"
                return "", f"✓ {display_label} (Đúng vị trí)"

            target_path_str = "/".join(path_parts)
            display_label = " | ".join(label_parts) if label_parts else parent_img_name
            return target_path_str, display_label

        # =========================================================================
        # 2. PHÂN LOẠI THÔNG MINH BẰNG AI NỘI DUNG NẾU BẬT
        # =========================================================================
        if self.enable_ai and self.ai_classifier is not None and (is_image or is_video):
            try:
                ai_cat_key = self.ai_classifier.classify_file(
                    file_path,
                    engine=self.ai_engine,
                    api_key=self.gemini_api_key
                )
            except Exception as e:
                print(f"[AI] Lỗi phân loại file {file_path.name}: {e}")
                ai_cat_key = "Khac"

            ai_info = AI_CATEGORIES.get(ai_cat_key, AI_CATEGORIES["Khac"])
            ai_display_label = ai_info["label"]
            ai_subfolder_name = ai_info["folder"]

            # Nếu thư mục hiện tại đã chính là danh mục AI này
            if is_ai_category_in_path(ai_cat_key, ai_info["label"], self.parent_dir):
                return "", f"✓ AI: {ai_display_label} (Đúng vị trí)"

            # Kiểm tra xem có thư mục con có sẵn nào khớp với danh mục AI này không
            if self.match_existing_folders and existing_subfolders:
                keywords = list(AI_SUBFOLDER_KEYWORDS.get(ai_cat_key, []))
                keywords.append(ai_info["label"])
                keywords.append(ai_info["folder"])

                for sub in existing_subfolders:
                    if folder_matches_keywords(sub.name, keywords):
                        return sub.name, f"AI: {ai_display_label}"

            sub_name = ai_display_label if self.use_accent_folder else ai_subfolder_name

            # Nếu đã ở trong thư mục ảnh rồi thì không bọc thêm 'Hình Ảnh'
            if is_image and is_in_photo_context(self.parent_dir):
                return sub_name, f"AI: {ai_display_label}"

            parent_cat_name = "Hình Ảnh" if (self.use_accent_folder and is_image) else (
                "Hinh_Anh" if is_image else ("Video" if self.use_accent_folder else "Video")
            )
            target_path_str = f"{parent_cat_name}/{sub_name}"
            return target_path_str, f"AI: {ai_display_label}"

        # =========================================================================
        # 3. PHÂN LOẠI THEO ĐUÔI FILE TIÊU CHUẨN
        # =========================================================================
        matched_cat_key = "Khac"
        for cat_key, cat_data in DEFAULT_CATEGORIES.items():
            if ext in cat_data["extensions"]:
                matched_cat_key = cat_key
                break

        cat_info = DEFAULT_CATEGORIES[matched_cat_key]
        all_keywords = list(cat_info["keywords"])
        all_keywords.append(cat_info["display_name"])
        all_keywords.append(cat_info["folder_name_no_accent"])

        # Nếu thư mục hiện tại đã chính là danh mục này (vd người dùng đang mở sẵn thư mục 'Tài Liệu')
        if folder_matches_keywords(self.parent_dir.name, all_keywords):
            return "", f"✓ {cat_info['display_name']} (Đúng vị trí)"

        if self.match_existing_folders and existing_subfolders:
            for subfolder in existing_subfolders:
                if folder_matches_keywords(subfolder.name, all_keywords):
                    return subfolder.name, cat_info["display_name"]

        if self.use_accent_folder:
            return cat_info["display_name"], cat_info["display_name"]
        else:
            return cat_info["folder_name_no_accent"], cat_info["display_name"]

    def scan_files(self, status_callback: Optional[Callable[[str], None]] = None) -> List[Dict]:
        if not self.parent_dir.exists() or not self.parent_dir.is_dir():
            return []

        existing_subfolders = self.get_existing_subfolders()
        plan = []

        if not self.recursive:
            try:
                candidates = [p for p in self.parent_dir.iterdir() if p.is_file()]
            except Exception:
                candidates = []

            total = len(candidates)
            for i, item in enumerate(candidates, 1):
                if status_callback and (i % 5 == 0 or i == total):
                    status_callback(f"Đang quét file {i}/{total}: {item.name}...")

                ext = item.suffix
                target_folder_name, cat_label = self.find_target_folder_name(item, existing_subfolders)

                # Bỏ qua nếu file đã ở đúng thư mục đích (không cần di chuyển)
                if not target_folder_name or target_folder_name == ".":
                    continue
                target_dir = self.parent_dir / Path(target_folder_name)
                try:
                    if item.parent.resolve() == target_dir.resolve():
                        continue
                except Exception:
                    pass

                try:
                    size = item.stat().st_size
                except Exception:
                    size = 0

                plan.append({
                    "file_path": item,
                    "file_name": item.name,
                    "ext": ext if ext else "(Không đuôi)",
                    "target_folder_name": target_folder_name,
                    "category_label": cat_label,
                    "size": size,
                    "formatted_size": format_file_size(size)
                })
        else:
            for root, dirs, files in os.walk(str(self.parent_dir)):
                root_path = Path(root)
                for file_name in files:
                    item = root_path / file_name
                    ext = item.suffix
                    target_folder_name, cat_label = self.find_target_folder_name(item, existing_subfolders)

                    if not target_folder_name or target_folder_name == ".":
                        continue
                    target_dir = self.parent_dir / Path(target_folder_name)

                    try:
                        if item.parent.resolve() == target_dir.resolve():
                            continue
                    except Exception:
                        pass

                    try:
                        size = item.stat().st_size
                    except Exception:
                        size = 0

                    plan.append({
                        "file_path": item,
                        "file_name": item.name,
                        "ext": ext if ext else "(Không đuôi)",
                        "target_folder_name": target_folder_name,
                        "category_label": cat_label,
                        "size": size,
                        "formatted_size": format_file_size(size)
                    })

        return plan

    @staticmethod
    def get_unique_destination(target_folder: Path, filename: str) -> Path:
        dest = target_folder / filename
        if not dest.exists():
            return dest

        stem = Path(filename).stem
        suffix = Path(filename).suffix
        counter = 1
        while True:
            candidate = target_folder / f"{stem} ({counter}){suffix}"
            if not candidate.exists():
                return candidate
            counter += 1

    def execute_organize(
        self,
        plan: List[Dict],
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Tuple[int, int, List[str]]:
        success_count = 0
        error_count = 0
        errors = []
        total = len(plan)

        for i, item in enumerate(plan, 1):
            src: Path = item["file_path"]
            target_folder_name = item["target_folder_name"]
            # Hỗ trợ phân cấp như 'Hinh_Anh/Con_Nguoi'
            target_dir = self.parent_dir / Path(target_folder_name)

            try:
                target_dir.mkdir(parents=True, exist_ok=True)
                final_dest = self.get_unique_destination(target_dir, src.name)

                shutil.move(str(src), str(final_dest))
                success_count += 1

                if progress_callback:
                    progress_callback(i, total, f"✓ [{target_folder_name}] {src.name} ➔ {final_dest.name}")

            except Exception as e:
                error_count += 1
                msg = f"✗ Lỗi khi chuyển {src.name}: {str(e)}"
                errors.append(msg)
                if progress_callback:
                    progress_callback(i, total, msg)

        return success_count, error_count, errors
