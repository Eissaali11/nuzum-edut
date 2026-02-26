"""
التخزين: ملفات محلية، أو تكامل مع خدمات سحابية لاحقاً.
"""
from src.infrastructure.storage.file_service import save_base64_image, save_uploaded_file

__all__ = ["save_base64_image", "save_uploaded_file"]
