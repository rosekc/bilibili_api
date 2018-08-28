import pickle


class BilibiliToken:
    def __init__(self, access_token, expires_in, mid, refresh_token):
        self.access_token = access_token
        self.expires_in = expires_in
        self.mid = mid
        self.refresh_token = refresh_token
        self.cookies = None

    @staticmethod
    def from_dict(json_dict, cookies):
        try:
            ret = BilibiliToken(**json_dict)
            ret.cookies = cookies
            return ret
        except TypeError:
            raise ValueError(
                '{json_dict} is NOT a valid bilibili token json.'.format(
                    json_dict=json_dict
                ))

    @staticmethod
    def from_file(filename):
        with open(filename, 'rb') as f:
            return pickle.load(f)

    def save(self, filename):
        with open(filename, 'wb') as f:
            pickle.dump(self, f)
