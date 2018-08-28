import requests
import abc

class Session(requests.Session):
    def __init__(self, injectors=None):
        super().__init__()
        if not injectors:
            injectors = []
        if not isinstance(injectors, list):
            injectors = [injectors]
        self.injectors = injectors

    def request(self, *args, **kwargs):
        if len(self.injectors) == 0:
            return super().request(*args, **kwargs)
        first = True
        for i in reversed(self.injectors):
            if first:
                func = i(super().request)
                first = False
            else:
                func = i(func)       
        a = func(*args, **kwargs)
        return a
