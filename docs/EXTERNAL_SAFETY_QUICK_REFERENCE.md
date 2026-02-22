# External Safety Service - Quick Reference

## 🎯 Service Methods Cheat Sheet

### 📊 Data Retrieval

```python
from services.external_safety_service import ExternalSafetyService

# Get current drivers with email
drivers = ExternalSafetyService.get_all_current_drivers_with_email()
# Returns: {vehicle_id: {'driver_name': str, 'email': str}}

# Get current drivers (names only)
drivers = ExternalSafetyService.get_all_current_drivers()
# Returns: {vehicle_id: driver_name}

# Get checks with filters
checks = ExternalSafetyService.get_safety_checks_with_filters({
    'status': 'pending',
    'vehicle_id': 123,
    'start_date': datetime(2024, 1, 1),
    'end_date': datetime(2024, 12, 31),
    'driver_name': 'أحمد'
})

# Get specific check
check = ExternalSafetyService.get_safety_check_by_id(456)

# Verify employee
result = ExternalSafetyService.verify_employee_by_national_id('1234567890')
# Returns: {'exists': bool, 'employee': Employee|None, 'name': str|None}
```

### 🖼️ Image Handling

```python
# Check if file is allowed
if ExternalSafetyService.allowed_file('photo.jpg'):
    # Process...

# Compress image
success = ExternalSafetyService.compress_image('/path/to/image.jpg', max_size=1200, quality=85)

# Process uploaded files (from Flask request.files)
result = ExternalSafetyService.process_uploaded_images(request.files.getlist('images'), check_id=123)
# Returns: {'success': bool, 'uploaded_count': int, 'errors': list}

# Delete images
result = ExternalSafetyService.delete_safety_check_images(check_id=123, image_ids=[1, 2, 3])
# Returns: {'success': bool, 'deleted_count': int, 'message': str}
```

### 🔔 Notifications

```python
# Create in-app notification
ExternalSafetyService.create_safety_check_notification(
    user_id=1,
    vehicle_plate='ABC-1234',
    supervisor_name='أحمد',
    check_status='pending',
    check_id=123
)

# Create review notification
ExternalSafetyService.create_safety_check_review_notification(
    user_id=1,
    vehicle_plate='ABC-1234',
    action='approved',  # or 'rejected'
    reviewer_name='محمد',
    check_id=123
)

# Send email to supervisor
result = ExternalSafetyService.send_supervisor_notification_email(safety_check)
# Returns: {'success': bool, 'message': str}

# Send WhatsApp
result = ExternalSafetyService.send_whatsapp_notification(
    phone_number='+966xxxxxxxxx',
    vehicle_plate='ABC-1234',
    check_url='https://...'
)
# Returns: {'success': bool, 'message': str}
```

### ✏️ CRUD Operations

```python
# Create check
result = ExternalSafetyService.create_safety_check(
    data={
        'vehicle_id': 1,
        'vehicle_plate_number': 'ABC-1234',
        'driver_name': 'أحمد محمد',
        'driver_national_id': '1234567890',
        'driver_department': 'النقل',
        'driver_city': 'الرياض',
        'tires_ok': True,
        'lights_ok': True,
        'mirrors_ok': True,
        'body_ok': True,
        'cleanliness_ok': True,
        'notes': 'ملاحظات',
        'latitude': 24.7136,
        'longitude': 46.6753
    },
    current_user_id=1
)
# Returns: {'success': bool, 'check': Check, 'message': str}

# Update check
result = ExternalSafetyService.update_safety_check(
    check_id=123,
    data={'notes': 'ملاحظات محدثة', 'tires_ok': False},
    current_user_id=1
)

# Approve check
result = ExternalSafetyService.approve_safety_check(
    check_id=123,
    reviewer_id=1,
    reviewer_name='محمد'
)

# Reject check
result = ExternalSafetyService.reject_safety_check(
    check_id=123,
    reviewer_id=1,
    reviewer_name='محمد',
    rejection_reason='الصور غير واضحة'
)

# Delete check
result = ExternalSafetyService.delete_safety_check(check_id=123, user_id=1)

# Bulk delete
result = ExternalSafetyService.bulk_delete_safety_checks(
    check_ids=[1, 2, 3],
    user_id=1
)
# Returns: {'success': bool, 'deleted_count': int, 'message': str}
```

### ☁️ Google Drive Integration

```python
result = ExternalSafetyService.upload_to_google_drive(check_id=123, user_id=1)
# Returns: {'success': bool, 'drive_url': str|None, 'message': str}
```

### 📈 Statistics

```python
stats = ExternalSafetyService.get_safety_check_statistics(
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 12, 31)
)
# Returns: {
#     'total_checks': int,
#     'pending': int,
#     'approved': int,
#     'rejected': int,
#     'approval_rate': float
# }
```

---

## 🌐 Web Routes (Controller)

```python
# Import blueprint
from routes.external_safety_refactored import external_safety_bp

# Register in app.py
app.register_blueprint(external_safety_bp, url_prefix='/external-safety')
```

### Public Routes
- `GET/POST /external-safety-check/<vehicle_id>` - نموذج الفحص
- `GET /success/<check_id>` - صفحة النجاح
- `GET /status/<check_id>` - API: حالة الفحص
- `GET /api/verify-employee/<national_id>` - API: التحقق من موظف

### Admin Routes
- `GET /admin/external-safety-checks` - قائمة الفحوصات
- `GET /admin/external-safety-check/<check_id>` - عرض فحص
- `POST /admin/external-safety-check/<check_id>/approve` - موافقة
- `GET/POST /admin/external-safety-check/<check_id>/reject` - رفض
- `GET/POST /admin/external-safety-check/<check_id>/edit` - تعديل
- `GET/POST /admin/external-safety-check/<check_id>/delete` - حذف
- `POST /admin/bulk-delete-safety-checks` - حذف جماعي
- `POST /admin/external-safety-check/<check_id>/delete-images` - حذف صور
- `POST /admin/external-safety-check/<check_id>/upload-file` - رفع ملف
- `POST /admin/external-safety-check/<check_id>/upload-to-drive` - رفع لـ Drive

### Share & Export
- `GET /` - الصفحة الرئيسية (redirect to share-links)
- `GET /share-links` - روابط المشاركة
- `GET /share-links/export-excel` - تصدير Excel

### Testing
- `GET/POST /test-notifications` - اختبار الإشعارات

---

## 🔌 API Routes (RESTful)

```python
# Import blueprint
from routes.api_external_safety_v2 import api_external_safety_bp

# Register in app.py
app.register_blueprint(api_external_safety_bp)  # Already has /api/v2 prefix
```

### Authentication
```python
# In request headers:
# Cookie: session=...  (for Flask-Login)
# Or Authorization: Bearer <JWT_TOKEN>  (future)
```

### Safety Checks CRUD
```bash
# Create
POST /api/v2/safety-checks
Body: {vehicle_id, driver_name, driver_national_id, ...}

# List (with filters)
GET /api/v2/safety-checks?status=pending&vehicle_id=1&start_date=2024-01-01

# Get
GET /api/v2/safety-checks/123

# Update
PUT /api/v2/safety-checks/123
Body: {notes: "...", tires_ok: true}

# Delete
DELETE /api/v2/safety-checks/123
```

### Check Actions
```bash
# Approve
POST /api/v2/safety-checks/123/approve
Body: {notes: "ملاحظات اختيارية"}

# Reject
POST /api/v2/safety-checks/123/reject
Body: {rejection_reason: "السبب"}

# Upload images
POST /api/v2/safety-checks/123/images
Content-Type: multipart/form-data
Files: images[]

# Delete images
DELETE /api/v2/safety-checks/123/images
Body: {image_ids: [1, 2, 3]}
```

### Utilities
```bash
# List vehicles
GET /api/v2/vehicles?status=active&make=Toyota&search=ABC

# Verify employee
GET /api/v2/employees/1234567890

# Send WhatsApp
POST /api/v2/notifications/whatsapp
Body: {phone_number: "+966...", vehicle_plate: "ABC-1234", check_url: "https://..."}

# Send Email
POST /api/v2/notifications/email
Body: {email: "user@example.com", subject: "...", body: "..."}
```

### Statistics
```bash
# Get stats
GET /api/v2/statistics/safety-checks?start_date=2024-01-01&end_date=2024-12-31
```

### Health Check
```bash
GET /api/v2/health
```

---

## 📝 Response Formats

### Success Response
```json
{
  "success": true,
  "data": {
    "check_id": 456,
    "status": "pending"
  },
  "message": "تم إنشاء الفحص بنجاح"
}
```

### Error Response
```json
{
  "success": false,
  "error": "يرجى ملء جميع الحقول المطلوبة",
  "code": "MISSING_FIELDS"
}
```

### List Response
```json
{
  "success": true,
  "data": {
    "checks": [...],
    "total": 100,
    "limit": 50,
    "offset": 0
  }
}
```

---

## 🧪 Testing Examples

### Unit Test (Service)
```python
def test_create_check():
    data = {'vehicle_id': 1, 'driver_name': 'أحمد', ...}
    result = ExternalSafetyService.create_safety_check(data, user_id=1)
    assert result['success'] == True
```

### Integration Test (Route)
```python
def test_approve_route(client):
    response = client.post('/external-safety/admin/external-safety-check/1/approve')
    assert response.status_code == 302
```

### API Test
```python
def test_api_create(client):
    response = client.post('/api/v2/safety-checks', json={...})
    assert response.status_code == 201
    assert response.json['success'] == True
```

---

## 🔒 Security Notes

1. **Authentication:**
   - Web routes: `@login_required`
   - API routes: `@require_api_auth`

2. **Input Validation:**
   - Always validate in controller
   - Service assumes trusted input

3. **Authorization:**
   - Check user roles before approval/rejection
   - Restrict delete operations to admins

---

## 📚 Additional Resources

- Full Guide: [EXTERNAL_SAFETY_REFACTORING_GUIDE.md](EXTERNAL_SAFETY_REFACTORING_GUIDE.md)
- Service Source: [services/external_safety_service.py](../services/external_safety_service.py)
- Controller Source: [routes/external_safety_refactored.py](../routes/external_safety_refactored.py)
- API Source: [routes/api_external_safety_v2.py](../routes/api_external_safety_v2.py)
