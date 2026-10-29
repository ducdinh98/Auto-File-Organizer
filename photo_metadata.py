import os
import sys
import re
import math
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except Exception:
    pass

from PIL import Image, ExifTags
import numpy as np


def sanitize_folder_name(name: str) -> str:
    """Xóa bỏ các ký tự cấm trong tên thư mục của hệ điều hành Windows."""
    cleaned = re.sub(r'[<>:"/\\|?*]+', '_', name)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip('. ')
    return cleaned if cleaned else 'Khac'


def parse_rational(val) -> Optional[float]:
    """Phân tích các giá trị dạng phân số hoặc rational trong EXIF."""
    if val is None:
        return None
    try:
        if isinstance(val, (int, float)):
            return float(val)
        if hasattr(val, 'numerator') and hasattr(val, 'denominator'):
            if val.denominator != 0:
                return float(val.numerator) / float(val.denominator)
            return None
        if isinstance(val, tuple) and len(val) == 2:
            if val[1] != 0:
                return float(val[0]) / float(val[1])
            return None
        return float(val)
    except Exception:
        return None


FAMOUS_STANDALONE_LINES = (
    "iphone", "ipad", "ipod", "pixel",
    "redmi", "poco", "mi ",
    "galaxy", "xperia",
    "reno", "find ", "iqoo",
    "oneplus", "realme",
    "lumix", "powershot"
)


def fix_device_casing(text: str) -> str:
    """Định dạng chữ hoa/thường đẹp mắt cho tên model thiết bị (ví dụ 'REDMI Note 17' -> 'Redmi Note 17')."""
    words = text.split()
    fixed_words = []
    preserve_caps = {
        "4G", "5G", "LTE", "GT", "SE", "FE", "II", "III", "IV", "V", "VI",
        "VII", "VIII", "IX", "X", "XR", "XS", "RAW", "HDR", "GPS", "EOS", "AI"
    }
    for w in words:
        w_up = w.upper()
        if w_up in preserve_caps:
            fixed_words.append(w_up)
        elif w_up in {"PRO", "MAX", "ULTRA", "PLUS", "MINI"}:
            fixed_words.append(w_up.capitalize())
        elif any(c.isdigit() or c == "-" for c in w):
            fixed_words.append(w)
        elif w.isupper() and len(w) > 2:
            fixed_words.append(w.capitalize())
        else:
            fixed_words.append(w)
    return " ".join(fixed_words)


def clean_device_name(make: Optional[str], model: Optional[str], use_accent: bool = True) -> str:
    """
    Chuẩn hóa tên thiết bị chụp thành tên thư mục đẹp, gọn gàng và tự nhiên.
    Ví dụ: 
    - Make='Apple', Model='iPhone 18 Pro Max' -> 'iPhone 18 Pro Max'
    - Make='Xiaomi', Model='REDMI Note 17' -> 'Redmi Note 17'
    - Make='Samsung', Model='Galaxy S24 Ultra' -> 'Galaxy S24 Ultra'
    - Make='Canon', Model='Canon EOS R5' -> 'Canon EOS R5'
    - Make='Sony', Model='ILCE-7M4' -> 'Sony ILCE-7M4'
    """
    make_clean = (make or "").strip()
    model_clean = (model or "").strip()
    
    if not make_clean and not model_clean:
        return "Thiết Bị Khác" if use_accent else "Thiet_Bi_Khac"
    
    if not make_clean:
        return sanitize_folder_name(fix_device_casing(model_clean))
    if not model_clean:
        return sanitize_folder_name(make_clean.title())
        
    make_lower = make_clean.lower()
    model_lower = model_clean.lower()
    formatted_model = fix_device_casing(model_clean)
    
    # Đối với các dòng máy nổi tiếng (iPhone, Redmi, Galaxy, Pixel, Xperia, Poco...) không cần lặp lại tên hãng
    for prefix in FAMOUS_STANDALONE_LINES:
        if model_lower.startswith(prefix) or f" {prefix}" in model_lower:
            return sanitize_folder_name(formatted_model)
    
    # Nếu Model đã chứa tên hãng (ví dụ Make="Canon", Model="Canon EOS R5")
    if make_lower in model_lower:
        return sanitize_folder_name(formatted_model)
    if model_lower in make_lower:
        return sanitize_folder_name(make_clean.title())
        
    brand = make_clean.title() if make_clean.islower() else make_clean
    return sanitize_folder_name(f"{brand} {formatted_model}")


def format_focal_length(focal_35mm: Optional[float], focal_phys: Optional[float], use_accent: bool = True) -> str:
    """
    Định dạng tiêu cự thành tên thư mục trực quan.
    Ví dụ: '24mm (Góc Rộng)', '13mm (Góc Siêu Rộng)', '77mm (Tele)'.
    """
    eff = focal_35mm if focal_35mm and focal_35mm > 0 else focal_phys
    if eff is None or eff <= 0:
        return "Không Rõ Tiêu Cự" if use_accent else "Khong_Ro_Tieu_Cu"
        
    mm_val = int(round(eff))
    if use_accent:
        if mm_val < 20:
            desc = "Góc Siêu Rộng"
        elif mm_val <= 35:
            desc = "Góc Rộng"
        elif mm_val <= 70:
            desc = "Tiêu Chuẩn"
        elif mm_val <= 150:
            desc = "Tele"
        else:
            desc = "Siêu Tele"
        return f"{mm_val}mm ({desc})"
    else:
        if mm_val < 20:
            desc = "Goc_Sieu_Rong"
        elif mm_val <= 35:
            desc = "Goc_Rong"
        elif mm_val <= 70:
            desc = "Tieu_Chuan"
        elif mm_val <= 150:
            desc = "Tele"
        else:
            desc = "Sieu_Tele"
        return f"{mm_val}mm_{desc}"


def calculate_ev100(f_num: Optional[float], exp_time: Optional[float], iso: Optional[float]) -> Optional[float]:
    """
    Tính chỉ số Exposure Value tại ISO 100 (EV100) theo chuẩn nhiếp ảnh APEX:
    EV100 = log2(N^2 / t) - log2(ISO / 100)
    - EV100 >= 8.0: Ban ngày, nắng to, ngoài trời hoặc phòng sáng mạnh (Đủ Sáng).
    - EV100 < 6.5: Ban đêm, chạng vạng, chụp thiếu sáng (Thiếu Sáng).
    """
    if not f_num or not exp_time or not iso or f_num <= 0 or exp_time <= 0 or iso <= 0:
        return None
    try:
        return math.log2((f_num ** 2) / exp_time) - math.log2(iso / 100.0)
    except Exception:
        return None


def evaluate_visual_lighting(img: Image.Image) -> str:
    """
    Đo độ sáng trực tiếp từ ma trận điểm ảnh bằng phương pháp downsample thumbnail siêu tốc.
    Trả về 'Du_Sang' hoặc 'Thieu_Sang'.
    """
    try:
        gray = img.convert('L')
        gray.thumbnail((300, 300))
        arr = np.array(gray)
        mean_val = float(np.mean(arr))
        dark_ratio = float(np.count_nonzero(arr < 40)) / arr.size
        vdark_ratio = float(np.count_nonzero(arr < 20)) / arr.size
        
        # Nếu độ sáng trung bình < 75 hoặc độ tối chiếm phần lớn diện tích
        if mean_val < 75 or dark_ratio > 0.35 or (mean_val < 90 and vdark_ratio > 0.15):
            return "Thieu_Sang"
        return "Du_Sang"
    except Exception:
        return "Du_Sang"


def extract_photo_metadata(file_path: Path, use_accent: bool = True) -> Dict[str, Any]:
    """
    Trích xuất toàn bộ siêu dữ liệu nhiếp ảnh từ file:
    - Thiết bị chụp (Device Model)
    - Điều kiện ánh sáng (Đủ Sáng / Thiếu Sáng)
    - Tiêu cự ống kính (Focal Length)
    """
    result = {
        "device": "Thiết Bị Khác" if use_accent else "Thiet_Bi_Khac",
        "has_device_info": False,
        "lighting": "Đủ Sáng" if use_accent else "Du_Sang",
        "lighting_key": "Du_Sang",
        "focal_length": "Không Rõ Tiêu Cự" if use_accent else "Khong_Ro_Tieu_Cu",
        "focal_mm": None,
        "is_photo": False
    }
    
    ext = file_path.suffix.lower()
    photo_exts = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".tif", ".tiff", ".bmp", ".dng", ".cr2", ".nef", ".arw"}
    if ext not in photo_exts:
        return result
        
    try:
        with Image.open(str(file_path)) as img:
            result["is_photo"] = True
            
            # 1. Trích xuất EXIF cơ bản
            exif = img.getexif()
            make = None
            model = None
            
            if exif:
                make = exif.get(271) or exif.get(0x010f)
                model = exif.get(272) or exif.get(0x0110)
                
            # Đọc Exif Sub-IFD chứa thông số chụp sâu
            exif_ifd = {}
            if exif:
                try:
                    exif_ifd = exif.get_ifd(ExifTags.IFD.Exif)
                except Exception:
                    try:
                        exif_ifd = exif.get_ifd(0x8769)
                    except Exception:
                        pass
                        
            # Nhận diện Model thiết bị
            if model or make:
                result["device"] = clean_device_name(make, model, use_accent=use_accent)
                result["has_device_info"] = True
                
            # 2. Nhận diện Điều kiện ánh sáng (Đủ Sáng vs Thiếu Sáng)
            bv = parse_rational(exif_ifd.get(37379) or exif_ifd.get(0x9203))
            iso = exif_ifd.get(34855) or exif_ifd.get(0x8827)
            exp_time = parse_rational(exif_ifd.get(33434) or exif_ifd.get(0x829A))
            f_num = parse_rational(exif_ifd.get(33437) or exif_ifd.get(0x829D))
            dt_str = str(exif.get(306) or exif_ifd.get(36867) or "")

            hour = None
            if " " in dt_str and ":" in dt_str.split()[1]:
                try:
                    hour = int(dt_str.split()[1].split(":")[0])
                except Exception:
                    pass

            # Khẩu độ mặc định nếu máy ảnh không ghi f-number (điện thoại thường là f/1.8)
            effective_f = f_num if (f_num and f_num > 0) else 1.8
            ev100 = calculate_ev100(effective_f, exp_time, iso)

            # Thu thập chỉ số phân tích điểm ảnh
            gray = img.convert('L')
            gray.thumbnail((300, 300))
            arr = np.array(gray)
            mean_val = float(np.mean(arr))
            dark_ratio = float(np.count_nonzero(arr < 40)) / arr.size
            vdark_ratio = float(np.count_nonzero(arr < 20)) / arr.size

            lighting_key = "Du_Sang"

            # Tầng 1: Sử dụng EV100 chuẩn nhiếp ảnh (chính xác tuyệt đối khi có thông số chụp)
            if ev100 is not None:
                if ev100 >= 8.0:
                    lighting_key = "Du_Sang"
                elif ev100 < 6.5:
                    lighting_key = "Thieu_Sang"
                else:  # Vùng chuyển tiếp 6.5 <= EV100 < 8.0 (hoàng hôn / phòng hơi tối)
                    if hour is not None and (hour >= 18 or hour < 6):
                        lighting_key = "Thieu_Sang"
                    elif iso and iso >= 800:
                        lighting_key = "Thieu_Sang"
                    elif mean_val < 85 or dark_ratio > 0.30:
                        lighting_key = "Thieu_Sang"
                    else:
                        lighting_key = "Du_Sang"

            # Tầng 2: Kiểm tra kết hợp ISO và Tốc độ chụp nếu thiếu khẩu độ
            elif iso is not None and isinstance(iso, (int, float)):
                if iso <= 100 and exp_time is not None and exp_time < 0.01:
                    lighting_key = "Du_Sang"
                elif iso >= 1000 or (iso >= 500 and exp_time is not None and exp_time >= 0.03):
                    lighting_key = "Thieu_Sang"
                elif hour is not None and (hour >= 18 or hour < 6) and iso >= 400:
                    lighting_key = "Thieu_Sang"
                else:
                    lighting_key = "Thieu_Sang" if (mean_val < 75 or dark_ratio > 0.35) else "Du_Sang"

            # Tầng 3: Kiểm tra BrightnessValue (chỉ tin nếu không phải dummy 0.0 của Android HAL)
            elif bv is not None:
                is_dummy_bv = (bv == 0.0 and (iso is None or iso <= 100) and (exp_time is None or exp_time < 0.01))
                if not is_dummy_bv:
                    if bv > 1.5:
                        lighting_key = "Du_Sang"
                    elif bv < 0.0:
                        lighting_key = "Thieu_Sang"
                    else:
                        lighting_key = "Thieu_Sang" if (mean_val < 75 or dark_ratio > 0.35) else "Du_Sang"
                else:
                    lighting_key = "Thieu_Sang" if (mean_val < 75 or dark_ratio > 0.35) else "Du_Sang"

            # Tầng 4: Phân tích thị giác ma trận điểm ảnh (fallback khi không có bất kỳ EXIF nào)
            else:
                if mean_val < 75 or dark_ratio > 0.35 or (mean_val < 90 and vdark_ratio > 0.15):
                    lighting_key = "Thieu_Sang"
                else:
                    lighting_key = "Du_Sang"

            result["lighting_key"] = lighting_key
            if use_accent:
                result["lighting"] = "Đủ Sáng" if lighting_key == "Du_Sang" else "Thiếu Sáng"
            else:
                result["lighting"] = "Du_Sang" if lighting_key == "Du_Sang" else "Thieu_Sang"
                
            # 3. Nhận diện Tiêu cự (Focal Length)
            focal_35mm = parse_rational(exif_ifd.get(41989) or exif_ifd.get(0xA405))
            focal_phys = parse_rational(exif_ifd.get(37386) or exif_ifd.get(0x920A))
            
            eff_mm = focal_35mm if focal_35mm and focal_35mm > 0 else focal_phys
            result["focal_mm"] = eff_mm
            result["focal_length"] = format_focal_length(focal_35mm, focal_phys, use_accent=use_accent)
            
    except Exception as e:
        # Nếu có lỗi khi đọc EXIF (ví dụ file hỏng), giữ kết quả an toàn
        pass
        
    return result
