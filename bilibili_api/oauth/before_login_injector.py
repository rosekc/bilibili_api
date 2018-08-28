import hashlib
import collections

from .sign_auth import SignAuth

from ..config import APP_KEY, BUV_ID, APP_SECRET


class BeforeLoginInjector:
     def __call__(self, nxt):
        def func(*args, **kwargs):
            if not kwargs.get('data'):
                kwargs['data'] = {}
            kwargs['data']['appkey'] = APP_KEY
            kwargs['data'] = collections.OrderedDict(sorted(kwargs['data'].items()))
            kwargs['auth'] = SignAuth()
            return nxt(*args, **kwargs)
        return func

class AddAccessKeyInjector:
    def __init__(self, token):
        super().__init__()
        self.token = token
    def __call__(self, nxt):
        def func(*args, **kwargs):
            if not kwargs.get('data'):
                kwargs['data'] = {}
            kwargs['data']['access_key'] = self.token.access_token
            return nxt(*args, **kwargs)
        return func