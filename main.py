import asyncio
import traceback

from colorama import Fore, init

from core.v2ray import V2RayConfig, V2RayController

init(autoreset=True)


async def main():
    config = V2RayConfig()
    controller = V2RayController(config)

    await controller.check_connection()
    configs_urls = await controller.fetch_configs()

    for url in configs_urls:
        if not await controller.generate_config(url):
            continue

        await controller.start_v2ray()
        await asyncio.sleep(0.1)

        if await controller.check_connection(use_proxy=True):
            await controller.append_config(url)

        await controller.stop_v2ray()

    await asyncio.sleep(0.1)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as e:
        print(Fore.RED + 'An error occurred during execution:', e)
        print(Fore.RED + traceback.format_exc())
