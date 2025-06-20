import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional
import logging
from jinja2 import Template

from app.core.config import settings

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.email_username = settings.EMAIL_USERNAME
        self.email_password = settings.EMAIL_PASSWORD
        self.from_email = settings.FROM_EMAIL
        
    def send_kyc_status_email(self, to_email: str, kyc_data: Dict[str, Any]) -> bool:
        """Send KYC status notification email"""
        try:
            # Create email templates based on status
            if kyc_data['status'] == 'passed':
                subject = "KYC Verification Successful"
                template = self._get_success_template()
            elif kyc_data['status'] == 'rejected':
                subject = "KYC Verification Failed"
                template = self._get_rejection_template()
            elif kyc_data['status'] == 'manual_review':
                subject = "KYC Under Manual Review"
                template = self._get_manual_review_template()
            else:
                subject = "KYC Status Update"
                template = self._get_default_template()
            
            # Render template with data
            html_content = template.render(
                full_name=kyc_data.get('full_name', 'User'),
                ticket_id=kyc_data.get('ticket_id'),
                status=kyc_data.get('status'),
                kyc_tier=kyc_data.get('kyc_tier', 0),
                note=kyc_data.get('note', ''),
                reviewed_at=kyc_data.get('reviewed_at')
            )
            
            return self._send_email(to_email, subject, html_content)
            
        except Exception as e:
            logger.error(f"Failed to send KYC status email: {str(e)}")
            return False
    
    def send_welcome_email(self, to_email: str, user_name: str) -> bool:
        """Send welcome email after successful KYC"""
        try:
            subject = "Welcome to EchoFi - KYC Completed"
            template = self._get_welcome_template()
            
            html_content = template.render(
                user_name=user_name,
                platform_name="EchoFi"
            )
            
            return self._send_email(to_email, subject, html_content)
            
        except Exception as e:
            logger.error(f"Failed to send welcome email: {str(e)}")
            return False
    
    def _send_email(self, to_email: str, subject: str, html_content: str) -> bool:
        """Send email using SMTP"""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = to_email
            
            # Create HTML part
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_username, self.email_password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return False
    
    def _get_success_template(self) -> Template:
        """Get success email template"""
        template_str = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .container { max-width: 600px; margin: 0 auto; }
                .header { background-color: #4CAF50; color: white; padding: 20px; text-align: center; }
                .content { padding: 20px; background-color: #f9f9f9; }
                .footer { padding: 10px; text-align: center; font-size: 12px; color: #666; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>✅ KYC Verification Successful</h1>
                </div>
                <div class="content">
                    <p>Dear {{ full_name }},</p>
                    <p>Congratulations! Your KYC verification has been successfully completed.</p>
                    <p><strong>Ticket ID:</strong> {{ ticket_id }}</p>
                    <p><strong>KYC Tier:</strong> {{ kyc_tier }}</p>
                    <p>You can now access all features of the EchoFi platform including token withdrawals.</p>
                    <p>Thank you for your patience during the verification process.</p>
                </div>
                <div class="footer">
                    <p>EchoFi Team</p>
                </div>
            </div>
        </body>
        </html>
        """
        return Template(template_str)
    
    def _get_rejection_template(self) -> Template:
        """Get rejection email template"""
        template_str = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .container { max-width: 600px; margin: 0 auto; }
                .header { background-color: #f44336; color: white; padding: 20px; text-align: center; }
                .content { padding: 20px; background-color: #f9f9f9; }
                .footer { padding: 10px; text-align: center; font-size: 12px; color: #666; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>❌ KYC Verification Failed</h1>
                </div>
                <div class="content">
                    <p>Dear {{ full_name }},</p>
                    <p>We regret to inform you that your KYC verification could not be completed at this time.</p>
                    <p><strong>Ticket ID:</strong> {{ ticket_id }}</p>
                    {% if note %}
                    <p><strong>Reason:</strong> {{ note }}</p>
                    {% endif %}
                    <p>You may resubmit your KYC application with updated documents.</p>
                    <p>If you have questions, please contact our support team.</p>
                </div>
                <div class="footer">
                    <p>EchoFi Team</p>
                </div>
            </div>
        </body>
        </html>
        """
        return Template(template_str)
    
    def _get_manual_review_template(self) -> Template:
        """Get manual review email template"""
        template_str = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .container { max-width: 600px; margin: 0 auto; }
                .header { background-color: #FF9800; color: white; padding: 20px; text-align: center; }
                .content { padding: 20px; background-color: #f9f9f9; }
                .footer { padding: 10px; text-align: center; font-size: 12px; color: #666; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔍 KYC Under Manual Review</h1>
                </div>
                <div class="content">
                    <p>Dear {{ full_name }},</p>
                    <p>Your KYC verification is currently under manual review by our compliance team.</p>
                    <p><strong>Ticket ID:</strong> {{ ticket_id }}</p>
                    <p>This process typically takes 1-3 business days. We will notify you once the review is complete.</p>
                    <p>Thank you for your patience.</p>
                </div>
                <div class="footer">
                    <p>EchoFi Team</p>
                </div>
            </div>
        </body>
        </html>
        """
        return Template(template_str)
    
    def _get_welcome_template(self) -> Template:
        """Get welcome email template"""
        template_str = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .container { max-width: 600px; margin: 0 auto; }
                .header { background-color: #2196F3; color: white; padding: 20px; text-align: center; }
                .content { padding: 20px; background-color: #f9f9f9; }
                .footer { padding: 10px; text-align: center; font-size: 12px; color: #666; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Welcome to {{ platform_name }}!</h1>
                </div>
                <div class="content">
                    <p>Dear {{ user_name }},</p>
                    <p>Welcome to {{ platform_name }}! Your KYC verification is complete and you now have full access to our platform.</p>
                    <p>You can now:</p>
                    <ul>
                        <li>Withdraw ECHO tokens</li>
                        <li>Access all platform features</li>
                        <li>Participate in all activities</li>
                    </ul>
                    <p>Thank you for choosing {{ platform_name }}!</p>
                </div>
                <div class="footer">
                    <p>{{ platform_name }} Team</p>
                </div>
            </div>
        </body>
        </html>
        """
        return Template(template_str)
    
    def _get_default_template(self) -> Template:
        """Get default email template"""
        template_str = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .container { max-width: 600px; margin: 0 auto; }
                .header { background-color: #607D8B; color: white; padding: 20px; text-align: center; }
                .content { padding: 20px; background-color: #f9f9f9; }
                .footer { padding: 10px; text-align: center; font-size: 12px; color: #666; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📋 KYC Status Update</h1>
                </div>
                <div class="content">
                    <p>Dear {{ full_name }},</p>
                    <p>Your KYC status has been updated.</p>
                    <p><strong>Ticket ID:</strong> {{ ticket_id }}</p>
                    <p><strong>Status:</strong> {{ status }}</p>
                    {% if note %}
                    <p><strong>Note:</strong> {{ note }}</p>
                    {% endif %}
                </div>
                <div class="footer">
                    <p>EchoFi Team</p>
                </div>
            </div>
        </body>
        </html>
        """
        return Template(template_str)
