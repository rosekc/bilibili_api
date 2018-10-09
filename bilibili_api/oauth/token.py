import pickle


class BilibiliToken:
    def __init__(self, access_token, expires_in, mid, refresh_token, cookies_info):
        self.access_token = access_token
        self.expires_in = expires_in
        self.mid = mid
        self.refresh_token = refresh_token
        self.cookies_info = cookies_info
    
    @classmethod
    def from_dict(cls, json_dict):
        d = json_dict['token_info']
        # cookies?
        return cls(**d, cookies_info=json_dict['cookie_info'])

    @staticmethod
    def from_file(filename):
        with open(filename, 'rb') as f:
            return pickle.load(f)

    def save(self, filename):
        with open(filename, 'wb') as f:
            pickle.dump(self, f)
