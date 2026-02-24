"""
دوال مساعدة لإدارة بطاقات SIM
إدارة الأرقام والتخصيصات والواردات
"""

from datetime import datetime
from core.extensions import db
from models import SimCard, ImportedPhoneNumber, Employee, DeviceAssignment, MobileDevice


def get_sim_card_by_phone_number(phone_number):
    """الحصول على بطاقة SIM برقم الهاتف"""
    return SimCard.query.filter_by(phone_number=phone_number).first()


def get_sim_cards_for_employee(employee_id):
    """جلب بطاقات SIM المخصصة لموظف معين"""
    sim_cards = []
    
    assignments = DeviceAssignment.query.filter_by(
        employee_id=employee_id,
        is_active=True
    ).all()
    
    for assignment in assignments:
        if assignment.sim_card_id:
            sim = SimCard.query.get(assignment.sim_card_id)
            if sim:
                sim_cards.append({
                    'sim': sim,
                    'assignment': assignment,
                    'device': assignment.mobile_device
                })
    
    return sim_cards


def get_available_sim_cards(carrier=None, limit=None):
    """جلب بطاقات SIM المتاحة (غير مخصصة)"""
    query = SimCard.query.filter_by(status='available')
    
    if carrier:
        query = query.filter_by(carrier=carrier)
    
    if limit:
        query = query.limit(limit)
    
    return query.all()


def get_sim_cards_statistics():
    """إحصائيات بطاقات SIM"""
    total_sims = SimCard.query.count()
    active_sims = SimCard.query.filter_by(status='active').count()
    available_sims = SimCard.query.filter_by(status='available').count()
    inactive_sims = SimCard.query.filter_by(status='inactive').count()
    
    # عد حسب المشغل
    carriers = {}
    all_sims = SimCard.query.all()
    for sim in all_sims:
        if sim.carrier not in carriers:
            carriers[sim.carrier] = 0
        carriers[sim.carrier] += 1
    
    return {
        'total': total_sims,
        'active': active_sims,
        'available': available_sims,
        'inactive': inactive_sims,
        'by_carrier': carriers
    }


def validate_phone_number(phone_number):
    """التحقق من صحة رقم الهاتف"""
    # إزالة المسافات والشرطات
    phone_number = phone_number.replace(' ', '').replace('-', '')
    
    # التحقق من الطول
    if len(phone_number) < 10:
        return False, 'رقم الهاتف قصير جداً'
    
    if len(phone_number) > 15:
        return False, 'رقم الهاتف طويل جداً'
    
    # التحقق من أنه أرقام فقط
    if not phone_number.isdigit():
        return False, 'رقم الهاتف يجب أن يحتوي على أرقام فقط'
    
    return True, phone_number


def get_device_assignments_for_sim(sim_card_id):
    """جلب جميع التخصيصات لبطاقة SIM"""
    assignments = DeviceAssignment.query.filter_by(
        sim_card_id=sim_card_id
    ).order_by(DeviceAssignment.assigned_date.desc()).all()
    
    return assignments


def get_imported_phone_numbers(limit=100):
    """جلب الأرقام المستوردة"""
    return ImportedPhoneNumber.query.order_by(
        ImportedPhoneNumber.imported_date.desc()
    ).limit(limit).all()


def get_sim_assignment_history(sim_card_id):
    """الحصول على سجل التخصيصات لبطاقة SIM"""
    assignments = DeviceAssignment.query.filter_by(
        sim_card_id=sim_card_id
    ).order_by(DeviceAssignment.assigned_date.desc()).all()
    
    history = []
    for assignment in assignments:
        emp = Employee.query.get(assignment.employee_id)
        device = MobileDevice.query.get(assignment.mobile_device_id)
        
        history.append({
            'date': assignment.assigned_date,
            'employee': emp.name if emp else '-',
            'device': device.device_model if device else '-',
            'status': 'نشط' if assignment.is_active else 'ملغي',
            'unassigned_date': assignment.unassigned_date
        })
    
    return history


def check_sim_duplicate(phone_number, exclude_id=None):
    """فحص وجود رقم هاتف مكرر"""
    query = SimCard.query.filter_by(phone_number=phone_number)
    
    if exclude_id:
        query = query.filter(SimCard.id != exclude_id)
    
    return query.first() is not None


def get_sim_cards_needing_renewal():
    """جلب بطاقات SIM التي تحتاج لتجديد الاشتراك"""
    from datetime import date, timedelta
    
    today = date.today()
    renewal_date = today + timedelta(days=30)  # في غضون 30 يوم
    
    sims_needing_renewal = SimCard.query.filter(
        SimCard.status.in_(['active', 'available']),
        SimCard.renewal_date != None,
        SimCard.renewal_date <= renewal_date,
        SimCard.renewal_date >= today
    ).all()
    
    return sims_needing_renewal
