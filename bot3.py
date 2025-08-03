from web3 import Web3
from web3.exceptions import TransactionNotFound
from eth_account import Account
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from aiohttp import ClientResponseError, ClientSession, ClientTimeout, BasicAuth
from aiohttp_socks import ProxyConnector
from fake_useragent import FakeUserAgent
from http.cookies import SimpleCookie
from datetime import datetime, timezone, timedelta
from colorama import Fore, Style, init
import asyncio, binascii, random, json, re, os, pytz
from dotenv import load_dotenv

init(autoreset=True)
load_dotenv()

class Colors:
    RESET = Style.RESET_ALL
    BOLD = Style.BRIGHT
    GREEN = Fore.GREEN
    YELLOW = Fore.YELLOW
    RED = Fore.RED
    CYAN = Fore.CYAN
    MAGENTA = Fore.MAGENTA
    WHITE = Fore.WHITE
    BLUE = Fore.BLUE
    BRIGHT_GREEN = Fore.LIGHTGREEN_EX
    BRIGHT_MAGENTA = Fore.LIGHTMAGENTA_EX
    BRIGHT_WHITE = Fore.LIGHTWHITE_EX
    BRIGHT_BLACK = Fore.LIGHTBLACK_EX

class Logger:
    @staticmethod
    def log(label, symbol, msg, color):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{Colors.BRIGHT_BLACK}[{timestamp}]{Colors.RESET} {color}[{symbol}] {msg}{Colors.RESET}")

    @staticmethod
    def info(msg): Logger.log("INFO", "✓", msg, Colors.GREEN)
    @staticmethod
    def warn(msg): Logger.log("WARN", "!", msg, Colors.YELLOW)
    @staticmethod
    def error(msg): Logger.log("ERR", "✗", msg, Colors.RED)
    @staticmethod
    def success(msg): Logger.log("OK", "+", msg, Colors.GREEN)
    @staticmethod
    def loading(msg): Logger.log("LOAD", "⟳", msg, Colors.CYAN)
    @staticmethod
    def step(msg): Logger.log("STEP", "➤", msg, Colors.WHITE)
    @staticmethod
    def action(msg): Logger.log("ACTION", "↪️", msg, Colors.CYAN)
    @staticmethod
    def actionSuccess(msg): Logger.log("ACTION", "✅", msg, Colors.GREEN)

logger = Logger()

def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')

async def display_welcome_screen():
    clear_console()
    now = datetime.now()
    print(f"{Colors.BRIGHT_GREEN}{Colors.BOLD}")
    print("  ╔══════════════════════════════════════╗")
    print("  ║           KITE AI  B O T            ║")
    print("  ║                                      ║")
    print(f"  ║     {Colors.YELLOW}{now.strftime('%H:%M:%S %d.%m.%Y')}{Colors.BRIGHT_GREEN}           ║")
    print("  ║                                      ║")
    print("  ║     Kiteai TESTNET AUTOMATION         ║")
    print(f"  ║   {Colors.BRIGHT_WHITE}ZonaAirdrop{Colors.BRIGHT_GREEN}  |  t.me/ZonaAirdr0p   ║")
    print("  ╚══════════════════════════════════════╝")
    print(f"{Colors.RESET}")
    await asyncio.sleep(1)

class KiteAi:
    def __init__(self) -> None:
        self.KITE_AI = {
            "name": "KITE AI",
            "rpc_url": "https://rpc-testnet.gokite.ai/",
            "explorer": "https://testnet.kitescan.ai/tx/",
            "tokens": [
                { "type": "native", "ticker": "KITE", "address": "0x0BBB7293c08dE4e62137a557BC40bc12FA1897d6" },
                { "type": "erc20", "ticker": "Bridged ETH", "address": "0x7AEFdb35EEaAD1A15E869a6Ce0409F26BFd31239" }
            ],
            "chain_id": 2368
        }
        self.BASE_SEPOLIA = {
            "name": "BASE SEPOLIA",
            "rpc_url": "https://base-sepolia-rpc.publicnode.com/",
            "explorer": "https://sepolia.basescan.org/tx/",
            "tokens": [
                { "type": "native", "ticker": "ETH", "address": "0x226D7950D4d304e749b0015Ccd3e2c7a4979bB7C" },
                { "type": "erc20", "ticker": "Bridged KITE", "address": "0xFB9a6AF5C014c32414b4a6e208a89904c6dAe266" }
            ],
            "chain_id": 84532
        }
        self.NATIVE_CONTRACT_ABI = json.loads('''[
            {"type":"function","name":"send","stateMutability":"payable","inputs":[{"name":"_destChainId","type":"uint256"},{"name":"_recipient","type":"address"},{"name":"_amount","type":"uint256"}],"outputs":[]}
        ]''')
        self.ERC20_CONTRACT_ABI = json.loads('''[
            {"type":"function","name":"send","stateMutability":"nonpayable","inputs":[{"name":"_destChainId","type":"uint256"},{"name":"_recipient","type":"address"},{"name":"_amount","type":"uint256"}],"outputs":[]},
            {"type":"function","name":"balanceOf","stateMutability":"view","inputs":[{"name":"address","type":"address"}],"outputs":[{"name":"","type":"uint256"}]},
            {"type":"function","name":"allowance","stateMutability":"view","inputs":[{"name":"owner","type":"address"},{"name":"spender","type":"address"}],"outputs":[{"name":"","type":"uint256"}]},
            {"type":"function","name":"approve","stateMutability":"nonpayable","inputs":[{"name":"spender","type":"address"},{"name":"amount","type":"uint256"}],"outputs":[{"name":"","type":"bool"}]},
            {"type":"function","name":"decimals","stateMutability":"view","inputs":[],"outputs":[{"name":"","type":"uint8"}]}
        ]''')
        self.SWAP_ROUTER = "0x04CfcA82fDf5F4210BC90f06C44EF25Bf743D556"
        self.USDT_CONTRACT = "0x0fF5393387ad2f9f691FD6Fd28e07E3969e27e63"
        self.WKITE_CONTRACT = "0x3bC8f037691Ce1d28c0bB224BD33563b49F99dE8"
        
        # Updated SWAP_ABI based on the full ABI you provided
        self.SWAP_ABI = json.loads('''[
            {
                "inputs": [
                    {"internalType":"address","name":"token","type":"address"},
                    {"internalType":"uint256","name":"amount","type":"uint256"},
                    {
                        "components": [
                            {"internalType":"uint256","name":"sourceId","type":"uint256"},
                            {"internalType":"address","name":"receiver","type":"address"},
                            {"internalType":"bool","name":"payableReceiver","type":"bool"},
                            {"internalType":"address","name":"rollbackReceiver","type":"address"},
                            {"internalType":"uint256","name":"rollbackTeleporterFee","type":"uint256"},
                            {"internalType":"uint256","name":"rollbackGasLimit","type":"uint256"},
                            {
                                "components": [
                                    {"internalType":"enum Action","name":"action","type":"uint8"},
                                    {"internalType":"uint256","name":"requiredGasLimit","type":"uint256"},
                                    {"internalType":"uint256","name":"recipientGasLimit","type":"uint256"},
                                    {"internalType":"bytes","name":"trade","type":"bytes"},
                                    {
                                        "components": [
                                            {"internalType":"address","name":"bridgeSourceChain","type":"address"},
                                            {"internalType":"bool","name":"sourceBridgeIsNative","type":"bool"},
                                            {"internalType":"address","name":"bridgeDestinationChain","type":"address"},
                                            {"internalType":"address","name":"cellDestinationChain","type":"address"},
                                            {"internalType":"bytes32","name":"destinationBlockchainID","type":"bytes32"},
                                            {"internalType":"uint256","name":"teleporterFee","type":"uint256"},
                                            {"internalType":"uint256","name":"secondaryTeleporterFee","type":"uint256"}
                                        ],
                                        "internalType":"struct BridgePath","name":"bridgePath","type":"tuple"
                                    }
                                ],
                                "internalType":"struct Hop[]","name":"hops","type":"tuple[]"
                            }
                        ],
                        "internalType":"struct Instructions","name":"instructions","type":"tuple"
                    }
                ],
                "name": "initiate",
                "outputs": [],
                "stateMutability": "payable",
                "type": "function"
            }
        ]''')
        
        self.TESTNET_API = "https://testnet.gokite.ai"
        self.BRIDGE_API = "https://bridge-backend.prod.gokite.ai"
        self.NEO_API = "https://neo.prod.gokite.ai/v2"
        self.OZONE_API = "https://ozone-point-system.prod.gokite.ai"
        self.SITE_KEY = "6Lc_VwgrAAAAALtx_UtYQnW-cFg8EPDgJ8QVqkaz"
        self.KITE_AI_SUBNET = "0xb132001567650917d6bd695d1fab55db7986e9a5"
        self.CAPTCHA_KEY = None
        self.TESTNET_HEADERS = {}
        self.BRIDGE_HEADERS = {}
        self.proxies = []
        self.proxy_index = 0
        self.account_proxies = {}
        self.auth_tokens = {}
        self.header_cookies = {}
        self.access_tokens = {}
        self.auto_faucet = False
        self.auto_quiz = False
        self.auto_stake = False
        self.auto_unstake = False
        self.auto_chat = False
        self.auto_bridge = False
        self.auto_swap = False
        self.chat_count = 0
        self.bridge_count = 0
        self.swap_count = 0
        self.min_bridge_amount = 0
        self.max_bridge_amount = 0
        self.min_swap_amount = 0
        self.max_swap_amount = 0
        self.agent_lists = []

    # ... [Keep all your existing methods unchanged until process_option_7]

    async def process_option_7(self, account: str, address: str, use_proxy: bool):
        logger.step("Random Swap:")

        for i in range(self.swap_count):
            logger.info(f"Swap {i+1} / {self.swap_count}")

            # Alternate between directions for each swap
            if i % 2 == 0:  # First swap is WKITE->USDT
                token_in = self.WKITE_CONTRACT
                token_out = "USDT"
                min_amount = self.min_swap_amount
                max_amount = self.max_swap_amount
            else:  # Second swap is USDT->WKITE
                token_in = self.USDT_CONTRACT
                token_out = "WKITE"
                min_amount = self.min_swap_amount
                max_amount = self.max_swap_amount

            amount = round(random.uniform(min_amount, max_amount), 6)

            balance = await self.get_token_balance(address, self.KITE_AI["rpc_url"], token_in, "erc20", use_proxy)

            logger.info(f"    Pair    : {token_out}->{token_in[:6]}...")
            logger.info(f"    Balance : {balance} {token_out}")
            logger.info(f"    Amount  : {amount} {token_out}")

            if not balance or balance <= amount:
                logger.warn(f"Insufficient {token_out} Token Balance. Skipping swap.")
                continue

            try:
                # Build instructions tuple
                instructions = (
                    1,  # sourceId
                    address,  # receiver
                    True,  # payableReceiver
                    address,  # rollbackReceiver
                    Web3.to_wei(0.001, 'ether'),  # rollbackTeleporterFee
                    100000,  # rollbackGasLimit
                    []  # empty hops array for simple swap
                )

                tx_hash, block_number, amount_to_wei = await self.perform_swap(
                    account, 
                    address, 
                    self.KITE_AI["rpc_url"], 
                    token_in, 
                    amount, 
                    instructions,
                    use_proxy
                )
                
                if tx_hash and block_number and amount_to_wei:
                    logger.info("Swap Transaction Success")
                    print(f"{Colors.CYAN}↪️ Tx hash {tx_hash} ✅ Explore {self.KITE_AI['explorer']}{tx_hash}{Colors.RESET}")
                else:
                    logger.error("Perform On-Chain Swap Failed")
                    
            except Exception as e:
                logger.error(f"Swap failed: {str(e)}")
                
            await self.print_timer("Tx")

    async def perform_swap(self, account: str, address: str, rpc_url: str, token_in: str, amount: float, instructions: tuple, use_proxy: bool):
        try:
            web3 = await self.get_web3_with_check(address, rpc_url, use_proxy)

            router_contract = web3.eth.contract(
                address=web3.to_checksum_address(self.SWAP_ROUTER),
                abi=self.SWAP_ABI
            )

            amount_to_wei = web3.to_wei(amount, "ether")
            
            swap_data = router_contract.functions.initiate(
                web3.to_checksum_address(token_in),
                amount_to_wei,
                instructions
            )

            estimated_gas = swap_data.estimate_gas({"from": address})

            max_priority_fee = web3.to_wei(0.001, "gwei")
            max_fee = max_priority_fee

            tx_data = {
                "from": address,
                "gas": int(estimated_gas * 1.2),
                "maxFeePerGas": int(max_fee),
                "maxPriorityFeePerGas": int(max_priority_fee),
                "nonce": web3.eth.get_transaction_count(address, "pending"),
                "chainId": web3.eth.chain_id,
            }

            swap_tx = swap_data.build_transaction(tx_data)

            tx_hash = await self.send_raw_transaction_with_retries(account, web3, swap_tx)
            receipt = await self.wait_for_receipt_with_retries(web3, tx_hash)

            block_number = receipt.blockNumber

            return tx_hash, block_number, amount_to_wei

        except Exception as e:
            logger.error(f"Perform swap failed: {str(e)}")
            return None, None, None

    # ... [Keep all your remaining methods unchanged]

if __name__ == "__main__":
    try:
        bot = KiteAi()
        asyncio.run(bot.main())
    except KeyboardInterrupt:
        logger.error("[ EXIT ] Kite Ai Ozone - BOT")
