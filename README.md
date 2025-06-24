# 🔐 SecShare - Secure File & Password Sharing Telegram Bot

A secure, end-to-end encrypted file and password sharing Telegram bot with automatic cleanup and premium features.

## ✨ Features

### 🔒 Security
- **End-to-end encryption** for all content
- **Password protection** for sensitive transfers
- **Automatic expiry** (15 minutes, extendable for premium)
- **Secure file storage** with no logs
- **Zero-knowledge architecture**

### 📤 Easy Sharing
- **One-click file uploads** - just send any file
- **Instant text sharing** - type and share
- **Direct links** - recipients get direct bot access
- **QR code generation** - scan to access packages instantly
- **AirDrop-style sharing** - instant nearby device transfer
- **Auto-cleanup** - files deleted after receipt

### 🎯 User Experience
- **Intuitive interface** with inline buttons
- **QR code sharing** for instant transfers
- **Multiple sharing options** (link, QR, Telegram share)
- **Usage statistics** and limits tracking
- **Premium tier** with increased limits
- **Mobile-friendly** design

### 📊 Plans

#### Free Plan
- 50MB max file size
- 5 transfers per day
- Basic encryption
- 15-minute expiry

#### Premium Plan
- 1GB max file size
- 20 transfers per day
- Advanced security features
- (Future) Extend expiry to 24 hours

## 🚀 Quick Start

### 1. Create Telegram Bot
1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot` and follow instructions
3. Copy your bot token

### 2. Deploy to Railway
1. Fork this repository
2. Connect to [Railway](https://railway.app)
3. Add environment variable: `TELEGRAM_BOT_TOKEN=your_bot_token`
4. Deploy!

### 3. Local Development
```bash
# Clone repository
git clone <your-repo-url>
cd SecShare

# Install dependencies
pip install -r requirements.txt

# Dependencies include:
# - python-telegram-bot: Telegram bot API
# - cryptography: Encryption and security
# - qrcode[pil]: QR code generation with custom styling
# - Pillow: Image processing for QR codes

# Set environment variable
export TELEGRAM_BOT_TOKEN=your_bot_token

# Run bot
python main.py
```

## 📁 Project Structure

```
SecShare/
├── main.py              # Telegram bot interface
├── SecShare.py          # Core bot functionality
├── requirements.txt     # Python dependencies
├── railway.json        # Railway deployment config
├── README.md           # This file
├── data/               # User and transfer data (auto-created)
└── temp_files/         # Temporary file storage (auto-created)
```

## 🔧 Configuration

### Environment Variables
- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token (required)
- `ADMIN_USER_ID`: Your Telegram user ID for admin access (optional)
- `STARS_PROVIDER_TOKEN`: Telegram Stars provider token for payments (optional)
- `CONTACT_INFO`: Contact information for support (optional, defaults to "Contact admin for support")

### Telegram Stars Payment Setup

To enable Telegram Stars payments for premium features:

1. **Get a Stars Provider Token:**
   - Contact @BotFather and request a Stars provider token
   - Or apply through Telegram's payment system
   - Set the token as `STARS_PROVIDER_TOKEN` environment variable

2. **Configure Prices:**
   - 1 Day: ⭐ 50 stars
   - 1 Week: ⭐ 150 stars
   - 1 Month: ⭐ 300 stars
   - 3 Months: ⭐ 500 stars
   - 1 Year: ⭐ 1000 stars
   - Prices are configured in the bot code

3. **Payment Flow:**
   - Users click "Upgrade to Premium"
   - Choose from 5 subscription options
   - Pay with Telegram Stars
   - Automatically upgraded to premium
   - Beta warning displayed to users

4. **Fallback:**
   - If Stars not configured, shows "I'm Interested" button
   - Sends admin notification for manual processing

### Bot Settings (in SecShare.py)
```python
self.config = {
    'free_file_size_limit': 50 * 1024 * 1024,      # 50MB
    'premium_file_size_limit': 1024 * 1024 * 1024, # 1GB
    'free_transfers_per_hour': 5,
    'premium_transfers_per_hour': 20,
    'transfer_expiry_minutes': 15,                 # 15 minutes (default)
    # Future: allow premium users to extend to 24 hours
    'temp_dir': 'temp_files',
    'data_dir': 'data'
}
```

## 🛠️ Usage

### For Senders
1. **Send a file** - Upload any file to the bot
2. **Send text** - Type your message and send
3. **Get link & QR code** - Bot provides secure link and QR code
4. **Share options** - Choose from multiple sharing methods:
   - 🔗 Direct link sharing
   - 📱 QR code scanning
   - 📤 Telegram built-in sharing
   - 📱 AirDrop-style nearby sharing

### For Recipients
1. **Click link or scan QR** - Opens bot with transfer
2. **Enter password** (if required)
3. **Receive content** - File or text delivered
4. **Confirm receipt** - Auto-deletes content (expires in 15 minutes)

### Commands
- `/start` - Welcome message and main menu
- `/help` - Show help information
- `/stats` - View your usage statistics
- `/premium` - Upgrade to premium plan
- `/airdrop` - AirDrop-style sharing interface

## 🔐 Security Features

### Encryption
- **Fernet symmetric encryption** for text content
- **PBKDF2 password hashing** with salt
- **Secure key generation** using cryptography library
- **Short-lived transfers** (15 minutes by default, extendable for premium in the future)

### Data Protection
- **No persistent logs** of file content
- **Automatic cleanup** of expired transfers
- **Secure file deletion** after receipt
- **User data isolation**

### Privacy
- **Anonymous transfers** - no sender tracking
- **Temporary storage** - files not permanently stored
- **Zero-knowledge** - bot can't access content

## 🚀 Deployment

### Railway (Recommended)
1. Connect your GitHub repository to Railway
2. Add environment variable: `TELEGRAM_BOT_TOKEN`
3. Deploy automatically on push

### Other Platforms
- **Heroku**: Add `Procfile` with `worker: python main.py`
- **DigitalOcean**: Use App Platform
- **VPS**: Run with `python main.py`

## 🔮 Future Improvements

### Planned Features
- [x] **QR code generation** with Telegram-style design
- [x] **AirDrop-style sharing** for instant nearby transfers
- [x] **Multiple sharing options** (link, QR, Telegram share)
- [ ] **Premium subscription system** with payment integration
- [ ] **Advanced encryption** with RSA key pairs
- [ ] **File compression** for larger transfers
- [ ] **Transfer scheduling** for delayed delivery
- [ ] **Group sharing** with multiple recipients
- [ ] **Transfer analytics** and usage reports
- [ ] **API endpoints** for external integrations
- [ ] **Web interface** for management

### Technical Enhancements
- [ ] **Database integration** (PostgreSQL/MongoDB)
- [ ] **Redis caching** for better performance
- [ ] **CDN integration** for file storage
- [ ] **Rate limiting** and DDoS protection
- [ ] **Monitoring** and alerting system

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Documentation**: Check this README
- **Issues**: Create a GitHub issue
- **Telegram**: Contact @your_support_username

## ⚠️ Disclaimer

This bot is designed for secure file sharing but should not be used for illegal content. Users are responsible for their own content and compliance with local laws.

---

**Made with ❤️ for secure communication** 