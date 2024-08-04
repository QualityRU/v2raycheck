import json
import os
import signal
import socket
import subprocess

import requests
import socks
from dotenv import load_dotenv

from core.v2ray2json import generateConfig

load_dotenv()

URL_CONFIGS_SUB = os.getenv('URL_CONFIGS_SUB')
CONFIG_CACHE_PATH = os.getenv('CONFIG_CACHE_PATH')
V2RAY_PATH = os.getenv('V2RAY_PATH')
CONFIG_PATH = os.getenv('CONFIG_PATH')
CONFIG_CHECK_PATH = os.getenv('CONFIG_CHECK_PATH')


def get_configs_sub(url):
    response = requests.get(url)
    response.raise_for_status()
    lines = response.text.splitlines()
    urls = list()

    for line in lines:
        if line.strip() == '':
            continue

        if line.startswith(('vmess://', 'vless://', 'trojan://', 'ss://')):
            urls.append(line)

    return urls


def get_config_v2ray(config_url):
    try:
        v2ray_config = generateConfig(
            config=config_url, dns_list=['8.8.8.8', '1.1.1.1']
        )

        with open(CONFIG_CACHE_PATH, 'w') as file:
            json.dump(json.loads(v2ray_config), file, indent=4)
    except Exception:
        return False
    return True


def write_config(text):
    with open(CONFIG_CHECK_PATH, 'a') as file:
        file.write(text + '\n')


def check_socks(url):
    socks.set_default_proxy(socks.SOCKS5, '127.0.0.1', 1080)
    socket.socket = socks.socksocket

    try:
        response = requests.get('http://httpbin.org/ip', timeout=1)
        print('Прокси ответ: ', response.json())
        if response:
            write_config(url)
    except Exception as e:
        print('Ошибка соединения через прокси:', e)


def start_v2ray():
    process = subprocess.Popen(
        [V2RAY_PATH, 'run', '-config', CONFIG_PATH],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return process


def stop_v2ray(process):
    process.send_signal(signal.SIGTERM)
    process.wait()
