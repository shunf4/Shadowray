from shadowray.subscribe.parser import Parser
from shadowray.core.server import Server
from shadowray.core.execute import Execute
from shadowray.config.v2ray import SERVER_KEY_FROM_ORIGINAL, SERVER_KEY_FROM_SUBSCRIBE
import json


class Manager:
    def __init__(self, subscribe_file_name=None, server_file_name=None, binary=None, template_file_name=None):
        if subscribe_file_name is not None:
            self.__subscribe = Parser(filename=subscribe_file_name, template=template_file_name)

        if server_file_name is not None:
            self.__server = Server(filename=server_file_name)

        if binary is not None:
            self.__execute = Execute(binary=binary)

    def add_subscribe(self, name, url):
        self.__subscribe.add(name, url)

    def get_subscribe(self):
        return self.__subscribe.subscribes

    def update_subscribe(self, show_info=False, **kwargs):
        self.__subscribe.update(show_info=show_info, **kwargs)

        self.__server.clear(SERVER_KEY_FROM_SUBSCRIBE)

        s = self.__subscribe.get_servers()

        for i in s:
            self.__server.add(protocol=i['protocol'], config=i['config'], ps=i['ps'], key=SERVER_KEY_FROM_SUBSCRIBE,
                              host=i['host'])

    def rm_subscribe(self, name):
        self.__subscribe.delete(name)

    def show_servers(self):
        servers = self.__server.get_servers()

        count = 0
        for s in servers[SERVER_KEY_FROM_ORIGINAL]:
            count += 1
            print(str(count) + " ---- " + s['ps'] + " ---- " + s['protocol'])

        for s in servers[SERVER_KEY_FROM_SUBSCRIBE]:
            count += 1
            print(str(count) + " ---- " + s['ps'] + " ---- " + s['protocol'])

    def proxy(self, index=None, config=None, daemon=False):
        if config is not None:
            self.__execute.exec(json.dumps(config), daemon=daemon)
        elif index is not None:
            self.__execute.exec(json.dumps(self.__server.get_config(index)), daemon=daemon)

    def save(self):
        self.__server.save()
        self.__subscribe.save()

    def save_servers(self):
        self.__server.save()

    def save_subscribe(self):
        self.__subscribe.save()

    def get_server(self, index):
        return self.__server.get_server(index)

    @property
    def server_number(self):
        return self.__server.original_servers_number + self.__server.subscribe_servers_number
