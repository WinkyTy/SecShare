import os
import json
import hashlib
import secrets
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, asdict
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import tempfile
import shutil
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class User:
    """User data structure with usage tracking"""
    user_id: int
    username: Optional[str]
    is_premium: bool = False
    files_sent_today: int = 0
    last_reset_date: str = ""
    total_transfers: int = 0

@dataclass
class Transfer:
    """Transfer data structure"""
    transfer_id: str
    sender_id: int
    recipient_id: Optional[int]
    file_path: Optional[str]
    encrypted_content: Optional[str]
    password_hash: Optional[str]
    created_at: str
    expires_at: str
    is_file: bool
    file_size: Optional[int] = None
    file_name: Optional[str] = None

class SecShareBot:
    """Secure file and password sharing Telegram bot"""
    
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.users: Dict[int, User] = {}
        self.transfers: Dict[str, Transfer] = {}
        self.encryption_key = Fernet.generate_key()
        self.cipher_suite = Fernet(self.encryption_key)
        
        # Admin and superuser support
        admin_id_env = os.getenv('ADMIN_USER_ID', '999999999')  # Default dummy ID for testing
        self.admin_ids = set()
        if admin_id_env:
            try:
                self.admin_ids.add(int(admin_id_env))
            except ValueError:
                logger.warning('ADMIN_USER_ID must be an integer')
        self.superuser_ids = set()  # For future superusers
        
        # Configuration
        self.config = {
            'free_file_size_limit': 50 * 1024 * 1024,  # 50MB
            'premium_file_size_limit': 1024 * 1024 * 1024,  # 1GB
            'free_transfers_per_hour': 5,
            'premium_transfers_per_hour': 20,
            'transfer_expiry_minutes': 15,  # 15 minutes for all users
            # Future: allow premium users to extend to 24 hours
            'temp_dir': 'temp_files',
            'data_dir': 'data'
        }
        
        # Create necessary directories
        self._setup_directories()
        self._load_data()
        
        # Don't start cleanup task here - will be started when event loop is running
    
    def _setup_directories(self):
        """Create necessary directories for file storage"""
        os.makedirs(self.config['temp_dir'], exist_ok=True)
        os.makedirs(self.config['data_dir'], exist_ok=True)
    
    def _load_data(self):
        """Load users and transfers from disk"""
        try:
            if os.path.exists(f"{self.config['data_dir']}/users.json"):
                with open(f"{self.config['data_dir']}/users.json", 'r') as f:
                    users_data = json.load(f)
                    self.users = {int(k): User(**v) for k, v in users_data.items()}
            
            if os.path.exists(f"{self.config['data_dir']}/transfers.json"):
                with open(f"{self.config['data_dir']}/transfers.json", 'r') as f:
                    transfers_data = json.load(f)
                    self.transfers = {k: Transfer(**v) for k, v in transfers_data.items()}
        except Exception as e:
            logger.error(f"Error loading data: {e}")
    
    def _save_data(self):
        """Save users and transfers to disk"""
        try:
            logger.info("Starting data save operation")
            
            # Save users
            logger.info(f"Saving {len(self.users)} users")
            users_file = f"{self.config['data_dir']}/users.json"
            with open(users_file, 'w') as f:
                json.dump({str(k): asdict(v) for k, v in self.users.items()}, f, indent=2)
            logger.info(f"Users saved to {users_file}")
            
            # Save transfers
            logger.info(f"Saving {len(self.transfers)} transfers")
            transfers_file = f"{self.config['data_dir']}/transfers.json"
            with open(transfers_file, 'w') as f:
                json.dump({k: asdict(v) for k, v in self.transfers.items()}, f, indent=2)
            logger.info(f"Transfers saved to {transfers_file}")
            
            logger.info("Data save operation completed successfully")
            
        except Exception as e:
            logger.error(f"Error saving data: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            # Don't re-raise the exception to avoid breaking the bot
            # Just log the error and continue
    
    def _generate_transfer_id(self) -> str:
        """Generate a unique transfer ID"""
        return secrets.token_urlsafe(16)
    
    def _hash_password(self, password: str) -> str:
        """Hash password using PBKDF2"""
        salt = os.urandom(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return base64.urlsafe_b64encode(salt + key).decode()
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        try:
            decoded = base64.urlsafe_b64decode(password_hash.encode())
            salt = decoded[:16]
            stored_key = decoded[16:]
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
            return stored_key == key
        except Exception:
            return False
    
    def _encrypt_content(self, content: str) -> str:
        """Encrypt text content"""
        try:
            logger.info(f"Encrypting content of length {len(content)}")
            encrypted = self.cipher_suite.encrypt(content.encode())
            result = encrypted.decode()
            logger.info(f"Content encrypted successfully, result length: {len(result)}")
            return result
        except Exception as e:
            logger.error(f"Error encrypting content: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise
    
    def _decrypt_content(self, encrypted_content: str) -> str:
        """Decrypt text content"""
        try:
            logger.info(f"Decrypting content of length {len(encrypted_content)}")
            decrypted = self.cipher_suite.decrypt(encrypted_content.encode())
            result = decrypted.decode()
            logger.info(f"Content decrypted successfully, result length: {len(result)}")
            return result
        except Exception as e:
            logger.error(f"Error decrypting content: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise
    
    def is_admin(self, user_id: int) -> bool:
        return user_id in self.admin_ids or user_id in self.superuser_ids

    def add_superuser(self, user_id: int):
        self.superuser_ids.add(user_id)

    def _get_user(self, user_id: int, username: Optional[str] = None) -> User:
        if user_id not in self.users:
            self.users[user_id] = User(user_id=user_id, username=username)
        # Admins and superusers always premium
        if self.is_admin(user_id):
            self.users[user_id].is_premium = True
        self._save_data()
        return self.users[user_id]
    
    def _check_user_limits(self, user_id: int) -> Tuple[bool, str]:
        if self.is_admin(user_id):
            return True, ""
        user = self._get_user(user_id)
        
        # Reset daily limits if needed
        today = datetime.now().strftime('%Y-%m-%d')
        if user.last_reset_date != today:
            user.files_sent_today = 0
            user.last_reset_date = today
        
        max_transfers = (self.config['premium_transfers_per_hour'] 
                        if user.is_premium 
                        else self.config['free_transfers_per_hour'])
        
        if user.files_sent_today >= max_transfers:
            return False, f"You've reached your daily limit of {max_transfers} transfers. Upgrade to premium for more!"
        
        return True, ""
    
    def _check_file_size_limit(self, file_size: int, user_id: int) -> Tuple[bool, str]:
        """Check if file size is within limits"""
        if self.is_admin(user_id):
            return True, ""
        user = self._get_user(user_id)
        max_size = (self.config['premium_file_size_limit'] 
                   if user.is_premium 
                   else self.config['free_file_size_limit'])
        
        if file_size > max_size:
            size_mb = max_size // (1024 * 1024)
            return False, f"File too large! Free users: {size_mb}MB max. Upgrade to premium for 1GB files."
        
        return True, ""
    
    async def create_text_transfer(self, user_id: int, content: str, password: Optional[str] = None) -> str:
        """Create a text transfer"""
        logger.info(f"Starting text transfer creation for user {user_id}")
        
        try:
            # Check limits
            logger.info(f"Checking user limits for user {user_id}")
            can_send, error_msg = self._check_user_limits(user_id)
            if not can_send:
                logger.warning(f"User {user_id} hit limits: {error_msg}")
                raise ValueError(error_msg)
            logger.info(f"User {user_id} passed limit check")
            
            # Encrypt content
            logger.info(f"Encrypting content for user {user_id}")
            encrypted_content = self._encrypt_content(content)
            logger.info(f"Content encrypted successfully for user {user_id}")
            
            # Create transfer
            logger.info(f"Creating transfer object for user {user_id}")
            transfer_id = self._generate_transfer_id()
            expires_at = (datetime.now() + timedelta(minutes=self.config['transfer_expiry_minutes'])).isoformat()
            
            transfer = Transfer(
                transfer_id=transfer_id,
                sender_id=user_id,
                recipient_id=None,
                file_path=None,
                encrypted_content=encrypted_content,
                password_hash=self._hash_password(password) if password else None,
                created_at=datetime.now().isoformat(),
                expires_at=expires_at,
                is_file=False
            )
            
            logger.info(f"Transfer object created: {transfer_id}")
            
            # Add to transfers dict
            self.transfers[transfer_id] = transfer
            logger.info(f"Transfer added to dict: {transfer_id}")
            
            # Update user stats
            logger.info(f"Updating user stats for user {user_id}")
            user = self._get_user(user_id)
            user.files_sent_today += 1
            user.total_transfers += 1
            logger.info(f"User stats updated: files_sent_today={user.files_sent_today}, total_transfers={user.total_transfers}")
            
            # Save data
            logger.info(f"Saving data for user {user_id}")
            self._save_data()
            logger.info(f"Data saved successfully for user {user_id}")
            
            logger.info(f"Text transfer creation completed successfully: {transfer_id}")
            return transfer_id
            
        except Exception as e:
            logger.error(f"Error in create_text_transfer for user {user_id}: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise
    
    async def create_file_transfer(self, user_id: int, file_path: str, file_name: str, 
                                 file_size: int, password: Optional[str] = None) -> str:
        """Create a file transfer"""
        # Check limits
        can_send, error_msg = self._check_user_limits(user_id)
        if not can_send:
            raise ValueError(error_msg)
        
        # Check file size
        size_ok, error_msg = self._check_file_size_limit(file_size, user_id)
        if not size_ok:
            raise ValueError(error_msg)
        
        # Create transfer
        transfer_id = self._generate_transfer_id()
        expires_at = (datetime.now() + timedelta(minutes=self.config['transfer_expiry_minutes'])).isoformat()
        
        transfer = Transfer(
            transfer_id=transfer_id,
            sender_id=user_id,
            recipient_id=None,
            file_path=file_path,
            encrypted_content=None,
            password_hash=self._hash_password(password) if password else None,
            created_at=datetime.now().isoformat(),
            expires_at=expires_at,
            is_file=True,
            file_size=file_size,
            file_name=file_name
        )
        
        self.transfers[transfer_id] = transfer
        
        # Update user stats
        user = self._get_user(user_id)
        user.files_sent_today += 1
        user.total_transfers += 1
        self._save_data()
        
        return transfer_id
    
    def get_transfer(self, transfer_id: str, password: Optional[str] = None) -> Optional[Transfer]:
        """Get transfer by ID with optional password verification"""
        if transfer_id not in self.transfers:
            return None
        
        transfer = self.transfers[transfer_id]
        
        # Check if expired
        if datetime.fromisoformat(transfer.expires_at) < datetime.now():
            self._delete_transfer(transfer_id)
            return None
        
        # Check password if required
        if transfer.password_hash:
            if not password:
                return None  # Password required but not provided
            if not self._verify_password(password, transfer.password_hash):
                return None  # Wrong password
        
        return transfer
    
    def _delete_transfer(self, transfer_id: str):
        """Delete transfer and associated files"""
        if transfer_id in self.transfers:
            transfer = self.transfers[transfer_id]
            
            # Delete file if exists
            if transfer.file_path and os.path.exists(transfer.file_path):
                try:
                    os.remove(transfer.file_path)
                except Exception as e:
                    logger.error(f"Error deleting file {transfer.file_path}: {e}")
            
            del self.transfers[transfer_id]
            self._save_data()
    
    async def confirm_received(self, transfer_id: str, recipient_id: int):
        """Confirm transfer was received and delete it"""
        if transfer_id in self.transfers:
            transfer = self.transfers[transfer_id]
            transfer.recipient_id = recipient_id
            self._delete_transfer(transfer_id)
    
    def get_user_stats(self, user_id: int) -> Dict:
        """Get user statistics"""
        user = self._get_user(user_id)
        max_transfers = (self.config['premium_transfers_per_hour'] 
                        if user.is_premium 
                        else self.config['free_transfers_per_hour'])
        max_file_size = (self.config['premium_file_size_limit'] 
                        if user.is_premium 
                        else self.config['free_file_size_limit'])
        
        return {
            'is_premium': user.is_premium,
            'transfers_used_today': user.files_sent_today,
            'transfers_remaining_today': max_transfers - user.files_sent_today,
            'total_transfers': user.total_transfers,
            'max_file_size_mb': max_file_size // (1024 * 1024),
            'max_transfers_per_day': max_transfers
        } 