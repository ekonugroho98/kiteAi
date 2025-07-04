from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from aiohttp import ClientResponseError, ClientSession, ClientTimeout
from aiohttp_socks import ProxyConnector
from fake_useragent import FakeUserAgent
from colorama import *
from datetime import datetime
import asyncio, binascii, random, json, os, pytz
from urllib.parse import urlparse
import socket
from telegram import Bot
from telegram.error import TelegramError

wib = pytz.timezone('Asia/Jakarta')

class KiteAiFaucet:
    def __init__(self) -> None:
        self.headers = {
            "Accept-Language": "application/json, text/plain, */*",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            "Origin": "https://testnet.gokite.ai",
            "Referer": "https://testnet.gokite.ai/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": FakeUserAgent().random
        }
        self.BASE_API = "https://testnet.gokite.ai"
        self.NEO_API = "https://neo.prod.gokite.ai/v2"
        self.OZONE_API = "https://ozone-point-system.prod.gokite.ai"
        self.SITE_KEY = "6Lc_VwgrAAAAALtx_UtYQnW-cFg8EPDgJ8QVqkaz"
        self.KEY_HEX = "6a1c35292b7c5b769ff47d89a17e7bc4f0adfe1b462981d28e0e9f7ff20b8f8a"
        self.CAPTCHA_KEY = None
        self.proxies = []
        self.proxy_index = 0
        self.account_proxies = {}
        self.auth_tokens = {}
        self.access_tokens = {}
        self.header_cookies = {}
        self.min_delay = 0
        self.max_delay = 0
        self.telegram_bot = None
        self.telegram_chat_id = None
        self.proxy_lock = asyncio.Lock()

    def clear_terminal(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def log(self, message):
        print(
            f"{Fore.CYAN + Style.BRIGHT}[ {datetime.now().astimezone(wib).strftime('%x %X %Z')} ]{Style.RESET_ALL}"
            f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}{message}",
            flush=True
        )

    def welcome(self):
        print(
            f"""
        {Fore.GREEN + Style.BRIGHT}Kite Ai Ozone {Fore.BLUE + Style.BRIGHT}Faucet Claimer
            """
        )

    def load_telegram_config(self):
        try:
            with open("telegram.json", 'r') as file:
                config = json.load(file)
                self.telegram_bot = Bot(token=config["bot_token"])
                self.telegram_chat_id = config["chat_id"]
                return True
        except FileNotFoundError:
            self.log(f"{Fore.YELLOW}telegram.json not found, Telegram notifications disabled.{Style.RESET_ALL}")
            return False
        except Exception as e:
            self.log(f"{Fore.RED}Error loading telegram.json: {e}{Style.RESET_ALL}")
            return False

    def load_captcha_key(self):
        try:
            with open("captcha_key.txt", 'r') as file:
                captcha_key = file.read().strip()
            return captcha_key
        except Exception as e:
            return None
    
    async def load_proxies(self, use_proxy_choice: int):
        filename = "proxy.txt"
        try:
            if use_proxy_choice == 1:
                async with ClientSession(timeout=ClientTimeout(total=30)) as session:
                    async with session.get("https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&proxy_format=protocolipport&format=text") as response:
                        response.raise_for_status()
                        content = await response.text()
                        with open(filename, 'w') as f:
                            f.write(content)
                        self.proxies = [line.strip() for line in content.splitlines() if line.strip()]
            else:
                if not os.path.exists(filename):
                    self.log(f"{Fore.RED + Style.BRIGHT}File {filename} Not Found.{Style.RESET_ALL}")
                    return
                with open(filename, 'r') as f:
                    self.proxies = [line.strip() for line in f.read().splitlines() if line.strip()]
            
            if not self.proxies:
                self.log(f"{Fore.RED + Style.BRIGHT}No Proxies Found.{Style.RESET_ALL}")
                return

            self.log(
                f"{Fore.GREEN + Style.BRIGHT}Proxies Total  : {Style.RESET_ALL}"
                f"{Fore.WHITE + Style.BRIGHT}{len(self.proxies)}{Style.RESET_ALL}"
            )
        
        except Exception as e:
            self.log(f"{Fore.RED + Style.BRIGHT}Failed To Load Proxies: {e}{Style.RESET_ALL}")
            self.proxies = []

    def check_proxy_schemes(self, proxies):
        schemes = ["http://", "https://", "socks4://", "socks5://"]
        if any(proxies.startswith(scheme) for scheme in schemes):
            return proxies
        return f"http://{proxies}"

    async def get_next_proxy_for_account(self, token):
        async with self.proxy_lock:
            if token not in self.account_proxies:
                if not self.proxies:
                    return None
                proxy = self.check_proxy_schemes(self.proxies[self.proxy_index])
                self.account_proxies[token] = proxy
                self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
            return self.account_proxies[token]

    async def rotate_proxy_for_account(self, token):
        async with self.proxy_lock:
            if not self.proxies:
                return None
            proxy = self.check_proxy_schemes(self.proxies[self.proxy_index])
            self.account_proxies[token] = proxy
            self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
            return proxy

    def generate_auth_token(self, address):
        try:
            key = bytes.fromhex(self.KEY_HEX)
            iv = os.urandom(12)
            encryptor = Cipher(algorithms.AES(key), modes.GCM(iv), backend=default_backend()).encryptor()

            ciphertext = encryptor.update(address.encode()) + encryptor.finalize()
            auth_tag = encryptor.tag

            result = iv + ciphertext + auth_tag
            result_hex = binascii.hexlify(result).decode()

            return result_hex
        except Exception as e:
            return None
    
    def extract_cookies(self, raw_cookies: list):
        cookies_dict = {}
        try:
            skip_keys = ['expires', 'path', 'domain', 'samesite', 'secure', 'httponly', 'max-age']

            for cookie_str in raw_cookies:
                cookie_parts = cookie_str.split(';')

                for part in cookie_parts:
                    cookie = part.strip()

                    if '=' in cookie:
                        name, value = cookie.split('=', 1)

                        if name and value and name.lower() not in skip_keys:
                            cookies_dict[name] = value

            cookie_header = "; ".join([f"{key}={value}" for key, value in cookies_dict.items()])
            
            return cookie_header
        except Exception as e:
            raise Exception(f"Extract Cookies Data Failed: {str(e)}")
    
    def mask_account(self, account):
        try:
            mask_account = account[:6] + '*' * 6 + account[-6:]
            return mask_account
        except Exception as e:
            return None
    
    async def send_telegram_message(self, message):
        if self.telegram_bot and self.telegram_chat_id:
            try:
                await self.telegram_bot.send_message(chat_id=self.telegram_chat_id, text=message)
            except TelegramError as e:
                self.log(f"{Fore.RED}Failed to send Telegram message: {e}{Style.RESET_ALL}")

    def print_question(self):
        import os
        if os.environ.get("AUTO_INPUT") == "1":
            # AUTO MODE (untuk Docker)
            choose = 2  # 1=Proxyscrape, 2=Private, 3=Tanpa Proxy
            rotate = True
            min_delay = 5
            max_delay = 10
            self.min_delay = min_delay
            self.max_delay = max_delay
            print(f"[AUTO] Proxy: {choose}, Rotate: {rotate}, Min Delay: {min_delay}, Max Delay: {max_delay}")
            return choose, rotate
        # ... lanjutkan dengan mode manual seperti biasa
        while True:
            try:
                print(f"{Fore.WHITE + Style.BRIGHT}1. Run With Proxyscrape Free Proxy{Style.RESET_ALL}")
                print(f"{Fore.WHITE + Style.BRIGHT}2. Run With Private Proxy{Style.RESET_ALL}")
                print(f"{Fore.WHITE + Style.BRIGHT}3. Run Without Proxy{Style.RESET_ALL}")
                choose = int(input(f"{Fore.BLUE + Style.BRIGHT}Choose [1/2/3] -> {Style.RESET_ALL}").strip())

                if choose in [1, 2, 3]:
                    proxy_type = (
                        "With Proxyscrape Free" if choose == 1 else 
                        "With Private" if choose == 2 else 
                        "Without"
                    )
                    print(f"{Fore.GREEN + Style.BRIGHT}Run {proxy_type} Proxy Selected.{Style.RESET_ALL}")
                    break
                else:
                    print(f"{Fore.RED + Style.BRIGHT}Please enter either 1, 2 or 3.{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED + Style.BRIGHT}Invalid input. Enter a number (1, 2 or 3).{Style.RESET_ALL}")

        rotate = False
        if choose in [1, 2]:
            while True:
                rotate = input(f"{Fore.BLUE + Style.BRIGHT}Rotate Invalid Proxy? [y/n] -> {Style.RESET_ALL}").strip()

                if rotate in ["y", "n"]:
                    rotate = rotate == "y"
                    break
                else:
                    print(f"{Fore.RED + Style.BRIGHT}Invalid input. Enter 'y' or 'n'.{Style.RESET_ALL}")

        while True:
            try:
                min_delay = int(input(f"{Fore.YELLOW + Style.BRIGHT}Min Delay Each Interactions -> {Style.RESET_ALL}").strip())
                if min_delay >= 0:
                    self.min_delay = min_delay
                    break
                else:
                    print(f"{Fore.RED + Style.BRIGHT}Min Delay must be >= 0.{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED + Style.BRIGHT}Invalid input. Enter a number.{Style.RESET_ALL}")

        while True:
            try:
                max_delay = int(input(f"{Fore.YELLOW + Style.BRIGHT}Max Delay Each Interactions -> {Style.RESET_ALL}").strip())
                if max_delay >= min_delay:
                    self.max_delay = max_delay
                    break
                else:
                    print(f"{Fore.RED + Style.BRIGHT}Min Delay must be >= Min Delay.{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED + Style.BRIGHT}Invalid input. Enter a number.{Style.RESET_ALL}")

        return choose, rotate
    
    async def solve_recaptcha(self, proxy=None, retries=5):
        if not self.CAPTCHA_KEY:
            self.log(f"{Fore.RED+Style.BRIGHT}Anti-Captcha key not found.{Style.RESET_ALL}")
            return None

        create_task_payload = {
            "clientKey": self.CAPTCHA_KEY,
            "task": {
                "type": "RecaptchaV2TaskProxyless",
                "websiteURL": self.BASE_API,
                "websiteKey": self.SITE_KEY,
            }
        }

        for attempt in range(retries):
            try:
                async with ClientSession(timeout=ClientTimeout(total=60)) as session:
                    async with session.post("https://api.anti-captcha.com/createTask", json=create_task_payload) as response:
                        response.raise_for_status()
                        result = await response.json()
                        if result.get("errorId") != 0:
                            self.log(f"{Fore.RED+Style.BRIGHT}Anti-Captcha Error (createTask): {result.get('errorDescription')}{Style.RESET_ALL}")
                            await asyncio.sleep(5)
                            continue

                        task_id = result.get("taskId")
                        self.log(
                            f"{Fore.MAGENTA + Style.BRIGHT}  ● {Style.RESET_ALL}"
                            f"{Fore.BLUE + Style.BRIGHT}Task Id :{Style.RESET_ALL}"
                            f"{Fore.WHITE + Style.BRIGHT} {task_id} {Style.RESET_ALL}"
                        )

                        get_task_payload = {
                            "clientKey": self.CAPTCHA_KEY,
                            "taskId": task_id
                        }
                        for _ in range(40):
                            await asyncio.sleep(3)
                            async with session.post("https://api.anti-captcha.com/getTaskResult", json=get_task_payload) as res_response:
                                res_response.raise_for_status()
                                res_result = await res_response.json()

                                if res_result.get("errorId") != 0:
                                    self.log(f"{Fore.RED+Style.BRIGHT}Anti-Captcha Error (getTaskResult): {res_result.get('errorDescription')}{Style.RESET_ALL}")
                                    break 

                                status = res_result.get("status")
                                if status == "ready":
                                    return res_result.get("solution", {}).get("gRecaptchaResponse")
                                elif status == "processing":
                                    self.log(
                                        f"{Fore.MAGENTA + Style.BRIGHT}  ● {Style.RESET_ALL}"
                                        f"{Fore.BLUE + Style.BRIGHT}Message :{Style.RESET_ALL}"
                                        f"{Fore.WHITE + Style.BRIGHT} Captcha Not Ready (processing) {Style.RESET_ALL}"
                                    )
                                    continue
                                else:
                                    self.log(f"{Fore.RED+Style.BRIGHT}Anti-Captcha unhandled status: {status}{Style.RESET_ALL}")
                                    break
            except (Exception, ClientResponseError) as e:
                self.log(f"{Fore.RED+Style.BRIGHT}Error solving captcha: {e}{Style.RESET_ALL}")
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
        return None
        
    async def user_signin(self, address: str, proxy=None, retries=5):
        url = f"{self.NEO_API}/signin"
        data = json.dumps({"eoa":address})
        headers = {
            **self.headers,
            "Authorization": self.auth_tokens[address],
            "Content-Length": str(len(data)),
            "Content-Type": "application/json"
        }
        await asyncio.sleep(3)
        for attempt in range(retries):
            connector = ProxyConnector.from_url(proxy) if proxy else None
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.post(url=url, headers=headers, data=data) as response:
                        response.raise_for_status()
                        result = await response.json()

                        raw_cookies = response.headers.getall('Set-Cookie', [])
                        if raw_cookies:
                            cookie_header = self.extract_cookies(raw_cookies)

                            if cookie_header:
                                return result, cookie_header
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                self.log(
                    f"{Fore.CYAN+Style.BRIGHT}Status    :{Style.RESET_ALL}"
                    f"{Fore.RED+Style.BRIGHT} Login Failed {Style.RESET_ALL}"
                    f"{Fore.MAGENTA+Style.BRIGHT}-{Style.RESET_ALL}"
                    f"{Fore.YELLOW+Style.BRIGHT} {str(e)} {Style.RESET_ALL}"
                )
        
        return None, None
        
    async def user_data(self, address: str, proxy=None, retries=5):
        url = f"{self.OZONE_API}/me"
        headers = {
            **self.headers,
            "Authorization": f"Bearer {self.access_tokens[address]}"
        }
        await asyncio.sleep(3)
        for attempt in range(retries):
            connector = ProxyConnector.from_url(proxy) if proxy else None
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.get(url=url, headers=headers) as response:
                        response.raise_for_status()
                        return await response.json()
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                self.log(
                    f"{Fore.CYAN+Style.BRIGHT}Error     :{Style.RESET_ALL}"
                    f"{Fore.RED+Style.BRIGHT} GET User Data Failed {Style.RESET_ALL}"
                    f"{Fore.MAGENTA+Style.BRIGHT}-{Style.RESET_ALL}"
                    f"{Fore.YELLOW+Style.BRIGHT} {str(e)} {Style.RESET_ALL}"
                )

        return None
            
    async def claim_faucet(self, address: str, recaptcha_token: str, proxy=None, retries=5):
        url = f"{self.OZONE_API}/blockchain/faucet-transfer"
        headers = {
            **self.headers,
            "Authorization": f"Bearer {self.access_tokens[address]}",
            "Content-Length":"2",
            "Content-Type": "application/json",
            "x-recaptcha-token": recaptcha_token
        }
        await asyncio.sleep(3)
        for attempt in range(retries):
            connector = ProxyConnector.from_url(proxy) if proxy else None
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.post(url=url, headers=headers, json={}) as response:
                        response.raise_for_status()
                        return await response.json()
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                self.log(
                    f"{Fore.MAGENTA + Style.BRIGHT}  ● {Style.RESET_ALL}"
                    f"{Fore.BLUE + Style.BRIGHT}Status  :{Style.RESET_ALL}"
                    f"{Fore.RED+Style.BRIGHT} Not Claimed {Style.RESET_ALL}"
                    f"{Fore.MAGENTA+Style.BRIGHT}-{Style.RESET_ALL}"
                    f"{Fore.YELLOW+Style.BRIGHT} {str(e)} {Style.RESET_ALL}"
                )

        return None
            
    async def token_balance(self, address: str, proxy=None, retries=5):
        url = f"{self.OZONE_API}/me/balance"
        headers = {
            **self.headers,
            "Authorization": f"Bearer {self.access_tokens[address]}"
        }
        await asyncio.sleep(3)
        for attempt in range(retries):
            connector = ProxyConnector.from_url(proxy) if proxy else None
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.get(url=url, headers=headers) as response:
                        response.raise_for_status()
                        return await response.json()
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                self.log(
                    f"{Fore.CYAN+Style.BRIGHT}Error     :{Style.RESET_ALL}"
                    f"{Fore.RED+Style.BRIGHT} GET Balance Failed {Style.RESET_ALL}"
                    f"{Fore.MAGENTA+Style.BRIGHT}-{Style.RESET_ALL}"
                    f"{Fore.YELLOW+Style.BRIGHT} {str(e)} {Style.RESET_ALL}"
                )

        return None
        
    async def process_user_signin(self, address: str, use_proxy: bool, rotate_proxy: bool):
        while True:
            proxy = await self.get_next_proxy_for_account(address) if use_proxy else None
            self.log(
                f"{Fore.CYAN+Style.BRIGHT}Proxy     :{Style.RESET_ALL}"
                f"{Fore.WHITE+Style.BRIGHT} {proxy} {Style.RESET_ALL}"
            )

            result, header_cookie = await self.user_signin(address, proxy)
            if result and header_cookie:
                self.access_tokens[address] = result["data"]["access_token"]
                self.header_cookies[address] = header_cookie

                self.log(
                    f"{Fore.CYAN+Style.BRIGHT}Status    :{Style.RESET_ALL}"
                    f"{Fore.GREEN+Style.BRIGHT} Login Success {Style.RESET_ALL}"
                )
                return True
            
            if rotate_proxy:
                proxy = await self.rotate_proxy_for_account(address)
                await asyncio.sleep(5)
                continue

            return False
        
    async def process_faucet_claim(self, account_index: int, address: str, use_proxy: bool, rotate_proxy: bool):
        faucet_status = "Failed"
        username = "Unknown"
        xp_balance = 0
        kite_balance = 0
        usdt_balance = 0
        final_message = ""
        masked_address = self.mask_account(address)

        signed = await self.process_user_signin(address, use_proxy, rotate_proxy)
        if not signed:
            final_message = f"👤 Wallet {account_index}: {masked_address}\n"
            final_message += "❌ Login Failed"
            await self.send_telegram_message(final_message)
            return

        proxy = await self.get_next_proxy_for_account(address) if use_proxy else None
        user = await self.user_data(address, proxy)
        if not user:
            final_message = f"👤 Wallet {account_index}: {masked_address}\n"
            final_message += "❌ Error: Failed to get user data."
            await self.send_telegram_message(final_message)
            return
        
        username = user.get("data", {}).get("profile", {}).get("username", "Unknown")
        xp_balance = user.get("data", {}).get("profile", {}).get("total_xp_points", 0)
        
        self.log(
            f"{Fore.CYAN+Style.BRIGHT}Username  :{Style.RESET_ALL}"
            f"{Fore.WHITE+Style.BRIGHT} {username} {Style.RESET_ALL}"
        )
        self.log(f"{Fore.CYAN+Style.BRIGHT}Balance   :{Style.RESET_ALL}")
        self.log(
            f"{Fore.MAGENTA+Style.BRIGHT}  ● {Style.RESET_ALL}"
            f"{Fore.WHITE+Style.BRIGHT} {xp_balance} XP {Style.RESET_ALL}"
        )

        balance = await self.token_balance(address, proxy)
        if balance:
            kite_balance = balance.get("data", {}).get("balances", {}).get("kite", 0)
            usdt_balance = balance.get("data", {}).get("balances", {}).get("usdt", 0)
            self.log(
                f"{Fore.MAGENTA+Style.BRIGHT}  ● {Style.RESET_ALL}"
                f"{Fore.WHITE+Style.BRIGHT} {kite_balance} KITE {Style.RESET_ALL}"
            )
            self.log(
                f"{Fore.MAGENTA+Style.BRIGHT}  ● {Style.RESET_ALL}"
                f"{Fore.WHITE+Style.BRIGHT} {usdt_balance} USDT {Style.RESET_ALL}"
            )

        # Check if faucet is claimable
        is_claimable = user.get("data", {}).get("faucet_claimable", False)
        self.log(f"{Fore.CYAN+Style.BRIGHT}Faucet    :{Style.RESET_ALL}")
        if is_claimable:
            self.log(f"{Fore.YELLOW + Style.BRIGHT}Solving reCaptcha...{Style.RESET_ALL}")
            recaptcha_token = await self.solve_recaptcha(proxy)
            if recaptcha_token:
                claim = await self.claim_faucet(address, recaptcha_token, proxy)
                if claim:
                    faucet_status = "Success"
                    self.log(f"{Fore.GREEN + Style.BRIGHT}Claimed Successfully{Style.RESET_ALL}")
                else:
                    faucet_status = "Failed"
            else:
                faucet_status = "Failed (reCaptcha)"
        else:
            faucet_status = "Not Time to Claim"
            self.log(f"{Fore.YELLOW+Style.BRIGHT}{faucet_status}{Style.RESET_ALL}")

        final_message = f"🎯 Faucet Claim - Wallet {account_index}: {masked_address}\n"
        final_message += f"💰 Balance: {xp_balance} XP\n"
        final_message += f"💎 KITE: {kite_balance}\n"
        final_message += f"💵 USDT: {usdt_balance}\n"
        faucet_emoji = "✅" if faucet_status == "Success" else "❌"
        final_message += f"{faucet_emoji} Faucet Claim: {faucet_status}"

        await self.send_telegram_message(final_message)

    async def main(self):
        try:
            with open('accounts.txt', 'r') as file:
                accounts = [line.strip() for line in file if line.strip()]

            captcha_key = self.load_captcha_key()
            if captcha_key:
                self.CAPTCHA_KEY = captcha_key

            self.load_telegram_config()
            
            use_proxy_choice, rotate_proxy = self.print_question()

            while True:
                use_proxy = False
                if use_proxy_choice in [1, 2]:
                    use_proxy = True

                self.clear_terminal()
                self.welcome()
                self.log(
                    f"{Fore.GREEN + Style.BRIGHT}Account's Total: {Style.RESET_ALL}"
                    f"{Fore.WHITE + Style.BRIGHT}{len(accounts)}{Style.RESET_ALL}"
                )

                if use_proxy:
                    await self.load_proxies(use_proxy_choice)
                
                tasks = []
                for i, address in enumerate(accounts, 1):
                    if address:
                        auth_token = self.generate_auth_token(address)
                        if not auth_token:
                            self.log(f"{Fore.RED+Style.BRIGHT}Gagal membuat token otentikasi untuk {self.mask_account(address)}, melompat.{Style.RESET_ALL}")
                            continue
                        
                        self.auth_tokens[address] = auth_token
                        
                        self.log(f"{Fore.YELLOW}Menjadwalkan akun {i} ({self.mask_account(address)}) untuk faucet claim.{Style.RESET_ALL}")
                        
                        task = asyncio.create_task(self.process_faucet_claim(i, address, use_proxy, rotate_proxy))
                        tasks.append(task)
                        
                        self.log(f"Menunggu 2 menit sebelum memulai akun berikutnya...")
                        await asyncio.sleep(120)

                if tasks:
                    self.log("Semua akun telah dimulai, menunggu penyelesaian...")
                    await asyncio.gather(*tasks)

                self.log(f"{Fore.CYAN + Style.BRIGHT}={Style.RESET_ALL}"*72)
                await self.send_telegram_message("Semua faucet claim telah diproses. Menunggu siklus berikutnya.")
                seconds = 24 * 60 * 60
                while seconds > 0:
                    formatted_time = f"{seconds//3600:02}:{(seconds%3600)//60:02}:{seconds%60:02}"
                    print(
                        f"{Fore.CYAN+Style.BRIGHT}[ Wait for{Style.RESET_ALL}"
                        f"{Fore.WHITE+Style.BRIGHT} {formatted_time} {Style.RESET_ALL}"
                        f"{Fore.CYAN+Style.BRIGHT}... ]{Style.RESET_ALL}"
                        f"{Fore.WHITE+Style.BRIGHT} | {Style.RESET_ALL}"
                        f"{Fore.BLUE+Style.BRIGHT}All Faucet Claims Have Been Processed.{Style.RESET_ALL}",
                        end="\r"
                    )
                    await asyncio.sleep(1)
                    seconds -= 1

        except FileNotFoundError:
            self.log(f"{Fore.RED}File 'accounts.txt' Not Found.{Style.RESET_ALL}")
            return
        except (Exception, ValueError) as e:
            self.log(f"{Fore.RED+Style.BRIGHT}Error: {e}{Style.RESET_ALL}")
            await self.send_telegram_message(f"Faucet claimer berhenti karena kesalahan: {e}")
            raise e

if __name__ == "__main__":
    try:
        bot = KiteAiFaucet()
        asyncio.run(bot.main())
    except KeyboardInterrupt:
        print(
            f"{Fore.CYAN + Style.BRIGHT}[ {datetime.now().astimezone(wib).strftime('%x %X %Z')} ]{Style.RESET_ALL}"
            f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}"
            f"{Fore.RED + Style.BRIGHT}[ EXIT ] Kite Ai Ozone - Faucet Claimer{Style.RESET_ALL}                                       "                              
        ) 