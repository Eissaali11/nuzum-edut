"""
مولد PDF عربي لتسليم المركبات باستخدام Cairo والخط العربي
"""

import os
from io import BytesIO
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import arabic_reshaper
from bidi.algorithm import get_display


def _resolve_image_path(path):
    if not path:
        return None
    candidates = [
        path,
        os.path.join(os.path.dirname(__file__), '..', path),
        os.path.join(os.path.dirname(__file__), '..', 'static', path),
    ]
    cleaned = path.replace('\\', '/').replace('static/', '', 1) if isinstance(path, str) else path
    if cleaned:
        candidates.extend([
            os.path.join(os.path.dirname(__file__), '..', cleaned),
            os.path.join(os.path.dirname(__file__), '..', 'static', cleaned),
        ])

    for candidate in candidates:
        real = os.path.normpath(candidate)
        if os.path.exists(real):
            return real
    return None


def _draw_attachment_pages(c, handover_data, width, height, primary_color):
    images = getattr(handover_data, 'images', None) or []
    prepared = []
    for image in images:
        path = None
        if hasattr(image, 'get_path'):
            path = image.get_path()
        path = path or getattr(image, 'file_path', None) or getattr(image, 'image_path', None)
        description = None
        if hasattr(image, 'get_description'):
            description = image.get_description()
        description = description or getattr(image, 'file_description', None) or getattr(image, 'image_description', None)
        resolved = _resolve_image_path(path)
        if resolved:
            prepared.append((resolved, description or 'بدون وصف'))

    if not prepared:
        return

    slot_w = (width - 120) / 2
    slot_h = 220
    x_slots = [50, 70 + slot_w]
    y_slots = [height - 320, height - 620]

    for idx, (img_path, desc) in enumerate(prepared):
        if idx % 4 == 0:
            c.showPage()
            c.setStrokeColor(primary_color)
            c.setLineWidth(2)
            c.rect(30, 20, width - 60, height - 40)
            c.setFont('Helvetica-Bold', 16)
            c.setFillColor(primary_color)
            c.drawString(50, height - 60, 'Handover Attachments')

        page_pos = idx % 4
        x = x_slots[page_pos % 2]
        y = y_slots[page_pos // 2]

        c.setStrokeColor(colors.lightgrey)
        c.setLineWidth(1)
        c.rect(x, y, slot_w, slot_h)
        try:
            c.drawImage(img_path, x + 6, y + 30, width=slot_w - 12, height=slot_h - 42, preserveAspectRatio=True, anchor='c')
        except Exception:
            c.setFont('Helvetica', 10)
            c.setFillColor(colors.red)
            c.drawString(x + 10, y + (slot_h / 2), 'Image unavailable')

        c.setFont('Helvetica', 8)
        c.setFillColor(colors.black)
        text = str(desc)
        if len(text) > 65:
            text = text[:62] + '...'
        c.drawString(x + 8, y + 12, text)

def setup_arabic_font():
    """إعداد الخط العربي"""
    try:
        root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
        font_candidates = [
            ('beIN-Normal', os.path.join(root_dir, 'static', 'fonts', 'beIN-Normal.ttf')),
            ('Cairo', os.path.join(root_dir, 'Cairo.ttf')),
            ('Cairo', os.path.join(root_dir, 'static', 'fonts', 'Cairo.ttf')),
        ]
        registered = set(pdfmetrics.getRegisteredFontNames())
        for font_name, font_path in font_candidates:
            if os.path.exists(font_path):
                if font_name not in registered:
                    pdfmetrics.registerFont(TTFont(font_name, font_path))
                return font_name
        return 'Helvetica'
    except:
        return 'Helvetica'

def process_arabic_text(text):
    """معالجة النص العربي للعرض الصحيح"""
    if not text:
        return ""
    
    try:
        # تشكيل النص العربي
        reshaped_text = arabic_reshaper.reshape(str(text))
        # ترتيب النص من اليمين لليسار
        bidi_text = get_display(reshaped_text)
        return bidi_text
    except:
        return str(text)

def create_vehicle_handover_pdf(handover_data):
    """
    إنشاء PDF عربي لتسليم المركبة
    """
    try:
        print("Starting Arabic handover PDF generation...")
        
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        
        # إعداد الخط العربي
        arabic_font = setup_arabic_font()
        
        # الألوان
        primary_color = colors.HexColor('#2E86AB')
        secondary_color = colors.HexColor('#A23B72')
        accent_color = colors.HexColor('#F18F01')
        
        # إضافة شعار الشركة
        try:
            logo_path = os.path.join(os.path.dirname(__file__), '..', 'attached_assets', 'logo.png')
            if os.path.exists(logo_path):
                c.drawImage(logo_path, 50, height - 80, width=60, height=40, preserveAspectRatio=True)
        except:
            pass
        
        # العنوان الرئيسي
        c.setFont(arabic_font, 18)
        c.setFillColor(primary_color)
        title = process_arabic_text("وثيقة تسليم واستلام المركبة")
        title_width = c.stringWidth(title, arabic_font, 18)
        c.drawString((width - title_width)/2, height - 60, title)
        
        # معلومات الوثيقة
        y_position = height - 100
        c.setFont(arabic_font, 10)
        c.setFillColor(colors.black)
        
        # رقم الوثيقة
        doc_id = process_arabic_text(f"رقم الوثيقة: {handover_data.id}")
        c.drawString(width - 150, y_position, doc_id)
        y_position -= 15
        
        # تاريخ الإنشاء
        current_date = datetime.now().strftime('%Y-%m-%d %H:%M')
        date_text = process_arabic_text(f"تاريخ الإنشاء: {current_date}")
        c.drawString(width - 150, y_position, date_text)
        y_position -= 15
        
        # نوع العملية
        operation_type = "تسليم" if str(handover_data.handover_type) == "delivery" else "استلام"
        type_text = process_arabic_text(f"نوع العملية: {operation_type}")
        c.drawString(width - 150, y_position, type_text)
        
        # خط فاصل
        y_position = height - 160
        c.setStrokeColor(primary_color)
        c.setLineWidth(2)
        c.line(50, y_position, width - 50, y_position)
        
        # معلومات المركبة
        y_position -= 40
        c.setFont(arabic_font, 14)
        c.setFillColor(secondary_color)
        vehicle_title = process_arabic_text("معلومات المركبة")
        c.drawString(width - 120, y_position, vehicle_title)
        
        # جدول معلومات المركبة
        if hasattr(handover_data, 'vehicle_rel') and handover_data.vehicle_rel:
            vehicle = handover_data.vehicle_rel
            
            vehicle_data = [
                [process_arabic_text("رقم اللوحة"), process_arabic_text(str(vehicle.plate_number) if vehicle.plate_number else "غير محدد")],
                [process_arabic_text("الصنع"), process_arabic_text(str(vehicle.make) if vehicle.make else "غير محدد")],
                [process_arabic_text("الموديل"), process_arabic_text(str(vehicle.model) if vehicle.model else "غير محدد")],
                [process_arabic_text("السنة"), process_arabic_text(str(vehicle.year) if hasattr(vehicle, 'year') and vehicle.year else "غير محدد")],
                [process_arabic_text("اللون"), process_arabic_text(str(vehicle.color) if hasattr(vehicle, 'color') and vehicle.color else "غير محدد")]
            ]
        else:
            vehicle_data = [
                [process_arabic_text("معلومات المركبة"), process_arabic_text("غير متوفرة")]
            ]
        
        # إنشاء جدول المركبة
        vehicle_table = Table(vehicle_data, colWidths=[2*inch, 3*inch])
        vehicle_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), arabic_font),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        table_width, table_height = vehicle_table.wrap(width, height)
        y_position -= table_height + 20
        vehicle_table.drawOn(c, width - table_width - 50, y_position)
        
        # تفاصيل التسليم
        y_position -= 40
        c.setFont(arabic_font, 14)
        c.setFillColor(secondary_color)
        handover_title = process_arabic_text("تفاصيل التسليم")
        c.drawString(width - 120, y_position, handover_title)
        
        # جدول تفاصيل التسليم
        handover_details = [
            [process_arabic_text("التاريخ"), process_arabic_text(handover_data.handover_date.strftime('%Y-%m-%d') if handover_data.handover_date else "غير محدد")],
            [process_arabic_text("الوقت"), process_arabic_text(handover_data.handover_date.strftime('%H:%M') if handover_data.handover_date else "غير محدد")],
            [process_arabic_text("اسم الشخص"), process_arabic_text(str(handover_data.person_name) if handover_data.person_name else "غير محدد")],
            [process_arabic_text("رقم الهاتف"), process_arabic_text("غير محدد")],
            [process_arabic_text("قراءة العداد"), process_arabic_text(f"{handover_data.mileage} كم" if handover_data.mileage else "غير محدد")],
            [process_arabic_text("مستوى الوقود"), process_arabic_text(f"{handover_data.fuel_level}%" if handover_data.fuel_level else "غير محدد")]
        ]
        
        handover_table = Table(handover_details, colWidths=[2*inch, 3*inch])
        handover_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), arabic_font),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightcyan),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        table_width, table_height = handover_table.wrap(width, height)
        y_position -= table_height + 20
        handover_table.drawOn(c, width - table_width - 50, y_position)
        
        # قائمة تحقق المعدات
        y_position -= 50
        c.setFont(arabic_font, 14)
        c.setFillColor(secondary_color)
        equipment_title = process_arabic_text("معدات المركبة")
        c.drawString(width - 120, y_position, equipment_title)
        
        # قائمة المعدات
        equipment_items = [
            process_arabic_text("الإطار الاحتياطي"),
            process_arabic_text("طفاية الحريق"),
            process_arabic_text("حقيبة الإسعافات الأولية"),
            process_arabic_text("مثلث التحذير"),
            process_arabic_text("عدة الأدوات")
        ]
        
        y_position -= 30
        c.setFont(arabic_font, 10)
        c.setFillColor(colors.black)
        
        for item in equipment_items:
            # مربع التحقق
            c.setStrokeColor(colors.black)
            c.setLineWidth(1)
            c.rect(width - 50, y_position - 5, 10, 10)
            
            # نص المعدات
            c.drawString(width - 80, y_position, item)
            y_position -= 20
        
        # قسم الملاحظات
        y_position -= 30
        c.setFont(arabic_font, 14)
        c.setFillColor(secondary_color)
        notes_title = process_arabic_text("ملاحظات إضافية")
        c.drawString(width - 120, y_position, notes_title)
        
        # مربع الملاحظات
        y_position -= 30
        c.setStrokeColor(colors.grey)
        c.setLineWidth(1)
        c.rect(50, y_position - 80, width - 100, 70)
        
        # نص الملاحظات
        if handover_data.notes:
            c.setFont(arabic_font, 10)
            c.setFillColor(colors.black)
            notes_text = process_arabic_text(str(handover_data.notes))
            c.drawString(60, y_position - 20, notes_text)
        
        # قسم التوقيعات
        y_position -= 100
        c.setFont(arabic_font, 12)
        c.setFillColor(colors.black)
        
        # توقيع المسلم
        deliverer_text = process_arabic_text("توقيع المسلم:")
        c.drawString(width - 150, y_position, deliverer_text)
        c.line(width - 300, y_position - 5, width - 160, y_position - 5)
        
        # توقيع المستلم
        receiver_text = process_arabic_text("توقيع المستلم:")
        c.drawString(150, y_position, receiver_text)
        c.line(50, y_position - 5, 140, y_position - 5)
        
        # تاريخ التوقيع
        y_position -= 30
        date_signature = process_arabic_text("التاريخ:")
        c.drawString(width - 150, y_position, date_signature)
        c.line(width - 300, y_position - 5, width - 160, y_position - 5)
        
        c.drawString(150, y_position, date_signature)
        c.line(50, y_position - 5, 140, y_position - 5)
        
        # تذييل الصفحة
        c.setFont(arabic_font, 8)
        c.setFillColor(colors.grey)
        footer_text = process_arabic_text(f"تم الإنشاء بواسطة نظام نُظم لإدارة المركبات - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        footer_width = c.stringWidth(footer_text, arabic_font, 8)
        c.drawString((width - footer_width)/2, 30, footer_text)
        
        # إطار الصفحة
        c.setStrokeColor(primary_color)
        c.setLineWidth(2)
        c.rect(30, 20, width - 60, height - 40)

        _draw_attachment_pages(c, handover_data, width, height, primary_color)
        
        c.save()
        buffer.seek(0)
        
        print("Arabic handover PDF generated successfully!")
        return buffer
        
    except Exception as e:
        print(f"Error generating Arabic handover PDF: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # إنشاء PDF بديل في حالة الخطأ
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        
        c.setFont('Helvetica', 16)
        c.drawString(100, height - 100, "Vehicle Handover Report")
        c.drawString(100, height - 130, f"Vehicle: {handover_data.vehicle.plate_number}")
        c.drawString(100, height - 160, f"Person: {handover_data.person_name or 'N/A'}")
        c.drawString(100, height - 190, f"Date: {handover_data.handover_date}")
        c.drawString(100, height - 220, f"Type: {handover_data.handover_type}")
        
        c.save()
        buffer.seek(0)
        return buffer

# دالة للتوافق مع النظام القديم
def create_vehicle_checklist_pdf(handover_data, vehicle_data=None):
    """دالة للتوافق مع النظام القديم"""
    return create_vehicle_handover_pdf(handover_data)