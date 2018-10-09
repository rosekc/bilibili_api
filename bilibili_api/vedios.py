import asyncio
import itertools
import logging
import math
import os
import sys
import time

import requests

CHUNK_SIZE = 4194304

_logger = logging.getLogger('bilibili_api')


class Vedio:
    def __init__(self, session, path=None, desc='', title=None, filename=None, **_):
        self.path = path
        self.local_filename = os.path.basename(self.path) if self.path else None
        """
        filename in remote server, without filename extension
        """
        self.filename = filename
        self.title = title or self.local_filename
        self.desc = desc
        self.finished = True

        if path:
            self.file_size = os.path.getsize(path)
            self.chunk_number = math.ceil(self.file_size / CHUNK_SIZE)
            self._session = session
            self.upload_id = None
            self.pre_upload_data = None
            self.endpoint = None
            self.uploaded = [False for i in range(self.chunk_number)]
            self.finished = False

            self._get_endpoint()

    def _get_endpoint(self):
        params = {
            'name': self.local_filename,
            'size': self.file_size,
            'r': 'upos',
            'profile': 'ugcupos/yb'
        }

        res = self._session.get(
            'https://member.bilibili.com/preupload', params=params)
        data = res.json()

        if data['OK'] != 1:
            # TODO: handle unsuccess request
            pass

        self.pre_upload_data = data
        self.endpoint = 'https:{}'.format(
            data['upos_uri'].replace('upos:/', data['endpoint']))
        self.filename = os.path.basename(self.endpoint).split('.')[0]

        header = {
            'X-Upos-Auth': self.pre_upload_data['auth']
        }
        res = self._session.post(
            self.endpoint, params='uploads&output=json', headers=header)
        data = res.json()
        self.upload_id = data['upload_id']

    def upload(self):
        if self.finished:
            return

        for i in range(self.chunk_number):
            self.upload_a_chunk(i)

    def upload_a_chunk(self, chunk_no, force=False):
        if self.uploaded[chunk_no]:
            if force:
                self.uploaded[chunk_no] = False
            else:
                return

        end_ptr = min([CHUNK_SIZE * (chunk_no + 1), self.file_size])
        parmas = {
            'partNumber': chunk_no + 1,
            'uploadId': self.upload_id,
            'chunk': chunk_no,
            'chunks': self.chunk_number,
            'size': end_ptr - CHUNK_SIZE * chunk_no,
            'start': CHUNK_SIZE * chunk_no,
            'end': end_ptr,
            'total': self.file_size
        }
        #TODO: other tpye of vedio
        headers = {
            'Access-Control-Request-Headers': 'x-upos-auth',
            'Access-Control-Request-Method': 'PUT',
            'Origin': 'https://member.bilibili.com',
            'X-Upos-Auth': self.pre_upload_data['auth'],
            'Content-Type': 'video/mp4'
        }

        _logger.debug('start chunk {}'.format(chunk_no))

        with open(self.path, 'rb') as f:
            f.seek(CHUNK_SIZE * chunk_no)
            res = self._session.put(self.endpoint, data=f.read(
                CHUNK_SIZE), params=parmas, headers=headers)
        if res.status_code == 200:
            self.uploaded[chunk_no] = True
        _logger.debug('finish chunk {}'.format(chunk_no))
        return self.uploaded[chunk_no]

    def finish(self):
        if not all(self.uploaded):
            return False

        header = {
            'X-Upos-Auth': self.pre_upload_data['auth'],
            'X-Upos-Fetch-Source': self.endpoint
        }
        res = requests.post(self.endpoint, params={
            'output': 'json',
            'name': os.path.basename(self.filename),
            'profile': 'ugcupos/yb',
            'biz_id': self.pre_upload_data['biz_id'],
            'fetch': ''
        }, headers=header)
        if res.status_code == 200:
            self.finished = True

        return True

    def info(self):
        info = {
            'desc': self.desc,  # P1 的简介
            'filename': self.filename,
            'title': self.title  # P1 的标题
        }
        return info


class VediosInfo:
    """Information of a vedio
    """

    def __init__(self, session, title, tid, tag, copyright=True, desc=None,
                 mission_id=0, no_reprint=0, **kwargs):
        self._session = session
        self.aid = None
        self.title = title
        self.tid = tid
        self.tag = tag
        self.copyright = copyright
        self.desc = desc
        self.source = ''
        self.mission_id = mission_id
        self.no_reprint = no_reprint
        self.vedios = []
        self.cover = None
        self.csrf = self._session.cookies.get(
            'bili_jct', domain='.bilibili.com')

        self.__dict__.update(kwargs)
        

    @classmethod
    def from_aid(cls, aid, session):
        res = session.get(
            'https://member.bilibili.com/x/web/archive/view', params={'aid': aid})
        data = res.json()['data']
        info = cls(session, **data['archive'])
        info.vedios = [Vedio(session, **v) for v in data['videos']]
        return info

    def add_vedio(self, path, desc='', title=None):
        self.vedios.append(Vedio(self._session, path, desc, title))

    def upload_all(self):
        for v in self.vedios:
            v.upload()

    def prepare_tag(self):
        if isinstance(self.tag, str):
            self.tag = [self.tag]

        if 0 < len(self.tag) > 12 or not all([isinstance(x, str) and 0 < len(x) <= 20 for x in self.tag]):
            raise ValueError(
                'tag size must less than 12 and not 0, each tag must not null and less than 20 char')

        self.tag = ','.join(self.tag)

    def prepare(self):
        self.prepare_tag()

        if self.copyright and self.source != '':
            raise ValueError('source must be none if copyrigth is true')

        prepared_vedio_info = {
            'copyright': 1 if self.copyright else 2,  # 1是原创2是转载
            'cover': self.cover,
            'csrf': None,  # cookie中一个叫bili_jct的字段
            'desc': '',  # 简介
            'mission_id': self.mission_id,  # 应该是参加活动
            'no_reprint': self.no_reprint,  # 是否禁止转载
            'source': self.source,  # 来源
            'tag': self.tag,  # 标签，半角逗号分隔
            'tid': self.tid,  # 投稿分类id
            'title': self.title,  # 标题
            'videos': [
                v.info() for v in self.vedios
            ]
        }
        return prepared_vedio_info

    def get_cover(self, vedio_no=0, try_time=10):
        for _ in range(try_time):
            try_time -= 1
            r = self._session.get('https://member.bilibili.com/x/web/archive/recovers', params={
                'fns': self.vedios[vedio_no].filename
            })
            try:
                self.cover = r.json()['data'][0]
            except IndexError:
                time.sleep(5)
                continue
            break

    def add(self):
        if self.aid:
            return
        self.get_cover()
        res = self._session.post('https://member.bilibili.com/x/vu/web/add', json=self.prepare(), params={
            'csrf': self.csrf
        })
        data = res.json()
        if data['code'] != 0:
            # TODO: error handle
            pass
        self.aid = data['data']['aid']
        return self.aid

    def edit(self):
        if not self.aid:
            return
        self.get_cover()
        info = self.prepare()
        info['aid'] = self.aid
        res = self._session.post('https://member.bilibili.com/x/vu/web/edit', json=info, params={
            'csrf': self.csrf
        })
        data = res.json()
        if data['code'] != 0:
            # TODO: error handle
            pass
        return data['data']['aid']
