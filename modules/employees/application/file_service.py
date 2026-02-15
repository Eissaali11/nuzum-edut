"""Employee file operations (uploads/verification)."""
import os
from datetime import datetime

from werkzeug.utils import secure_filename


UPLOAD_FOLDER = "static/uploads/employees"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "pdf"}


def allowed_file(filename: str) -> bool:
    """Check whether a filename extension is allowed."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def verify_employee_image(image_path: str):
    """Verify the file exists and return the normalized path or None."""
    if not image_path:
        return None

    if image_path.startswith("static/"):
        full_path = image_path
    else:
        full_path = f"static/{image_path}"

    if os.path.exists(full_path) and os.path.getsize(full_path) > 0:
        return image_path
    return None


def save_employee_image(file, employee_id: int, image_type: str):
    """Save employee image with triple-check integrity before returning path."""
    if not file or not file.filename:
        print("ERROR لا يوجد ملف للحفظ")
        return None

    try:
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        filename = secure_filename(file.filename)
        name, ext = os.path.splitext(filename)
        if not ext:
            content_type = file.content_type or ""
            if "pdf" in content_type:
                ext = ".pdf"
            elif "jpeg" in content_type or "jpg" in content_type:
                ext = ".jpg"
            elif "png" in content_type:
                ext = ".png"
            elif "gif" in content_type:
                ext = ".gif"
            else:
                ext = ".jpg"

        unique_filename = f"{employee_id}_{image_type}_{datetime.now().strftime('%Y%m%d_%H%M%S%f')}{ext}"
        filepath = os.path.join(UPLOAD_FOLDER, unique_filename)

        file_content = file.read()
        file.seek(0)

        with open(filepath, "wb") as f:
            f.write(file_content)

        if not os.path.exists(filepath):
            print(f"ERROR الملف غير موجود بعد الحفظ: {filepath}")
            return None

        file_size = os.path.getsize(filepath)
        if file_size == 0:
            print(f"WARN الملف فارغ: {filepath}")
            return None

        if file_size != len(file_content):
            print(f"WARN عدم تطابق حجم الملف: {file_size} != {len(file_content)}")
            return None

        relative_path = f"uploads/employees/{unique_filename}"
        print(f"OK حفظ نجح: {relative_path} ({file_size} bytes)")
        return relative_path
    except Exception as e:
        print(f"ERROR خطأ في حفظ الصورة: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
