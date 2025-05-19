import os
import asyncio
import logging
from dotenv import load_dotenv
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError

# Load environment variables
load_dotenv()

# Constants
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_GROUP_ID = os.getenv('TELEGRAM_GROUP_ID')
TELEGRAM_ADMIN_ID = os.getenv('TELEGRAM_ADMIN_ID')  # For error notifications

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NotifyTelegramView(APIView):
    """
    API endpoint for sending college registration requests to Telegram group.
    Includes interactive buttons for admins to approve/reject requests.
    """
    
    async def send_telegram_message(self, name, phone, fees_paid, email=None, course=None):
        """Send formatted message to Telegram with action buttons."""
        try:
            bot = Bot(token=TELEGRAM_BOT_TOKEN)
            
            # Format the message
            message = (
                "🎓 *New Registration Request*\n\n"
                f"👤 *Name:* {name}\n"
                f"📞 *Phone:* {phone}\n"
            )
            
            if email:
                message += f"📧 *Email:* {email}\n"
            if course:
                message += f"📚 *Course:* {course}\n"
                
            message += f"💰 *Fees Paid:* {'✅ Yes' if fees_paid else '❌ No'}\n\n"
            message += f"🆔 *Request ID:* {self.generate_request_id()}"
            
            # Create inline keyboard for actions
            keyboard = [
                [
                    InlineKeyboardButton("✅ Approve", callback_data=f"approve_{phone}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"reject_{phone}"),
                ],
                [
                    InlineKeyboardButton("ℹ️ More Info", callback_data=f"info_{phone}"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await bot.send_message(
                chat_id=TELEGRAM_GROUP_ID,
                text=message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
            # Send confirmation to admin
            await bot.send_message(
                chat_id=TELEGRAM_ADMIN_ID,
                text=f"ℹ️ New registration request from {name} received and forwarded to group."
            )
            
        except TelegramError as e:
            logger.error(f"Telegram API error: {e}")
            await self.notify_admin_error(f"Failed to send message: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            await self.notify_admin_error(f"Unexpected error: {e}")
            raise
    
    async def notify_admin_error(self, error_message):
        """Notify admin about errors"""
        try:
            bot = Bot(token=TELEGRAM_BOT_TOKEN)
            await bot.send_message(
                chat_id=TELEGRAM_ADMIN_ID,
                text=f"🚨 *System Error*\n\n{error_message}",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to notify admin: {e}")

    def generate_request_id(self):
        """Generate a simple request ID"""
        import uuid
        return str(uuid.uuid4())[:8].upper()

    def validate_input(self, data):
        """Validate incoming request data"""
        required_fields = ['name', 'phone']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
            
        if not isinstance(data.get('fees_paid', False), bool):
            raise ValueError("fees_paid must be a boolean value")
            
        phone = data['phone']
        if not (phone.isdigit() and len(phone) >= 10):
            raise ValueError("Phone number must be at least 10 digits")

    def post(self, request):
        """
        Handle POST request with registration data.
        Expected JSON format:
        {
            "name": "Student Name",
            "phone": "1234567890",
            "fees_paid": true/false,
            "email": "student@example.com",  # optional
            "course": "Computer Science"     # optional
        }
        """
        try:
            # Validate input
            self.validate_input(request.data)
            
            # Extract data
            name = request.data['name']
            phone = request.data['phone']
            fees_paid = request.data.get('fees_paid', False)
            email = request.data.get('email')
            course = request.data.get('course')
            
            # Send to Telegram
            asyncio.run(self.send_telegram_message(name, phone, fees_paid, email, course))
            
            return Response({
                'status': 'success',
                'message': 'Registration request sent successfully!',
                'data': {
                    'name': name,
                    'phone': phone,
                    'fees_paid': fees_paid
                }
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            logger.warning(f"Validation error: {e}")
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except TelegramError as e:
            logger.error(f"Telegram API error: {e}")
            return Response({
                'status': 'error',
                'message': 'Failed to send notification to Telegram'
            }, status=status.HTTP_502_BAD_GATEWAY)
            
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return Response({
                'status': 'error',
                'message': 'An unexpected error occurred'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)