import requests
import json
from shadowray.common.B64 import decode
from shadowray.config.v2ray import SUBSCRIBE_FILE
from shadowray.core.configuration import Configuration
import urllib.parse
import itertools
import base64

def base64_decode(x):
    #if debug: eprint(x)
    return base64.urlsafe_b64decode(x + '=' * (-len(x) % 4)).decode("utf-8")

def urlsafe_base64_decode(x):
    #if debug: eprint(x)
    return base64.urlsafe_b64decode(x + '=' * (-len(x) % 4)).decode("utf-8")

def compat_base64_decode(x):
    try:
        return base64_decode(x)
    except Exception:
        return urlsafe_base64_decode(x)

def urlsafe_base64_encode(x):
    if debug: eprint(x)
    r = base64.urlsafe_b64encode(x.encode("utf-8")).decode("ascii")
    if debug: eprint(r)
    while r and r[-1] == '=':
        r = r[:-1]
    if debug: eprint(r)
    return r
class Parser:
    def __init__(self, filename=None, template=None):
        self.servers = []
        self.filename = None

        self.subscribes = json.loads("{}")
        if filename is not None:
            f = open(filename, "r")
            self.subscribes = json.load(f)
            f.close()

            self.filename = filename

        if template is not None:
            f = open(template, "r")
            self.template = json.load(f)
            f.close()
        else:
            self.template = None

    def get_url(self, url, **kwargs):
        r = requests.get(url).text
        text = decode(r)

        text = text.split('\n')

        mux = 0
        if kwargs.get("mux") is not None:
            mux = kwargs.get("mux")

        for t in text:
            if len(t) == 0:
                continue
            original_t = t
            t = t.split("://")

            if self.template:
                config = Configuration(self.template)
            else:
                config = Configuration()

                port = 1082
                if kwargs.get("port") is not None:
                    port = kwargs.get("port")
                inbound = Configuration.Inbound(port, "127.0.0.1", "socks")
                socks = Configuration.ProtocolSetting.Inbound.Socks()
                inbound.set_settings(socks)
                config.add_inbound(inbound)

            if t[0] == "vmess":
                t[1] = json.loads(decode(t[1]))
                outbound = Configuration.Outbound("vmess", "proxy")
                vmess = Configuration.ProtocolSetting.Outbound.VMess()
                vmess_server = Configuration.ProtocolSetting.Outbound.VMess.Server(addr=t[1]['add'],
                                                                                   port=int(t[1]['port']))
                vmess_server.add_user(id=t[1]['id'],
                                      aid=int(t[1].get('aid', 0)),
                                      security='auto',
                                      level=int(t[1].get('level', 0)))
                vmess.add_server(vmess_server)
                outbound.set_settings(vmess)

                stream = Configuration.StreamSetting(type=Configuration.StreamSetting.STREAMSETTING,
                                                     network=t[1]['net'], security=t[1].get('tls', 'auto'))

                stream.set_web_socket(Configuration.StreamSetting.WebSocket(t[1].get('path', '/')))
                masquerade_type = t[1].get('type', 'none')
                stream.set_tcp(Configuration.StreamSetting.TCP(masquerade_type != 'none', masquerade_type))

                outbound.set_stream(stream)
                outbound.set_mux(Configuration.Outbound.Mux(mux != 0, mux))

                server_obj = {
                    "protocol": t[0],
                    "config": None,
                    "ps": t[1]['ps'],
                    "host": t[1]['add']
                }

            if t[0] == "ss":
                outbound = Configuration.Outbound("shadowsocks", "proxy")
                ss = Configuration.ProtocolSetting.Outbound.Shadowsocks()

                tmp1 = original_t[len("ss://"):].split('#')
                if len(tmp1) < 2:
                    tmp1.append("")
                tmp_ps = urllib.parse.unquote(tmp1[-1])

                ss_body = '#'.join(tmp1[:-1])
                if not ('@' in ss_body):
                    ss_body = compat_base64_decode(ss_body)

                tmp2 = ss_body.split("@")
                if ':' in tmp2[0]:
                    ss_user = tmp2[0]
                else:
                    ss_user = compat_base64_decode(tmp2[0])

                ss_enc, ss_password = ss_user.split(":")
                ss_add, ss_port = tmp2[1].split(":")

                ss_port = ''.join(itertools.takewhile(str.isdigit, ss_port))
                ss_ps = ("%s:%s" % (ss_add, ss_port)) if not tmp_ps else tmp_ps.strip()

                ss_obj = {
                    "is_ss": True,
                    "add": ss_add,
                    "port": ss_port,
                    "enc": ss_enc,
                    "password": ss_password,
                    "ps": ss_ps
                }

                ss.add_server(str(ss_obj["add"]), int(ss_obj["port"]), str(ss_obj["enc"]), str(ss_obj["password"]), 0)
                
                outbound.set_settings(ss)

                stream = Configuration.StreamSetting(type=Configuration.StreamSetting.STREAMSETTING,
                                                     network="tcp", security="none")

                outbound.set_stream(stream)
                
                server_obj = {
                    "protocol": t[0],
                    "config": None,
                    "ps": ss_ps,
                    "host": ss_add
                }
                

            config.insert_outbound(0, outbound)
            server_obj["config"] = config.json_obj
            self.servers.append(server_obj)

    def update(self, name=None, show_info=False, **kwargs):
        self.servers.clear()
        if name is None:
            for j in self.subscribes:
                if show_info:
                    print("update %s : %s" % (j, self.subscribes[j]))
                self.get_url(self.subscribes[j], **kwargs)
        else:
            if show_info:
                print("update %s : %s" % (name, self.subscribes[name]))
            self.get_url(self.subscribes[name], **kwargs)

    def save(self, filename=None):
        if filename is None:
            filename = SUBSCRIBE_FILE
        f = open(filename, 'w')
        f.write(json.dumps(self.subscribes))
        f.close()

    def add(self, name, url):
        self.subscribes[name] = url

    def delete(self, name):
        del self.subscribes[name]

    def get_servers(self):
        return self.servers
