#!/usr/bin/env python
import sys
import io

# اصلاح الترميز على Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, '.')

from main import app
from core.extensions import db

with app.app_context():
    db.create_all()
    print('Done: Tables created!')
    
    # التحقق
    from models import Department
    depts = Department.query.count()
    print(f'Departments count: {depts}')
