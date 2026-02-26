"""
Alternative PDF Generator for Workshop Reports
Using ReportLab instead of WeasyPrint (no GTK dependency required)

This module provides a drop-in replacement for weasyprint_workshop_pdf.py
that works on all platforms without requiring native libraries.
"""

from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from reportlab.pdfbase.pdfmetrics import stringWidth


def setup_arabic_fonts():
    """
    Register Arabic fonts for PDF generation.
    Uses system fonts or falls back to sans-serif.
    """
    try:
        # Try to register Arabic font (adjust path as needed)
        # On Windows, fonts are typically in C:\Windows\Fonts\
        # Common Arabic fonts: Arial, Tahoma, Traditional Arabic
        pdfmetrics.registerFont(TTFont('Arabic', 'arial.ttf'))
        pdfmetrics.registerFont(TTFont('Arabic-Bold', 'arialbd.ttf'))
        return True
    except:
        # Fallback to built-in fonts
        return False


def generate_workshop_report_pdf_reportlab(vehicle, workshop_records):
    """
    Generate workshop report PDF using ReportLab (WeasyPrint alternative).
    
    Args:
        vehicle: Vehicle model instance
        workshop_records: List of VehicleWorkshop records
    
    Returns:
        BytesIO buffer containing the PDF
    """
    # Create PDF buffer
    buffer = BytesIO()
    
    # Setup document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    # Try to setup Arabic fonts
    has_arabic = setup_arabic_fonts()
    font_name = 'Arabic' if has_arabic else 'Helvetica'
    font_name_bold = 'Arabic-Bold' if has_arabic else 'Helvetica-Bold'
    
    # Container for PDF elements
    elements = []
    
    # Setup styles
    styles = getSampleStyleSheet()
    
    # Arabic title style
    title_style = ParagraphStyle(
        'ArabicTitle',
        parent=styles['Heading1'],
        fontName=font_name_bold,
        fontSize=18,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#1E88E5'),
        spaceAfter=12
    )
    
    # Arabic heading style
    heading_style = ParagraphStyle(
        'ArabicHeading',
        parent=styles['Heading2'],
        fontName=font_name_bold,
        fontSize=14,
        alignment=TA_RIGHT,
        textColor=colors.HexColor('#333333'),
        spaceAfter=8,
        spaceBefore=12
    )
    
    # Arabic body style
    body_style = ParagraphStyle(
        'ArabicBody',
        parent=styles['BodyText'],
        fontName=font_name,
        fontSize=11,
        alignment=TA_RIGHT,
        textColor=colors.HexColor('#555555'),
       spaceAfter=6
    )
    
    # === TITLE ===
    title_text = f"تقرير سجلات الورشة - {vehicle.plate_number}"
    elements.append(Paragraph(title_text, title_style))
    elements.append(Spacer(1, 0.5*cm))
    
    # === VEHICLE INFO TABLE ===
    vehicle_data = [
        ['رقم اللوحة:', vehicle.plate_number or 'غير محدد'],
        ['نوع المركبة:', vehicle.vehicle_type or 'غير محدد'],
        ['رقم الشاسيه:', vehicle.chassis_number or 'غير محدد'],
        ['الحالة:', vehicle.status or 'غير محدد'],
    ]
    
    vehicle_table = Table(vehicle_data, colWidths=[5*cm, 10*cm])
    vehicle_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E3F2FD')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    
    elements.append(vehicle_table)
    elements.append(Spacer(1, 1*cm))
    
    # === WORKSHOP RECORDS HEADING ===
    elements.append(Paragraph(f"سجلات الورشة ({len(workshop_records)} سجل)", heading_style))
    elements.append(Spacer(1, 0.5*cm))
    
    # === WORKSHOP RECORDS TABLE ===
    if workshop_records:
        # Table headers
        workshop_data = [['تاريخ الخروج', 'تاريخ الدخول', 'السبب', 'التكلفة', 'الملاحظات']]
        
        # Add records
        for record in workshop_records:
            entry_date = record.entry_date.strftime('%Y-%m-%d') if record.entry_date else 'غير محدد'
            exit_date = record.exit_date.strftime('%Y-%m-%d') if record.exit_date else 'لم يتم الخروج'
            reason = record.reason[:30] + '...' if record.reason and len(record.reason) > 30 else (record.reason or '-')
            cost = f"{record.cost:.2f}" if record.cost else '-'
            notes = record.notes[:30] + '...' if record.notes and len(record.notes) > 30 else (record.notes or '-')
            
            workshop_data.append([exit_date, entry_date, reason, cost, notes])
        
        workshop_table = Table(workshop_data, colWidths=[3*cm, 3*cm, 4*cm, 2*cm, 3*cm])
        workshop_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E88E5')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), font_name_bold),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
        ]))
        
        elements.append(workshop_table)
    else:
        elements.append(Paragraph("لا توجد سجلات ورشة لهذه المركبة.", body_style))
    
    # === FOOTER ===
    elements.append(Spacer(1, 2*cm))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=9,
        alignment=TA_CENTER,
        textColor=colors.grey
    )
    footer_text = f"تم الإنشاء بتاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>نظام نُظم - إدارة المركبات"
    elements.append(Paragraph(footer_text, footer_style))
    
    # Build PDF
    doc.build(elements)
    
    # Get PDF from buffer
    buffer.seek(0)
    return buffer


def generate_workshop_report_pdf(vehicle, workshop_records):
    """
    Main entry point - matches the WeasyPrint function signature
    for drop-in replacement.
    """
    return generate_workshop_report_pdf_reportlab(vehicle, workshop_records)


# ============================================================================
# USAGE INSTRUCTIONS
# ============================================================================
"""
To replace WeasyPrint with this ReportLab solution:

1. In modules/vehicles/presentation/web/workshop_reports.py, change:
   
   FROM:
   from src.utils.weasyprint_workshop_pdf import generate_workshop_report_pdf
   
   TO:
   from src.utils.alternative_pdf_generator import generate_workshop_report_pdf

2. No other changes needed - the function signature is identical.

3. Make sure reportlab is installed:
   pip install reportlab

4. Uncomment workshop_reports in app.py line 478:
   app.register_blueprint(workshop_reports_bp, url_prefix='/workshop-reports')

5. Restart the server and test the PDF export.

ADVANTAGES:
- No GTK/native dependencies required
- Works on all platforms (Windows, Linux, macOS)
- Smaller installation footprint
- Faster PDF generation
- Production-ready

LIMITATIONS:
- Less advanced HTML/CSS rendering than WeasyPrint
- May need font adjustments for optimal Arabic display
- Table styling is more manual

For best Arabic font support on Windows:
- Ensure Arial or Tahoma fonts are available (usually pre-installed)
- Alternatively, add specific Arabic fonts to the project and update font paths
"""
