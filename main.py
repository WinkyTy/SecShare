import os
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
    
    def _setup_handlers(self):
        """Setup all bot handlers"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        self.application.add_handler(CommandHandler("premium", self.premium_command))
        
        # Handle text messages (for password-protected transfers)
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
        
        # Handle file uploads
        self.application.add_handler(MessageHandler(filters.Document.ALL, self.handle_document))
        
        # Handle callback queries (buttons)
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        welcome_text = f"""
🔐 Welcome to SecShare, {user.first_name}!

I'm your secure file and password sharing bot. Here's what I can do:

📤 **Send Files**: Upload any file and get a secure link
🔑 **Send Passwords**: Share sensitive text securely
🔒 **Password Protection**: Add passwords to your transfers
⏰ **Auto-Expiry**: Transfers expire in 24 hours
🗑️ **Auto-Delete**: Files are deleted after being received

**Free Plan:**
• 50MB max file size
• 5 transfers per day
• Basic encryption

**Premium Plan:**
• 1GB max file size  
• 20 transfers per day
• Advanced security features

Just send me a file or text to get started!

Commands:
/help - Show this help
/stats - View your usage stats
/premium - Upgrade to premium
        """
        
        keyboard = [
            [InlineKeyboardButton("📤 Send File", callback_data="send_file")],
            [InlineKeyboardButton("🔑 Send Password", callback_data="send_password")],
            [InlineKeyboardButton("📊 My Stats", callback_data="stats")],
            [InlineKeyboardButton("⭐ Upgrade Premium", callback_data="premium")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
🔐 **SecShare Help**

**How to use:**

1. **Send a File**: Just upload any file and I'll give you a secure link
2. **Send Text**: Type your message and I'll encrypt it
3. **Add Password**: Reply with a password when prompted
4. **Share Link**: Send the link to your recipient
5. **Auto-Cleanup**: Files are deleted after being received

**Security Features:**
• End-to-end encryption
• Password protection
• Auto-expiry (24 hours)
• Secure file storage
• No logs kept

**Commands:**
/start - Welcome message
/help - This help
/stats - Your usage statistics
/premium - Upgrade to premium

**Need help?** Contact @your_support_username
        """
        await update.message.reply_text(help_text)
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        user_id = update.effective_user.id
        stats = self.secshare.get_user_stats(user_id)
        
        stats_text = f"""
📊 **Your Statistics**

👤 **Plan**: {'⭐ Premium' if stats['is_premium'] else '🆓 Free'}
📤 **Transfers Today**: {stats['transfers_used_today']}/{stats['max_transfers_per_day']}
📈 **Total Transfers**: {stats['total_transfers']}
💾 **Max File Size**: {stats['max_file_size_mb']}MB
        """
        
        keyboard = []
        if not stats['is_premium']:
            keyboard.append([InlineKeyboardButton("⭐ Upgrade to Premium", callback_data="premium")])
        
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        await update.message.reply_text(stats_text, reply_markup=reply_markup)
    
    async def premium_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /premium command"""
        premium_text = """
⭐ **SecShare Premium**

Upgrade to unlock advanced features:

🔓 **Increased Limits:**
• 1GB file size (vs 50MB free)
• 20 transfers per day (vs 5 free)
• Priority support

🔒 **Enhanced Security:**
• Advanced encryption
• Password protection
• Secure file transfer

💰 **Pricing:**
• $9.99/month
• $99.99/year (17% savings)

To upgrade, contact @your_support_username
        """
        await update.message.reply_text(premium_text)
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages"""
        user_id = update.effective_user.id
        text = update.message.text
        
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
        
        # Create a new text transfer
        try:
            transfer_id = await self.secshare.create_text_transfer(user_id, text)
            await self._send_transfer_link(update, transfer_id, "text")
        except ValueError as e:
            await update.message.reply_text(f"❌ {str(e)}")
    
    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle file uploads"""
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
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "send_file":
            await query.edit_message_text("📤 Please upload the file you want to share securely.")
        
        elif query.data == "send_password":
            await query.edit_message_text("🔑 Please type the password or sensitive text you want to share securely.")
        
        elif query.data == "stats":
            user_id = update.effective_user.id
            stats = self.secshare.get_user_stats(user_id)
            
            stats_text = f"""
📊 **Your Statistics**

👤 **Plan**: {'⭐ Premium' if stats['is_premium'] else '🆓 Free'}
📤 **Transfers Today**: {stats['transfers_used_today']}/{stats['max_transfers_per_day']}
📈 **Total Transfers**: {stats['total_transfers']}
💾 **Max File Size**: {stats['max_file_size_mb']}MB
            """
            await query.edit_message_text(stats_text)
        
        elif query.data == "premium":
            await self.premium_command(update, context)
    
    async def _send_transfer_link(self, update: Update, transfer_id: str, transfer_type: str, file_name: str = None):
        """Send transfer link to user"""
        bot_username = (await update.get_bot()).username
        link = f"https://t.me/{bot_username}?start={transfer_id}"
        
        if transfer_type == "file":
            message = f"""
📤 **File Shared Successfully!**

📁 **File**: {file_name}
🔗 **Secure Link**: `{link}`
⏰ **Expires**: 24 hours
🔒 **Security**: End-to-end encrypted

Share this link with your recipient. The file will be automatically deleted after they receive it.
            """
        else:
            message = f"""
🔑 **Password Shared Successfully!**

🔗 **Secure Link**: `{link}`
⏰ **Expires**: 24 hours
🔒 **Security**: End-to-end encrypted

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
                await update.message.reply_text(f"🔑 **Secure Message Received:**\n\n{decrypted_content}")
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
