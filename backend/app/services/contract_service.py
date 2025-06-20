import asyncio
import aiohttp
from typing import Dict, Any, Optional
import logging
from web3 import Web3
from eth_account import Account
import json

from app.core.config import settings

logger = logging.getLogger(__name__)

class SmartContractService:
    def __init__(self):
        self.rpc_url = settings.BLOCKCHAIN_RPC_URL
        self.contract_address = settings.CONTRACT_ADDRESS
        self.private_key = settings.CONTRACT_PRIVATE_KEY
        
        # Initialize Web3
        if self.rpc_url:
            self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
            self.account = Account.from_key(self.private_key) if self.private_key else None
        else:
            self.w3 = None
            self.account = None
    
    async def update_kyc_status(self, user_address: str, kyc_tier: int, approved: bool) -> Dict[str, Any]:
        """Update KYC status on smart contract"""
        try:
            if not self.w3 or not self.account:
                return {
                    'success': False,
                    'error': 'Blockchain connection not configured'
                }
            
            # Simple contract ABI for KYC status
            contract_abi = [
                {
                    "inputs": [
                        {"name": "user", "type": "address"},
                        {"name": "tier", "type": "uint8"},
                        {"name": "approved", "type": "bool"}
                    ],
                    "name": "updateKYCStatus",
                    "outputs": [],
                    "stateMutability": "nonpayable",
                    "type": "function"
                }
            ]
            
            contract = self.w3.eth.contract(
                address=self.contract_address,
                abi=contract_abi
            )
            
            # Build transaction
            transaction = contract.functions.updateKYCStatus(
                user_address,
                kyc_tier,
                approved
            ).build_transaction({
                'from': self.account.address,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'gas': 100000,
                'gasPrice': self.w3.to_wei('20', 'gwei')
            })
            
            # Sign and send transaction
            signed_txn = self.w3.eth.account.sign_transaction(transaction, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Wait for confirmation
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            return {
                'success': True,
                'tx_hash': receipt.transactionHash.hex(),
                'block_number': receipt.blockNumber,
                'gas_used': receipt.gasUsed
            }
            
        except Exception as e:
            logger.error(f"Smart contract update failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def check_kyc_status(self, user_address: str) -> Dict[str, Any]:
        """Check KYC status from smart contract"""
        try:
            if not self.w3:
                return {
                    'success': False,
                    'error': 'Blockchain connection not configured'
                }
            
            # Contract ABI for checking KYC status
            contract_abi = [
                {
                    "inputs": [{"name": "user", "type": "address"}],
                    "name": "getKYCStatus",
                    "outputs": [
                        {"name": "tier", "type": "uint8"},
                        {"name": "approved", "type": "bool"},
                        {"name": "timestamp", "type": "uint256"}
                    ],
                    "stateMutability": "view",
                    "type": "function"
                }
            ]
            
            contract = self.w3.eth.contract(
                address=self.contract_address,
                abi=contract_abi
            )
            
            # Call contract function
            result = contract.functions.getKYCStatus(user_address).call()
            
            return {
                'success': True,
                'tier': result[0],
                'approved': result[1],
                'timestamp': result[2],
                'user_address': user_address
            }
            
        except Exception as e:
            logger.error(f"Smart contract check failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def verify_withdrawal_eligibility(self, user_address: str, amount: int) -> Dict[str, Any]:
        """Verify if user is eligible for withdrawal based on KYC status"""
        try:
            # Check KYC status first
            kyc_status = await self.check_kyc_status(user_address)
            
            if not kyc_status['success']:
                return {
                    'eligible': False,
                    'error': 'Could not verify KYC status'
                }
            
            if not kyc_status['approved']:
                return {
                    'eligible': False,
                    'reason': 'KYC not approved'
                }
            
            # Check tier limits
            tier = kyc_status['tier']
            if tier == 0:
                return {
                    'eligible': False,
                    'reason': 'KYC Tier 0 - withdrawals not allowed'
                }
            elif tier == 1:
                # Tier 1 - limited withdrawals
                daily_limit = 1000  # Example limit
                if amount > daily_limit:
                    return {
                        'eligible': False,
                        'reason': f'Amount exceeds Tier 1 daily limit of {daily_limit}'
                    }
            elif tier == 2:
                # Tier 2 - full access
                pass  # No additional restrictions
            
            return {
                'eligible': True,
                'tier': tier,
                'kyc_timestamp': kyc_status['timestamp']
            }
            
        except Exception as e:
            logger.error(f"Withdrawal eligibility check failed: {str(e)}")
            return {
                'eligible': False,
                'error': str(e)
            }
    
    async def get_kyc_events(self, user_address: Optional[str] = None) -> Dict[str, Any]:
        """Get KYC-related events from blockchain"""
        try:
            if not self.w3:
                return {
                    'success': False,
                    'error': 'Blockchain connection not configured'
                }
            
            # Event ABI
            event_abi = [
                {
                    "anonymous": False,
                    "inputs": [
                        {"indexed": True, "name": "user", "type": "address"},
                        {"indexed": False, "name": "tier", "type": "uint8"},
                        {"indexed": False, "name": "approved", "type": "bool"},
                        {"indexed": False, "name": "timestamp", "type": "uint256"}
                    ],
                    "name": "KYCStatusUpdated",
                    "type": "event"
                }
            ]
            
            contract = self.w3.eth.contract(
                address=self.contract_address,
                abi=event_abi
            )
            
            # Get recent blocks
            latest_block = self.w3.eth.block_number
            from_block = max(0, latest_block - 10000)  # Last ~10k blocks
            
            # Filter events
            event_filter = contract.events.KYCStatusUpdated.create_filter(
                fromBlock=from_block,
                toBlock='latest',
                argument_filters={'user': user_address} if user_address else {}
            )
            
            events = event_filter.get_all_entries()
            
            # Format events
            formatted_events = []
            for event in events:
                formatted_events.append({
                    'user': event['args']['user'],
                    'tier': event['args']['tier'],
                    'approved': event['args']['approved'],
                    'timestamp': event['args']['timestamp'],
                    'block_number': event['blockNumber'],
                    'transaction_hash': event['transactionHash'].hex()
                })
            
            return {
                'success': True,
                'events': formatted_events,
                'total_events': len(formatted_events)
            }
            
        except Exception as e:
            logger.error(f"Get KYC events failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def is_valid_address(self, address: str) -> bool:
        """Validate Ethereum address format"""
        try:
            return Web3.is_address(address)
        except:
            return False
    
    async def estimate_gas_cost(self, user_address: str) -> Dict[str, Any]:
        """Estimate gas cost for KYC status update"""
        try:
            if not self.w3 or not self.account:
                return {
                    'success': False,
                    'error': 'Blockchain connection not configured'
                }
            
            # Simple contract ABI
            contract_abi = [
                {
                    "inputs": [
                        {"name": "user", "type": "address"},
                        {"name": "tier", "type": "uint8"},
                        {"name": "approved", "type": "bool"}
                    ],
                    "name": "updateKYCStatus",
                    "outputs": [],
                    "stateMutability": "nonpayable",
                    "type": "function"
                }
            ]
            
            contract = self.w3.eth.contract(
                address=self.contract_address,
                abi=contract_abi
            )
            
            # Estimate gas
            gas_estimate = contract.functions.updateKYCStatus(
                user_address,
                2,  # Tier 2
                True  # Approved
            ).estimate_gas({'from': self.account.address})
            
            # Get current gas price
            gas_price = self.w3.eth.gas_price
            
            # Calculate cost in ETH
            cost_wei = gas_estimate * gas_price
            cost_eth = self.w3.from_wei(cost_wei, 'ether')
            
            return {
                'success': True,
                'gas_estimate': gas_estimate,
                'gas_price_wei': gas_price,
                'cost_wei': cost_wei,
                'cost_eth': float(cost_eth)
            }
            
        except Exception as e:
            logger.error(f"Gas estimation failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
