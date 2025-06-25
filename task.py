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

class KiteAi:
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
        self.BITMIND_SUBNET = "0xc368ae279275f80125284d16d292b650ecbbff8d"
        self.BITTE_SUBNET = "0xca312b44a57cc9fd60f37e6c9a343a1ad92a3b6c"
        self.KITE_AI_SUBNET = "0xb132001567650917d6bd695d1fab55db7986e9a5"
        self.CAPTCHA_KEY = None
        self.proxies = []
        self.proxy_index = 0
        self.account_proxies = {}
        self.auth_tokens = {}
        self.access_tokens = {}
        self.header_cookies = {}
        self.agent_lists = []
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
        {Fore.GREEN + Style.BRIGHT}Auto BOT {Fore.BLUE + Style.BRIGHT}Kite Ai Ozone
            """
        )

    def format_seconds(self, seconds):
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
    
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
    
    def load_ai_agents(self):
        filename = "agents.json"
        try:
            if not os.path.exists(filename):
                self.log(f"{Fore.RED}File {filename} Not Found.{Style.RESET_ALL}")
                return

            with open(filename, 'r') as file:
                data = json.load(file)
                if isinstance(data, list):
                    return data
                return []
        except json.JSONDecodeError:
            return []
    
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
    
    def generate_quiz_title(self):
        today = datetime.today().strftime('%Y-%m-%d')
        return f"daily_quiz_{today}"
    
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
        
    def setup_ai_agent(self, agents: list):
        agent = random.choice(agents)

        agent_name = agent["agentName"]
        service_id = agent["serviceId"]
        question = random.choice(agent["questionLists"])

        return agent_name, service_id, question
        
    def generate_inference_payload(self, service_id: str, question: str):
        try:
            payload = {
                "service_id":service_id,
                "subnet":"kite_ai_labs",
                "stream":True,
                "body":{
                    "stream":True,
                    "message":question
                }
            }

            return payload
        except Exception as e:
            raise Exception(f"Generate Inference Payload Failed: {str(e)}")
        
    def generate_receipt_payload(self, address: str, service_id: str, question: str, answer: str):
        try:
            payload = {
                "address":address,
                "service_id":service_id,
                "input":[{
                    "type":"text/plain",
                    "value":question
                }],
                "output":[{
                    "type":"text/plain",
                    "value":answer
                }]
            }

            return payload
        except Exception as e:
            raise Exception(f"Generate Receipt Payload Failed: {str(e)}")
    
    def mask_account(self, account):
        try:
            mask_account = account[:6] + '*' * 6 + account[-6:]
            return mask_account
        except Exception as e:
            return None
    
    async def print_timer(self):
        for remaining in range(random.randint(self.min_delay, self.max_delay), 0, -1):
            print(
                f"{Fore.CYAN + Style.BRIGHT}[ {datetime.now().astimezone(wib).strftime('%x %X %Z')} ]{Style.RESET_ALL}"
                f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}"
                f"{Fore.BLUE + Style.BRIGHT}Wait For{Style.RESET_ALL}"
                f"{Fore.WHITE + Style.BRIGHT} {remaining} {Style.RESET_ALL}"
                f"{Fore.BLUE + Style.BRIGHT}Seconds For Next Interaction...{Style.RESET_ALL}",
                end="\r",
                flush=True
            )
            await asyncio.sleep(1)
    
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
        
    async def create_quiz(self, address: str, proxy=None, retries=5):
        url = f"{self.NEO_API}/quiz/create"
        data = json.dumps({"title":self.generate_quiz_title(), "num":1, "eoa":address})
        headers = {
            **self.headers,
            "Authorization": f"Bearer {self.access_tokens[address]}",
            "Cookie": self.header_cookies[address],
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
                        return await response.json()
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                self.log(
                    f"{Fore.CYAN+Style.BRIGHT}Daily Quiz:{Style.RESET_ALL}"
                    f"{Fore.RED+Style.BRIGHT} GET Id Failed {Style.RESET_ALL}"
                    f"{Fore.MAGENTA+Style.BRIGHT}-{Style.RESET_ALL}"
                    f"{Fore.YELLOW+Style.BRIGHT} {str(e)} {Style.RESET_ALL}"
                )

        return None
        
    async def get_quiz(self, address: str, quiz_id: int, proxy=None, retries=5):
        url = f"{self.NEO_API}/quiz/get?id={quiz_id}&eoa={address}"
        headers = {
            **self.headers,
            "Authorization": f"Bearer {self.access_tokens[address]}",
            "Cookie": self.header_cookies[address]
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
                    f"{Fore.MAGENTA + Style.BRIGHT}  ● {Style.RESET_ALL}"
                    f"{Fore.BLUE + Style.BRIGHT}Status  :{Style.RESET_ALL}"
                    f"{Fore.RED+Style.BRIGHT} GET Question & Answer Failed {Style.RESET_ALL}"
                    f"{Fore.MAGENTA+Style.BRIGHT}-{Style.RESET_ALL}"
                    f"{Fore.YELLOW+Style.BRIGHT} {str(e)} {Style.RESET_ALL}"
                )

        return None
            
    async def submit_quiz(self, address: str, quiz_id: int, question_id: int, quiz_answer: str, proxy=None, retries=5):
        url = f"{self.NEO_API}/quiz/submit"
        data = json.dumps({"quiz_id":quiz_id, "question_id":question_id, "answer":quiz_answer, "finish":True, "eoa":address})
        headers = {
            **self.headers,
            "Authorization": f"Bearer {self.access_tokens[address]}",
            "Cookie": self.header_cookies[address],
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
                        return await response.json()
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                self.log(
                    f"{Fore.MAGENTA + Style.BRIGHT}  ● {Style.RESET_ALL}"
                    f"{Fore.BLUE + Style.BRIGHT}Status  :{Style.RESET_ALL}"
                    f"{Fore.RED+Style.BRIGHT} Submit Answer Failed {Style.RESET_ALL}"
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
            
    async def stake_token(self, address: str, amount: float, proxy=None, retries=5):
        url = f"{self.OZONE_API}/subnet/delegate"
        data = json.dumps({"subnet_address":self.KITE_AI_SUBNET, "amount":amount})
        headers = {
            **self.headers,
            "Authorization": f"Bearer {self.access_tokens[address]}",
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
                        return await response.json()
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                self.log(
                    f"{Fore.CYAN+Style.BRIGHT}Stake     :{Style.RESET_ALL}"
                    f"{Fore.RED+Style.BRIGHT} Failed {Style.RESET_ALL}"
                    f"{Fore.MAGENTA+Style.BRIGHT}-{Style.RESET_ALL}"
                    f"{Fore.YELLOW+Style.BRIGHT} {str(e)} {Style.RESET_ALL}"
                )

        return None
            
    async def claim_stake_rewards(self, address: str, proxy=None, retries=5):
        url = f"{self.OZONE_API}/subnet/claim-rewards"
        data = json.dumps({"subnet_address":self.KITE_AI_SUBNET})
        headers = {
            **self.headers,
            "Authorization": f"Bearer {self.access_tokens[address]}",
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
                        return await response.json()
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                self.log(
                    f"{Fore.CYAN+Style.BRIGHT}Unstake   :{Style.RESET_ALL}"
                    f"{Fore.RED+Style.BRIGHT} Failed {Style.RESET_ALL}"
                    f"{Fore.MAGENTA+Style.BRIGHT}-{Style.RESET_ALL}"
                    f"{Fore.YELLOW+Style.BRIGHT} {str(e)} {Style.RESET_ALL}"
                )

        return None
            
    async def agent_inference(self, address: str, service_id: str, question: str, use_proxy: bool, rotate_proxy: bool, proxy=None, retries=5):
        url = f"{self.OZONE_API}/agent/inference"
        data = json.dumps(self.generate_inference_payload(service_id, question))
        headers = {
            **self.headers,
            "Authorization": f"Bearer {self.access_tokens[address]}",
            "Content-Length": str(len(data)),
            "Content-Type": "application/json"
        }
        await asyncio.sleep(3)
        for attempt in range(retries):
            connector = ProxyConnector.from_url(proxy) if proxy else None
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.post(url=url, headers=headers, data=data) as response:
                        if response.status == 401:
                            await self.process_user_signin(address, use_proxy, rotate_proxy)
                            headers["Authorization"] = f"Bearer {self.access_tokens[address]}"
                            continue

                        response.raise_for_status()
                        result = ""

                        async for line in response.content:
                            line = line.decode("utf-8").strip()
                            if line.startswith("data:"):
                                try:
                                    json_data = json.loads(line[len("data:"):].strip())
                                    delta = json_data.get("choices", [{}])[0].get("delta", {})
                                    content = delta.get("content")
                                    if content:
                                        result += content
                                except json.JSONDecodeError:
                                    continue

                        return result
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                self.log(
                    f"{Fore.MAGENTA + Style.BRIGHT}  ● {Style.RESET_ALL}"
                    f"{Fore.BLUE + Style.BRIGHT}Status  :{Style.RESET_ALL}"
                    f"{Fore.RED+Style.BRIGHT} Agents Didn't Respond {Style.RESET_ALL}"
                    f"{Fore.MAGENTA+Style.BRIGHT}-{Style.RESET_ALL}"
                    f"{Fore.YELLOW+Style.BRIGHT} {str(e)} {Style.RESET_ALL}"
                )

        return None
            
    async def submit_receipt(self, address: str, sa_address: str, service_id: str, question: str, answer: str, proxy=None, retries=5):
        url = f"{self.NEO_API}/submit_receipt"
        data = json.dumps(self.generate_receipt_payload(sa_address, service_id, question, answer))
        headers = {
            **self.headers,
            "Authorization": f"Bearer {self.access_tokens[address]}",
            "Cookie": self.header_cookies[address],
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
                        return await response.json()
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                self.log(
                    f"{Fore.MAGENTA + Style.BRIGHT}  ● {Style.RESET_ALL}"
                    f"{Fore.BLUE + Style.BRIGHT}Status  :{Style.RESET_ALL}"
                    f"{Fore.RED+Style.BRIGHT} Submit Receipt Failed {Style.RESET_ALL}"
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
        
    async def process_accounts(self, account_index: int, address: str, use_proxy: bool, rotate_proxy: bool):
        quiz_status = "Skipped"
        stake_status = "Skipped"
        unstake_status = "Skipped"
        agent_status_str = "0/30 Successful"
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
        sa_address = user.get("data", {}).get("profile", {}).get("smart_account_address", "Undefined")
        xp_balance = user.get("data", {}).get("profile", {}).get("total_xp_points", 0)
        
        self.log(
            f"{Fore.CYAN+Style.BRIGHT}Username  :{Style.RESET_ALL}"
            f"{Fore.WHITE+Style.BRIGHT} {username} {Style.RESET_ALL}"
        )
        self.log(
            f"{Fore.CYAN+Style.BRIGHT}SA Address:{Style.RESET_ALL}"
            f"{Fore.WHITE+Style.BRIGHT} {self.mask_account(sa_address)} {Style.RESET_ALL}"
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

        create = await self.create_quiz(address, proxy)
        self.log(f"{Fore.CYAN+Style.BRIGHT}Daily Quiz:{Style.RESET_ALL}")
        if create:
            status = create.get("data", {}).get("status")
            if status == 0:
                quiz_id = create.get("data", {}).get("quiz_id")
                quiz = await self.get_quiz(address, quiz_id, proxy)
                if quiz:
                    quiz_questions = quiz.get("data", {}).get("question", [])
                    all_correct = True
                    if not quiz_questions:
                        quiz_status = "Failed (No Questions)"
                    else:
                        for quiz_question in quiz_questions:
                            question_id, content, answer = quiz_question.get("question_id"), quiz_question.get("content"), quiz_question.get("answer")
                            self.log(f"{Fore.MAGENTA + Style.BRIGHT}  ● {Style.RESET_ALL}{Fore.BLUE + Style.BRIGHT}Question:{Style.RESET_ALL}{Fore.WHITE+Style.BRIGHT} {content} {Style.RESET_ALL}")
                            self.log(f"{Fore.MAGENTA + Style.BRIGHT}  ● {Style.RESET_ALL}{Fore.BLUE + Style.BRIGHT}Answer  :{Style.RESET_ALL}{Fore.WHITE+Style.BRIGHT} {answer} {Style.RESET_ALL}")
                            submit = await self.submit_quiz(address, quiz_id, question_id, answer, proxy)
                            if not submit or submit.get("data", {}).get("result") != "RIGHT":
                                all_correct = False
                                self.log(f"{Fore.MAGENTA + Style.BRIGHT}  ● {Style.RESET_ALL}{Fore.RED+Style.BRIGHT}Wrong Answer / Failed to Submit{Style.RESET_ALL}")
                                break
                            self.log(f"{Fore.MAGENTA + Style.BRIGHT}  ● {Style.RESET_ALL}{Fore.GREEN+Style.BRIGHT}Answered Successfully{Style.RESET_ALL}")
                        quiz_status = "Answered Successfully" if all_correct else "Wrong Answer"
                else:
                    quiz_status = "Failed (Get Quiz)"
            else:
                quiz_status = "Already Answered"
            self.log(f"{Fore.YELLOW+Style.BRIGHT}{quiz_status}{Style.RESET_ALL}")
        else:
            quiz_status = "Failed (Create Quiz)"
            self.log(f"{Fore.RED+Style.BRIGHT}{quiz_status}{Style.RESET_ALL}")

        balance_stake_data = await self.token_balance(address, proxy)
        self.log(f"{Fore.CYAN+Style.BRIGHT}Stake     :{Style.RESET_ALL}")
        if balance_stake_data:
            kite_balance_for_stake = balance_stake_data.get("data", {}).get("balances", {}).get("kite", 0)
            min_stake = 0.01
            max_stake = 0.1
            if kite_balance_for_stake >= min_stake:
                amount_to_stake = round(random.uniform(min_stake, max_stake), 4)
                if kite_balance_for_stake >= amount_to_stake:
                    self.log(f"{Fore.YELLOW+Style.BRIGHT}Attempting to stake {amount_to_stake} KITE...{Style.RESET_ALL}")
                    stake = await self.stake_token(address, amount_to_stake, proxy)
                    stake_status = f"Success ({amount_to_stake} KITE)" if stake else "Failed"
                else:
                    stake_status = f"Insufficient balance for random stake ({amount_to_stake} KITE)"
            else:
                stake_status = "Insufficient Balance for staking (min 0.01 KITE)"
        else:
            stake_status = "Failed (Get Balance)"
        self.log(f"{Fore.YELLOW+Style.BRIGHT}{stake_status}{Style.RESET_ALL}")

        self.log(f"{Fore.CYAN+Style.BRIGHT}Unstake   :{Style.RESET_ALL}")
        unstake = await self.claim_stake_rewards(address, proxy)
        if unstake:
            unstake_status = "Success"
        else:
            unstake_status = "Failed"
        self.log(f"{Fore.YELLOW+Style.BRIGHT}{unstake_status}{Style.RESET_ALL}")
        
        self.log(f"{Fore.CYAN+Style.BRIGHT}AI Agents :{Style.RESET_ALL}")
        success_count = 0
        while success_count < 30:
            self.log(f"{Fore.MAGENTA+Style.BRIGHT}  ● {Style.RESET_ALL}{Fore.GREEN+Style.BRIGHT}Interactions{Style.RESET_ALL}{Fore.WHITE+Style.BRIGHT} {success_count+1}/30 {Style.RESET_ALL}")
            agent = random.choice(self.agent_lists)
            question = random.choice(agent["questionLists"])
            self.log(f"{Fore.BLUE+Style.BRIGHT}    AI Agent: {Style.RESET_ALL}{Fore.WHITE+Style.BRIGHT}{agent['agentName']}{Style.RESET_ALL}")
            self.log(f"{Fore.BLUE+Style.BRIGHT}    Question: {Style.RESET_ALL}{Fore.WHITE+Style.BRIGHT}{question}{Style.RESET_ALL}")
            answer = await self.agent_inference(address, agent["serviceId"], question, use_proxy, rotate_proxy, proxy)
            if answer:
                self.log(f"{Fore.BLUE+Style.BRIGHT}    Answer  : {Style.RESET_ALL}{Fore.WHITE+Style.BRIGHT}{answer.strip()}{Style.RESET_ALL}")
                submit = await self.submit_receipt(address, sa_address, agent["serviceId"], question, answer, proxy)
                if submit:
                    success_count += 1
                    self.log(f"{Fore.BLUE+Style.BRIGHT}    Status  : {Style.RESET_ALL}{Fore.GREEN+Style.BRIGHT}Receipt Submited Successfully{Style.RESET_ALL}")
            await self.print_timer()
        agent_status_str = f"{success_count}/30 Successful"

        final_message = f"👤 Wallet {account_index}: {masked_address}\n"
        final_message += f"💰 Balance: {xp_balance} XP\n"
        final_message += f"💎 KITE: {kite_balance}\n"
        final_message += f"💵 USDT: {usdt_balance}\n"
        quiz_emoji = "✅" if quiz_status == "Answered Successfully" else "❌"
        final_message += f"{quiz_emoji} Daily Quiz: {quiz_status}\n"
        stake_emoji = "✅" if stake_status == "Success" else "❌"
        final_message += f"{stake_emoji} Stake: {stake_status}\n"
        unstake_emoji = "✅" if unstake_status == "Success" else "❌"
        final_message += f"{unstake_emoji} Unstake: {unstake_status}\n"
        final_message += f"🤖 AI Agents: {agent_status_str}"

        await self.send_telegram_message(final_message)

    async def main(self):
        try:
            with open('accounts.txt', 'r') as file:
                accounts = [line.strip() for line in file if line.strip()]

            captcha_key = self.load_captcha_key()
            if captcha_key:
                self.CAPTCHA_KEY = captcha_key

            agents = self.load_ai_agents()
            if not agents:
                self.log(f"{Fore.RED + Style.BRIGHT}No Agents Loaded.{Style.RESET_ALL}")
                return
            
            self.agent_lists = agents
            
            self.load_telegram_config()
            
            choose, rotate_proxy = self.print_question()

            while True:
                use_proxy = False
                if choose in [1, 2]:
                    use_proxy = True

                self.clear_terminal()
                self.welcome()
                self.log(
                    f"{Fore.GREEN + Style.BRIGHT}Account's Total: {Style.RESET_ALL}"
                    f"{Fore.WHITE + Style.BRIGHT}{len(accounts)}{Style.RESET_ALL}"
                )

                if use_proxy:
                    await self.load_proxies(choose)
                
                tasks = []
                for i, address in enumerate(accounts, 1):
                    if address:
                        auth_token = self.generate_auth_token(address)
                        if not auth_token:
                            self.log(f"{Fore.RED+Style.BRIGHT}Gagal membuat token otentikasi untuk {self.mask_account(address)}, melompat.{Style.RESET_ALL}")
                            continue
                        
                        self.auth_tokens[address] = auth_token
                        
                        self.log(f"{Fore.YELLOW}Menjadwalkan akun {i} ({self.mask_account(address)}) untuk dijalankan.{Style.RESET_ALL}")
                        
                        task = asyncio.create_task(self.process_accounts(i, address, use_proxy, rotate_proxy))
                        tasks.append(task)
                        
                        self.log(f"Menunggu 2 menit sebelum memulai akun berikutnya...")
                        await asyncio.sleep(120)

                if tasks:
                    self.log("Semua akun telah dimulai, menunggu penyelesaian...")
                    await asyncio.gather(*tasks)

                self.log(f"{Fore.CYAN + Style.BRIGHT}={Style.RESET_ALL}"*72)
                await self.send_telegram_message("Semua akun telah diproses. Menunggu siklus berikutnya.")
                seconds = 24 * 60 * 60
                while seconds > 0:
                    formatted_time = self.format_seconds(seconds)
                    print(
                        f"{Fore.CYAN+Style.BRIGHT}[ Wait for{Style.RESET_ALL}"
                        f"{Fore.WHITE+Style.BRIGHT} {formatted_time} {Style.RESET_ALL}"
                        f"{Fore.CYAN+Style.BRIGHT}... ]{Style.RESET_ALL}"
                        f"{Fore.WHITE+Style.BRIGHT} | {Style.RESET_ALL}"
                        f"{Fore.BLUE+Style.BRIGHT}All Accounts Have Been Processed.{Style.RESET_ALL}",
                        end="\r"
                    )
                    await asyncio.sleep(1)
                    seconds -= 1

        except FileNotFoundError:
            self.log(f"{Fore.RED}File 'accounts.txt' Not Found.{Style.RESET_ALL}")
            return
        except (Exception, ValueError) as e:
            self.log(f"{Fore.RED+Style.BRIGHT}Error: {e}{Style.RESET_ALL}")
            await self.send_telegram_message(f"Bot berhenti karena kesalahan: {e}")
            raise e

if __name__ == "__main__":
    try:
        bot = KiteAi()
        asyncio.run(bot.main())
    except KeyboardInterrupt:
        print(
            f"{Fore.CYAN + Style.BRIGHT}[ {datetime.now().astimezone(wib).strftime('%x %X %Z')} ]{Style.RESET_ALL}"
            f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}"
            f"{Fore.RED + Style.BRIGHT}[ EXIT ] Kite Ai Ozone - BOT{Style.RESET_ALL}                                       "                              
        )