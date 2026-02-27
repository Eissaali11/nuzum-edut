import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app as app_module
from routes.salaries_mgmt.v1 import salary_approval, salary_ops
from models import Salary

app = app_module.app
print('import_app_ok')
print('salary_ops_has_compute_net_salary', 'compute_net_salary' in salary_ops.__dict__)

app.config['LOGIN_DISABLED'] = True
with app.app_context():
    client = app.test_client()

    for url in ['/salaries/notifications/batch', '/salaries/notifications/deduction/batch']:
        response = client.get(url)
        print(url, response.status_code)

    first_salary = Salary.query.first()
    if first_salary:
        approval_urls = [
            f'/salaries/notification/{first_salary.id}/share_whatsapp',
            f'/salaries/notification/{first_salary.id}/share_deduction_whatsapp',
            f'/salaries/notification/{first_salary.id}/whatsapp',
            f'/salaries/notification/{first_salary.id}/deduction/whatsapp',
        ]
        for url in approval_urls:
            response = client.get(url, follow_redirects=False)
            print(url, response.status_code, response.headers.get('Location', ''))
    else:
        print('no_salary_records')
