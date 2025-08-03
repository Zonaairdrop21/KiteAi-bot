from web3 import Web3
from eth_abi import encode_abi
from eth_utils import function_signature_to_4byte_selector
from hexbytes import HexBytes

# ... [keep all previous imports and code until the SWAP_ABI]

class KiteAi:
    def __init__(self) -> None:
        # ... [keep all previous init code until SWAP_ABI]
        
        # Simplified SWAP_ABI that matches the contract
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
                                    {"internalType":"uint8","name":"action","type":"uint8"},
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

    # ... [keep all other methods until process_option_7]

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
                # Build instructions tuple with empty hops for simple swap
                instructions = (
                    1,                          # sourceId
                    address,                    # receiver
                    True,                       # payableReceiver
                    address,                    # rollbackReceiver
                    Web3.to_wei(0.001, 'ether'), # rollbackTeleporterFee
                    100000,                     # rollbackGasLimit
                    []                          # empty hops array
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

            # Create contract instance with the correct ABI
            router_contract = web3.eth.contract(
                address=web3.to_checksum_address(self.SWAP_ROUTER),
                abi=self.SWAP_ABI
            )

            amount_to_wei = web3.to_wei(amount, "ether")
            
            # Manually encode the function call to ensure proper tuple encoding
            function = router_contract.functions.initiate
            args = [web3.to_checksum_address(token_in), amount_to_wei, instructions]
            
            # Build transaction data manually
            data = function(*args)._encode_transaction_data()
            
            # Estimate gas
            try:
                estimated_gas = web3.eth.estimate_gas({
                    'from': address,
                    'to': self.SWAP_ROUTER,
                    'data': data
                })
            except Exception as e:
                logger.error(f"Gas estimation failed: {str(e)}")
                estimated_gas = 200000  # fallback gas limit

            max_priority_fee = web3.to_wei(0.001, "gwei")
            max_fee = max_priority_fee

            tx_data = {
                "from": address,
                "to": self.SWAP_ROUTER,
                "data": data,
                "gas": int(estimated_gas * 1.2),
                "maxFeePerGas": int(max_fee),
                "maxPriorityFeePerGas": int(max_priority_fee),
                "nonce": web3.eth.get_transaction_count(address, "pending"),
                "chainId": web3.eth.chain_id,
            }

            # Sign and send transaction
            signed_tx = web3.eth.account.sign_transaction(tx_data, account)
            tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            tx_hash = web3.to_hex(tx_hash)
            
            # Wait for receipt
            receipt = await self.wait_for_receipt_with_retries(web3, tx_hash)

            block_number = receipt.blockNumber

            return tx_hash, block_number, amount_to_wei

        except Exception as e:
            logger.error(f"Perform swap failed: {str(e)}")
            return None, None, None

    # ... [keep all remaining methods]
