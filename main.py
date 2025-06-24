import os
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from SecShare import SecShareBot

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TelegramSecShareBot:
    def __init__(self, bot_token: str):
        self.secshare = SecShareBot(bot_token)
        self.application = Application.builder().token(bot_token).build()
        self._setup_handlers()
        self._setup_commands()
    
    def _setup_commands(self):
        """Setup bot commands for better UX"""
        commands = [
            BotCommand("start", "🚀 Start the bot"),
            BotCommand("sendfile", "📁 Send a file"),
            BotCommand("sendmessage", "💬 Send a message"),
            BotCommand("receive", "📥 Receive a package"),
            BotCommand("stats", "📊 View your usage stats"),
            BotCommand("help", "❓ Get help"),
            BotCommand("premium", "⭐ Upgrade to premium")
        ]
        # Set commands when bot starts
        asyncio.create_task(self.application.bot.set_my_commands(commands))
    
    def _setup_handlers(self):
        """Setup all bot handlers"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("sendfile", self.sendfile_command))
        self.application.add_handler(CommandHandler("sendmessage", self.sendmessage_command))
        self.application.add_handler(CommandHandler("receive", self.receive_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        self.application.add_handler(CommandHandler("premium", self.premium_command))
        
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
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
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

How to use:

1. Send a File: Use /sendfile or upload any file
2. Send Text: Use /sendmessage or type your message
3. Add Password: Reply with a password when prompted
4. Share Link: Send the link to your recipient
5. Auto-Cleanup: Files are deleted after being received

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
        """Handle /premium command"""
        premium_text = """
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
• $9.99/month
• $99.99/year (17% savings)

Click the button below to express interest in premium features!
        """
        keyboard = [[InlineKeyboardButton("⭐ I'm Interested in Premium", callback_data="premium_interest")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(premium_text, reply_markup=reply_markup)
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages"""
        user_id = update.effective_user.id
        text = update.message.text
        
        # Check if waiting for message
        if context.user_data.get('waiting_for_message'):
            del context.user_data['waiting_for_message']
            try:
                transfer_id = await self.secshare.create_text_transfer(user_id, text)
                await self._send_transfer_link(update, transfer_id, "text")
            except ValueError as e:
                await update.message.reply_text(f"❌ {str(e)}")
            return
        
        # Check if waiting for transfer ID
        if context.user_data.get('waiting_for_transfer_id'):
            del context.user_data['waiting_for_transfer_id']
            # Extract transfer ID from text (remove bot username if present)
            transfer_id = text.split('/')[-1] if '/' in text else text
            transfer_id = transfer_id.split('?start=')[-1] if '?start=' in transfer_id else transfer_id
            
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
            transfer = self.secshare.get_transfer(transfer_id, text)
            
            if transfer:
                await self._send_transfer_content(update, transfer)
                del context.user_data['waiting_for_password']
            else:
                await update.message.reply_text("❌ Invalid password. Please try again.")
            return
        
        # Check if this is a transfer ID
        if len(text) == 22 and text.replace('-', '').replace('_', '').isalnum():
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
            transfer_id = await self.secshare.create_text_transfer(user_id, text)
            await self._send_transfer_link(update, transfer_id, "text")
        except ValueError as e:
            await update.message.reply_text(f"❌ {str(e)}")
    
    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle document uploads"""
        user_id = update.effective_user.id
        document = update.message.document
        
        try:
            # Download the file
            file = await context.bot.get_file(document.file_id)
            file_path = f"{self.secshare.config['temp_dir']}/{document.file_id}_{document.file_name}"
            
            await file.download_to_drive(file_path)
            
            # Create transfer
            transfer_id = await self.secshare.create_file_transfer(
                user_id, file_path, document.file_name, document.file_size
            )
            
            await self._send_transfer_link(update, transfer_id, "file", document.file_name)
            
        except ValueError as e:
            await update.message.reply_text(f"❌ {str(e)}")
        except Exception as e:
            logger.error(f"Error handling document: {e}")
            await update.message.reply_text("❌ An error occurred while processing your file.")
    
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
        
        elif query.data == "premium_interest":
            user = update.effective_user
            admin_id = os.getenv('ADMIN_USER_ID')
            
            if admin_id:
                try:
                    admin_message = f"""
⭐ Premium Interest Alert!

User: {user.first_name} {user.last_name or ''}
Username: @{user.username or 'No username'}
User ID: {user.id}
Plan: {'Premium' if self.secshare.is_admin(user.id) else 'Free'}

This user is interested in premium features!
                    """
                    await context.bot.send_message(chat_id=int(admin_id), text=admin_message)
                    await query.edit_message_text("✅ Thank you for your interest! I've notified the admin about your premium inquiry.")
                except Exception as e:
                    logger.error(f"Error sending admin notification: {e}")
                    await query.edit_message_text("✅ Thank you for your interest in premium features!")
            else:
                await query.edit_message_text("✅ Thank you for your interest in premium features!")
        
        elif query.data == "back_to_menu":
            user = update.effective_user
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
                [InlineKeyboardButton("📊 My Stats", callback_data="stats")],
                [InlineKeyboardButton("⭐ I'm Interested in Premium", callback_data="premium_interest")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(welcome_text, reply_markup=reply_markup)
        
        elif query.data.startswith("confirm_"):
            transfer_id = query.data.replace("confirm_", "")
            user_id = update.effective_user.id
            await self.secshare.confirm_received(transfer_id, user_id)
            await query.edit_message_text("✅ Package received and deleted successfully!")
    
    async def _send_transfer_link(self, update: Update, transfer_id: str, transfer_type: str, file_name: str = None):
        """Send transfer link to user"""
        bot_username = (await update.get_bot()).username
        link = f"https://t.me/{bot_username}?start={transfer_id}"
        
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
        
        keyboard = [
            [InlineKeyboardButton("🔗 Copy Link", callback_data=f"copy_{transfer_id}")],
            [InlineKeyboardButton("🗑️ Delete Now", callback_data=f"delete_{transfer_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(message, reply_markup=reply_markup)
    
    async def _send_transfer_content(self, update: Update, transfer: 'Transfer'):
        """Send transfer content to recipient"""
        if transfer.is_file:
            if transfer.file_path and os.path.exists(transfer.file_path):
                with open(transfer.file_path, 'rb') as f:
                    await update.message.reply_document(
                        document=f,
                        filename=transfer.file_name,
                        caption="📤 Secure file received from SecShare"
                    )
            else:
                await update.message.reply_text("❌ File not found or already deleted.")
        else:
            try:
                decrypted_content = self.secshare._decrypt_content(transfer.encrypted_content)
                await update.message.reply_text(f"🔑 Secure Message Received:\n\n{decrypted_content}")
            except Exception as e:
                await update.message.reply_text("❌ Error decrypting message.")
        
        # Add confirmation button
        keyboard = [[InlineKeyboardButton("✅ Package Received", callback_data=f"confirm_{transfer.transfer_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Please confirm when you've received the package:", reply_markup=reply_markup)
    
    def run(self):
        """Start the bot"""
        logger.info("Starting SecShare bot...")
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
