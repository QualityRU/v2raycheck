import os

from dotenv import load_dotenv

from core.json2config import (
    check_socks,
    get_config_v2ray,
    get_configs_sub,
    start_v2ray,
    stop_v2ray,
)

load_dotenv()

URL_CONFIGS_SUB = os.getenv('URL_CONFIGS_SUB')


def main():
    configs_urls = get_configs_sub(URL_CONFIGS_SUB)

    for u in configs_urls:
        if not get_config_v2ray(u):
            continue

        v2ray_process = start_v2ray()
        # print('V2Ray запущен')

        check_socks(u)

        stop_v2ray(v2ray_process)
        # print('V2Ray остановлен')


if __name__ == '__main__':
    main()
