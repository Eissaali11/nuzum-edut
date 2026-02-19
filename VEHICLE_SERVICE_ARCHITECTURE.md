# Vehicle Service Layer Architecture

## 🏛️ Clean Architecture Pattern Applied

```
┌─────────────────────────────────────────────────────────────┐
│                     PRESENTATION LAYER                       │
│  modules/vehicles/presentation/web/vehicle_routes.py         │
│                                                               │
│  ✅ Handles HTTP requests/responses                          │
│  ✅ Form validation (WTForms)                                │
│  ✅ Template rendering                                       │
│  ✅ Flash messages & redirects                               │
│  ✅ No database queries                                      │
│  ✅ No business logic                                        │
└────────────────────┬────────────────────────────────────────┘
                     │ Delegates to
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   APPLICATION LAYER                          │
│  modules/vehicles/application/vehicle_management_service.py  │
│                                                               │
│  ✅ CRUD operations                                          │
│  ✅ Business rules & validation                              │
│  ✅ Database queries (SQLAlchemy)                            │
│  ✅ File handling                                            │
│  ✅ Audit logging                                            │
│  ✅ Transaction management                                   │
└────────────────────┬────────────────────────────────────────┘
                     │ Uses
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                      DOMAIN LAYER                            │
│  modules/vehicles/domain/models.py                           │
│                                                               │
│  ✅ Vehicle model                                            │
│  ✅ VehicleHandover model                                    │
│  ✅ VehicleWorkshop model                                    │
│  ✅ Relationships & constraints                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Service Methods Inventory

### **Query Abstraction Layer**
```python
# Single Record Retrieval
get_vehicle_or_404(vehicle_id: int) -> Vehicle
    """Fetch vehicle by ID or raise 404"""

# Collection Retrieval
get_active_users() -> List[User]
    """Fetch all active users (is_active=True)"""

get_all_departments() -> List[Department]
    """Fetch all departments"""

get_distinct_projects() -> List[str]
    """Fetch unique project names from vehicles"""
```

### **CRUD Operations**
```python
# Create
create_vehicle_record(
    form_data: Dict[str, Any],
    files: Optional[Dict[str, Any]],
    upload_base_path: Optional[str]
) -> Tuple[bool, str, Optional[int]]
    """
    Create new vehicle record with:
    - Plate number validation
    - Duplicate check
    - File upload handling
    - User authorization linking
    - Audit logging
    
    Returns: (success, message, vehicle_id)
    """

# Update
update_vehicle_record(
    vehicle_id: int,
    form_data: Dict[str, Any],
    files: Optional[Dict[str, Any]],
    upload_base_path: Optional[str]
) -> Tuple[bool, str, Optional[int]]
    """
    Update vehicle record with:
    - Existence check
    - Plate number validation
    - Duplicate check (excluding self)
    - File upload handling
    - Audit logging
    
    Returns: (success, message, vehicle_id)
    """

# Delete
delete_vehicle_record(
    vehicle_id: int,
    upload_base_path: Optional[str]
) -> Tuple[bool, str]
    """
    Delete vehicle record with:
    - Cascade deletion of related records
    - File cleanup (license image)
    - Operation requests cleanup
    - Notifications cleanup
    - Audit logging
    
    Returns: (success, message)
    """
```

### **Context Builders**
```python
get_create_form_context() -> Dict[str, Any]
    """
    Build context for vehicle creation form
    
    Returns:
        {
            'statuses': VEHICLE_STATUS_CHOICES,
            'all_users': List[User],
            'projects': List[str],
            'departments': List[Department]
        }
    """

get_edit_form_context(vehicle_id: int) -> Dict[str, Any]
    """
    Build context for vehicle edit form
    
    Returns:
        {
            'vehicle': Vehicle,
            'statuses': VEHICLE_STATUS_CHOICES,
            'all_users': List[User],
            'departments': List[Department]
        }
    
    Raises: 404 if vehicle not found
    """
```

---

## 🔄 Data Flow Examples

### **Example 1: Create Vehicle**

```
User submits form
       │
       ▼
┌──────────────────────────────────────┐
│ Route: /vehicles/create (POST)       │
│                                       │
│ 1. Validate form (WTForms)           │
│ 2. Extract form data                 │
│ 3. Call service:                     │
│    create_vehicle_record(...)        │
└────────────┬─────────────────────────┘
             │
             ▼
┌──────────────────────────────────────┐
│ Service: create_vehicle_record()     │
│                                       │
│ 1. ✅ Validate plate_number          │
│ 2. ✅ Check duplicates                │
│ 3. ✅ Create Vehicle object           │
│ 4. ✅ Link authorized users           │
│ 5. ✅ Save license image              │
│ 6. ✅ Commit transaction              │
│ 7. ✅ Log audit trail                 │
│ 8. ✅ Return (success, msg, id)       │
└────────────┬─────────────────────────┘
             │
             ▼
┌──────────────────────────────────────┐
│ Route: Handle response               │
│                                       │
│ 1. Flash message                     │
│ 2. Redirect to view page             │
└──────────────────────────────────────┘
```

### **Example 2: Edit Vehicle**

```
User visits edit page
       │
       ▼
┌──────────────────────────────────────┐
│ Route: /vehicles/<id>/edit (GET)     │
│                                       │
│ 1. Call service:                     │
│    get_edit_form_context(id)         │
└────────────┬─────────────────────────┘
             │
             ▼
┌──────────────────────────────────────┐
│ Service: get_edit_form_context()     │
│                                       │
│ 1. ✅ Fetch vehicle (or 404)          │
│ 2. ✅ Fetch active users              │
│ 3. ✅ Fetch departments               │
│ 4. ✅ Return context dict             │
└────────────┬─────────────────────────┘
             │
             ▼
┌──────────────────────────────────────┐
│ Route: Render template               │
│                                       │
│ 1. Pre-fill form with vehicle data  │
│ 2. Render edit.html                  │
└──────────────────────────────────────┘
```

---

## 🧪 Testing Strategy

### **Unit Tests (Service Layer)**
```python
# test_vehicle_management_service.py

def test_get_vehicle_or_404_success():
    """Test fetching existing vehicle"""
    vehicle = create_test_vehicle()
    result = get_vehicle_or_404(vehicle.id)
    assert result.id == vehicle.id

def test_get_vehicle_or_404_not_found():
    """Test 404 raised for non-existent vehicle"""
    with pytest.raises(NotFound):
        get_vehicle_or_404(99999)

def test_create_vehicle_record_success():
    """Test successful vehicle creation"""
    form_data = {"plate_number": "ABC123", ...}
    success, message, vehicle_id = create_vehicle_record(form_data)
    assert success is True
    assert vehicle_id is not None

def test_create_vehicle_record_duplicate():
    """Test duplicate plate number validation"""
    create_test_vehicle(plate_number="ABC123")
    form_data = {"plate_number": "ABC123", ...}
    success, message, vehicle_id = create_vehicle_record(form_data)
    assert success is False
    assert "مسجل مسبقاً" in message
```

### **Integration Tests (Routes)**
```python
# test_vehicle_routes.py

def test_create_vehicle_route_get(client):
    """Test create form renders correctly"""
    response = client.get('/vehicles/create')
    assert response.status_code == 200
    assert b'statuses' in response.data

def test_create_vehicle_route_post_success(client):
    """Test vehicle creation via HTTP"""
    data = {"plate_number": "ABC123", ...}
    response = client.post('/vehicles/create', data=data)
    assert response.status_code == 302  # Redirect
    assert "تمت إضافة السيارة" in flash_messages

def test_edit_vehicle_route_not_found(client):
    """Test edit route returns 404 for invalid ID"""
    response = client.get('/vehicles/99999/edit')
    assert response.status_code == 404
```

---

## 📈 Performance Considerations

### **Database Query Optimization**

**Before (Multiple Queries):**
```python
# Route executes 4 separate queries
users = User.query.filter_by(is_active=True).all()
departments = Department.query.all()
projects = db.session.query(Vehicle.project)...
vehicle = Vehicle.query.get(id)
```

**After (Optimized Service):**
```python
# Service layer can batch or cache queries
context = get_create_form_context()  # Single method call
# Can add caching here in future:
# @lru_cache(maxsize=128)
# def get_all_departments():
#     return Department.query.all()
```

### **Transaction Management**

**Atomic Operations:**
```python
try:
    db.session.add(vehicle)
    db.session.flush()  # Get ID before commit
    
    # Link authorized users
    for user in users:
        vehicle.authorized_users.append(user)
    
    db.session.commit()  # Single transaction
except Exception:
    db.session.rollback()  # Rollback on any error
    raise
```

---

## 🔒 Security Benefits

### **1. Input Validation Centralized**
```python
def _safe_str(v: Any) -> str:
    """Prevent None/injection issues"""
    if v is None:
        return ""
    return str(v).strip()
```

### **2. File Upload Security**
```python
if allowed_file(f.filename):
    filename = secure_filename(f.filename)
    # Safe file handling
```

### **3. SQL Injection Prevention**
```python
# ORM queries (safe from injection)
Vehicle.query.filter_by(plate_number=plate_number).first()
# vs raw SQL (vulnerable)
# db.execute(f"SELECT * FROM vehicles WHERE plate_number='{plate_number}'")
```

---

## 🎯 Migration Path for Other Modules

This pattern can be applied to:

1. **Attendance Routes** (4562 LOC) → `AttendanceManagementService`
2. **Employee Requests** (3403 LOC) → `EmployeeRequestService`
3. **Mobile Vehicle Routes** (4348 LOC) → Reuse existing `VehicleManagementService`
4. **Handover Routes** → `HandoverManagementService`
5. **Workshop Routes** → `WorkshopManagementService`

---

**Architect:** Principal Software Architect  
**Status:** ✅ Production Ready  
**Next:** Apply pattern to remaining modules
