import asyncio
import json
import os
import signal
import subprocess
from dataclasses import dataclass, field

import aiofiles
from aiohttp import ClientSession, ClientTimeout
from aiohttp_socks import ProxyConnector, ProxyType
from colorama import Fore
from dotenv import load_dotenv

from core.v2ray2json import generateConfig

# Load environment variables
load_dotenv()


@dataclass
class V2RayConfig:
    """Data class to hold V2Ray configuration settings."""

    url: str = os.getenv('URL_CONFIGS_SUB')
    config_cache_path: str = os.getenv('CONFIG_CACHE_PATH')
    config_check_path: str = os.getenv('CONFIG_CHECK_PATH')
    v2ray_path: str = os.getenv('V2RAY_PATH')
    config_path: str = os.getenv('CONFIG_PATH')
    proxy_host: str = '127.0.0.1'
    proxy_port: int = 1080
    timeout: ClientTimeout = field(
        default_factory=lambda: ClientTimeout(total=1)
    )
    proxy_username: str = os.getenv('V2RAY_LOGIN')
    proxy_password: str = os.getenv('V2RAY_PASSWORD')


class V2RayController:
    def __init__(self, config: V2RayConfig):
        self.config = config
        self.process = None

    async def fetch_configs(self):
        """Fetch configuration URLs from a specified source."""
        print(Fore.BLUE + 'Fetching configuration URLs...')
        async with ClientSession(timeout=self.config.timeout) as session:
            try:
                async with session.get(self.config.url) as response:
                    response.raise_for_status()
                    text = await response.text()
                    urls = [
                        line
                        for line in text.splitlines()
                        if line.startswith(
                            ('vmess://', 'vless://', 'trojan://', 'ss://')
                        )
                    ]
                    print(
                        Fore.GREEN + f'Fetched {len(urls)} configuration URLs.'
                    )
                    return urls
            except Exception as e:
                print(Fore.RED + f'Error fetching configuration URLs: {e}')
                return []

    async def generate_config(self, config_url):
        """Generate a V2Ray configuration file from a given URL."""
        try:
            v2ray_config = generateConfig(
                config=config_url, dns_list=['8.8.8.8', '1.1.1.1']
            )
            async with aiofiles.open(
                self.config.config_cache_path, 'w'
            ) as file:
                await file.write(
                    json.dumps(json.loads(v2ray_config), indent=4)
                )
            print(Fore.GREEN + 'V2Ray configuration generated successfully.')
            return True
        except Exception as e:
            print(Fore.RED + f'Error generating config: {e}')
            return False

    async def append_config(self, url, country):
        """Append a configuration URL to the config check path."""
        url = url.split('#')[0]
        async with aiofiles.open(self.config.config_check_path, 'a') as file:
            await file.write(f'{url}#{country}\n')
        print(Fore.YELLOW + f'Configuration URL written to file: {url}')

    async def check_connection(self, use_proxy=False):
        """Check connection using either direct or proxy settings."""
        connector = None
        if use_proxy:
            connector = ProxyConnector(
                proxy_type=ProxyType.SOCKS5,
                host=self.config.proxy_host,
                port=self.config.proxy_port,
                rdns=True,
            )
            print(Fore.BLUE + 'Checking proxy connection...')
        else:
            print(Fore.BLUE + 'Checking direct connection to ipwho.is...')

        try:
            async with ClientSession(
                connector=connector, timeout=self.config.timeout
            ) as session:
                async with session.get('https://google.com') as response:
                    if not response.status == 200:
                        return False
                async with session.get('http://ipwho.is?lang=ru') as response:
                    data = await response.json()
                    connection_type = 'Proxy' if use_proxy else 'Direct'
                    print(
                        Fore.GREEN
                        + f'{connection_type} connection response: {data.get("ip")} -  {data.get("country")}'
                    )
                    return data.get('country')
        except asyncio.TimeoutError:
            print(Fore.RED + 'Timeout error')
            return False
        except Exception as e:
            connection_type = 'Proxy' if use_proxy else 'Direct'
            print(Fore.RED + f'{connection_type} connection error:', e)
            return False

    async def start_v2ray(self):
        """Start the V2Ray process."""
        try:
            self.process = await asyncio.create_subprocess_exec(
                self.config.v2ray_path,
                'run',
                '-config',
                self.config.config_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            print(Fore.GREEN + 'V2Ray started.')
        except Exception as e:
            print(Fore.RED + f'Error starting V2Ray: {e}')

    async def stop_v2ray(self):
        """Stop the V2Ray process if it is running."""
        if self.process and self.process.returncode is None:
            try:
                self.process.send_signal(signal.SIGTERM)
                await self.process.wait()
                print(Fore.GREEN + 'V2Ray stopped.')
            except ProcessLookupError:
                print(Fore.YELLOW + 'V2Ray process already terminated.')
            finally:
                self.process = None
