import os
import sys
import json
import base64
import urllib.request
import urllib.error
from pathlib import Path
from typing import Tuple, List, Optional
import cv2
import numpy as np

# Đăng ký đọc file ảnh iPhone (.HEIC / .HEIF)
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except Exception:
    pass
from PIL import Image

AI_CATEGORIES = {
    "Con_Nguoi": {
        "label": "Người & Chân Dung",
        "folder": "Con_Nguoi",
        "description": "Ảnh chân dung, selfie, nhóm người, sự kiện có người"
    },
    "Dong_Vat": {
        "label": "Động Vật & Thú Cưng",
        "folder": "Dong_Vat",
        "description": "Chó, mèo, chim chóc, thú cưng, động vật hoang dã"
    },
    "Phong_Canh": {
        "label": "Phong Cảnh & Thiên Nhiên",
        "folder": "Phong_Canh",
        "description": "Biển, núi rừng, hoàng hôn, bầu trời, kiến trúc ngoài trời"
    },
    "Xe_Co": {
        "label": "Xe Cộ & Phương Tiện",
        "folder": "Xe_Co",
        "description": "Ô tô, xe máy, xe đạp, xe tải, máy bay, tàu thuyền..."
    },
    "Do_An_Uong": {
        "label": "Đồ Ăn & Ẩm Thực",
        "folder": "Do_An_Uong",
        "description": "Món ăn, thức uống, bánh ngọt, cà phê, nhà hàng"
    },
    "Tai_Lieu_Chup": {
        "label": "Tài Liệu & Hóa Đơn",
        "folder": "Tai_Lieu_Chup",
        "description": "Văn bản chụp, hóa đơn, giấy tờ, slide thuyết trình"
    },
    "Screenshots": {
        "label": "Ảnh Chụp Màn Hình",
        "folder": "Screenshots",
        "description": "Ảnh chụp màn hình máy tính, điện thoại, tin nhắn, meme"
    },
    "Khac": {
        "label": "Khác",
        "folder": "Khac",
        "description": "Các hình ảnh hoặc video khác"
    }
}

ANIMAL_KEYWORDS = {
    "dog", "cat", "bird", "fish", "horse", "cow", "sheep", "elephant", "bear",
    "lion", "tiger", "fox", "wolf", "rabbit", "monkey", "chimp", "snake", "lizard",
    "frog", "turtle", "eagle", "owl", "parrot", "penguin", "whale", "dolphin",
    "shark", "butterfly", "spider", "beetle", "bee", "duck", "goose", "swan",
    "rooster", "hen", "terrier", "retriever", "spaniel", "hound", "poodle",
    "collie", "shepherd", "pug", "chihuahua", "tabby", "persian", "siamese",
    "lynx", "leopard", "cheetah", "jaguar", "cougar", "deer", "gazelle", "zebra",
    "pig", "boar", "ox", "bison", "ram", "goat", "camel", "llama", "kangaroo",
    "koala", "panda", "otter", "beaver", "seal", "walrus", "squirrel", "hamster",
    "mouse", "rat", "hedgehog", "skunk", "badger", "raccoon", "armadillo"
}

FOOD_KEYWORDS = {
    "pizza", "burger", "hamburger", "hotdog", "sandwich", "espresso", "coffee",
    "soup", "bread", "cake", "ice cream", "cookie", "chocolate", "pie", "salad",
    "burrito", "taco", "bagel", "pretzel", "banana", "apple", "orange", "lemon",
    "strawberry", "grape", "pineapple", "watermelon", "broccoli", "carrot",
    "cucumber", "mushroom", "pasta", "spaghetti", "carbonara", "sushi", "wine",
    "beer", "cocktail", "tea", "potpie", "meatloaf", "guacamole", "dough", "trifle"
}

SCENERY_KEYWORDS = {
    "alp", "cliff", "promontory", "seashore", "lakeside", "volcano", "valley",
    "beacon", "coral reef", "sandbar", "mountain", "beach", "ocean", "sea",
    "coast", "geyser", "dam", "bridge", "castle", "palace", "church", "monastery",
    "mosque", "pagoda", "stupa", "triumphal arch", "bell cot", "fountain"
}

VEHICLE_KEYWORDS = {
    "car", "automobile", "motorcycle", "moped", "scooter", "bicycle", "bike",
    "cab", "taxi", "truck", "van", "bus", "train", "locomotive", "subway",
    "airplane", "airliner", "aircraft", "jet", "helicopter", "boat", "ship",
    "ferry", "canoe", "yacht", "speedboat", "sailboat", "jeep", "trailer",
    "tractor", "forklift", "ambulance", "police van", "fire engine", "limousine",
    "sports car", "convertible", "minivan", "pickup", "racer", "go-kart",
    "snowmobile", "tank", "bullet train", "steam locomotive", "lifeboat",
    "tow truck", "garbage truck", "tricycle", "unicycle", "carriage", "rickshaw",
    "airship", "balloon", "space shuttle", "wheelbarrow"
}

PERSON_KEYWORDS = {
    "groom", "bride", "kimono", "scuba diver", "swimming trunks", "bikini",
    "sarong", "stole", "apron", "sombrero", "cowboy hat", "jersey", "sweatshirt",
    "trench coat", "cardigan", "suit", "gown", "jean", "pajama", "uniform"
}

import time

GEMINI_MODELS_PRIORITY = [
    # Nhóm Flash Lite (Hạn mức RPM cao: 10 - 15 RPM, phản hồi siêu tốc)
    "gemini-2.5-flash-lite",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-2.0-flash-lite",
    "gemini-2-flash-lite",

    # Nhóm Flash tiêu chuẩn (5 RPM mỗi model)
    "gemini-2.5-flash",
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3-flash",
    "gemini-2.0-flash",
    "gemini-2-flash",

    # Nhóm dự phòng
    "gemini-1.5-flash-latest",
    "gemini-2.0-flash-exp"
]


def load_image_bgr(file_path: Path) -> Optional[np.ndarray]:
    """Đọc ảnh an toàn hỗ trợ JPG, PNG, WEBP và HEIC (iPhone) với đường dẫn tiếng Việt."""
    try:
        ext = file_path.suffix.lower()
        if ext in [".heic", ".heif"]:
            with Image.open(str(file_path)) as pil_img:
                rgb_img = pil_img.convert("RGB")
                return cv2.cvtColor(np.array(rgb_img), cv2.COLOR_RGB2BGR)

        img_data = np.fromfile(str(file_path), dtype=np.uint8)
        img = cv2.imdecode(img_data, cv2.IMREAD_COLOR)
        if img is not None:
            return img

        # Fallback qua PIL
        with Image.open(str(file_path)) as pil_img:
            rgb_img = pil_img.convert("RGB")
            return cv2.cvtColor(np.array(rgb_img), cv2.COLOR_RGB2BGR)
    except Exception as e:
        print(f"[AI] Lỗi đọc ảnh {file_path.name}: {e}")
        return None


class AIClassifier:
    """Bộ phân loại đa phương tiện kết hợp Offline AI và Cloud Gemini AI."""
    def __init__(self, models_dir: Optional[str] = None):
        if not models_dir:
            if getattr(sys, "frozen", False):
                if hasattr(sys, "_MEIPASS"):
                    bundled_dir = Path(sys._MEIPASS) / "models"
                    if bundled_dir.exists():
                        models_dir = str(bundled_dir)
                if not models_dir:
                    exe_dir = Path(sys.executable).resolve().parent / "models"
                    if exe_dir.exists():
                        models_dir = str(exe_dir)
            if not models_dir:
                models_dir = str(Path(__file__).resolve().parent / "models")
        self.models_dir = Path(models_dir)

        # Mô hình Offline
        self.net = None
        self.synset_classes: List[str] = []
        self.face_cascade = None
        self._active_gemini_model: Optional[str] = None
        self._model_cooldowns: dict = {}
        self._init_offline_models()

    def _init_offline_models(self):
        try:
            local_cascade = self.models_dir / "haarcascade_frontalface_default.xml"
            if local_cascade.exists():
                self.face_cascade = cv2.CascadeClassifier(str(local_cascade))
            else:
                cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
                if os.path.exists(cascade_path):
                    self.face_cascade = cv2.CascadeClassifier(cascade_path)
        except Exception as e:
            print(f"[AI] Lỗi nạp Haar Cascade: {e}")

        model_path = self.models_dir / "squeezenet.onnx"
        synset_path = self.models_dir / "synset.txt"

        if model_path.exists():
            try:
                self.net = cv2.dnn.readNetFromONNX(str(model_path))
            except Exception as e:
                print(f"[AI] Lỗi nạp ONNX model: {e}")

        if synset_path.exists():
            try:
                with open(synset_path, "r", encoding="utf-8") as f:
                    self.synset_classes = [line.strip().split(" ", 1)[-1].lower() for line in f if line.strip()]
            except Exception as e:
                print(f"[AI] Lỗi nạp synset: {e}")

    # =========================================================================
    # 1. PHÂN LOẠI OFFLINE (LOCAL COMPUTER VISION)
    # =========================================================================
    def classify_image_offline(self, img_bgr: np.ndarray) -> Tuple[str, float]:
        if img_bgr is None or img_bgr.size == 0:
            return "Khac", 0.0

        h, w = img_bgr.shape[:2]

        # Bước 1: Kiểm tra Người (Face Detection)
        if self.face_cascade is not None:
            gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            scale = 600.0 / max(h, w) if max(h, w) > 600 else 1.0
            if scale < 1.0:
                small_gray = cv2.resize(gray, (int(w * scale), int(h * scale)))
            else:
                small_gray = gray

            faces = self.face_cascade.detectMultiScale(
                small_gray,
                scaleFactor=1.15,
                minNeighbors=4,
                minSize=(30, 30)
            )
            if len(faces) > 0:
                return "Con_Nguoi", 0.95

        # Bước 2: Kiểm tra Tài Liệu Chụp (Văn bản, Hóa đơn)
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        mean_brightness = np.mean(gray)
        edges = cv2.Canny(gray, 100, 200)
        edge_ratio = np.count_nonzero(edges) / (h * w)

        if mean_brightness > 190 and 0.04 < edge_ratio < 0.25:
            hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
            mean_saturation = np.mean(hsv[:, :, 1])
            if mean_saturation < 35:
                return "Tai_Lieu_Chup", 0.88

        # Bước 3: Phân loại bằng SqueezeNet ONNX
        if self.net is not None and len(self.synset_classes) > 0:
            blob = cv2.dnn.blobFromImage(
                img_bgr,
                scalefactor=1.0 / 255.0,
                size=(224, 224),
                mean=(0, 0, 0),
                swapRB=True,
                crop=False
            )
            self.net.setInput(blob)
            preds = self.net.forward()

            top_indices = np.argsort(preds[0])[::-1][:5]
            for idx in top_indices:
                if idx < len(self.synset_classes):
                    class_name = self.synset_classes[idx]
                    tokens = set(class_name.replace(",", " ").split())

                    if tokens & VEHICLE_KEYWORDS:
                        return "Xe_Co", 0.92
                    if tokens & ANIMAL_KEYWORDS:
                        return "Dong_Vat", 0.90
                    if tokens & FOOD_KEYWORDS:
                        return "Do_An_Uong", 0.90
                    if tokens & SCENERY_KEYWORDS:
                        return "Phong_Canh", 0.85
                    if tokens & PERSON_KEYWORDS:
                        return "Con_Nguoi", 0.85

        # Bước 4: Heuristic màu sắc tổng thể (Trời xanh, cây cỏ, biển)
        hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        green_mask = cv2.inRange(hsv, (35, 40, 40), (85, 255, 255))
        blue_mask = cv2.inRange(hsv, (90, 40, 40), (130, 255, 255))
        nature_ratio = (np.count_nonzero(green_mask) + np.count_nonzero(blue_mask)) / (h * w)

        if nature_ratio > 0.40:
            return "Phong_Canh", 0.75

        return "Khac", 0.50

    # =========================================================================
    # 2. PHÂN LOẠI CLOUD (GOOGLE GEMINI VISION API CÓ TỰ DÒ MODEL)
    # =========================================================================
    def get_available_models_order(self) -> List[str]:
        now = time.time()
        # Ưu tiên các model chưa chạm giới hạn (không trong cooldown)
        available = [m for m in GEMINI_MODELS_PRIORITY if self._model_cooldowns.get(m, 0) <= now]
        # Sau đó tới các model đang cooldown (đề phòng tất cả đều bị)
        cooling = [m for m in GEMINI_MODELS_PRIORITY if m not in available]
        return available + cooling

    def classify_image_cloud(self, img_bgr: np.ndarray, api_key: str) -> Tuple[str, float]:
        if not api_key:
            return self.classify_image_offline(img_bgr)

        try:
            h, w = img_bgr.shape[:2]
            scale = 640.0 / max(h, w) if max(h, w) > 640 else 1.0
            if scale < 1.0:
                resized = cv2.resize(img_bgr, (int(w * scale), int(h * scale)))
            else:
                resized = img_bgr

            ret, buf = cv2.imencode(".jpg", resized, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if not ret:
                return self.classify_image_offline(img_bgr)

            b64_image = base64.b64encode(buf.tobytes()).decode("utf-8")
            prompt_text = (
                "Phân tích ảnh này và phân loại vào CHÍNH XÁC MỘT trong các nhóm sau: "
                "[Con_Nguoi, Dong_Vat, Xe_Co, Phong_Canh, Do_An_Uong, Tai_Lieu_Chup, Screenshots, Khac]. "
                "Quy tắc: "
                "- Có người/chân dung/selfie/nhóm người -> Con_Nguoi. "
                "- Có thú cưng, chim chóc, động vật -> Dong_Vat. "
                "- Xe cộ, ô tô, xe máy, xe đạp, máy bay, tàu thuyền, phương tiện giao thông -> Xe_Co. "
                "- Cảnh thiên nhiên, biển, núi, kiến trúc ngoài trời -> Phong_Canh. "
                "- Món ăn, đồ uống, ẩm thực -> Do_An_Uong. "
                "- Chụp giấy tờ, hóa đơn, văn bản -> Tai_Lieu_Chup. "
                "- Ảnh chụp màn hình máy tính/điện thoại, tin nhắn chat, meme -> Screenshots. "
                "- Khác -> Khac. "
                "CHỈ TRẢ VỀ DUY NHẤT TÊN NHÓM TRÊN (không giải thích thêm)."
            )

            payload = {
                "contents": [{
                    "parts": [
                        {"text": prompt_text},
                        {"inline_data": {"mime_type": "image/jpeg", "data": b64_image}}
                    ]
                }],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 20
                }
            }

            models_to_try = self.get_available_models_order()

            for model in models_to_try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                try:
                    with urllib.request.urlopen(req, timeout=8) as resp:
                        resp_data = json.loads(resp.read().decode("utf-8"))
                        text_result = resp_data["candidates"][0]["content"]["parts"][0]["text"].strip()
                        self._active_gemini_model = model

                        for cat in AI_CATEGORIES.keys():
                            if cat.lower() in text_result.lower():
                                return cat, 0.98
                        return "Khac", 0.60
                except urllib.error.HTTPError as he:
                    if he.code in [404, 429, 503]:
                        # 429: Chạm giới hạn Quota/Rate limit -> tự động chuyển model kế tiếp!
                        print(f"[Gemini Auto-Rotate] Model '{model}' chạm giới hạn (mã {he.code}). Tự động luân chuyển sang model kế tiếp...")
                        self._model_cooldowns[model] = time.time() + 60
                        continue
                    else:
                        raise he

            return self.classify_image_offline(img_bgr)
        except Exception as e:
            print(f"[Gemini API Error] {e} -> Tự động chuyển sang Offline AI")
            return self.classify_image_offline(img_bgr)

    # =========================================================================
    # 3. PHÂN LOẠI FILE (ẢNH HOẶC VIDEO)
    # =========================================================================
    def classify_file(self, file_path: Path, engine: str = "offline", api_key: str = "") -> str:
        ext = file_path.suffix.lower()
        image_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".heic", ".heif"}
        video_exts = {".mp4", ".mkv", ".mov", ".avi", ".wmv", ".flv", ".webm", ".3gp"}

        if ext in image_exts:
            try:
                img = load_image_bgr(file_path)
                if img is None:
                    return "Khac"

                if engine == "cloud" and api_key:
                    category, _ = self.classify_image_cloud(img, api_key)
                else:
                    category, _ = self.classify_image_offline(img)
                return category
            except Exception as e:
                print(f"[AI] Lỗi đọc ảnh {file_path.name}: {e}")
                return "Khac"

        elif ext in video_exts:
            try:
                cap = cv2.VideoCapture(str(file_path))
                if not cap.isOpened():
                    return "Khac"

                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                if total_frames <= 0:
                    cap.release()
                    return "Khac"

                indices = [int(total_frames * r) for r in [0.15, 0.50, 0.80]]
                votes = []

                for idx in indices:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        if engine == "cloud" and api_key:
                            cat, _ = self.classify_image_cloud(frame, api_key)
                        else:
                            cat, _ = self.classify_image_offline(frame)
                        votes.append(cat)

                cap.release()

                if not votes:
                    return "Khac"

                if "Con_Nguoi" in votes:
                    return "Con_Nguoi"

                return max(set(votes), key=votes.count)
            except Exception as e:
                print(f"[AI] Lỗi phân tích video {file_path.name}: {e}")
                return "Khac"

        return "Khac"
