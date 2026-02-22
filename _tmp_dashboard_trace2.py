import traceback
from core.app_factory import create_app

app = create_app()
with app.app_context():
    from routes.dashboard import index
    raw = getattr(getattr(index, '__wrapped__', index), '__wrapped__', index)
    try:
        with app.test_request_context('/dashboard/'):
            res = raw()
            print('OK', type(res))
    except Exception as e:
        print('ERROR', e)
        traceback.print_exc()
