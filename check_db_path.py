#!/usr/bin/env python
from main import app

print(f'Database URL: {app.config["SQLALCHEMY_DATABASE_URI"]}')
