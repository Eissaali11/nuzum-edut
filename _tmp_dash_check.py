import traceback
from core.app_factory import create_app
app = create_app()
with app.app_context():
    from routes.dashboard import index
    raw = getattr(getattr(index, '__wrapped__', index), '__wrapped__', index)
    with app.test_request_context('/dashboard/'):
        try:
            res = raw()
            print('RAW_OK', type(res))
        except Exception as e:
            print('RAW_ERR', e)
            traceback.print_exc()
