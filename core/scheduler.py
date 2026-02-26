import atexit
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta, timezone
from sqlalchemy import update

logger = logging.getLogger(__name__)

def cleanup_old_location_data(app):
    """حذف مواقع الموظفين الأقدم من 14 ساعة"""
    with app.app_context():
        from models import EmployeeLocation
        from core.extensions import db
        
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=14)
            old_locations = EmployeeLocation.query.filter(
                EmployeeLocation.recorded_at < cutoff_time
            ).delete()
            
            db.session.commit()
            
            if old_locations > 0:
                logger.info(f"تم حذف {old_locations} موقع قديم")
            
            return old_locations
        except Exception as e:
            logger.error(f"خطأ في حذف البيانات القديمة: {str(e)}")
            db.session.rollback()
            return 0

def cleanup_old_geofence_events(app):
    """حذف جلسات وأحداث الدوائر الجغرافية الأقدم من 24 ساعة"""
    with app.app_context():
        from models import GeofenceEvent, GeofenceSession
        from core.extensions import db
        
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
            
            # أولاً: فصل الـ FK constraints - تعيين entry_event_id و exit_event_id إلى NULL
            db.session.execute(
                update(GeofenceSession).where(
                    GeofenceSession.entry_time < cutoff_time
                ).values(entry_event_id=None, exit_event_id=None)
            )
            
            # حذف جميع الـ sessions التي دخلت قبل 24 ساعة
            old_sessions = db.session.query(GeofenceSession).filter(
                GeofenceSession.entry_time < cutoff_time
            ).delete()
            
            # حذف الأحداث القديمة
            old_events = db.session.query(GeofenceEvent).filter(
                GeofenceEvent.recorded_at < cutoff_time
            ).delete()
            
            db.session.commit()
            
            if old_events > 0 or old_sessions > 0:
                logger.info(f"✅ حذف {old_sessions} جلسة و {old_events} حدث دائرة جغرافية قديمة (> 24 ساعة)")
            
            return old_events + old_sessions
        except Exception as e:
            logger.error(f"خطأ في حذف أحداث الدوائر الجغرافية: {str(e)}")
            db.session.rollback()
            return 0

def init_scheduler(app):
    """تهيئة وتشغيل المجدول لمهام التنظيف الخلفية"""
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=lambda: cleanup_old_location_data(app), trigger="interval", hours=6)
    scheduler.add_job(func=lambda: cleanup_old_geofence_events(app), trigger="interval", hours=24)
    scheduler.start()
    
    # تشغيل التنظيف عند بدء التطبيق
    cleanup_old_location_data(app)
    cleanup_old_geofence_events(app)
    
    # إيقاف المجدول عند إيقاف التطبيق
    atexit.register(lambda: scheduler.shutdown())
