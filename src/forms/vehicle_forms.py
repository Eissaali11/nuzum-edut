"""
نماذج وحدة السيارات
"""

from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, DateField, BooleanField, DecimalField, HiddenField, IntegerField, SubmitField, FileField
from wtforms.validators import DataRequired, Optional, NumberRange, URL, Length
from datetime import date


# قائمة الحالات لاستخدامها في نموذج التعديل (يُملأ من application.vehicles.vehicle_service)
VEHICLE_EDIT_STATUS_CHOICES = [
    ("available", "متاحة"),
    ("rented", "مؤجرة"),
    ("in_project", "نشطة مع سائق"),
    ("in_workshop", "في الورشة صيانة"),
    ("accident", "في الورشة حادث"),
    ("out_of_service", "خارج الخدمة"),
]


class VehicleEditForm(FlaskForm):
    """نموذج تعديل بيانات المركبة (يُستخدم مع form.validate_on_submit() في مسار التعديل)."""
    plate_number = StringField("رقم اللوحة", validators=[DataRequired(), Length(max=20)])
    make = StringField("الشركة المصنعة", validators=[DataRequired(), Length(max=50)])
    model = StringField("الموديل", validators=[DataRequired(), Length(max=50)])
    year = IntegerField("سنة الصنع", validators=[DataRequired(), NumberRange(min=1990, max=2030)])
    color = StringField("اللون", validators=[DataRequired(), Length(max=30)])
    status = SelectField("الحالة", choices=VEHICLE_EDIT_STATUS_CHOICES, validators=[DataRequired()])
    type_of_car = StringField("نوع السيارة", validators=[Optional(), Length(max=100)])
    driver_name = StringField("اسم السائق", validators=[Optional(), Length(max=100)])
    project = StringField("المشروع", validators=[Optional(), Length(max=100)])
    owned_by = StringField("الشركة المالكة", validators=[Optional(), Length(max=100)])
    region = StringField("المنطقة", validators=[Optional(), Length(max=100)])
    notes = TextAreaField("ملاحظات", validators=[Optional()])
    license_image = FileField("صورة الرخصة", validators=[Optional()])


class VehicleCreateForm(FlaskForm):
    """نموذج إضافة سيارة جديدة (يُستخدم مع form.validate_on_submit() في مسار create)."""
    plate_number = StringField("رقم اللوحة", validators=[DataRequired(), Length(max=20)])
    make = StringField("الشركة المصنعة", validators=[DataRequired(), Length(max=50)])
    model = StringField("الموديل", validators=[DataRequired(), Length(max=50)])
    year = IntegerField("سنة الصنع", validators=[DataRequired(), NumberRange(min=1990, max=2030)])
    color = StringField("اللون", validators=[DataRequired(), Length(max=30)])
    status = SelectField("الحالة", choices=VEHICLE_EDIT_STATUS_CHOICES, validators=[DataRequired()])
    type_of_car = StringField("نوع السيارة", validators=[Optional(), Length(max=100)])
    driver_name = StringField("اسم السائق", validators=[Optional(), Length(max=100)])
    project = StringField("المشروع", validators=[Optional(), Length(max=100)])
    owned_by = StringField("الشركة المالكة", validators=[Optional(), Length(max=100)])
    region = StringField("المنطقة", validators=[Optional(), Length(max=100)])
    notes = TextAreaField("ملاحظات", validators=[Optional()])
    license_image = FileField("صورة الرخصة", validators=[Optional()])


class VehicleDocumentsForm(FlaskForm):
    """نموذج تحديث تواريخ انتهاء وثائق السيارة الهامة"""
    vehicle_id = HiddenField('معرف السيارة')
    authorization_expiry_date = DateField('تاريخ انتهاء التفويض', validators=[Optional()])
    registration_expiry_date = DateField('تاريخ انتهاء استمارة السيارة', validators=[Optional()])
    inspection_expiry_date = DateField('تاريخ انتهاء الفحص الدوري', validators=[Optional()])
    submit = SubmitField('حفظ')


class VehicleAccidentForm(FlaskForm):
    """نموذج إضافة وتعديل سجل حادث مروري"""
    vehicle_id = HiddenField('معرف السيارة')
    accident_date = DateField('تاريخ الحادث', validators=[DataRequired()], default=date.today)
    driver_name = StringField('اسم السائق', validators=[DataRequired(), Length(min=2, max=100)])
    accident_status = SelectField('حالة الحادث', choices=[
        ('قيد المعالجة', 'قيد المعالجة'),
        ('مغلق', 'مغلق'),
        ('معلق', 'معلق'),
        ('في التأمين', 'في التأمين')
    ], default='قيد المعالجة')
    vehicle_condition = StringField('حالة السيارة', validators=[Optional(), Length(max=100)])
    deduction_amount = DecimalField('مبلغ الخصم على السائق', validators=[Optional(), NumberRange(min=0)], default=0.0)
    deduction_status = BooleanField('تم الخصم')
    liability_percentage = SelectField('نسبة تحمل السائق', choices=[
        ('0', 'لا يوجد تحمل (0%)'),
        ('25', 'تحمل جزئي (25%)'),
        ('50', 'تحمل متوسط (50%)'),
        ('75', 'تحمل كبير (75%)'),
        ('100', 'تحمل كامل (100%)')
    ], default='0', coerce=int)
    accident_file_link = StringField('رابط ملف الحادث', validators=[Optional()])
    location = StringField('موقع الحادث', validators=[Optional(), Length(max=255)])
    police_report = BooleanField('تم عمل محضر شرطة')
    insurance_claim = BooleanField('تم رفع مطالبة للتأمين')
    description = TextAreaField('وصف الحادث', validators=[Optional()])
    notes = TextAreaField('ملاحظات إضافية', validators=[Optional()])
    submit = SubmitField('حفظ')