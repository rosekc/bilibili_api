import base64
import functools
import hashlib
import pickle
import requests
import rsa
import os

from .config import APP_KEY, GET_KEY_URL, LOGIN_URL
from .injected_session import Session
from .oauth.before_login_injector import BeforeLoginInjector, AddAccessKeyInjector
from .oauth.sign_auth import SignAuth
from .oauth.token import BilibiliToken


def need_login(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if self.is_login():
            return func(self, *args, **kwargs)
        else:
            raise Exception(func.__name__)
    return wrapper


class BilibiliClient:
    def __init__(self):
        self._session = Session(BeforeLoginInjector())
        self.auth = SignAuth()
        self._token = None

    def _get_key(self):
        j = self._session.post(GET_KEY_URL).json()
        return j['data']['key'], j['data']['hash']

    def encrypt_password(self, password, salt, key):
        public_key = rsa.PublicKey.load_pkcs1_openssl_pem(key.encode())
        password = base64.b64encode(rsa.encrypt(
            (salt + password).encode('utf-8'), public_key)).decode('utf-8')
        return password

    def is_login(self):
        return self._token is not None

    def login(self, username, password):
        if self.is_login():
            self._init_logined_session()
            return True, ''

        # it is salt not hash lol
        key, salt = self._get_key()
        password = self.encrypt_password(password, salt, key)

        payload = {
            'username': username,
            'password': password
        }

        headers = {"Content-type": "application/x-www-form-urlencoded"}
        res = self._session.post(LOGIN_URL, data=payload, headers=headers)

        try:
            json_dict = res.json()
            if json_dict['code'] < 0:
                return False, json_dict['message']

            self._token = BilibiliToken.from_dict(
                json_dict['data']['token_info'], json_dict['data']['cookie_info']['cookies'])
            self._init_logined_session()
        
            return True, ''
        except (ValueError, KeyError) as e:
            return False, str(e)
        return False, '????'

    @need_login
    def _init_logined_session(self):
        self._session.injectors = [
            BeforeLoginInjector(), AddAccessKeyInjector(self._token)]
        for c in self._token.cookies:
            self._session.cookies.set(c['name'], c['value'])

    def load_token(self, filename):
        self._token = BilibiliToken.from_file(filename)
        self._init_logined_session()

    @need_login
    def save_token(self, filename):
        self._token.save(filename)


# class BilibiliWebApi:
#     def __init__(self, cookies=None):
#         self._session = Session()
#         self._session.cookies = cookies

#     def upload(self, file_path, data):
#         with open('c', 'rb') as f:
#             self._session.cookies = pickle.load(f)
#         from .uploader import Uploader
#         u = Uploader(file_path, 4194304, 2, self._session.cookies, data)
#         u.process()
#         return
