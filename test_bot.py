#!/usr/bin/env python3
"""
Simple test script for SecShare bot components
"""

import os
import sys
import asyncio
import tempfile
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from SecShare import SecShareBot

async def test_secshare_bot():
    """Test the SecShare bot functionality"""
    print("🧪 Testing SecShare Bot Components...")
    
    # Initialize bot with dummy token
    bot = SecShareBot("dummy_token")
    
    # Use a different user ID to avoid hitting limits
    test_user_id = 99999
    
    # Test 1: User creation and management
    print("\n1. Testing user management...")
    user = bot._get_user(test_user_id, "testuser")
    print(f"✅ User created: {user.user_id}, Premium: {user.is_premium}")
    
    # Test 2: Text transfer creation
    print("\n2. Testing text transfer creation...")
    try:
        transfer_id = await bot.create_text_transfer(test_user_id, "Hello, this is a test message!")
        print(f"✅ Text transfer created: {transfer_id}")
        
        # Test 3: Text transfer retrieval
        print("\n3. Testing text transfer retrieval...")
        transfer = bot.get_transfer(transfer_id)
        if transfer:
            print(f"✅ Transfer retrieved: {transfer.transfer_id}")
            print(f"   Is file: {transfer.is_file}")
            print(f"   Has password: {transfer.password_hash is not None}")
        else:
            print("❌ Failed to retrieve transfer")
            
    except Exception as e:
        print(f"❌ Error creating text transfer: {e}")
    
    # Test 4: File transfer creation
    print("\n4. Testing file transfer creation...")
    try:
        # Create a temporary test file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("This is a test file content")
            temp_file_path = f.name
        
        transfer_id = await bot.create_file_transfer(test_user_id, temp_file_path, "test.txt", 1024)
        print(f"✅ File transfer created: {transfer_id}")
        
        # Test 5: File transfer retrieval
        print("\n5. Testing file transfer retrieval...")
        transfer = bot.get_transfer(transfer_id)
        if transfer:
            print(f"✅ File transfer retrieved: {transfer.transfer_id}")
            print(f"   File name: {transfer.file_name}")
            print(f"   File size: {transfer.file_size}")
            print(f"   File path exists: {os.path.exists(transfer.file_path)}")
        else:
            print("❌ Failed to retrieve file transfer")
            
        # Clean up temp file
        os.unlink(temp_file_path)
        
    except Exception as e:
        print(f"❌ Error creating file transfer: {e}")
    
    # Test 6: User stats
    print("\n6. Testing user stats...")
    stats = bot.get_user_stats(test_user_id)
    print(f"✅ User stats: {stats}")
    
    # Test 7: Password protection
    print("\n7. Testing password protection...")
    try:
        transfer_id = await bot.create_text_transfer(test_user_id, "Secret message", "mypassword")
        print(f"✅ Password-protected transfer created: {transfer_id}")
        
        # Try to get without password (should fail)
        transfer = bot.get_transfer(transfer_id)
        if transfer is None:
            print("✅ Password protection working (no access without password)")
        else:
            print("❌ Password protection not working")
        
        # Try to get with wrong password (should fail)
        transfer = bot.get_transfer(transfer_id, "wrongpassword")
        if transfer is None:
            print("✅ Wrong password correctly rejected")
        else:
            print("❌ Wrong password accepted")
        
        # Try to get with correct password (should succeed)
        transfer = bot.get_transfer(transfer_id, "mypassword")
        if transfer:
            print("✅ Correct password accepted")
        else:
            print("❌ Correct password rejected")
            
    except Exception as e:
        print(f"❌ Error testing password protection: {e}")
    
    # Test 8: Directory permissions
    print("\n8. Testing directory permissions...")
    temp_dir = bot.config['temp_dir']
    data_dir = bot.config['data_dir']
    
    print(f"   Temp directory: {temp_dir} (exists: {os.path.exists(temp_dir)})")
    print(f"   Data directory: {data_dir} (exists: {os.path.exists(data_dir)})")
    
    # Test write permissions
    try:
        test_file = os.path.join(temp_dir, "test_write.tmp")
        with open(test_file, 'w') as f:
            f.write("test")
        os.remove(test_file)
        print("✅ Temp directory is writable")
    except Exception as e:
        print(f"❌ Temp directory not writable: {e}")
    
    print("\n🎉 Testing completed!")

if __name__ == "__main__":
    asyncio.run(test_secshare_bot()) 