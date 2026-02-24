import base64
import io
import os

import qrcode
from flask import current_app, render_template
from xhtml2pdf import pisa


def _image_to_base64(file_path):
    if not file_path or file_path in {"None", "null"}:
        return None

    possible_paths = [
        file_path,
        os.path.join(current_app.root_path, file_path),
        os.path.join(current_app.root_path, "static", file_path),
        os.path.join(current_app.root_path, "uploads", file_path),
        os.path.join(current_app.root_path, "static", "uploads", file_path),
        os.path.join(current_app.static_folder, file_path),
        os.path.join(current_app.static_folder, "uploads", file_path),
    ]

    for path in possible_paths:
        if os.path.exists(path):
            try:
                with open(path, "rb") as image_file:
                    data = image_file.read()
                ext = os.path.splitext(path)[1].lower()
                mime_type = {
                    ".png": "image/png",
                    ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".gif": "image/gif",
                    ".bmp": "image/bmp",
                    ".webp": "image/webp",
                }.get(ext, "image/png")
                encoded = base64.b64encode(data).decode("utf-8")
                return f"data:{mime_type};base64,{encoded}"
            except Exception:
                continue
    return None


def _link_callback(uri, rel):
    if not uri:
        return uri
    if uri.startswith("data:") or uri.startswith("http://") or uri.startswith("https://"):
        return uri

    root = current_app.root_path
    static_root = current_app.static_folder

    if uri.startswith("/static/"):
        return os.path.join(root, uri.lstrip("/"))
    if uri.startswith("static/"):
        return os.path.join(root, uri)
    if uri.startswith("/uploads/"):
        return os.path.join(root, "uploads", uri.replace("/uploads/", "", 1))
    if uri.startswith("uploads/"):
        return os.path.join(root, "uploads", uri.replace("uploads/", "", 1))
    if uri.startswith("images/"):
        return os.path.join(static_root, uri)

    static_candidate = os.path.join(static_root, uri)
    if os.path.exists(static_candidate):
        return static_candidate

    return os.path.join(root, uri)


def generate_handover_report_pdf_xhtml2pdf(handover):
    damage_diagram_b64 = _image_to_base64(handover.damage_diagram_path) if handover.damage_diagram_path else None
    driver_signature_b64 = _image_to_base64(handover.driver_signature_path) if handover.driver_signature_path else None
    supervisor_signature_b64 = _image_to_base64(handover.supervisor_signature_path) if handover.supervisor_signature_path else None
    movement_officer_signature_b64 = (
        _image_to_base64(handover.movement_officer_signature_path)
        if getattr(handover, "movement_officer_signature_path", None)
        else None
    )

    # إعادة تحميل الصور من قاعدة البيانات لضمان تحديث الملاحظات
    from modules.vehicles.domain.handover_models import VehicleHandoverImage
    images = VehicleHandoverImage.query.filter_by(handover_record_id=handover.id).all()
    handover_images_b64 = []
    for image in images:
        image_b64 = _image_to_base64(getattr(image, "file_path", None))
        if image_b64:
            handover_images_b64.append(
                {
                    "file_path": image_b64,
                    "file_description": getattr(image, "file_description", None),
                }
            )

    qr_code_url = None
    if handover.form_link:
        qr_image = qrcode.make(handover.form_link)
        buf = io.BytesIO()
        qr_image.save(buf, format="PNG")
        qr_code_url = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('utf-8')}"

    qr_code_url_2 = None
    if getattr(handover, "form_link_2", None):
        qr_image_2 = qrcode.make(handover.form_link_2)
        buf2 = io.BytesIO()
        qr_image_2.save(buf2, format="PNG")
        qr_code_url_2 = f"data:image/png;base64,{base64.b64encode(buf2.getvalue()).decode('utf-8')}"

    html_string = render_template(
        "vehicles/handover_report.html",
        handover=handover,
        qr_code_url=qr_code_url,
        qr_code_url_2=qr_code_url_2,
        damage_diagram_b64=damage_diagram_b64,
        driver_signature_b64=driver_signature_b64,
        supervisor_signature_b64=supervisor_signature_b64,
        movement_officer_signature_b64=movement_officer_signature_b64,
        handover_images_b64=handover_images_b64,
    )

    html_string = html_string.replace('src="/uploads/', 'src="uploads/')
    html_string = html_string.replace('src="/static/', 'src="static/')

    pdf_buffer = io.BytesIO()
    status = pisa.CreatePDF(
        src=html_string,
        dest=pdf_buffer,
        encoding="utf-8",
        link_callback=_link_callback,
    )

    if status.err:
        raise RuntimeError("xhtml2pdf failed to render handover report")

    pdf_buffer.seek(0)
    return pdf_buffer