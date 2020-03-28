import sys, getopt
from shadowray.config.version import VERSION_ID, HELP_INFO, COMMAND_LONG, COMMAND_SHORT
from shadowray.config.v2ray import PROJECT_CONFIG_FILE
from shadowray.config.v2_repo import RELEASE_API
from shadowray.config.version import *
from shadowray.common.utils import parse_yes_or_no
from shadowray.common.utils import download_file
from shadowray.common.utils import print_progress, find_arg_in_opts, write_to_file, ping
from shadowray.config.v2ray import V2RAY_BINARY, SUBSCRIBE_FILE, SERVER_FILE, V2RAY_FOLDER, RESOURCES_FOLDER, \
    PROJECT_PATH, V2CTL_BINARY, SHADOWRAY_CONFIG_FOLDER, V2RAY_PID_FILE
from shadowray.core.manager import Manager
import requests
import json
import platform
import zipfile
import os, stat, signal
try:
    from bullet import ScrollBar
except ModuleNotFoundError:
    pass


def create_basic_config_file():
    if os.path.exists(SHADOWRAY_CONFIG_FOLDER) is False:
        os.mkdir(SHADOWRAY_CONFIG_FOLDER)

    if os.path.exists(PROJECT_CONFIG_FILE) is False:
        f = open(PROJECT_CONFIG_FILE, 'w')
        f.write('{ \
                    "v2ray_binary": null, \
                    "servers_file": null, \
                    "template_file": null, \
                    "subscribe_file": null \
                    }')
        f.close()


def parse_json_from_file(path):
    f = open(path, 'r')
    j = json.load(f)
    f.close()
    return j


def have_config():
    create_basic_config_file()
    j = parse_json_from_file(PROJECT_CONFIG_FILE)

    if j['v2ray_binary'] is None:
        print(
            "Binary file of v2ray not config.\nYou can config it by --config-v2ray path.Also, you can use --autoconfig to config it automatic.")
        return False

    if j['subscribe_file'] is None:
        print(
            "Subscribe file not config.\nYou can config it by --config-subscribe path.Also, you can use --autoconfig to config it automatic.")
        return False

    if j['servers_file'] is None:
        print(
            "Servers file not config.\nYou can config it by --config-servers path.Also, you can use --autoconfig to config it automatic.")
        return False

    # if j['template_file'] is None:
    #     print(
    #         "Template file not config (this is optional).\nYou can config it by --config-template path.\nNote: This warning does not affect what you are doing next.")

    return True


def add_subscribe(args):
    v = args.split(',')

    j = parse_json_from_file(PROJECT_CONFIG_FILE)

    manager = Manager(subscribe_file_name=j['subscribe_file'])

    manager.add_subscribe(v[0], v[1])
    manager.save_subscribe()

def ls_subscribe():
    j = parse_json_from_file(PROJECT_CONFIG_FILE)

    manager = Manager(subscribe_file_name=j['subscribe_file'])
    subscribes = manager.get_subscribe()
    for k in subscribes.keys():
        sys.stdout.write(k + " " + subscribes[k] + "\n")

def rm_subscribe(arg):
    j = parse_json_from_file(PROJECT_CONFIG_FILE)

    manager = Manager(subscribe_file_name=j['subscribe_file'])
    try:
        subscribes = manager.rm_subscribe(arg)
        return True
    except KeyError as err:
        sys.stderr.write("Error: subscription %s does not exist\n" % err.args[0])

def basic_config_v2ray(v2ray_binary=None):
    create_basic_config_file()

    if v2ray_binary is not None:
        f = open(PROJECT_CONFIG_FILE, 'r')
        j = json.load(f)
        f.close()

        j['v2ray_binary'] = v2ray_binary

        write_to_file(PROJECT_CONFIG_FILE, 'w', json.dumps(j))


def basic_config_subscribe(subscribe_file=None):
    create_basic_config_file()

    if subscribe_file is not None:
        f = open(PROJECT_CONFIG_FILE, 'r')
        j = json.load(f)
        f.close()

        j['subscribe_file'] = subscribe_file

        write_to_file(SUBSCRIBE_FILE, "w", "{}")

        write_to_file(PROJECT_CONFIG_FILE, 'w', json.dumps(j))


def basic_config_servers(servers_file=None):
    create_basic_config_file()

    if servers_file is not None:
        f = open(PROJECT_CONFIG_FILE, 'r')
        j = json.load(f)
        f.close()

        j['servers_file'] = servers_file

        write_to_file(servers_file, "w", '{"servers_subscribe": [] ,"servers_original": []}')

        write_to_file(PROJECT_CONFIG_FILE, 'w', json.dumps(j))

def basic_config_template(template_file=None):
    create_basic_config_file()

    f = open(PROJECT_CONFIG_FILE, 'r')
    j = json.load(f)
    f.close()

    if not template_file or template_file.strip() == "":
        template_file = None

    j['template_file'] = template_file

    write_to_file(PROJECT_CONFIG_FILE, 'w', json.dumps(j))


def download_latest_v2ray():
    r = json.loads(requests.get(RELEASE_API).text)
    print("Latest publish date of v2ray-core: " + r['published_at'])
    print("Latest version of v2ray-core: " + r['tag_name'])

    os_str = str(platform.system())
    arch = str(platform.architecture()[0])

    if os_str.endswith("Darwin"):
        os_str = "macos"

    print("Platform: " + os_str + " " + arch)

    assets = r['assets']

    download_url = None
    for asset in assets:
        name = str(asset['name'])

        if name.endswith("zip") and name.find(os_str.lower()) != -1:
            if os_str.endswith("macos") or name.find(arch[0:2]) != -1:
                download_url = str(asset['browser_download_url'])
                break

    if download_url is None:
        print("Download failed,you can download by yourself.")
    else:
        print('Download from %s' % download_url)

        download_file_name = os.path.join(V2RAY_FOLDER, download_url.split('/')[-1])
        download_file(download_url, download_file_name, show_progress=True)

        print("\nU=uncompression:")
        f = zipfile.ZipFile(download_file_name, 'r')
        total = len(f.filelist)
        count = 0
        for file in f.filelist:
            f.extract(file, V2RAY_FOLDER)
            count += 1
            print_progress(100 * count / total, extra="%d/%d" % (count, total))

        print("\nSuccess!")
        os.remove(download_file_name)

        os.chmod(path=V2RAY_BINARY, mode=stat.S_IXUSR)
        os.chmod(path=V2CTL_BINARY, mode=stat.S_IXUSR)
        basic_config_v2ray(V2RAY_BINARY)


def auto_config():
    create_basic_config_file()

    if os.path.exists(RESOURCES_FOLDER) is False:
        os.mkdir(RESOURCES_FOLDER)
        print("Create resources folder.(%s)" % RESOURCES_FOLDER)

    if os.path.exists(SERVER_FILE) is False:
        # os.mknod(SERVER_FILE)
        open(SERVER_FILE, "w").close()  # for mac os x
        print("Create servers file.(%s)" % SERVER_FILE)
        write_to_file(SERVER_FILE, "w", '{"servers_subscribe": [] ,"servers_original": []}')

    if os.path.exists(SUBSCRIBE_FILE) is False:
        # os.mknod(SUBSCRIBE_FILE)
        open(SUBSCRIBE_FILE, "w").close()
        print("Create subscribe file.(%s)" % SUBSCRIBE_FILE)
        write_to_file(SUBSCRIBE_FILE, "w", '{}')

    basic_config_subscribe(SUBSCRIBE_FILE)
    basic_config_servers(SERVER_FILE)

    if os.path.exists(V2RAY_FOLDER) is False:
        os.mkdir(V2RAY_FOLDER)
        print("Create v2ray-core folder.(%s)" % V2RAY_FOLDER)

    s = None
    while s is None:
        t = input("Do you want to download the v2ray-core automatically?(Y/N)\n")
        s = parse_yes_or_no(t)

    if os.path.exists("v2ray") is False:
        os.mkdir("v2ray")

    if s:
        download_latest_v2ray()
    else:
        print("Please setup v2ray by yourself.")


def update_subscribe(**kwargs):
    j = parse_json_from_file(PROJECT_CONFIG_FILE)
    manager = Manager(server_file_name=j['servers_file'], subscribe_file_name=j['subscribe_file'], template_file_name=j.get('template_file'))

    manager.update_subscribe(show_info=True, **kwargs)
    manager.save_servers()


def show_servers():
    j = parse_json_from_file(PROJECT_CONFIG_FILE)
    manager = Manager(server_file_name=j['servers_file'])

    manager.show_servers()


def proxy(index=None, config_file=None):
    j = parse_json_from_file(PROJECT_CONFIG_FILE)

    manager = Manager(server_file_name=j['servers_file'], binary=j['v2ray_binary'])

    daemon = False

    if "--daemon" in sys.argv or "-d" in sys.argv:
        daemon = True
    if index is not None:
        index = int(index)

        server = manager.get_server(index - 1)
        print("Choose: " + server['ps'])

        ports = []
        for c in server['config']['inbounds']:
            if "port" in c:
                ports.append(c['port'])
        print("Local port: " + str(ports))
        manager.proxy(config=server['config'], daemon=daemon)
    elif config_file is not None:
        config = parse_json_from_file(config_file)

        ports = []
        for c in config['inbounds']:
            if "port" in c:
                ports.append(c['port'])
        print("Local port: " + str(ports))

        manager.proxy(config=config, daemon=daemon)


def servers_export(index, path):
    j = parse_json_from_file(PROJECT_CONFIG_FILE)

    manager = Manager(server_file_name=j['servers_file'], binary=j['v2ray_binary'])
    s = manager.get_server(index - 1)
    write_to_file(path, "w", json.dumps(s['config']))


def prepare_ping():
    j = parse_json_from_file(PROJECT_CONFIG_FILE)

    manager = Manager(server_file_name=j['servers_file'], binary=j['v2ray_binary'])

    choices = ["ping all"]

    l = manager.server_number
    for i in range(l):
        s = manager.get_server(i)
        choices.append(str(i + 1) + "  " + s['ps'] + "  " + s['host'])

    prompt = ScrollBar(height=10, choices=choices)
    result = prompt.launch()
    index = choices.index(result)
    print("index            ps          time")
    if index == 0:
        for i in range(l):
            s = manager.get_server(i)
            r = ping(host=s['host'])
            result = str(r) + "ms" if r != -1 else "timeout"
            print(str(i + 1) + "  " + s['ps'] + "  " + result)
    else:
        s = manager.get_server(index - 1)
        r = ping(host=s['host'])
        result = str(r) + "ms" if r != -1 else "timeout"
        print(str(index) + "  " + s['ps'] + "  " + result)


def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], shortopts=COMMAND_SHORT, longopts=COMMAND_LONG)
    except Exception as e:
        print("some error occurs when parsing your command args.")
        return 1

    if len(opts) == 0:
        print("Use shadowray --help to get more information.")

    for op_name, op_value in opts:
        if op_name in ("-h", "--help"):
            print(HELP_INFO)
            break

        if op_name in ("-v", "--version"):
            print("Shadowray: " + VERSION_ID)
            break

        if op_name in ("--subscribe-add",):
            if have_config() is True:
                add_subscribe(op_value)
            break

        if op_name in ("--subscribe-ls",):
            if have_config() is True:
                ls_subscribe()
            break

        if op_name in ("--subscribe-rm",):
            if have_config() is True:
                rm_subscribe(op_value)
            break

        if op_name in ("--config-v2ray",):
            basic_config_v2ray(op_value)
            break

        if op_name in ("--config-servers",):
            basic_config_servers(op_value)
            break

        if op_name in ("--config-subscribe",):
            basic_config_subscribe(op_value)
            break

        if op_name in ("--config-template",):
            basic_config_template(None if not op_value else op_value)
            break

        if op_name in ("--autoconfig",):
            auto_config()
            break

        if op_name in ("--subscribe-update",):
            socks_port = 1082
            http_port = 8118
            mux = 0
            listen_addr = "127.0.0.1"

            if "--port" in sys.argv:
                socks_port = int(find_arg_in_opts(opts, "--port"))
            if "--socks-port" in sys.argv:
                socks_port = int(find_arg_in_opts(opts, "--socks-port"))
            if "--http-port" in sys.argv:
                http_port = int(find_arg_in_opts(opts, "--http-port"))
            if "--listen-addr" in sys.argv:
                listen_addr = find_arg_in_opts(opts, "--listen-addr")
            if "--mux" in sys.argv:
                mux = int(find_arg_in_opts(opts, "--mux"))
                if mux < 0 or mux > 1024:
                    mux = 0

            if have_config():
                update_subscribe(socks_port=socks_port, http_port=http_port, listen_addr=listen_addr, mux=mux)

            break

        if op_name in ("--list", "-l"):
            if have_config():
                show_servers()
            break

        if op_name in ("--start", "-s"):
            if have_config():
                proxy(op_value)
            break

        if op_name in ("--config-file", "-f"):
            proxy(config_file=op_value)
            break

        if op_name in ("--servers-export",):
            if have_config():
                v = op_value.split(':')
                servers_export(int(v[0]), v[1])
            break

        if op_name in ("--stop",):
            f = open(V2RAY_PID_FILE, "r")
            s = f.read().strip()
            f.close()

            if s == "":
                print("no running process.")
            else:
                try:
                    os.kill(int(s), signal.SIGKILL)
                except ProcessLookupError:
                    print("Process[%s] not exist" % s)
                write_to_file(V2RAY_PID_FILE, "w", "")

        if op_name in ("--v2ray-update",):
            if have_config():
                download_latest_v2ray()

        if op_name in ("--ping",):
            if have_config():
                prepare_ping()

if __name__ == "__main__":
    main()
# TODO: configure single proxy by users
