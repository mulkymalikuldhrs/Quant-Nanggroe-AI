"""
⛓️ Web3 Plugin Agent - Blockchain & Smart Contract Integration
Ethereum-compatible network interactions, DeFi reads, wallet queries, and gas estimation

Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩
"""

import asyncio
import os
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

# Optional: web3.py for on-chain interactions
try:
    from web3 import Web3  # type: ignore
    from web3.exceptions import ContractLogicError  # type: ignore
    _WEB3_AVAILABLE = True
except ImportError:
    _WEB3_AVAILABLE = False

# Optional: aiohttp for HTTP-based RPC calls as a fallback
try:
    import aiohttp
    _AIOHTTP_AVAILABLE = True
except ImportError:
    _AIOHTTP_AVAILABLE = False


# ── Well-known network configurations ───────────────────────────────

NETWORK_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "ethereum": {
        "chain_id": 1,
        "currency": "ETH",
        "rpc_env": "ETH_RPC_URL",
        "rpc_default": "https://eth.llamarpc.com",
        "explorer": "https://etherscan.io",
    },
    "goerli": {
        "chain_id": 5,
        "currency": "ETH",
        "rpc_env": "GOERLI_RPC_URL",
        "rpc_default": "https://rpc.ankr.com/eth_goerli",
        "explorer": "https://goerli.etherscan.io",
    },
    "sepolia": {
        "chain_id": 11155111,
        "currency": "ETH",
        "rpc_env": "SEPOLIA_RPC_URL",
        "rpc_default": "https://rpc.ankr.com/eth_sepolia",
        "explorer": "https://sepolia.etherscan.io",
    },
    "polygon": {
        "chain_id": 137,
        "currency": "MATIC",
        "rpc_env": "POLYGON_RPC_URL",
        "rpc_default": "https://polygon-rpc.com",
        "explorer": "https://polygonscan.com",
    },
    "bsc": {
        "chain_id": 56,
        "currency": "BNB",
        "rpc_env": "BSC_RPC_URL",
        "rpc_default": "https://bsc-dataseed.binance.org",
        "explorer": "https://bscscan.com",
    },
    "arbitrum": {
        "chain_id": 42161,
        "currency": "ETH",
        "rpc_env": "ARBITRUM_RPC_URL",
        "rpc_default": "https://arb1.arbitrum.io/rpc",
        "explorer": "https://arbiscan.io",
    },
    "optimism": {
        "chain_id": 10,
        "currency": "ETH",
        "rpc_env": "OPTIMISM_RPC_URL",
        "rpc_default": "https://mainnet.optimism.io",
        "explorer": "https://optimistic.etherscan.io",
    },
    "avalanche": {
        "chain_id": 43114,
        "currency": "AVAX",
        "rpc_env": "AVAX_RPC_URL",
        "rpc_default": "https://api.avax.network/ext/bc/C/rpc",
        "explorer": "https://snowtrace.io",
    },
}

# ERC-20 minimal ABI (balanceOf, decimals, symbol, name, totalSupply)
ERC20_MINIMAL_ABI: List[Dict[str, Any]] = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "name",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "totalSupply",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
]

# Well-known ERC-20 tokens per chain
KNOWN_TOKENS: Dict[str, Dict[str, str]] = {
    "ethereum": {
        "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
        "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "DAI": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
        "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
    },
    "polygon": {
        "USDT": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",
        "USDC": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",
        "DAI": "0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063",
        "WMATIC": "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",
    },
    "bsc": {
        "USDT": "0x55d398326f99059fF775485246999027B3197955",
        "USDC": "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d",
        "BUS": "0xe9e7CEA3DedcA5984780Bafc599bD69ADd0862799",
        "WBNB": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",
    },
}


class Web3Plugin:
    """
    Web3 / Blockchain Agent that:
    - Connects to Ethereum-compatible networks via Web3
    - Reads smart contract data (view/pure functions)
    - Queries wallet native & token balances
    - Estimates gas costs for transactions
    - Reads DeFi protocol data (read-only for safety)
    - Supports multiple networks (Ethereum, Polygon, BSC, etc.)
    - Has configurable RPC endpoints from environment variables
    """

    def __init__(self):
        self.agent_id = "web3_plugin"
        self.name = "Web3 Agent"
        self.status = "ready"
        self.capabilities = [
            "smart_contracts",
            "blockchain",
            "defi",
            "nft",
            "wallet_queries",
            "gas_estimation",
            "token_info",
            "multi_chain",
        ]

        # Default network
        self.default_network = os.getenv("WEB3_DEFAULT_NETWORK", "ethereum")

        # Cached Web3 instances keyed by network name
        self._w3_instances: Dict[str, Any] = {}

        # Performance tracking
        self._stats = {
            "total_tasks": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "rpc_calls": 0,
            "avg_response_time": 0.0,
        }

    # ------------------------------------------------------------------
    # Web3 connection management
    # ------------------------------------------------------------------

    def _get_w3(self, network: str) -> Any:
        """
        Return a cached Web3 instance for the given network.
        Returns None if web3.py is unavailable or RPC cannot be reached.
        """
        if not _WEB3_AVAILABLE:
            return None

        if network in self._w3_instances:
            return self._w3_instances[network]

        net_config = NETWORK_DEFAULTS.get(network)
        if not net_config:
            return None

        rpc_url = os.getenv(net_config["rpc_env"], net_config["rpc_default"])
        provider = Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 30})
        w3 = Web3(provider)
        self._w3_instances[network] = w3
        return w3

    def _resolve_network(self, task: Dict[str, Any]) -> str:
        """Determine the target network from a task dict."""
        return task.get("network", self.default_network)

    # ------------------------------------------------------------------
    # Public task dispatcher
    # ------------------------------------------------------------------

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Route a task dictionary to the appropriate handler."""
        try:
            action = task.get("action", "get_balance")

            handlers = {
                "get_balance": self._get_balance,
                "get_token_balance": self._get_token_balance,
                "get_token_info": self._get_token_info,
                "get_block": self._get_block,
                "get_transaction": self._get_transaction,
                "estimate_gas": self._estimate_gas,
                "call_contract": self._call_contract,
                "get_gas_price": self._get_gas_price,
                "get_network_info": self._get_network_info,
                "list_networks": self._list_networks_async,
                "get_native_price": self._get_native_price,
                "defi_read": self._defi_read,
                "get_ens": self._get_ens,
            }

            handler = handlers.get(action)
            if handler is None:
                return self._create_error_response(f"Unknown action: {action}")

            # All handlers are async; synchronous web3.py calls are already
            # wrapped in run_in_executor inside each handler via _run_sync.
            return await handler(task)

        except Exception as exc:
            return self._create_error_response(str(exc))

    # ------------------------------------------------------------------
    # Action handlers (all async, web3 calls wrapped in run_in_executor)
    # ------------------------------------------------------------------

    async def _run_sync(self, fn, *args):
        """Run a synchronous web3 function in the default executor."""
        return await asyncio.get_event_loop().run_in_executor(None, fn, *args)

    async def _get_balance(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Get the native token balance for an address."""
        network = self._resolve_network(task)
        address = task.get("address", "")
        block = task.get("block", "latest")

        if not address:
            return self._create_error_response("address is required")

        w3 = self._get_w3(network)
        if w3 is None:
            return self._create_error_response(
                f"Web3 not available for network '{network}'. Install web3.py."
            )

        try:
            if not w3.is_address(address):
                return self._create_error_response(f"Invalid address: {address}")

            start = time.time()
            checksummed = w3.to_checksum_address(address)
            raw_balance = await self._run_sync(
                w3.eth.get_balance, checksummed, block
            )
            balance_wei = int(raw_balance)
            balance_eth = w3.from_wei(balance_wei, "ether")
            elapsed = time.time() - start

            self._update_stats(True, elapsed)

            net_config = NETWORK_DEFAULTS.get(network, {})
            return {
                "success": True,
                "address": checksummed,
                "network": network,
                "chain_id": net_config.get("chain_id"),
                "balance_wei": balance_wei,
                "balance": float(balance_eth),
                "currency": net_config.get("currency", "ETH"),
                "block": block,
            }
        except Exception as exc:
            self._update_stats(False, 0)
            return self._create_error_response(f"Balance query failed: {exc}")

    async def _get_token_balance(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Get an ERC-20 token balance for an address."""
        network = self._resolve_network(task)
        address = task.get("address", "")
        token_address = task.get("token_address", "")
        token_symbol = task.get("token", "")  # can use symbol instead of address

        if not address:
            return self._create_error_response("address is required")

        # Resolve token symbol to address
        if not token_address and token_symbol:
            known = KNOWN_TOKENS.get(network, {})
            token_address = known.get(token_symbol.upper(), "")
            if not token_address:
                return self._create_error_response(
                    f"Unknown token '{token_symbol}' on {network}"
                )

        if not token_address:
            return self._create_error_response("token_address or token symbol is required")

        w3 = self._get_w3(network)
        if w3 is None:
            return self._create_error_response(
                f"Web3 not available for network '{network}'"
            )

        try:
            checksummed_addr = w3.to_checksum_address(address)
            checksummed_token = w3.to_checksum_address(token_address)

            contract = w3.eth.contract(address=checksummed_token, abi=ERC20_MINIMAL_ABI)

            start = time.time()
            raw_balance = await self._run_sync(contract.functions.balanceOf(checksummed_addr).call)
            decimals = await self._run_sync(contract.functions.decimals().call)
            symbol = await self._run_sync(contract.functions.symbol().call)
            elapsed = time.time() - start

            human_balance = raw_balance / (10 ** decimals)

            self._update_stats(True, elapsed)
            return {
                "success": True,
                "address": checksummed_addr,
                "token_address": checksummed_token,
                "token_symbol": symbol,
                "decimals": decimals,
                "raw_balance": raw_balance,
                "balance": human_balance,
                "network": network,
            }
        except Exception as exc:
            self._update_stats(False, 0)
            return self._create_error_response(f"Token balance query failed: {exc}")

    async def _get_token_info(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Get ERC-20 token metadata (name, symbol, decimals, total supply)."""
        network = self._resolve_network(task)
        token_address = task.get("token_address", "")

        if not token_address:
            return self._create_error_response("token_address is required")

        w3 = self._get_w3(network)
        if w3 is None:
            return self._create_error_response(f"Web3 not available for network '{network}'")

        try:
            checksummed = w3.to_checksum_address(token_address)
            contract = w3.eth.contract(address=checksummed, abi=ERC20_MINIMAL_ABI)

            start = time.time()
            name = await self._run_sync(contract.functions.name().call)
            symbol = await self._run_sync(contract.functions.symbol().call)
            decimals = await self._run_sync(contract.functions.decimals().call)
            total_supply = await self._run_sync(contract.functions.totalSupply().call)
            elapsed = time.time() - start

            self._update_stats(True, elapsed)
            return {
                "success": True,
                "token_address": checksummed,
                "name": name,
                "symbol": symbol,
                "decimals": decimals,
                "total_supply": total_supply,
                "total_supply_human": total_supply / (10 ** decimals),
                "network": network,
            }
        except Exception as exc:
            self._update_stats(False, 0)
            return self._create_error_response(f"Token info query failed: {exc}")

    async def _get_block(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Get block information by number or 'latest'."""
        network = self._resolve_network(task)
        block_id = task.get("block", "latest")
        full_transactions = task.get("full_transactions", False)

        w3 = self._get_w3(network)
        if w3 is None:
            return self._create_error_response(f"Web3 not available for network '{network}'")

        try:
            start = time.time()
            if isinstance(block_id, str) and block_id.isdigit():
                block_id = int(block_id)
            block = await self._run_sync(
                w3.eth.get_block, block_id, full_transactions
            )
            elapsed = time.time() - start

            self._update_stats(True, elapsed)

            # Serialize block data
            result: Dict[str, Any] = {}
            for key, value in block.items():
                if isinstance(value, bytes):
                    result[key] = value.hex()
                elif isinstance(value, (list,)):
                    result[key] = [
                        v.hex() if isinstance(v, bytes) else v for v in value
                    ]
                else:
                    result[key] = value

            return {
                "success": True,
                "network": network,
                "block": result,
            }
        except Exception as exc:
            self._update_stats(False, 0)
            return self._create_error_response(f"Block query failed: {exc}")

    async def _get_transaction(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Get transaction details by hash."""
        network = self._resolve_network(task)
        tx_hash = task.get("tx_hash", "")

        if not tx_hash:
            return self._create_error_response("tx_hash is required")

        w3 = self._get_w3(network)
        if w3 is None:
            return self._create_error_response(f"Web3 not available for network '{network}'")

        try:
            start = time.time()
            if isinstance(tx_hash, str):
                tx_hash = bytes.fromhex(tx_hash.removeprefix("0x"))

            tx = await self._run_sync(w3.eth.get_transaction, tx_hash)
            receipt = await self._run_sync(w3.eth.get_transaction_receipt, tx_hash)
            elapsed = time.time() - start

            self._update_stats(True, elapsed)

            # Serialize
            def _serialize(obj):
                result = {}
                for k, v in obj.items():
                    if isinstance(v, bytes):
                        result[k] = v.hex()
                    elif isinstance(v, (list,)):
                        result[k] = [
                            vi.hex() if isinstance(vi, bytes) else vi for vi in v
                        ]
                    else:
                        result[k] = v
                return result

            net_config = NETWORK_DEFAULTS.get(network, {})
            return {
                "success": True,
                "network": network,
                "transaction": _serialize(tx),
                "receipt": _serialize(receipt),
                "explorer_url": f"{net_config.get('explorer', '')}/tx/0x{tx_hash.hex()}",
            }
        except Exception as exc:
            self._update_stats(False, 0)
            return self._create_error_response(f"Transaction query failed: {exc}")

    async def _estimate_gas(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate gas for a transaction."""
        network = self._resolve_network(task)
        tx_params = task.get("transaction", {})

        if not tx_params:
            return self._create_error_response("transaction parameters are required")

        w3 = self._get_w3(network)
        if w3 is None:
            return self._create_error_response(f"Web3 not available for network '{network}'")

        try:
            # Ensure addresses are checksummed
            for addr_key in ("from", "to"):
                if addr_key in tx_params and w3.is_address(tx_params[addr_key]):
                    tx_params[addr_key] = w3.to_checksum_address(tx_params[addr_key])

            start = time.time()
            gas_estimate = await self._run_sync(w3.eth.estimate_gas, tx_params)
            gas_price = await self._run_sync(w3.eth.gas_price)
            elapsed = time.time() - start

            total_cost_wei = gas_estimate * gas_price
            total_cost_eth = w3.from_wei(total_cost_wei, "ether")

            net_config = NETWORK_DEFAULTS.get(network, {})
            self._update_stats(True, elapsed)

            return {
                "success": True,
                "network": network,
                "gas_estimate": gas_estimate,
                "gas_price_wei": gas_price,
                "gas_price_gwei": w3.from_wei(gas_price, "gwei"),
                "total_cost_wei": total_cost_wei,
                "total_cost_eth": float(total_cost_eth),
                "currency": net_config.get("currency", "ETH"),
            }
        except Exception as exc:
            self._update_stats(False, 0)
            return self._create_error_response(f"Gas estimation failed: {exc}")

    async def _call_contract(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a read-only (view/pure) smart contract function.

        Provide:
          - contract_address
          - abi  (JSON string or list of dicts)
          - function_name
          - function_args  (list, optional)
        """
        network = self._resolve_network(task)
        contract_address = task.get("contract_address", "")
        abi = task.get("abi", [])
        function_name = task.get("function_name", "")
        function_args = task.get("function_args", [])

        if not contract_address or not function_name:
            return self._create_error_response("contract_address and function_name are required")

        if isinstance(abi, str):
            try:
                abi = json.loads(abi)
            except json.JSONDecodeError:
                return self._create_error_response("Invalid ABI JSON string")

        w3 = self._get_w3(network)
        if w3 is None:
            return self._create_error_response(f"Web3 not available for network '{network}'")

        try:
            checksummed = w3.to_checksum_address(contract_address)
            contract = w3.eth.contract(address=checksummed, abi=abi)
            contract_fn = getattr(contract.functions, function_name)

            start = time.time()
            result = await self._run_sync(contract_fn(*function_args).call)
            elapsed = time.time() - start

            # Serialize result
            serialized = self._serialize_contract_result(result)

            self._update_stats(True, elapsed)
            return {
                "success": True,
                "network": network,
                "contract_address": checksummed,
                "function_name": function_name,
                "function_args": function_args,
                "result": serialized,
            }
        except Exception as exc:
            self._update_stats(False, 0)
            return self._create_error_response(f"Contract call failed: {exc}")

    async def _get_gas_price(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Get current gas price for a network."""
        network = self._resolve_network(task)

        w3 = self._get_w3(network)
        if w3 is None:
            return self._create_error_response(f"Web3 not available for network '{network}'")

        try:
            start = time.time()
            gas_price = await self._run_sync(w3.eth.gas_price)
            elapsed = time.time() - start

            self._update_stats(True, elapsed)
            net_config = NETWORK_DEFAULTS.get(network, {})

            return {
                "success": True,
                "network": network,
                "gas_price_wei": gas_price,
                "gas_price_gwei": float(w3.from_wei(gas_price, "gwei")),
                "gas_price_eth": float(w3.from_wei(gas_price, "ether")),
                "currency": net_config.get("currency", "ETH"),
            }
        except Exception as exc:
            self._update_stats(False, 0)
            return self._create_error_response(f"Gas price query failed: {exc}")

    async def _get_network_info(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Get information about a connected network."""
        network = self._resolve_network(task)

        w3 = self._get_w3(network)
        if w3 is None:
            return self._create_error_response(f"Web3 not available for network '{network}'")

        try:
            start = time.time()
            chain_id = await self._run_sync(w3.eth.chain_id)
            block_number = await self._run_sync(w3.eth.block_number)
            gas_price = await self._run_sync(w3.eth.gas_price)
            is_connected = await self._run_sync(w3.is_connected)
            elapsed = time.time() - start

            self._update_stats(True, elapsed)
            net_config = NETWORK_DEFAULTS.get(network, {})

            return {
                "success": True,
                "network": network,
                "connected": is_connected,
                "chain_id": chain_id,
                "latest_block": block_number,
                "gas_price_gwei": float(w3.from_wei(gas_price, "gwei")),
                "currency": net_config.get("currency", "ETH"),
                "explorer": net_config.get("explorer", ""),
            }
        except Exception as exc:
            self._update_stats(False, 0)
            return self._create_error_response(f"Network info query failed: {exc}")

    def _list_networks(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """List all configured / supported networks."""
        networks = []
        for name, config in NETWORK_DEFAULTS.items():
            rpc_url = os.getenv(config["rpc_env"], config["rpc_default"])
            w3 = self._get_w3(name)
            connected = False
            if w3 is not None:
                try:
                    connected = w3.is_connected()
                except Exception:
                    connected = False

            networks.append(
                {
                    "name": name,
                    "chain_id": config["chain_id"],
                    "currency": config["currency"],
                    "rpc_configured": bool(os.getenv(config["rpc_env"])),
                    "connected": connected,
                    "explorer": config["explorer"],
                }
            )

        return {
            "success": True,
            "total_networks": len(networks),
            "networks": networks,
            "default_network": self.default_network,
        }

    async def _list_networks_async(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Async wrapper for _list_networks."""
        return self._list_networks(task)

    async def _get_native_price(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch native token price from a public API (CoinGecko).
        Read-only; no API key required for basic usage.
        """
        network = self._resolve_network(task)
        net_config = NETWORK_DEFAULTS.get(network, {})
        currency = net_config.get("currency", "ETH").lower()

        # Map to CoinGecko IDs
        coingecko_ids = {
            "ethereum": "ethereum",
            "polygon": "matic-network",
            "bsc": "binancecoin",
            "arbitrum": "ethereum",
            "optimism": "ethereum",
            "avalanche": "avalanche-2",
        }

        cg_id = coingecko_ids.get(network, "ethereum")

        if not _AIOHTTP_AVAILABLE:
            return self._create_error_response("aiohttp not installed; cannot fetch price")

        try:
            async with aiohttp.ClientSession() as session:
                url = (
                    f"https://api.coingecko.com/api/v3/simple/price"
                    f"?ids={cg_id}&vs_currencies=usd"
                )
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status != 200:
                        return {
                            "success": False,
                            "error": f"CoinGecko API returned status {resp.status}",
                        }
                    data = await resp.json()
                    price = data.get(cg_id, {}).get("usd")

                    return {
                        "success": True,
                        "network": network,
                        "currency": net_config.get("currency", "ETH"),
                        "price_usd": price,
                        "source": "coingecko",
                    }
        except Exception as exc:
            return self._create_error_response(f"Price fetch failed: {exc}")

    async def _defi_read(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Read-only DeFi protocol interaction.

        Supports common patterns:
        - "protocol": "aave_v3" — get user account data / reserves
        - "protocol": "uniswap_v3" — get pool info
        - "protocol": "compound_v3" — get market info
        - Or provide a custom contract_address + abi + function_name + function_args
        """
        network = self._resolve_network(task)
        protocol = task.get("protocol", "").lower()

        # If a custom contract call is provided, delegate to call_contract
        if task.get("contract_address") and task.get("function_name"):
            return await self._call_contract(task)

        if not protocol:
            return self._create_error_response(
                "protocol name or contract_address + function_name is required"
            )

        # Built-in protocol helpers
        if protocol == "uniswap_v3":
            return await self._defi_uniswap_v3(task, network)
        elif protocol == "aave_v3":
            return await self._defi_aave_v3(task, network)
        elif protocol == "compound_v3":
            return await self._defi_compound_v3(task, network)
        else:
            return self._create_error_response(
                f"Unknown protocol '{protocol}'. Provide contract_address + abi for custom reads."
            )

    async def _defi_uniswap_v3(self, task: Dict[str, Any], network: str) -> Dict[str, Any]:
        """Read Uniswap V3 pool data (read-only)."""
        pool_address = task.get("pool_address", "")
        if not pool_address:
            return self._create_error_response("pool_address is required for Uniswap V3 read")

        # Minimal Uniswap V3 Pool ABI
        uni_v3_pool_abi: List[Dict[str, Any]] = [
            {"inputs": [], "name": "token0", "outputs": [{"name": "", "type": "address"}], "stateMutability": "view", "type": "function"},
            {"inputs": [], "name": "token1", "outputs": [{"name": "", "type": "address"}], "stateMutability": "view", "type": "function"},
            {"inputs": [], "name": "fee", "outputs": [{"name": "", "type": "uint24"}], "stateMutability": "view", "type": "function"},
            {"inputs": [], "name": "liquidity", "outputs": [{"name": "", "type": "uint128"}], "stateMutability": "view", "type": "function"},
            {"inputs": [], "name": "slot0", "outputs": [
                {"name": "sqrtPriceX96", "type": "uint160"},
                {"name": "tick", "type": "int24"},
                {"name": "observationIndex", "type": "uint16"},
                {"name": "observationCardinality", "type": "uint16"},
                {"name": "observationCardinalityNext", "type": "uint16"},
                {"name": "feeProtocol", "type": "uint8"},
                {"name": "unlocked", "type": "bool"},
            ], "stateMutability": "view", "type": "function"},
        ]

        return await self._call_contract(
            {
                "network": network,
                "contract_address": pool_address,
                "abi": uni_v3_pool_abi,
                "function_name": "slot0",
                "function_args": [],
            }
        )

    async def _defi_aave_v3(self, task: Dict[str, Any], network: str) -> Dict[str, Any]:
        """Read Aave V3 lending pool data (read-only)."""
        # Aave V3 Lending Pool addresses provider is well-known per chain
        aave_task = {
            "network": network,
            "contract_address": task.get("contract_address", ""),
            "abi": task.get("abi", []),
            "function_name": task.get("function_name", ""),
            "function_args": task.get("function_args", []),
        }

        if not aave_task["contract_address"] or not aave_task["function_name"]:
            return self._create_error_response(
                "For Aave V3, provide contract_address, abi, function_name, and function_args"
            )

        return await self._call_contract(aave_task)

    async def _defi_compound_v3(self, task: Dict[str, Any], network: str) -> Dict[str, Any]:
        """Read Compound V3 market data (read-only)."""
        compound_task = {
            "network": network,
            "contract_address": task.get("contract_address", ""),
            "abi": task.get("abi", []),
            "function_name": task.get("function_name", ""),
            "function_args": task.get("function_args", []),
        }

        if not compound_task["contract_address"] or not compound_task["function_name"]:
            return self._create_error_response(
                "For Compound V3, provide contract_address, abi, function_name, and function_args"
            )

        return await self._call_contract(compound_task)

    async def _get_ens(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve an ENS name to an address, or reverse-resolve an address to a name."""
        network = self._resolve_network(task)
        name = task.get("name", "")
        address = task.get("address", "")

        if not name and not address:
            return self._create_error_response("name or address is required for ENS lookup")

        # ENS only works on mainnet
        if network != "ethereum":
            network = "ethereum"

        w3 = self._get_w3(network)
        if w3 is None:
            return self._create_error_response("Web3 not available for Ethereum mainnet")

        try:
            start = time.time()
            if name:
                # Forward resolution
                resolved = await self._run_sync(w3.ens.address, name)
                elapsed = time.time() - start
                self._update_stats(True, elapsed)
                return {
                    "success": True,
                    "name": name,
                    "address": resolved,
                    "direction": "forward",
                }
            else:
                # Reverse resolution
                checksummed = w3.to_checksum_address(address)
                resolved_name = await self._run_sync(w3.ens.name, checksummed)
                elapsed = time.time() - start
                self._update_stats(True, elapsed)
                return {
                    "success": True,
                    "address": checksummed,
                    "name": resolved_name,
                    "direction": "reverse",
                }
        except Exception as exc:
            self._update_stats(False, 0)
            return self._create_error_response(f"ENS lookup failed: {exc}")

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------

    def _serialize_contract_result(self, result: Any) -> Any:
        """Recursively serialize contract call results for JSON compatibility."""
        if isinstance(result, bytes):
            return result.hex()
        if isinstance(result, (int,)):
            # Return both raw int and hex for large values
            if result > 2**53:
                return {"raw": result, "hex": hex(result)}
            return result
        if isinstance(result, bool):
            return result
        if isinstance(result, (list, tuple)):
            return [self._serialize_contract_result(item) for item in result]
        if isinstance(result, dict):
            return {k: self._serialize_contract_result(v) for k, v in result.items()}
        return result

    # ------------------------------------------------------------------
    # Common helpers
    # ------------------------------------------------------------------

    def _update_stats(self, success: bool, elapsed: float):
        """Update running performance statistics."""
        self._stats["total_tasks"] += 1
        self._stats["rpc_calls"] += 1
        if success:
            self._stats["successful_tasks"] += 1
        else:
            self._stats["failed_tasks"] += 1
        total = self._stats["total_tasks"]
        current_avg = self._stats["avg_response_time"]
        self._stats["avg_response_time"] = (current_avg * (total - 1) + elapsed) / total

    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create a standardized error response."""
        self._stats["failed_tasks"] += 1
        return {
            "success": False,
            "error": error_message,
            "timestamp": datetime.now().isoformat(),
            "agent": self.agent_id,
        }

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Return agent performance metrics."""
        return {
            "agent_id": self.agent_id,
            "status": self.status,
            "capabilities": self.capabilities,
            "stats": self._stats,
            "default_network": self.default_network,
            "web3_available": _WEB3_AVAILABLE,
            "configured_networks": list(self._w3_instances.keys()),
        }


# Global instance
web3_plugin = Web3Plugin()
