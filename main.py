import os
import asyncio
import logging
import qrcode
from PIL import Image, ImageDraw, ImageFont
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, LabeledPrice, InputMediaPhoto
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters, PreCheckoutQueryHandler
from SecShare import SecShareBot

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TelegramSecShareBot:
    def __init__(self, bot_token: str):
        self.secshare = SecShareBot(bot_token)
        self.application = Application.builder().token(bot_token).build()
        
        # Telegram Stars configuration
        self.stars_provider_token = os.getenv('STARS_PROVIDER_TOKEN')
        self.contact_info = os.getenv('CONTACT_INFO', 'Contact admin for support')
        self.premium_prices = {
            '1day': LabeledPrice('SecShare Premium - 1 Day', 50),      # 50 stars = $0.50
            '1week': LabeledPrice('SecShare Premium - 1 Week', 150),   # 150 stars = $1.50
            '1month': LabeledPrice('SecShare Premium - 1 Month', 300), # 300 stars = $3.00
            '3months': LabeledPrice('SecShare Premium - 3 Months', 500), # 500 stars = $5.00
            '1year': LabeledPrice('SecShare Premium - 1 Year', 1000),  # 1000 stars = $10.00
        }
        
        self._setup_handlers()
        self._setup_commands()
    
    def _setup_commands(self):
        """Setup bot commands for better UX"""
        self.commands = [
            BotCommand("start", "🚀 Start the bot"),
            BotCommand("sendfile", "📁 Send a file"),
            BotCommand("sendmessage", "💬 Send a message"),
            BotCommand("receive", "📥 Receive a package"),
            BotCommand("stats", "📊 View your usage stats"),
            BotCommand("help", "❓ Get help"),
            BotCommand("premium", "⭐ Upgrade to premium"),
            BotCommand("airdrop", "📱 AirDrop-style sharing")
        ]
    
    def _setup_handlers(self):
        """Setup all bot handlers"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("sendfile", self.sendfile_command))
        self.application.add_handler(CommandHandler("sendmessage", self.sendmessage_command))
        self.application.add_handler(CommandHandler("receive", self.receive_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        self.application.add_handler(CommandHandler("premium", self.premium_command))
        self.application.add_handler(CommandHandler("airdrop", self.airdrop_command))
        
        # Handle text messages (for password-protected transfers)
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
        
        # Handle file uploads (documents, photos, videos, audio, voice)
        self.application.add_handler(MessageHandler(filters.Document.ALL, self.handle_document))
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        self.application.add_handler(MessageHandler(filters.VIDEO, self.handle_video))
        self.application.add_handler(MessageHandler(filters.AUDIO, self.handle_audio))
        self.application.add_handler(MessageHandler(filters.VOICE, self.handle_voice))
        
        # Handle callback queries (buttons)
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Handle Telegram Stars payments
        if self.stars_provider_token:
            self.application.add_handler(PreCheckoutQueryHandler(self.precheckout_callback))
            # Add handler for successful payments
            self.application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, self.successful_payment_callback))
    
    async def precheckout_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle pre-checkout queries for Telegram Stars"""
        query = update.pre_checkout_query
        await query.answer(ok=True)
    
    async def successful_payment_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle successful payments"""
        payment_info = update.message.successful_payment
        user_id = update.effective_user.id
        
        # Determine subscription type based on amount
        if payment_info.total_amount == 50:  # 1 day
            subscription_type = "1 day"
            duration_days = 1
        elif payment_info.total_amount == 150:  # 1 week
            subscription_type = "1 week"
            duration_days = 7
        elif payment_info.total_amount == 300:  # 1 month
            subscription_type = "1 month"
            duration_days = 30
        elif payment_info.total_amount == 500:  # 3 months
            subscription_type = "3 months"
            duration_days = 90
        elif payment_info.total_amount == 1000:  # 1 year
            subscription_type = "1 year"
            duration_days = 365
        else:
            subscription_type = "unknown"
            duration_days = 30
        
        # Upgrade user to premium
        user = self.secshare._get_user(user_id)
        user.is_premium = True
        self.secshare._save_data()
        
        # Log the payment
        logger.info(f"User {user_id} upgraded to premium ({subscription_type})")
        
        # Send confirmation message
        await update.message.reply_text(
            f"🎉 Payment successful! You're now a SecShare Premium user!\n\n"
            f"📅 Subscription: {subscription_type}\n"
            f"⭐ Amount: {payment_info.total_amount} stars\n"
            f"🔓 New limits: 1GB files, 20 transfers/day\n\n"
            f"Thank you for upgrading! 🚀"
        )
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        
        # Check if this is a transfer link (has start parameter)
        if context.args:
            transfer_id = context.args[0]
            logger.info(f"User {user.id} accessed transfer via start command: {transfer_id}")
            
            # Try to get the transfer
            transfer = self.secshare.get_transfer(transfer_id)
            if transfer:
                if transfer.password_hash:
                    # Password protected - ask for password
                    context.user_data['waiting_for_password'] = transfer_id
                    await update.message.reply_text(
                        f"🔐 This transfer is password protected.\n\n"
                        f"📁 Type: {'File' if transfer.is_file else 'Message'}\n"
                        f"⏰ Expires: 15 minutes\n\n"
                        f"Please enter the password:"
                    )
                else:
                    await self._send_transfer_content(update, transfer)
                return
            else:
                await update.message.reply_text(
                    "❌ Transfer not found or expired.\n\n"
                    "The transfer may have:\n"
                    "• Expired (15 minutes)\n"
                    "• Been already received\n"
                    "• Been deleted\n\n"
                    "Please ask the sender to create a new transfer."
                )
                return
        
        # Regular start command - show welcome message
        welcome_text = f"""
🔐 Welcome to SecShare, {user.first_name}!

I'm your secure file and password sharing bot. Here's what I can do:

📤 Send Files: Upload any file and get a secure link
🔑 Send Messages: Share sensitive text securely
🔒 Password Protection: Add passwords to your transfers
⏰ Auto-Expiry: Transfers expire in 15 minutes
🗑️ Auto-Delete: Files are deleted after being received

Free Plan:
• 50MB max file size
• 5 transfers per day
• Basic encryption

Premium Plan:
• 1GB max file size  
• 20 transfers per day
• Advanced security features

Just send me a file or text to get started!

Commands:
/sendfile - Send a file
/sendmessage - Send a message
/receive - Receive a package
/stats - View your usage stats
/help - Show this help
/premium - Upgrade to premium
        """
        
        keyboard = [
            [InlineKeyboardButton("📁 Send File", callback_data="send_file")],
            [InlineKeyboardButton("💬 Send Message", callback_data="send_message")],
            [InlineKeyboardButton("📥 Receive Package", callback_data="receive_package")],
            [InlineKeyboardButton("📱 AirDrop Sharing", callback_data="airdrop")],
            [InlineKeyboardButton("📊 My Stats", callback_data="stats")],
            [InlineKeyboardButton("⭐ I'm Interested in Premium", callback_data="premium_interest")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    
    async def sendfile_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /sendfile command"""
        await update.message.reply_text(
            "📁 Please upload the file you want to share securely.\n\n"
            "Supported file types:\n"
            "• Documents (PDF, DOC, TXT, etc.)\n"
            "• Images (JPG, PNG, GIF, etc.)\n"
            "• Videos (MP4, AVI, MOV, etc.)\n"
            "• Audio files (MP3, WAV, etc.)\n"
            "• Voice messages\n\n"
            "Max size: 50MB (free) / 1GB (premium)"
        )
    
    async def sendmessage_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /sendmessage command"""
        await update.message.reply_text(
            "💬 Please type the message or password you want to share securely.\n\n"
            "Your message will be encrypted and shared via a secure link."
        )
        context.user_data['waiting_for_message'] = True
    
    async def receive_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /receive command"""
        await update.message.reply_text(
            "📥 To receive a package:\n\n"
            "1. Click the secure link shared with you\n"
            "2. Or paste the transfer ID here\n"
            "3. Enter password if required\n"
            "4. Confirm receipt to auto-delete\n\n"
            "🔗 Paste the transfer ID or link here:"
        )
        context.user_data['waiting_for_transfer_id'] = True
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
🔐 SecShare Help

Quick Commands:
/sendfile - Send a file
/sendmessage - Send a message
/receive - Receive a package  
/stats - View your usage stats
/premium - Upgrade to premium
/airdrop - AirDrop-style sharing

How to use:

1. Send a File: Use /sendfile or upload any file
2. Send Text: Use /sendmessage or type your message
3. Add Password: Reply with a password when prompted
4. Share Link: Send the link to your recipient
5. QR Code: Generate QR code for easy sharing
6. Auto-Cleanup: Files are deleted after being received

Sharing Options:
• 🔗 Direct Link: Copy and share the secure link
• 📱 QR Code: Generate QR code for instant sharing
• 📤 Telegram Share: Use Telegram's built-in sharing
• 📱 AirDrop Style: Scan QR code for instant transfer

Supported File Types:
• Documents (PDF, DOC, TXT, etc.)
• Images (JPG, PNG, GIF, etc.)
• Videos (MP4, AVI, MOV, etc.)
• Audio files (MP3, WAV, etc.)
• Voice messages

Security Features:
• End-to-end encryption
• Password protection
• Auto-expiry (15 minutes)
• Secure file storage
• No logs kept
• QR code sharing

Need help? Use the "I'm Interested in Premium" button to contact support.
        """
        await update.message.reply_text(help_text)
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        user_id = update.effective_user.id
        stats = self.secshare.get_user_stats(user_id)
        
        stats_text = f"""
📊 Your Statistics

👤 Plan: {'⭐ Premium' if stats['is_premium'] else '🆓 Free'}
📤 Transfers Today: {stats['transfers_used_today']}/{stats['max_transfers_per_day']}
📈 Total Transfers: {stats['total_transfers']}
💾 Max File Size: {stats['max_file_size_mb']}MB
        """
        
        keyboard = []
        if not stats['is_premium']:
            keyboard.append([InlineKeyboardButton("⭐ I'm Interested in Premium", callback_data="premium_interest")])
        keyboard.append([InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(stats_text, reply_markup=reply_markup)
    
    async def premium_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /premium command with Telegram Stars integration"""
        user_id = update.effective_user.id
        user = self.secshare._get_user(user_id)
        
        if user.is_premium:
            premium_text = """
⭐ You're already a SecShare Premium user!

🔓 Your current benefits:
• 1GB max file size
• 20 transfers per day
• Advanced security features
• Priority support

Thank you for being a premium user! 🚀
            """
            keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(premium_text, reply_markup=reply_markup)
            return
        
        if self.stars_provider_token:
            # Show Telegram Stars payment options
            premium_text = f"""
⭐ SecShare Premium

Upgrade to unlock advanced features:

🔓 Increased Limits:
• 1GB file size (vs 50MB free)
• 20 transfers per day (vs 5 free)
• Priority support

🔒 Enhanced Security:
• Advanced encryption
• Password protection
• Secure file transfer

💰 Pricing Options:
• 1 Day - ⭐ 50 stars
• 1 Week - ⭐ 150 stars
• 1 Month - ⭐ 300 stars
• 3 Months - ⭐ 500 stars
• 1 Year - ⭐ 1000 stars

⚠️ BETA WARNING:
This bot is currently in beta state. It is not recommended to make long-term purchases yet. For any questions, contact: {self.contact_info}

Choose your subscription plan:
            """
            
            keyboard = [
                [InlineKeyboardButton("💳 1 Day - ⭐ 50", callback_data="pay_1day")],
                [InlineKeyboardButton("💳 1 Week - ⭐ 150", callback_data="pay_1week")],
                [InlineKeyboardButton("💳 1 Month - ⭐ 300", callback_data="pay_1month")],
                [InlineKeyboardButton("💳 3 Months - ⭐ 500", callback_data="pay_3months")],
                [InlineKeyboardButton("💳 1 Year - ⭐ 1000", callback_data="pay_1year")],
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(premium_text, reply_markup=reply_markup)
        else:
            # Fallback to admin notification
            premium_text = f"""
⭐ SecShare Premium

Upgrade to unlock advanced features:

🔓 Increased Limits:
• 1GB file size (vs 50MB free)
• 20 transfers per day (vs 5 free)
• Priority support

🔒 Enhanced Security:
• Advanced encryption
• Password protection
• Secure file transfer

💰 Pricing:
• ⭐ 50 stars/day
• ⭐ 150 stars/week
• ⭐ 300 stars/month
• ⭐ 500 stars/3 months
• ⭐ 1000 stars/year

⚠️ BETA WARNING:
This bot is currently in beta state. It is not recommended to make long-term purchases yet. For any questions, contact: {self.contact_info}

Click the button below to express interest in premium features!
            """
            keyboard = [[InlineKeyboardButton("⭐ I'm Interested in Premium", callback_data="premium_interest")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(premium_text, reply_markup=reply_markup)
    
    async def airdrop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /airdrop command for AirDrop-style sharing"""
        airdrop_text = """
📱 SecShare AirDrop

Share files and messages instantly with nearby devices!

How it works:
1. 📤 Send a file or message
2. 📱 Generate QR code
3. 📱 Recipient scans QR code
4. ✅ Instant secure transfer

Features:
• 🔒 End-to-end encryption
• ⚡ Instant transfer
• 📱 QR code sharing
• 🗑️ Auto-cleanup
• 🔐 Password protection

Perfect for:
• 📄 Document sharing
• 🖼️ Photo sharing
• 🎵 Music sharing
• 🔑 Password sharing
• 📝 Note sharing

Just send me a file or message to get started!
        """
        
        keyboard = [
            [InlineKeyboardButton("📁 Send File", callback_data="send_file")],
            [InlineKeyboardButton("💬 Send Message", callback_data="send_message")],
            [InlineKeyboardButton("📥 Receive Package", callback_data="receive_package")],
            [InlineKeyboardButton("📱 AirDrop Sharing", callback_data="airdrop")],
            [InlineKeyboardButton("📊 My Stats", callback_data="stats")],
            [InlineKeyboardButton("⭐ I'm Interested in Premium", callback_data="premium_interest")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(airdrop_text, reply_markup=reply_markup)
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages"""
        user_id = update.effective_user.id
        text = update.message.text
        
        logger.info(f"Received text from user {user_id}: {text[:50]}...")
        
        # Check if waiting for message
        if context.user_data.get('waiting_for_message'):
            logger.info(f"User {user_id} is waiting for message input")
            del context.user_data['waiting_for_message']
            try:
                transfer_id = await self.secshare.create_text_transfer(user_id, text)
                await self._send_transfer_link(update, transfer_id, "text")
                logger.info(f"Created text transfer {transfer_id} for user {user_id}")
            except ValueError as e:
                await update.message.reply_text(f"❌ {str(e)}")
                logger.error(f"Error creating text transfer for user {user_id}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error creating text transfer for user {user_id}: {e}")
                await update.message.reply_text("❌ An error occurred while creating your transfer. Please try again.")
            return
        
        # Check if waiting for transfer ID
        if context.user_data.get('waiting_for_transfer_id'):
            logger.info(f"User {user_id} is waiting for transfer ID input")
            del context.user_data['waiting_for_transfer_id']
            # Extract transfer ID from text (remove bot username if present)
            transfer_id = text.split('/')[-1] if '/' in text else text
            transfer_id = transfer_id.split('?start=')[-1] if '?start=' in transfer_id else transfer_id
            
            logger.info(f"User {user_id} provided transfer ID: {transfer_id}")
            transfer = self.secshare.get_transfer(transfer_id)
            if transfer:
                if transfer.password_hash:
                    context.user_data['waiting_for_password'] = transfer_id
                    await update.message.reply_text("🔐 This transfer is password protected. Please enter the password:")
                else:
                    await self._send_transfer_content(update, transfer)
            else:
                await update.message.reply_text("❌ Transfer not found or expired.")
            return
        
        # Check if this is a password for a transfer
        if 'waiting_for_password' in context.user_data:
            transfer_id = context.user_data['waiting_for_password']
            logger.info(f"User {user_id} provided password for transfer {transfer_id}")
            transfer = self.secshare.get_transfer(transfer_id, text)
            
            if transfer:
                await self._send_transfer_link(update, transfer_id, "file" if transfer.is_file else "text", transfer.file_name if transfer.is_file else None)
                del context.user_data['waiting_for_password']
            else:
                await update.message.reply_text("❌ Invalid password. Please try again.")
            return
        
        # Check if this is a transfer ID
        if len(text) == 22 and text.replace('-', '').replace('_', '').isalnum():
            logger.info(f"User {user_id} provided transfer ID directly: {text}")
            transfer = self.secshare.get_transfer(text)
            if transfer:
                if transfer.password_hash:
                    context.user_data['waiting_for_password'] = text
                    await update.message.reply_text("🔐 This transfer is password protected. Please enter the password:")
                else:
                    await self._send_transfer_content(update, transfer)
            else:
                await update.message.reply_text("❌ Transfer not found or expired.")
            return
        
        # Create a new text transfer (default behavior)
        try:
            logger.info(f"Creating default text transfer for user {user_id}")
            logger.info(f"Text content length: {len(text)} characters")
            logger.info(f"User data: {context.user_data}")
            
            # Check if user exists and get their info
            user = self.secshare._get_user(user_id)
            logger.info(f"User info: {user}")
            
            transfer_id = await self.secshare.create_text_transfer(user_id, text)
            logger.info(f"Transfer created successfully: {transfer_id}")
            
            await self._send_transfer_link(update, transfer_id, "text")
            logger.info(f"Created default text transfer {transfer_id} for user {user_id}")
        except ValueError as e:
            await update.message.reply_text(f"❌ {str(e)}")
            logger.error(f"ValueError creating default text transfer for user {user_id}: {e}")
            logger.error(f"ValueError details: {type(e).__name__}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error creating default text transfer for user {user_id}: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            logger.error(f"Exception details: {str(e)}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            await update.message.reply_text("❌ An error occurred while creating your transfer. Please try again.")
    
    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle document uploads"""
        user_id = update.effective_user.id
        document = update.message.document
        
        logger.info(f"Received document from user {user_id}: {document.file_name} ({document.file_size} bytes)")
        
        try:
            # Check file size first
            if document.file_size is None:
                await update.message.reply_text("❌ Unable to determine file size. Please try again.")
                return
            
            # Ensure temp directory exists with proper permissions
            temp_dir = self.secshare.config['temp_dir']
            os.makedirs(temp_dir, exist_ok=True)
            
            # Test write permissions
            test_file = os.path.join(temp_dir, "test_write.tmp")
            try:
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)
            except Exception as e:
                logger.error(f"Temp directory not writable: {e}")
                await update.message.reply_text("❌ Server storage error. Please try again later.")
                return
            
            # Download the file
            file = await context.bot.get_file(document.file_id)
            file_path = os.path.join(temp_dir, f"{document.file_id}_{document.file_name}")
            
            logger.info(f"Downloading file to {file_path}")
            await file.download_to_drive(file_path)
            
            # Verify file was downloaded and has correct size
            if not os.path.exists(file_path):
                raise Exception("File download failed - file not found on disk")
            
            actual_size = os.path.getsize(file_path)
            if actual_size != document.file_size:
                logger.warning(f"File size mismatch: expected {document.file_size}, got {actual_size}")
            
            logger.info(f"File downloaded successfully: {file_path} ({actual_size} bytes)")
            
            # Create transfer
            transfer_id = await self.secshare.create_file_transfer(
                user_id, file_path, document.file_name, document.file_size
            )
            
            logger.info(f"Created file transfer {transfer_id} for user {user_id}")
            await self._send_transfer_link(update, transfer_id, "file", document.file_name)
            
        except ValueError as e:
            await update.message.reply_text(f"❌ {str(e)}")
            logger.error(f"ValueError in document handling for user {user_id}: {e}")
        except Exception as e:
            logger.error(f"Error handling document for user {user_id}: {e}")
            await update.message.reply_text("❌ An error occurred while processing your file. Please try again.")
            
            # Clean up any partially downloaded file
            if 'file_path' in locals() and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.info(f"Cleaned up partial file: {file_path}")
                except Exception as cleanup_error:
                    logger.error(f"Failed to cleanup partial file: {cleanup_error}")
    
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle photo uploads"""
        user_id = update.effective_user.id
        photo = update.message.photo[-1]  # Get the largest photo
        
        try:
            # Download the file
            file = await context.bot.get_file(photo.file_id)
            file_path = f"{self.secshare.config['temp_dir']}/{photo.file_id}_image.jpg"
            
            await file.download_to_drive(file_path)
            
            # Create transfer
            transfer_id = await self.secshare.create_file_transfer(
                user_id, file_path, "image.jpg", photo.file_size
            )
            
            await self._send_transfer_link(update, transfer_id, "file", "image.jpg")
            
        except ValueError as e:
            await update.message.reply_text(f"❌ {str(e)}")
        except Exception as e:
            logger.error(f"Error handling photo: {e}")
            await update.message.reply_text("❌ An error occurred while processing your image.")
    
    async def handle_video(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle video uploads"""
        user_id = update.effective_user.id
        video = update.message.video
        
        try:
            # Download the file
            file = await context.bot.get_file(video.file_id)
            file_path = f"{self.secshare.config['temp_dir']}/{video.file_id}_video.mp4"
            
            await file.download_to_drive(file_path)
            
            # Create transfer
            transfer_id = await self.secshare.create_file_transfer(
                user_id, file_path, "video.mp4", video.file_size
            )
            
            await self._send_transfer_link(update, transfer_id, "file", "video.mp4")
            
        except ValueError as e:
            await update.message.reply_text(f"❌ {str(e)}")
        except Exception as e:
            logger.error(f"Error handling video: {e}")
            await update.message.reply_text("❌ An error occurred while processing your video.")
    
    async def handle_audio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle audio uploads"""
        user_id = update.effective_user.id
        audio = update.message.audio
        
        try:
            # Download the file
            file = await context.bot.get_file(audio.file_id)
            file_path = f"{self.secshare.config['temp_dir']}/{audio.file_id}_{audio.file_name or 'audio.mp3'}"
            
            await file.download_to_drive(file_path)
            
            # Create transfer
            transfer_id = await self.secshare.create_file_transfer(
                user_id, file_path, audio.file_name or "audio.mp3", audio.file_size
            )
            
            await self._send_transfer_link(update, transfer_id, "file", audio.file_name or "audio.mp3")
            
        except ValueError as e:
            await update.message.reply_text(f"❌ {str(e)}")
        except Exception as e:
            logger.error(f"Error handling audio: {e}")
            await update.message.reply_text("❌ An error occurred while processing your audio.")
    
    async def handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle voice message uploads"""
        user_id = update.effective_user.id
        voice = update.message.voice
        
        try:
            # Download the file
            file = await context.bot.get_file(voice.file_id)
            file_path = f"{self.secshare.config['temp_dir']}/{voice.file_id}_voice.ogg"
            
            await file.download_to_drive(file_path)
            
            # Create transfer
            transfer_id = await self.secshare.create_file_transfer(
                user_id, file_path, "voice.ogg", voice.file_size
            )
            
            await self._send_transfer_link(update, transfer_id, "file", "voice.ogg")
            
        except ValueError as e:
            await update.message.reply_text(f"❌ {str(e)}")
        except Exception as e:
            logger.error(f"Error handling voice: {e}")
            await update.message.reply_text("❌ An error occurred while processing your voice message.")
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "send_file":
            await query.edit_message_text(
                "📁 Please upload the file you want to share securely.\n\n"
                "Supported file types:\n"
                "• Documents (PDF, DOC, TXT, etc.)\n"
                "• Images (JPG, PNG, GIF, etc.)\n"
                "• Videos (MP4, AVI, MOV, etc.)\n"
                "• Audio files (MP3, WAV, etc.)\n"
                "• Voice messages\n\n"
                "Max size: 50MB (free) / 1GB (premium)"
            )
        
        elif query.data == "send_message":
            await query.edit_message_text(
                "💬 Please type the message or password you want to share securely.\n\n"
                "Your message will be encrypted and shared via a secure link."
            )
            context.user_data['waiting_for_message'] = True
        
        elif query.data == "receive_package":
            await query.edit_message_text(
                "📥 To receive a package:\n\n"
                "1. Click the secure link shared with you\n"
                "2. Or paste the transfer ID here\n"
                "3. Enter password if required\n"
                "4. Confirm receipt to auto-delete\n\n"
                "🔗 Paste the transfer ID or link here:"
            )
            context.user_data['waiting_for_transfer_id'] = True
        
        elif query.data == "stats":
            user_id = update.effective_user.id
            stats = self.secshare.get_user_stats(user_id)
            
            stats_text = f"""
📊 Your Statistics

👤 Plan: {'⭐ Premium' if stats['is_premium'] else '🆓 Free'}
📤 Transfers Today: {stats['transfers_used_today']}/{stats['max_transfers_per_day']}
📈 Total Transfers: {stats['total_transfers']}
💾 Max File Size: {stats['max_file_size_mb']}MB
            """
            await query.edit_message_text(stats_text)
        
        elif query.data == "airdrop":
            airdrop_text = """
📱 SecShare AirDrop

Share files and messages instantly with nearby devices!

How it works:
1. 📤 Send a file or message
2. 📱 Generate QR code
3. 📱 Recipient scans QR code
4. ✅ Instant secure transfer

Features:
• 🔒 End-to-end encryption
• ⚡ Instant transfer
• 📱 QR code sharing
• 🗑️ Auto-cleanup
• 🔐 Password protection

Perfect for:
• 📄 Document sharing
• 🖼️ Photo sharing
• 🎵 Music sharing
• 🔑 Password sharing
• 📝 Note sharing

Just send me a file or message to get started!
            """
            
            keyboard = [
                [InlineKeyboardButton("📁 Send File", callback_data="send_file")],
                [InlineKeyboardButton("💬 Send Message", callback_data="send_message")],
                [InlineKeyboardButton("📥 Receive Package", callback_data="receive_package")],
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(airdrop_text, reply_markup=reply_markup)
        
        elif query.data == "pay_1day":
            if self.stars_provider_token:
                try:
                    await context.bot.send_invoice(
                        chat_id=update.effective_chat.id,
                        title="SecShare Premium - 1 Day",
                        description="Upgrade to SecShare Premium for 1 day",
                        payload="premium_1day",
                        provider_token=self.stars_provider_token,
                        currency="USD",
                        prices=[self.premium_prices['1day']],
                        start_parameter="premium_1day",
                        photo_url="https://your-bot-logo-url.com/logo.png",  # Optional
                        photo_width=512,
                        photo_height=512,
                        photo_size=512,
                        need_name=False,
                        need_phone_number=False,
                        need_email=False,
                        need_shipping_address=False,
                        send_phone_number_to_provider=False,
                        send_email_to_provider=False,
                        is_flexible=False,
                        disable_notification=False,
                        protect_content=True
                    )
                except Exception as e:
                    logger.error(f"Error sending 1 day invoice: {e}")
                    await query.edit_message_text("❌ Payment system temporarily unavailable. Please try again later.")
            else:
                await query.edit_message_text("❌ Payment system not configured.")
        
        elif query.data == "pay_1week":
            if self.stars_provider_token:
                try:
                    await context.bot.send_invoice(
                        chat_id=update.effective_chat.id,
                        title="SecShare Premium - 1 Week",
                        description="Upgrade to SecShare Premium for 1 week",
                        payload="premium_1week",
                        provider_token=self.stars_provider_token,
                        currency="USD",
                        prices=[self.premium_prices['1week']],
                        start_parameter="premium_1week",
                        photo_url="https://your-bot-logo-url.com/logo.png",  # Optional
                        photo_width=512,
                        photo_height=512,
                        photo_size=512,
                        need_name=False,
                        need_phone_number=False,
                        need_email=False,
                        need_shipping_address=False,
                        send_phone_number_to_provider=False,
                        send_email_to_provider=False,
                        is_flexible=False,
                        disable_notification=False,
                        protect_content=True
                    )
                except Exception as e:
                    logger.error(f"Error sending 1 week invoice: {e}")
                    await query.edit_message_text("❌ Payment system temporarily unavailable. Please try again later.")
            else:
                await query.edit_message_text("❌ Payment system not configured.")
        
        elif query.data == "pay_1month":
            if self.stars_provider_token:
                try:
                    await context.bot.send_invoice(
                        chat_id=update.effective_chat.id,
                        title="SecShare Premium - 1 Month",
                        description="Upgrade to SecShare Premium for 1 month",
                        payload="premium_1month",
                        provider_token=self.stars_provider_token,
                        currency="USD",
                        prices=[self.premium_prices['1month']],
                        start_parameter="premium_1month",
                        photo_url="https://your-bot-logo-url.com/logo.png",  # Optional
                        photo_width=512,
                        photo_height=512,
                        photo_size=512,
                        need_name=False,
                        need_phone_number=False,
                        need_email=False,
                        need_shipping_address=False,
                        send_phone_number_to_provider=False,
                        send_email_to_provider=False,
                        is_flexible=False,
                        disable_notification=False,
                        protect_content=True
                    )
                except Exception as e:
                    logger.error(f"Error sending 1 month invoice: {e}")
                    await query.edit_message_text("❌ Payment system temporarily unavailable. Please try again later.")
            else:
                await query.edit_message_text("❌ Payment system not configured.")
        
        elif query.data == "pay_3months":
            if self.stars_provider_token:
                try:
                    await context.bot.send_invoice(
                        chat_id=update.effective_chat.id,
                        title="SecShare Premium - 3 Months",
                        description="Upgrade to SecShare Premium for 3 months",
                        payload="premium_3months",
                        provider_token=self.stars_provider_token,
                        currency="USD",
                        prices=[self.premium_prices['3months']],
                        start_parameter="premium_3months",
                        photo_url="https://your-bot-logo-url.com/logo.png",  # Optional
                        photo_width=512,
                        photo_height=512,
                        photo_size=512,
                        need_name=False,
                        need_phone_number=False,
                        need_email=False,
                        need_shipping_address=False,
                        send_phone_number_to_provider=False,
                        send_email_to_provider=False,
                        is_flexible=False,
                        disable_notification=False,
                        protect_content=True
                    )
                except Exception as e:
                    logger.error(f"Error sending 3 months invoice: {e}")
                    await query.edit_message_text("❌ Payment system temporarily unavailable. Please try again later.")
            else:
                await query.edit_message_text("❌ Payment system not configured.")
        
        elif query.data == "pay_1year":
            if self.stars_provider_token:
                try:
                    await context.bot.send_invoice(
                        chat_id=update.effective_chat.id,
                        title="SecShare Premium - 1 Year",
                        description="Upgrade to SecShare Premium for 1 year",
                        payload="premium_1year",
                        provider_token=self.stars_provider_token,
                        currency="USD",
                        prices=[self.premium_prices['1year']],
                        start_parameter="premium_1year",
                        photo_url="https://your-bot-logo-url.com/logo.png",  # Optional
                        photo_width=512,
                        photo_height=512,
                        photo_size=512,
                        need_name=False,
                        need_phone_number=False,
                        need_email=False,
                        need_shipping_address=False,
                        send_phone_number_to_provider=False,
                        send_email_to_provider=False,
                        is_flexible=False,
                        disable_notification=False,
                        protect_content=True
                    )
                except Exception as e:
                    logger.error(f"Error sending 1 year invoice: {e}")
                    await query.edit_message_text("❌ Payment system temporarily unavailable. Please try again later.")
            else:
                await query.edit_message_text("❌ Payment system not configured.")
        
        elif query.data == "premium_interest":
            premium_interest_text = f"""
⭐ Interested in SecShare Premium?

Thank you for your interest! Premium features include:

🔓 Increased Limits:
• 1GB file size (vs 50MB free)
• 20 transfers per day (vs 5 free)
• Priority support

🔒 Enhanced Security:
• Advanced encryption
• Password protection
• Secure file transfer

💰 Pricing Options:
• 1 Day - ⭐ 50 stars
• 1 Week - ⭐ 150 stars
• 1 Month - ⭐ 300 stars
• 3 Months - ⭐ 500 stars
• 1 Year - ⭐ 1000 stars

For questions or support, contact: {self.contact_info}

Choose your subscription plan:
            """
            
            keyboard = [
                [InlineKeyboardButton("⭐ 1 Day - 50 stars", callback_data="pay_1day")],
                [InlineKeyboardButton("⭐ 1 Week - 150 stars", callback_data="pay_1week")],
                [InlineKeyboardButton("⭐ 1 Month - 300 stars", callback_data="pay_1month")],
                [InlineKeyboardButton("⭐ 3 Months - 500 stars", callback_data="pay_3months")],
                [InlineKeyboardButton("⭐ 1 Year - 1000 stars", callback_data="pay_1year")],
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(premium_interest_text, reply_markup=reply_markup)
        
        elif query.data == "back_to_menu":
            welcome_text = f"""
🔐 Welcome to SecShare!

I'm your secure file and password sharing bot. Here's what I can do:

📤 Send Files: Upload any file and get a secure link
🔑 Send Messages: Share sensitive text securely
🔒 Password Protection: Add passwords to your transfers
⏰ Auto-Expiry: Transfers expire in 15 minutes
🗑️ Auto-Delete: Files are deleted after being received

Free Plan:
• 50MB max file size
• 5 transfers per day
• Basic encryption

Premium Plan:
• 1GB max file size  
• 20 transfers per day
• Advanced security features

Just send me a file or text to get started!

Commands:
/sendfile - Send a file
/sendmessage - Send a message
/receive - Receive a package
/stats - View your usage stats
/help - Show this help
/premium - Upgrade to premium
            """
            
            keyboard = [
                [InlineKeyboardButton("📁 Send File", callback_data="send_file")],
                [InlineKeyboardButton("💬 Send Message", callback_data="send_message")],
                [InlineKeyboardButton("📥 Receive Package", callback_data="receive_package")],
                [InlineKeyboardButton("📱 AirDrop Sharing", callback_data="airdrop")],
                [InlineKeyboardButton("📊 My Stats", callback_data="stats")],
                [InlineKeyboardButton("⭐ I'm Interested in Premium", callback_data="premium_interest")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(welcome_text, reply_markup=reply_markup)
        
        elif query.data.startswith("confirm_"):
            transfer_id = query.data.replace("confirm_", "")
            user_id = update.effective_user.id
            logger.info(f"User {user_id} confirmed receipt of transfer {transfer_id}")
            try:
                await self.secshare.confirm_received(transfer_id, user_id)
                await query.edit_message_text("✅ Package received and deleted successfully!")
                logger.info(f"Transfer {transfer_id} confirmed and deleted by user {user_id}")
            except Exception as e:
                logger.error(f"Error confirming transfer {transfer_id} for user {user_id}: {e}")
                await query.edit_message_text("❌ Error confirming receipt. Please try again.")
        
        elif query.data.startswith("delete_"):
            transfer_id = query.data.replace("delete_", "")
            user_id = update.effective_user.id
            logger.info(f"User {user_id} requested deletion of transfer {transfer_id}")
            try:
                # Check if user is the sender
                transfer = self.secshare.get_transfer(transfer_id)
                if transfer and transfer.sender_id == user_id:
                    self.secshare._delete_transfer(transfer_id)
                    await query.edit_message_text("🗑️ Transfer deleted successfully!")
                    logger.info(f"Transfer {transfer_id} deleted by sender {user_id}")
                else:
                    await query.edit_message_text("❌ You can only delete your own transfers.")
            except Exception as e:
                logger.error(f"Error deleting transfer {transfer_id} for user {user_id}: {e}")
                await query.edit_message_text("❌ Error deleting transfer. Please try again.")
        
        elif query.data.startswith("copy_"):
            transfer_id = query.data.replace("copy_", "")
            bot_username = (await update.get_bot()).username
            link = f"https://t.me/{bot_username}?start={transfer_id}"
            
            await query.edit_message_text(
                f"🔗 Copy this link:\n\n`{link}`\n\nClick the link above to copy it to your clipboard.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data=f"back_to_link_{transfer_id}")]
                ])
            )
        
        elif query.data.startswith("qr_"):
            transfer_id = query.data.replace("qr_", "")
            bot_username = (await update.get_bot()).username
            link = f"https://t.me/{bot_username}?start={transfer_id}"
            
            # Generate QR code
            qr_path = self._generate_qr_code(link, transfer_id)
            
            if qr_path and os.path.exists(qr_path):
                try:
                    with open(qr_path, 'rb') as qr_file:
                        await query.edit_message_media(
                            media=InputMediaPhoto(
                                media=qr_file,
                                caption="📱 QR Code for easy sharing\n\nScan this code to access the package directly!"
                            ),
                            reply_markup=InlineKeyboardMarkup([
                                [InlineKeyboardButton("📤 Share QR Code", callback_data=f"share_qr_{transfer_id}")],
                                [InlineKeyboardButton("🔄 Regenerate QR", callback_data=f"regenerate_qr_{transfer_id}")],
                                [InlineKeyboardButton("🔙 Back to Link", callback_data=f"back_to_link_{transfer_id}")]
                            ])
                        )
                except Exception as e:
                    logger.error(f"Error sending QR code: {e}")
                    await query.edit_message_text("❌ Failed to generate QR code. Please try again.")
            else:
                await query.edit_message_text("❌ Failed to generate QR code. Please try again.")
        
        elif query.data.startswith("share_"):
            transfer_id = query.data.replace("share_", "")
            bot_username = (await update.get_bot()).username
            link = f"https://t.me/{bot_username}?start={transfer_id}"
            
            # Create shareable message
            share_text = f"""
📤 SecShare Package

🔗 Secure Link: {link}
⏰ Expires: 15 minutes
🔒 End-to-end encrypted

Click the link to receive the package securely.
            """
            
            # Use Telegram's built-in sharing
            await query.edit_message_text(
                share_text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📤 Share via Telegram", switch_inline_query=f"share {link}")],
                    [InlineKeyboardButton("🔗 Copy Link", callback_data=f"copy_{transfer_id}")],
                    [InlineKeyboardButton("🔙 Back", callback_data=f"back_to_link_{transfer_id}")]
                ])
            )
        
        elif query.data.startswith("share_qr_"):
            transfer_id = query.data.replace("share_qr_", "")
            bot_username = (await update.get_bot()).username
            link = f"https://t.me/{bot_username}?start={transfer_id}"
            
            # Regenerate QR code for sharing
            qr_path = self._generate_qr_code(link, transfer_id)
            
            if qr_path and os.path.exists(qr_path):
                try:
                    with open(qr_path, 'rb') as qr_file:
                        await query.edit_message_media(
                            media=InputMediaPhoto(
                                media=qr_file,
                                caption="📱 QR Code for easy sharing\n\nScan this code to access the package directly!"
                            ),
                            reply_markup=InlineKeyboardMarkup([
                                [InlineKeyboardButton("📤 Share via Telegram", switch_inline_query=f"share {link}")],
                                [InlineKeyboardButton("🔄 Regenerate QR", callback_data=f"regenerate_qr_{transfer_id}")],
                                [InlineKeyboardButton("🔙 Back", callback_data=f"back_to_link_{transfer_id}")]
                            ])
                        )
                except Exception as e:
                    logger.error(f"Error sharing QR code: {e}")
                    await query.edit_message_text("❌ Failed to share QR code. Please try again.")
            else:
                await query.edit_message_text("❌ Failed to generate QR code for sharing.")
        
        elif query.data.startswith("regenerate_qr_"):
            transfer_id = query.data.replace("regenerate_qr_", "")
            bot_username = (await update.get_bot()).username
            link = f"https://t.me/{bot_username}?start={transfer_id}"
            
            # Regenerate QR code
            qr_path = self._generate_qr_code(link, transfer_id)
            
            if qr_path and os.path.exists(qr_path):
                try:
                    with open(qr_path, 'rb') as qr_file:
                        await query.edit_message_media(
                            media=InputMediaPhoto(
                                media=qr_file,
                                caption="📱 QR Code for easy sharing\n\nScan this code to access the package directly!"
                            ),
                            reply_markup=InlineKeyboardMarkup([
                                [InlineKeyboardButton("📤 Share QR Code", callback_data=f"share_qr_{transfer_id}")],
                                [InlineKeyboardButton("🔄 Regenerate QR", callback_data=f"regenerate_qr_{transfer_id}")],
                                [InlineKeyboardButton("🔙 Back to Link", callback_data=f"back_to_link_{transfer_id}")]
                            ])
                        )
                except Exception as e:
                    logger.error(f"Error regenerating QR code: {e}")
                    await query.edit_message_text("❌ Failed to regenerate QR code. Please try again.")
            else:
                await query.edit_message_text("❌ Failed to regenerate QR code. Please try again.")
        
        elif query.data.startswith("back_to_link_"):
            transfer_id = query.data.replace("back_to_link_", "")
            bot_username = (await update.get_bot()).username
            link = f"https://t.me/{bot_username}?start={transfer_id}"
            
            # Return to original link message
            message = f"""
🔗 Secure Package Link

🔗 Link: `{link}`
⏰ Expires: 15 minutes
🔒 Security: End-to-end encrypted

Share this link with your recipient.
            """
            
            keyboard = [
                [InlineKeyboardButton("🔗 Copy Link", callback_data=f"copy_{transfer_id}")],
                [InlineKeyboardButton("📱 Generate QR Code", callback_data=f"qr_{transfer_id}")],
                [InlineKeyboardButton("📤 Share via Telegram", callback_data=f"share_{transfer_id}")],
                [InlineKeyboardButton("🗑️ Delete Now", callback_data=f"delete_{transfer_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(message, reply_markup=reply_markup)
    
    async def _send_transfer_link(self, update: Update, transfer_id: str, transfer_type: str, file_name: str = None):
        """Send transfer link to user with QR code and sharing options"""
        try:
            logger.info(f"Starting _send_transfer_link for transfer {transfer_id}, type: {transfer_type}")
            
            # Get bot username
            try:
                bot_username = (await update.get_bot()).username
                logger.info(f"Bot username: {bot_username}")
            except Exception as e:
                logger.error(f"Error getting bot username: {e}")
                bot_username = "SecShareBot"  # Fallback
            
            link = f"https://t.me/{bot_username}?start={transfer_id}"
            logger.info(f"Generated link: {link}")
            
            if transfer_type == "file":
                message = f"""
📤 File Shared Successfully!

📁 File: {file_name}
🔗 Secure Link: `{link}`
⏰ Expires: 15 minutes
🔒 Security: End-to-end encrypted

Share this link with your recipient. The file will be automatically deleted after they receive it.
                """
            else:
                message = f"""
🔑 Password Shared Successfully!

🔗 Secure Link: `{link}`
⏰ Expires: 15 minutes
🔒 Security: End-to-end encrypted

Share this link with your recipient. The content will be automatically deleted after they receive it.
                """
            
            logger.info(f"Message prepared for transfer {transfer_id}")
            
            # Generate QR code
            try:
                qr_path = self._generate_qr_code(link, transfer_id)
                logger.info(f"QR code generated: {qr_path}")
            except Exception as e:
                logger.error(f"Error generating QR code: {e}")
                qr_path = None
            
            # Create enhanced keyboard with sharing options
            keyboard = [
                [InlineKeyboardButton("🔗 Copy Link", callback_data=f"copy_{transfer_id}")],
                [InlineKeyboardButton("📱 Generate QR Code", callback_data=f"qr_{transfer_id}")],
                [InlineKeyboardButton("📤 Share via Telegram", callback_data=f"share_{transfer_id}")],
                [InlineKeyboardButton("🗑️ Delete Now", callback_data=f"delete_{transfer_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Send the message
            logger.info(f"Sending message for transfer {transfer_id}")
            await update.message.reply_text(message, reply_markup=reply_markup)
            logger.info(f"Message sent successfully for transfer {transfer_id}")
            
            # If QR code was generated successfully, send it as a separate message
            if qr_path and os.path.exists(qr_path):
                try:
                    logger.info(f"Sending QR code for transfer {transfer_id}")
                    with open(qr_path, 'rb') as qr_file:
                        await update.message.reply_photo(
                            photo=qr_file,
                            caption="📱 QR Code for easy sharing\n\nScan this code to access the package directly!",
                            reply_markup=InlineKeyboardMarkup([
                                [InlineKeyboardButton("📤 Share QR Code", callback_data=f"share_qr_{transfer_id}")],
                                [InlineKeyboardButton("🔄 Regenerate QR", callback_data=f"regenerate_qr_{transfer_id}")],
                                [InlineKeyboardButton("🔙 Back to Link", callback_data=f"back_to_link_{transfer_id}")]
                            ])
                        )
                    logger.info(f"QR code sent successfully for transfer {transfer_id}")
                except Exception as e:
                    logger.error(f"Error sending QR code: {e}")
                    await update.message.reply_text("❌ Failed to generate QR code. You can still share the link above.")
            
            logger.info(f"_send_transfer_link completed successfully for transfer {transfer_id}")
            
        except Exception as e:
            logger.error(f"Error in _send_transfer_link for transfer {transfer_id}: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            # Try to send a simple message as fallback
            try:
                await update.message.reply_text(
                    f"✅ Transfer created successfully!\n\n"
                    f"🔗 Link: https://t.me/{(await update.get_bot()).username}?start={transfer_id}\n\n"
                    f"Share this link with your recipient."
                )
            except Exception as fallback_error:
                logger.error(f"Fallback message also failed: {fallback_error}")
                await update.message.reply_text("❌ Transfer created but failed to send link. Please try again.")
    
    async def _send_transfer_content(self, update: Update, transfer: 'Transfer'):
        """Send transfer content to recipient"""
        user_id = update.effective_user.id
        logger.info(f"Sending transfer content to user {user_id}: {transfer.transfer_id}")
        
        try:
            if transfer.is_file:
                if transfer.file_path and os.path.exists(transfer.file_path):
                    logger.info(f"Sending file: {transfer.file_path}")
                    with open(transfer.file_path, 'rb') as f:
                        await update.message.reply_document(
                            document=f,
                            filename=transfer.file_name,
                            caption="📤 Secure file received from SecShare"
                        )
                    logger.info(f"File sent successfully to user {user_id}")
                else:
                    logger.error(f"File not found: {transfer.file_path}")
                    await update.message.reply_text("❌ File not found or already deleted.")
            else:
                try:
                    logger.info(f"Decrypting text content for user {user_id}")
                    decrypted_content = self.secshare._decrypt_content(transfer.encrypted_content)
                    await update.message.reply_text(f"🔑 Secure Message Received:\n\n{decrypted_content}")
                    logger.info(f"Text content sent successfully to user {user_id}")
                except Exception as e:
                    logger.error(f"Error decrypting message for user {user_id}: {e}")
                    await update.message.reply_text("❌ Error decrypting message.")
            
            # Add confirmation button
            keyboard = [[InlineKeyboardButton("✅ Package Received", callback_data=f"confirm_{transfer.transfer_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("Please confirm when you've received the package:", reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Error sending transfer content to user {user_id}: {e}")
            await update.message.reply_text("❌ An error occurred while sending the content. Please try again.")
    
    def _generate_qr_code(self, link: str, transfer_id: str) -> str:
        """Generate a Telegram-style QR code for the transfer link"""
        try:
            # Create QR code with custom styling
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(link)
            qr.make(fit=True)
            
            # Create QR code image with Telegram blue color
            qr_image = qr.make_image(fill_color="#0088CC", back_color="white")
            
            # Convert to PIL Image for further customization
            qr_pil = qr_image.convert('RGBA')
            
            # Create a larger canvas for the final image
            canvas_width = qr_pil.width + 100
            canvas_height = qr_pil.height + 120
            canvas = Image.new('RGBA', (canvas_width, canvas_height), (255, 255, 255, 255))
            
            # Paste QR code in center
            qr_x = (canvas_width - qr_pil.width) // 2
            qr_y = 20
            canvas.paste(qr_pil, (qr_x, qr_y), qr_pil)
            
            # Add Telegram-style header
            draw = ImageDraw.Draw(canvas)
            
            # Try to use a system font, fallback to default if not available
            try:
                # Try different font options
                font_large = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
                font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
            except:
                try:
                    font_large = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 24)
                    font_small = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 16)
                except:
                    # Fallback to default font
                    font_large = ImageFont.load_default()
                    font_small = ImageFont.load_default()
            
            # Add title
            title_text = "SecShare"
            title_bbox = draw.textbbox((0, 0), title_text, font=font_large)
            title_width = title_bbox[2] - title_bbox[0]
            title_x = (canvas_width - title_width) // 2
            draw.text((title_x, qr_y + qr_pil.height + 10), title_text, fill="#0088CC", font=font_large)
            
            # Add subtitle
            subtitle_text = f"Transfer ID: {transfer_id[:8]}..."
            subtitle_bbox = draw.textbbox((0, 0), subtitle_text, font=font_small)
            subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
            subtitle_x = (canvas_width - subtitle_width) // 2
            draw.text((subtitle_x, qr_y + qr_pil.height + 40), subtitle_text, fill="#666666", font=font_small)
            
            # Add instruction
            instruction_text = "Scan to receive package"
            instruction_bbox = draw.textbbox((0, 0), instruction_text, font=font_small)
            instruction_width = instruction_bbox[2] - instruction_bbox[0]
            instruction_x = (canvas_width - instruction_width) // 2
            draw.text((instruction_x, qr_y + qr_pil.height + 65), instruction_text, fill="#999999", font=font_small)
            
            # Save the QR code
            qr_path = f"{self.secshare.config['temp_dir']}/qr_{transfer_id}.png"
            canvas.save(qr_path, 'PNG')
            
            return qr_path
            
        except Exception as e:
            logger.error(f"Error generating QR code: {e}")
            return None
    
    def run(self):
        """Start the bot"""
        logger.info("Starting SecShare bot...")
        
        # Set bot commands using a simple approach
        try:
            import requests
            bot_token = self.application.bot.token
            commands_data = {
                "commands": [
                    {"command": "start", "description": "🚀 Start the bot"},
                    {"command": "sendfile", "description": "📁 Send a file"},
                    {"command": "sendmessage", "description": "💬 Send a message"},
                    {"command": "receive", "description": "📥 Receive a package"},
                    {"command": "stats", "description": "📊 View your usage stats"},
                    {"command": "help", "description": "❓ Get help"},
                    {"command": "premium", "description": "⭐ Upgrade to premium"},
                    {"command": "airdrop", "description": "📱 AirDrop-style sharing"}
                ]
            }
            
            response = requests.post(
                f"https://api.telegram.org/bot{bot_token}/setMyCommands",
                json=commands_data,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("Bot commands set successfully via API")
            else:
                logger.warning(f"Failed to set bot commands: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.warning(f"Could not set bot commands: {e}")
        
        self.application.run_polling()

def main():
    """Main function"""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set!")
        return
    
    bot = TelegramSecShareBot(bot_token)
    bot.run()

if __name__ == "__main__":
    main()
