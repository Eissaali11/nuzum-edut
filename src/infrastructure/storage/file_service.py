"""
خدمة تخزين الملفات — حفظ صور Base64 وملفات مرفوعة.
مستخرجة من المسارات القديمة وقابلة لإعادة الاستخدام في البنية الجديدة.
لا تتجاوز 400 سطر.
"""
import os
import base64
import uuid
from typing import Optional, Union

try:
    from werkzeug.datastructures import FileStorage
    from werkzeug.utils import secure_filename
except ImportError:
    FileStorage = None
    secure_filename = None


def _get_upload_root() -> Optional[str]:
    """مسار جذر مجلد الرفع (static/uploads). يُستمد من Flask إن وُجد."""
    try:
        from flask import current_app
        root = getattr(current_app, "root_path", None)
        if root:
            return os.path.join(root, "static", "uploads")
    except RuntimeError:
        pass
    return None


def save_base64_image(
    base64_string: Optional[str],
    subfolder: str,
    upload_root: Optional[str] = None,
) -> Optional[str]:
    """
    تحويل سلسلة Base64 (أو data URL) إلى ملف PNG وحفظه في مجلد فرعي.
    تُرجع المسار النسبي من جذر التطبيق (مثلاً static/uploads/subfolder/uuid.png) أو None.
    """
    if not base64_string or not base64_string.startswith("data:image/"):
        return None
    root = upload_root or _get_upload_root()
    if not root:
        return None
    try:
        upload_folder = os.path.join(root, subfolder)
        os.makedirs(upload_folder, exist_ok=True)
        if "," in base64_string:
            _, encoded_data = base64_string.split(",", 1)
        else:
            encoded_data = base64_string
        image_data = base64.b64decode(encoded_data)
        filename = f"{uuid.uuid4().hex}.png"
        file_path = os.path.join(upload_folder, filename)
        with open(file_path, "wb") as f:
            f.write(image_data)
        return os.path.join("static", "uploads", subfolder, filename).replace("\\", "/")
    except Exception:
        return None


def save_uploaded_file(
    file: Union["FileStorage", object],
    subfolder: str,
    upload_root: Optional[str] = None,
    max_size_bytes: Optional[int] = None,
) -> Optional[str]:
    """
    حفظ ملف مرفوع (مثل request.files[...]) في مجلد فرعي.
    تُرجع المسار النسبي (static/uploads/subfolder/name_uuid.ext) أو None.
    file يجب أن يدعم .filename و .save(path).
    """
    if file is None:
        return None
    filename = getattr(file, "filename", None) or getattr(file, "name", None)
    if not filename or (isinstance(filename, str) and filename.strip() == ""):
        return None
    if secure_filename is None:
        return None
    root = upload_root or _get_upload_root()
    if not root:
        return None
    try:
        upload_folder = os.path.join(root, subfolder)
        os.makedirs(upload_folder, exist_ok=True)
        name, ext = os.path.splitext(secure_filename(filename))
        unique_filename = f"{name}_{uuid.uuid4().hex[:8]}{ext}"
        file_path = os.path.join(upload_folder, unique_filename)
        save_method = getattr(file, "save", None)
        if not callable(save_method):
            return None
        save_method(file_path)
        if not os.path.exists(file_path):
            return None
        if os.path.getsize(file_path) == 0:
            return None
        if max_size_bytes and os.path.getsize(file_path) > max_size_bytes:
            try:
                os.remove(file_path)
            except OSError:
                pass
            return None
        return os.path.join("static", "uploads", subfolder, unique_filename).replace("\\", "/")
    except Exception:
        return None
