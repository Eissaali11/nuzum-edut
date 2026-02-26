"""
خدمة تصدير المركبات — توليد ملفات PDF و Excel.
تُستخدم من: مسارات التصدير في presentation/web/vehicle_routes.py.
لا استخدام لـ request أو Flask globals؛ المعاملات تُمرَّر من طبقة العرض.
"""
import io
import os
from datetime import datetime
from typing import Optional, Tuple

import pandas as pd

from src.modules.vehicles.domain.models import Vehicle, VehicleProject, VehicleRental, VehicleWorkshop
from src.domain.employees.models import Employee
from src.utils.excel import generate_vehicles_excel
from src.utils.vehicle_helpers import log_audit
from src.utils.vehicles_export import export_vehicle_excel, export_vehicle_pdf


def build_expired_documents_excel() -> Tuple[io.BytesIO, str, str]:
    """
    بناء ملف Excel للوثائق المنتهية (استمارة، فحص دوري، تفويض) مع ملخص ومخطط.
    Returns:
        (buffer, filename, mimetype)
    """
    today = datetime.now().date()

    expired_registration = Vehicle.query.filter(
        Vehicle.registration_expiry_date.isnot(None),
        Vehicle.registration_expiry_date < today,
    ).order_by(Vehicle.registration_expiry_date).all()

    expired_inspection = Vehicle.query.filter(
        Vehicle.inspection_expiry_date.isnot(None),
        Vehicle.inspection_expiry_date < today,
    ).order_by(Vehicle.inspection_expiry_date).all()

    expired_authorization = Vehicle.query.filter(
        Vehicle.authorization_expiry_date.isnot(None),
        Vehicle.authorization_expiry_date < today,
    ).order_by(Vehicle.authorization_expiry_date).all()

    registration_data = [
        {
            "رقم اللوحة": v.plate_number,
            "الشركة المصنعة": v.make,
            "الموديل": v.model,
            "السنة": v.year,
            "تاريخ انتهاء الاستمارة": v.registration_expiry_date.strftime("%Y-%m-%d"),
            "عدد أيام الانتهاء": (today - v.registration_expiry_date).days,
            "نوع الوثيقة": "استمارة السيارة",
        }
        for v in expired_registration
    ]
    inspection_data = [
        {
            "رقم اللوحة": v.plate_number,
            "الشركة المصنعة": v.make,
            "الموديل": v.model,
            "السنة": v.year,
            "تاريخ انتهاء الفحص": v.inspection_expiry_date.strftime("%Y-%m-%d"),
            "عدد أيام الانتهاء": (today - v.inspection_expiry_date).days,
            "نوع الوثيقة": "الفحص الدوري",
        }
        for v in expired_inspection
    ]
    authorization_data = [
        {
            "رقم اللوحة": v.plate_number,
            "الشركة المصنعة": v.make,
            "الموديل": v.model,
            "السنة": v.year,
            "تاريخ انتهاء التفويض": v.authorization_expiry_date.strftime("%Y-%m-%d"),
            "عدد أيام الانتهاء": (today - v.authorization_expiry_date).days,
            "نوع الوثيقة": "التفويض",
        }
        for v in expired_authorization
    ]

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        if registration_data:
            reg_df = pd.DataFrame(registration_data)
            reg_df.to_excel(writer, sheet_name="استمارات منتهية", index=False)
            workbook = writer.book
            worksheet = writer.sheets["استمارات منتهية"]
            header_format = workbook.add_format(
                {"bold": True, "text_wrap": True, "valign": "top", "fg_color": "#FFD7D7", "border": 1, "align": "center"}
            )
            for col_num, value in enumerate(reg_df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                worksheet.set_column(col_num, col_num, 18)
            data_format = workbook.add_format({"border": 1, "align": "center"})
            for row in range(1, len(reg_df) + 1):
                for col in range(len(reg_df.columns)):
                    worksheet.write(row, col, reg_df.iloc[row - 1, col], data_format)
            days_col = reg_df.columns.get_loc("عدد أيام الانتهاء")
            days_format = workbook.add_format({"border": 1, "align": "center", "fg_color": "#FFCCCC"})
            for row in range(1, len(reg_df) + 1):
                worksheet.write(row, days_col, reg_df.iloc[row - 1, days_col], days_format)

        if inspection_data:
            insp_df = pd.DataFrame(inspection_data)
            insp_df.to_excel(writer, sheet_name="فحص دوري منتهي", index=False)
            workbook = writer.book
            worksheet = writer.sheets["فحص دوري منتهي"]
            header_format = workbook.add_format(
                {"bold": True, "text_wrap": True, "valign": "top", "fg_color": "#D7E4BC", "border": 1, "align": "center"}
            )
            for col_num, value in enumerate(insp_df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                worksheet.set_column(col_num, col_num, 18)
            data_format = workbook.add_format({"border": 1, "align": "center"})
            for row in range(1, len(insp_df) + 1):
                for col in range(len(insp_df.columns)):
                    worksheet.write(row, col, insp_df.iloc[row - 1, col], data_format)
            days_col = insp_df.columns.get_loc("عدد أيام الانتهاء")
            days_format = workbook.add_format({"border": 1, "align": "center", "fg_color": "#E2EFDA"})
            for row in range(1, len(insp_df) + 1):
                worksheet.write(row, days_col, insp_df.iloc[row - 1, days_col], days_format)

        if authorization_data:
            auth_df = pd.DataFrame(authorization_data)
            auth_df.to_excel(writer, sheet_name="تفويض منتهي", index=False)
            workbook = writer.book
            worksheet = writer.sheets["تفويض منتهي"]
            header_format = workbook.add_format(
                {"bold": True, "text_wrap": True, "valign": "top", "fg_color": "#B4C6E7", "border": 1, "align": "center"}
            )
            for col_num, value in enumerate(auth_df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                worksheet.set_column(col_num, col_num, 18)
            data_format = workbook.add_format({"border": 1, "align": "center"})
            for row in range(1, len(auth_df) + 1):
                for col in range(len(auth_df.columns)):
                    worksheet.write(row, col, auth_df.iloc[row - 1, col], data_format)
            days_col = auth_df.columns.get_loc("عدد أيام الانتهاء")
            days_format = workbook.add_format({"border": 1, "align": "center", "fg_color": "#DDEBF7"})
            for row in range(1, len(auth_df) + 1):
                worksheet.write(row, days_col, auth_df.iloc[row - 1, days_col], days_format)

        summary_data = {
            "نوع الوثيقة": ["الاستمارة", "الفحص الدوري", "التفويض", "الإجمالي"],
            "عدد الوثائق المنتهية": [
                len(expired_registration),
                len(expired_inspection),
                len(expired_authorization),
                len(expired_registration) + len(expired_inspection) + len(expired_authorization),
            ],
        }
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name="ملخص", index=False)
        workbook = writer.book
        worksheet = writer.sheets["ملخص"]
        header_format = workbook.add_format(
            {
                "bold": True,
                "text_wrap": True,
                "valign": "top",
                "fg_color": "#BDD7EE",
                "border": 1,
                "align": "center",
                "font_size": 12,
            }
        )
        for col_num, value in enumerate(summary_df.columns.values):
            worksheet.write(0, col_num, value, header_format)
            worksheet.set_column(col_num, col_num, 25)
        reg_format = workbook.add_format({"border": 1, "align": "center", "fg_color": "#FFD7D7"})
        insp_format = workbook.add_format({"border": 1, "align": "center", "fg_color": "#D7E4BC"})
        auth_format = workbook.add_format({"border": 1, "align": "center", "fg_color": "#B4C6E7"})
        total_format = workbook.add_format(
            {"border": 1, "align": "center", "bold": True, "fg_color": "#FFC000", "font_size": 12}
        )
        worksheet.write(1, 0, summary_df.iloc[0, 0], reg_format)
        worksheet.write(1, 1, summary_df.iloc[0, 1], reg_format)
        worksheet.write(2, 0, summary_df.iloc[1, 0], insp_format)
        worksheet.write(2, 1, summary_df.iloc[1, 1], insp_format)
        worksheet.write(3, 0, summary_df.iloc[2, 0], auth_format)
        worksheet.write(3, 1, summary_df.iloc[2, 1], auth_format)
        worksheet.write(4, 0, summary_df.iloc[3, 0], total_format)
        worksheet.write(4, 1, summary_df.iloc[3, 1], total_format)
        chart = workbook.add_chart({"type": "pie"})
        chart.add_series(
            {
                "name": "توزيع الوثائق المنتهية",
                "categories": ["ملخص", 1, 0, 3, 0],
                "values": ["ملخص", 1, 1, 3, 1],
                "points": [
                    {"fill": {"color": "#FFD7D7"}},
                    {"fill": {"color": "#D7E4BC"}},
                    {"fill": {"color": "#B4C6E7"}},
                ],
                "data_labels": {"value": True, "category": True, "percentage": True},
            }
        )
        chart.set_title({"name": "توزيع الوثائق المنتهية"})
        chart.set_style(10)
        chart.set_size({"width": 500, "height": 300})
        worksheet.insert_chart("D2", chart)

    output.seek(0)
    filename = f"الوثائق_المنتهية_{datetime.now().strftime('%Y-%m-%d')}.xlsx"
    log_audit("export", "vehicle_documents", 0, "تم تصدير تقرير الوثائق المنتهية للمركبات إلى Excel")
    return output, filename, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def build_vehicles_excel(
    status_filter: str = "",
    make_filter: str = "",
) -> Tuple[io.BytesIO, str, str]:
    """
    بناء ملف Excel لقائمة المركبات مع التصفية حسب الحالة والشركة المصنعة.
    Returns:
        (buffer, filename, mimetype)
    """
    query = Vehicle.query
    if status_filter:
        query = query.filter(Vehicle.status == status_filter)
    if make_filter:
        query = query.filter(Vehicle.make == make_filter)
    vehicles = query.order_by(Vehicle.status, Vehicle.plate_number).all()
    output = io.BytesIO()
    generate_vehicles_excel(vehicles, output)
    output.seek(0)
    filename = f"تقرير_المركبات_{datetime.now().strftime('%Y-%m-%d')}.xlsx"
    return output, filename, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def build_vehicle_pdf(vehicle_id: int) -> Tuple[Optional[io.BytesIO], Optional[str], str]:
    """
    بناء PDF لتفاصيل مركبة واحدة مع ورشة وإيجار.
    Returns:
        (buffer, filename, mimetype) أو (None, None, mimetype) إذا لم تُوجد المركبة.
    """
    vehicle = Vehicle.query.get(vehicle_id)
    if not vehicle:
        return None, None, "application/pdf"
    workshop_records = (
        VehicleWorkshop.query.filter_by(vehicle_id=vehicle_id)
        .order_by(VehicleWorkshop.entry_date.desc())
        .all()
    )
    rental_records = (
        VehicleRental.query.filter_by(vehicle_id=vehicle_id).order_by(VehicleRental.start_date.desc()).all()
    )
    pdf_buffer = export_vehicle_pdf(vehicle, workshop_records, rental_records)
    log_audit("export", "vehicle", vehicle_id, f"تم تصدير بيانات السيارة {vehicle.plate_number} إلى PDF")
    filename = f"vehicle_{vehicle.plate_number}_{datetime.now().strftime('%Y%m%d')}.pdf"
    return pdf_buffer, filename, "application/pdf"


def build_vehicle_excel(vehicle_id: int) -> Tuple[Optional[io.BytesIO], Optional[str], str]:
    """
    بناء Excel لتفاصيل مركبة واحدة مع ورشة وإيجار.
    Returns:
        (buffer, filename, mimetype) أو (None, None, mimetype) إذا لم تُوجد المركبة.
    """
    vehicle = Vehicle.query.get(vehicle_id)
    if not vehicle:
        return None, None, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    workshop_records = (
        VehicleWorkshop.query.filter_by(vehicle_id=vehicle_id)
        .order_by(VehicleWorkshop.entry_date.desc())
        .all()
    )
    rental_records = (
        VehicleRental.query.filter_by(vehicle_id=vehicle_id).order_by(VehicleRental.start_date.desc()).all()
    )
    excel_buffer = export_vehicle_excel(vehicle, workshop_records, rental_records)
    log_audit("export", "vehicle", vehicle_id, f"تم تصدير بيانات السيارة {vehicle.plate_number} إلى Excel")
    filename = f"vehicle_{vehicle.plate_number}_{datetime.now().strftime('%Y%m%d')}.xlsx"
    return excel_buffer, filename, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def build_valid_documents_excel(
    plate_number: str = "",
    vehicle_make: str = "",
) -> Tuple[io.BytesIO, str, str]:
    """
    بناء Excel لحالة الوثائق السارية (الفحص الدوري) مع فلترة اختيارية.
    Returns:
        (buffer, filename, mimetype)
    """
    from sqlalchemy import or_

    today = datetime.now().date()
    query = Vehicle.query
    if plate_number:
        query = query.filter(Vehicle.plate_number.ilike(f"%{plate_number}%"))
    if vehicle_make:
        query = query.filter(
            or_(
                Vehicle.make.ilike(f"%{vehicle_make}%"),
                Vehicle.model.ilike(f"%{vehicle_make}%"),
            )
        )
    all_vehicles = query.all()

    vehicle_data = []
    for vehicle in all_vehicles:
        if vehicle.inspection_expiry_date is None:
            inspection_status = "غير محدد"
            days_info = "-"
        elif vehicle.inspection_expiry_date >= today:
            inspection_status = "ساري"
            days_remaining = (vehicle.inspection_expiry_date - today).days
            days_info = f"{days_remaining} يوم باقي"
        else:
            inspection_status = "منتهي"
            days_expired = (today - vehicle.inspection_expiry_date).days
            days_info = f"{days_expired} يوم منقضي"
        vehicle_data.append(
            {
                "رقم اللوحة": vehicle.plate_number,
                "الشركة المصنعة": vehicle.make,
                "الموديل": vehicle.model,
                "السنة": vehicle.year,
                "تاريخ انتهاء الفحص": vehicle.inspection_expiry_date.strftime("%Y-%m-%d")
                if vehicle.inspection_expiry_date
                else "غير محدد",
                "حالة الفحص الدوري": inspection_status,
                "الأيام المتبقية/المنقضية": days_info,
            }
        )

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        if vehicle_data:
            df = pd.DataFrame(vehicle_data)
            df.to_excel(writer, sheet_name="جميع السيارات", index=False)
            workbook = writer.book
            worksheet = writer.sheets["جميع السيارات"]
            header_format = workbook.add_format(
                {"bold": True, "text_wrap": True, "valign": "top", "fg_color": "#D7E4BC", "border": 1}
            )
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
            worksheet.set_column("A:G", 15)
    output.seek(0)
    filename = f"vehicles_inspection_status_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return output, filename, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def build_vehicles_pdf_english(static_folder: Optional[str] = None) -> Tuple[io.BytesIO, str, str]:
    """
    بناء تقرير PDF إنجليزي لقائمة المركبات (وضع أفقي، شعار، جدول).
    static_folder: مسار مجلد الـ static (للشعار images/logo.png).
    Returns:
        (buffer, filename, mimetype)
    """
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    vehicles = Vehicle.query.all()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=1 * cm,
        leftMargin=1 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    elements = []

    logo_path = None
    if static_folder:
        logo_path = os.path.join(static_folder, "images", "logo.png")
    if not logo_path or not os.path.exists(logo_path):
        logo_path = os.path.join("static", "images", "logo.png") if os.path.exists("static/images/logo.png") else None
    if logo_path and os.path.exists(logo_path):
        try:
            logo = Image(logo_path, width=3 * cm, height=3 * cm)
            elements.append(logo)
            elements.append(Spacer(1, 0.3 * cm))
        except Exception:
            pass

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=24,
        textColor=colors.HexColor("#18B2B0"),
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
    )
    title = Paragraph("<b>NUZUM FLEET MANAGEMENT SYSTEM</b>", title_style)
    elements.append(title)
    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontSize=14,
        textColor=colors.HexColor("#666666"),
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName="Helvetica",
    )
    subtitle = Paragraph(
        f"Vehicles Fleet Report - {datetime.now().strftime('%Y-%m-%d')}",
        subtitle_style,
    )
    elements.append(subtitle)
    elements.append(Spacer(1, 0.5 * cm))

    data = [
        [
            "#",
            "Driver Name",
            "ID Number",
            "EMP",
            "Private Phone",
            "Work Phone",
            "Plate Number",
            "Owned By",
            "Vehicle Type",
            "Project",
            "Location",
            "Start Date",
        ]
    ]
    for idx, vehicle in enumerate(vehicles, start=1):
        driver_name = vehicle.driver_name or ""
        employee_id_num = employee_num = private_num = work_num = ""
        project = vehicle.project or ""
        location = vehicle.region or ""
        start_date = ""
        owner = vehicle.owned_by or ""
        if driver_name:
            driver = Employee.query.filter_by(name=driver_name).first()
            if driver:
                employee_id_num = driver.national_id or ""
                employee_num = driver.employee_id or ""
                private_num = driver.mobilePersonal or ""
                work_num = driver.mobile or ""
        if vehicle.project:
            project_obj = VehicleProject.query.filter_by(project_name=vehicle.project).first()
            if project_obj and project_obj.start_date:
                start_date = project_obj.start_date.strftime("%Y-%m-%d")
        if not owner:
            rental = VehicleRental.query.filter_by(vehicle_id=vehicle.id, is_active=True).first()
            if rental:
                owner = rental.lessor_name or ""
        data.append(
            [
                str(idx),
                (driver_name[:25] if driver_name else ""),
                (employee_id_num[:15] if employee_id_num else ""),
                (employee_num[:10] if employee_num else ""),
                (private_num[:12] if private_num else ""),
                (work_num[:12] if work_num else ""),
                vehicle.plate_number or "",
                (owner[:15] if owner else ""),
                f"{vehicle.make or ''} {vehicle.model or ''}"[:20],
                (project[:15] if project else ""),
                (location[:12] if location else ""),
                start_date,
            ]
        )

    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#18B2B0")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("TOPPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                ("TEXTCOLOR", (0, 1), (-1, -1), colors.black),
                ("ALIGN", (0, 1), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 8),
                ("TOPPADDING", (0, 1), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F2F2")]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BOX", (0, 0), (-1, -1), 2, colors.HexColor("#18B2B0")),
            ]
        )
    )
    elements.append(table)
    elements.append(Spacer(1, 1 * cm))
    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#999999"),
        alignment=TA_CENTER,
        fontName="Helvetica-Oblique",
    )
    footer = Paragraph(
        f"Total Vehicles: {len(vehicles)} | Generated by NUZUM System | https://nuzum.site",
        footer_style,
    )
    elements.append(footer)
    doc.build(elements)
    buffer.seek(0)
    filename = f"NUZUM_Vehicles_Fleet_{datetime.now().strftime('%Y%m%d')}.pdf"
    return buffer, filename, "application/pdf"


def build_vehicle_report_pdf(vehicle_id: int) -> Tuple[Optional[io.BytesIO], Optional[str], str]:
    """
    بناء تقرير شامل للسيارة (PDF) — يستخدم simple_pdf_generator.
    Returns:
        (buffer, filename, mimetype) أو (None, None, mimetype) إذا لم تُوجد المركبة.
    """
    from types import SimpleNamespace
    from src.utils.simple_pdf_generator import create_vehicle_handover_pdf as generate_complete_vehicle_report

    vehicle = Vehicle.query.get(vehicle_id)
    if not vehicle:
        return None, None, "application/pdf"
    rental = VehicleRental.query.filter_by(vehicle_id=vehicle_id, is_active=True).first()
    workshop_records = (
        VehicleWorkshop.query.filter_by(vehicle_id=vehicle_id)
        .order_by(VehicleWorkshop.entry_date.desc())
        .all()
    )
    handover_data = SimpleNamespace(
        vehicle=vehicle,
        rental=rental,
        workshop_records=workshop_records,
        documents=None,
    )
    pdf_bytes = generate_complete_vehicle_report(handover_data)
    buffer = io.BytesIO(pdf_bytes if isinstance(pdf_bytes, bytes) else pdf_bytes.getvalue())
    log_audit("generate_report", "vehicle", vehicle_id, f"تم إنشاء تقرير شامل للسيارة (PDF): {vehicle.plate_number}")
    return buffer, f"تقرير_شامل_{vehicle.plate_number}.pdf", "application/pdf"


def build_vehicle_report_excel(vehicle_id: int) -> Tuple[Optional[io.BytesIO], Optional[str], str]:
    """
    بناء تقرير شامل للسيارة (Excel).
    Returns:
        (buffer, filename, mimetype) أو (None, None, mimetype) إذا لم تُوجد المركبة.
    """
    from src.modules.vehicles.domain.models import VehicleHandover, VehiclePeriodicInspection
    from src.utils.vehicle_excel_report import generate_complete_vehicle_excel_report

    vehicle = Vehicle.query.get(vehicle_id)
    if not vehicle:
        return None, None, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    rental = VehicleRental.query.filter_by(vehicle_id=vehicle_id, is_active=True).first()
    workshop_records = (
        VehicleWorkshop.query.filter_by(vehicle_id=vehicle_id)
        .order_by(VehicleWorkshop.entry_date.desc())
        .all()
    )
    handovers = (
        VehicleHandover.query.filter_by(vehicle_id=vehicle_id)
        .order_by(VehicleHandover.handover_date.desc())
        .all()
    )
    inspections = (
        VehiclePeriodicInspection.query.filter_by(vehicle_id=vehicle_id)
        .order_by(VehiclePeriodicInspection.inspection_date.desc())
        .all()
    )
    excel_bytes = generate_complete_vehicle_excel_report(
        vehicle,
        rental=rental,
        workshop_records=workshop_records,
        documents=None,
        handovers=handovers,
        inspections=inspections,
    )
    buffer = io.BytesIO(excel_bytes)
    buffer.seek(0)
    log_audit("generate_report", "vehicle", vehicle_id, f"تم إنشاء تقرير شامل للسيارة (Excel): {vehicle.plate_number}")
    return buffer, f"تقرير_شامل_{vehicle.plate_number}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def process_import_vehicles(file_stream) -> Tuple[int, int, list]:
    """
    معالجة استيراد مركبات من ملف Excel.
    Returns:
        (success_count, error_count, errors_list)
    """
    from src.core.extensions import db
    from src.utils.audit_logger import log_activity

    import pandas as pd

    required_columns = ["رقم اللوحة", "الشركة المصنعة", "الموديل", "السنة", "اللون", "نوع السيارة"]
    status_reverse_map = {
        "متاحة": "available",
        "مؤجرة": "rented",
        "في المشروع": "in_project",
        "في الورشة": "in_workshop",
        "حادث": "accident",
    }
    df = pd.read_excel(file_stream)
    missing = [c for c in required_columns if c not in df.columns]
    if missing:
        raise ValueError(f"الأعمدة التالية مفقودة: {', '.join(missing)}")
    success_count = 0
    error_count = 0
    errors = []
    for index, row in df.iterrows():
        try:
            if pd.isna(row["رقم اللوحة"]) or str(row["رقم اللوحة"]).strip() == "":
                error_count += 1
                errors.append(f"الصف {index + 2}: رقم اللوحة مطلوب")
                continue
            plate_number = str(row["رقم اللوحة"]).strip()
            if Vehicle.query.filter_by(plate_number=plate_number).first():
                error_count += 1
                errors.append(f"الصف {index + 2}: السيارة برقم اللوحة {plate_number} موجودة مسبقاً")
                continue
            vehicle = Vehicle()
            vehicle.plate_number = plate_number
            vehicle.make = str(row["الشركة المصنعة"]).strip() if not pd.isna(row["الشركة المصنعة"]) else ""
            vehicle.model = str(row["الموديل"]).strip() if not pd.isna(row["الموديل"]) else ""
            vehicle.color = str(row["اللون"]).strip() if not pd.isna(row["اللون"]) else ""
            vehicle.type_of_car = (
                str(row["نوع السيارة"]).strip() if not pd.isna(row["نوع السيارة"]) else "سيارة عادية"
            )
            if not pd.isna(row["السنة"]):
                try:
                    vehicle.year = int(float(row["السنة"]))
                except (ValueError, TypeError):
                    vehicle.year = None
            else:
                vehicle.year = None
            if "الحالة" in df.columns and not pd.isna(row["الحالة"]):
                vehicle.status = status_reverse_map.get(str(row["الحالة"]).strip(), "available")
            else:
                vehicle.status = "available"
            if "ملاحظات" in df.columns and not pd.isna(row["ملاحظات"]):
                vehicle.notes = str(row["ملاحظات"]).strip()
            vehicle.created_at = datetime.now()
            vehicle.updated_at = datetime.now()
            db.session.add(vehicle)
            success_count += 1
        except Exception as e:
            error_count += 1
            errors.append(f"الصف {index + 2}: {str(e)}")
    if success_count > 0:
        db.session.commit()
        log_activity(
            action="استيراد السيارات من ملف Excel",
            entity_type="Vehicle",
            details=f"تم استيراد {success_count} سيارة بنجاح، {error_count} خطأ",
        )
    return success_count, error_count, errors
