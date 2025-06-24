#!/usr/bin/env python3
"""
Test script to identify the specific error in transfer creation
"""

import os
import sys
import asyncio
import logging

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from SecShare import SecShareBot

async def test_transfer_creation():
    """Test transfer creation with detailed logging"""
    print("🔍 Testing transfer creation with detailed logging...")
    
    try:
        # Initialize bot
        bot = SecShareBot("dummy_token")
        print("✅ Bot initialized successfully")
        
        # Test user creation
        user_id = 123456
        user = bot._get_user(user_id, "testuser")
        print(f"✅ User created: {user}")
        
        # Test text transfer creation
        print("\n📝 Testing text transfer creation...")
        try:
            transfer_id = await bot.create_text_transfer(user_id, "Test message")
            print(f"✅ Text transfer created successfully: {transfer_id}")
            
            # Test retrieval
            transfer = bot.get_transfer(transfer_id)
            if transfer:
                print(f"✅ Transfer retrieved successfully: {transfer.transfer_id}")
                decrypted = bot._decrypt_content(transfer.encrypted_content)
                print(f"✅ Content decrypted: {decrypted}")
            else:
                print("❌ Failed to retrieve transfer")
                
        except Exception as e:
            print(f"❌ Error creating text transfer: {e}")
            import traceback
            print(f"Full traceback: {traceback.format_exc()}")
        
        # Test file transfer creation
        print("\n📁 Testing file transfer creation...")
        try:
            # Create a test file
            test_file_path = "test_file.txt"
            with open(test_file_path, 'w') as f:
                f.write("Test file content")
            
            transfer_id = await bot.create_file_transfer(user_id, test_file_path, "test.txt", 1024)
            print(f"✅ File transfer created successfully: {transfer_id}")
            
            # Clean up
            os.remove(test_file_path)
            
        except Exception as e:
            print(f"❌ Error creating file transfer: {e}")
            import traceback
            print(f"Full traceback: {traceback.format_exc()}")
        
        # Test data persistence
        print("\n💾 Testing data persistence...")
        try:
            bot._save_data()
            print("✅ Data saved successfully")
        except Exception as e:
            print(f"❌ Error saving data: {e}")
            import traceback
            print(f"Full traceback: {traceback.format_exc()}")
        
    except Exception as e:
        print(f"❌ Error in test setup: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(test_transfer_creation()) 