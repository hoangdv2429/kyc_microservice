import asyncio
import aiohttp
from typing import Dict, Any, Optional
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

class TelegramService:
    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        
    async def send_kyc_notification(self, chat_id: str, kyc_data: Dict[str, Any]) -> bool:
        """Send KYC status notification via Telegram"""
        try:
            if kyc_data['status'] == 'passed':
                message = self._format_success_message(kyc_data)
            elif kyc_data['status'] == 'rejected':
                message = self._format_rejection_message(kyc_data)
            elif kyc_data['status'] == 'manual_review':
                message = self._format_manual_review_message(kyc_data)
            else:
                message = self._format_default_message(kyc_data)
            
            return await self._send_message(chat_id, message)
            
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {str(e)}")
            return False
    
    async def send_admin_notification(self, admin_chat_id: str, kyc_data: Dict[str, Any]) -> bool:
        """Send notification to admin for manual review"""
        try:
            message = f"""
🔍 *New KYC for Manual Review*

👤 *User:* {kyc_data.get('full_name', 'Unknown')}
🎫 *Ticket ID:* `{kyc_data.get('ticket_id')}`
📧 *Email:* {kyc_data.get('email', 'N/A')}
📱 *Phone:* {kyc_data.get('phone', 'N/A')}
🏠 *Address:* {kyc_data.get('address', 'N/A')}

📊 *Scores:*
• OCR Confidence: {kyc_data.get('ocr_confidence', 'N/A')}
• Face Match: {kyc_data.get('face_score', 'N/A')}
• Liveness: {kyc_data.get('liveness_score', 'N/A')}
• Risk Score: {kyc_data.get('risk_score', 'N/A')}

⏰ *Submitted:* {kyc_data.get('submitted_at')}

Please review in admin panel.
            """
            
            return await self._send_message(admin_chat_id, message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Failed to send admin notification: {str(e)}")
            return False
    
    async def _send_message(self, chat_id: str, text: str, parse_mode: str = 'Markdown') -> bool:
        """Send message via Telegram Bot API"""
        try:
            url = f"{self.base_url}/sendMessage"
            
            data = {
                'chat_id': chat_id,
                'text': text,
                'parse_mode': parse_mode
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    if response.status == 200:
                        logger.info(f"Telegram message sent successfully to {chat_id}")
                        return True
                    else:
                        logger.error(f"Telegram API error: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {str(e)}")
            return False
    
    def _format_success_message(self, kyc_data: Dict[str, Any]) -> str:
        """Format success notification message"""
        return f"""
✅ *KYC Verification Successful!*

Congratulations {kyc_data.get('full_name', 'User')}! 

Your KYC verification has been approved.

🎫 *Ticket ID:* `{kyc_data.get('ticket_id')}`
⭐ *KYC Tier:* {kyc_data.get('kyc_tier', 0)}
📅 *Approved:* {kyc_data.get('reviewed_at', 'Just now')}

You can now access all EchoFi features including token withdrawals!

🎉 Welcome to EchoFi!
        """
    
    def _format_rejection_message(self, kyc_data: Dict[str, Any]) -> str:
        """Format rejection notification message"""
        message = f"""
❌ *KYC Verification Failed*

Dear {kyc_data.get('full_name', 'User')},

Unfortunately, your KYC verification could not be completed.

🎫 *Ticket ID:* `{kyc_data.get('ticket_id')}`
📅 *Reviewed:* {kyc_data.get('reviewed_at', 'Recently')}
        """
        
        if kyc_data.get('note'):
            message += f"\n💬 *Reason:* {kyc_data['note']}"
        
        message += "\n\nYou may resubmit with updated documents. Contact support if you need assistance."
        
        return message
    
    def _format_manual_review_message(self, kyc_data: Dict[str, Any]) -> str:
        """Format manual review notification message"""
        return f"""
🔍 *KYC Under Manual Review*

Hello {kyc_data.get('full_name', 'User')},

Your KYC verification is currently being reviewed by our compliance team.

🎫 *Ticket ID:* `{kyc_data.get('ticket_id')}`
⏱️ *Status:* Manual Review in Progress

This typically takes 1-3 business days. We'll notify you once complete.

Thank you for your patience! 🙏
        """
    
    def _format_default_message(self, kyc_data: Dict[str, Any]) -> str:
        """Format default notification message"""
        return f"""
📋 *KYC Status Update*

Hello {kyc_data.get('full_name', 'User')},

Your KYC status has been updated.

🎫 *Ticket ID:* `{kyc_data.get('ticket_id')}`
📊 *Status:* {kyc_data.get('status', 'Unknown')}

Check your email for more details.
        """
    
    async def send_bulk_notifications(self, notifications: list) -> Dict[str, int]:
        """Send multiple notifications in bulk"""
        results = {'success': 0, 'failed': 0}
        
        tasks = []
        for notification in notifications:
            task = self._send_message(
                notification['chat_id'],
                notification['message'],
                notification.get('parse_mode', 'Markdown')
            )
            tasks.append(task)
        
        # Send all notifications concurrently
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        for response in responses:
            if isinstance(response, Exception):
                results['failed'] += 1
            elif response:
                results['success'] += 1
            else:
                results['failed'] += 1
        
        return results
    
    async def get_chat_info(self, chat_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a chat"""
        try:
            url = f"{self.base_url}/getChat"
            data = {'chat_id': chat_id}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get('result')
                    else:
                        return None
                        
        except Exception as e:
            logger.error(f"Failed to get chat info: {str(e)}")
            return None
