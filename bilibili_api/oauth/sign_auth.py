import hashlib

from requests.auth import AuthBase

from ..config import APP_KEY, APP_SECRET, BUV_ID


class SignAuth(AuthBase):
    def sign(self, unsigned_str):
        # sorted_key = sorted(params.keys())
        unsigned_str += APP_SECRET
        hasher = hashlib.md5()
        hasher.update(unsigned_str.encode('utf-8'))
        signed = hasher.hexdigest()
        return signed

    def __call__(self, r):
        if not isinstance(r.body, str):
            raise TypeError
        r.body = '{}&sign={}'.format(r.body, self.sign(r.body))
        return r
