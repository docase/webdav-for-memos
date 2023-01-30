from cheroot import wsgi
from wsgidav.wsgidav_app import WsgiDAVApp
from wsgidav.dav_provider import DAVCollection, DAVNonCollection, DAVProvider
from wsgidav.util import join_uri

import requests

# settings for memos
MEMOS_HOME_URL = '' #your memos home page url
MEMOS_OPENID = '' #your memos openid, find it in settings
# settings for wsgidav
WEBDAV_USERNAME = 'admin'
WEBDAV_PASSWORD = 'admin'
WEBDAV_PORT = 8080
WEBDAV_HOST = '0.0.0.0'

# from memowebdav import VirtualResourceProvider4Memos
class VirtualResourceProvider4Memos(DAVProvider):

    def __init__(self, homeUrl, openId):
        super().__init__()
        self.data = {
            'ResourceUrl': f'{homeUrl}/api/resource?openId={openId}',
            'FileUrl' : f'{homeUrl}/o/r/%d/%s?openId={openId}'
        }

    def get_resource_inst(self, path, environ):
        self._count_get_resource_inst += 1
        root = RootCollection(environ, self.data)
        return root.resolve("", path)


class RootCollection(DAVCollection):

    def __init__(self, environ, data):
        DAVCollection.__init__(self, "/", environ)
        self.resourceData = {}
        resourceList = requests.get(data['ResourceUrl']).json()['data']
        for item in resourceList:
            fileName = f"{item['id']}+{item['filename']}"
            self.resourceData[fileName] = {
                'size': item['size'],
                'type': item['type'],
                'createdTs': item['createdTs'],
                'updatedTs': item['updatedTs'],
                'url': data['FileUrl'] % (item['id'],item['filename'])
            }
        self.fileList = list(self.resourceData.keys())

    def get_member_names(self):
        return self.fileList

    def get_member(self, name):
        if name in self.fileList:
            return VirtualResFile(join_uri(self.path, name), self.environ, self.resourceData, None)
        return None


class VirtualResFile(DAVNonCollection):

    def __init__(self, path, environ, resourceData, file_path):
        DAVNonCollection.__init__(self, path, environ)
        self.resourceData = resourceData
        self.file_path = file_path

    def get_display_name(self):
        return self.name

    def get_etag(self):
        return None

    def support_etag(self):
        return True

    def support_ranges(self):
        return False

    def get_content_length(self):
        return self.resourceData[self.name]['size']

    def get_content_type(self):
        return self.resourceData[self.name]['type']

    def get_creation_date(self):
        return self.resourceData[self.name]['createdTs']

    def get_display_info(self):
        return {"type": "Content file"}

    def get_last_modified(self):
        return self.resourceData[self.name]['updatedTs']

    def get_ref_url(self):
        return self.provider.share_path + '/' + self.name

    def get_content(self):
        from io import BytesIO
        return BytesIO(requests.get(self.resourceData[self.name]['url']).content)

if __name__ == '__main__':
    # settings for wsgidav
    config = {
        "host": WEBDAV_HOST,
        "port": WEBDAV_PORT,
        "provider_mapping": {
            "/": VirtualResourceProvider4Memos(MEMOS_HOME_URL,MEMOS_OPENID),
        },
        "simple_dc": {"user_mapping": {"*": {WEBDAV_USERNAME: {"password": WEBDAV_PASSWORD}}}},
        "verbose": 1,
    }
    app = WsgiDAVApp(config)

    server_args = {
        "bind_addr": (config["host"], config["port"]),
        "wsgi_app": app,
    }
    server = wsgi.Server(**server_args)
    server.start()
