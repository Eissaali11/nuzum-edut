"""Employee-related message translations for UI display"""


def translate_service_message(result):
    """Translate service result message to Arabic for user display"""
    message = result.message
    data = result.data or {}
    
    if message == "employee.created":
        return "تم إنشاء الموظف بنجاح"
    if message == "employee.updated":
        return "تم تحديث بيانات الموظف وأقسامه بنجاح."
    if message == "employee.deleted":
        return "تم حذف الموظف بنجاح"
    if message == "employee.duplicate_employee_id":
        employee_id = data.get("employee_id")
        if employee_id:
            return f"رقم الموظف '{employee_id}' مستخدم بالفعل."
        return "هذه المعلومات مسجلة مسبقاً: رقم الموظف موجود بالفعل في النظام"
    if message == "employee.duplicate_national_id":
        national_id = data.get("national_id")
        if national_id:
            return f"الرقم الوطني '{national_id}' مستخدم بالفعل."
        return "هذه المعلومات مسجلة مسبقاً: رقم الهوية موجود بالفعل في النظام"
    if message == "employee.duplicate":
        return "هذه المعلومات مسجلة مسبقاً، لا يمكن تكرار بيانات الموظفين"
    if message == "employee.pending_requests":
        count = data.get("pending_count", 0)
        return f"لا يمكن حذف الموظف لديه {count} طلب(ات) معلقة. يرجى حذف الطلبات أولاً"
    if message == "employee.create_failed":
        detail = data.get("detail", "")
        return f"حدث خطأ: {detail}"
    if message == "employee.update_failed":
        detail = data.get("detail", "")
        return (
            "حدث خطأ غير متوقع أثناء عملية التحديث. يرجى المحاولة مرة أخرى. "
            f"Error updating employee (ID: {data.get('employee_id', '')}): {detail}"
        )
    if message == "employee.delete_failed":
        detail = data.get("detail", "")
        return f"حدث خطأ أثناء حذف الموظف: {detail}"
    if message == "employee.not_found":
        return "الموظف غير موجود"
    if message == "employee.invalid_status":
        return "حالة غير صالحة"
    if message == "employee.status_update_failed":
        detail = data.get("detail", "")
        return f"حدث خطأ أثناء تحديث حالة الموظف: {detail}"
    if message == "employee.status_updated":
        status_names = data.get(
            "status_names",
            {"active": "نشط", "inactive": "غير نشط", "on_leave": "في إجازة"},
        )
        new_status = data.get("new_status")
        return f"تم تحديث حالة الموظف إلى {status_names.get(new_status, new_status)} بنجاح"
    if message == "employee.iban_updated":
        return "تم حفظ بيانات الإيبان البنكي بنجاح"
    if message == "employee.iban_image_deleted":
        return "تم حذف صورة الإيبان بنجاح"
    if message == "employee.housing_image_deleted":
        return "تم حذف صورة السكن بنجاح"
    
    return message
