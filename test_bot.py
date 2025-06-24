#!/usr/bin/env python3
"""
Test script for SecShare bot functionality
Run this to test the core features without Telegram
"""

import asyncio
import os
import tempfile
from SecShare import SecShareBot

async def test_secshare_bot():
    """Test the SecShare bot functionality"""
    print("🔐 Testing SecShare Bot...")
    
    # Initialize bot
    bot = SecShareBot("test_token")
    
    # Test 1: Text transfer
    print("\n📝 Test 1: Text Transfer")
    try:
        transfer_id = await bot.create_text_transfer(12345, "Hello, this is a test message!")
        print(f"✅ Text transfer created: {transfer_id}")
        
        # Retrieve transfer
        transfer = bot.get_transfer(transfer_id)
        if transfer:
            decrypted = bot._decrypt_content(transfer.encrypted_content)
            print(f"✅ Text retrieved: {decrypted}")
        else:
            print("❌ Failed to retrieve transfer")
    except Exception as e:
        print(f"❌ Text transfer failed: {e}")
    
    # Test 2: Password protected transfer
    print("\n🔐 Test 2: Password Protected Transfer")
    try:
        transfer_id = await bot.create_text_transfer(12345, "Secret message!", "mypassword123")
        print(f"✅ Password protected transfer created: {transfer_id}")
        
        # Try without password (should fail)
        transfer = bot.get_transfer(transfer_id)
        if transfer:
            print("❌ Transfer accessible without password (should be protected)")
        else:
            print("✅ Transfer properly protected")
        
        # Try with correct password
        transfer = bot.get_transfer(transfer_id, "mypassword123")
        if transfer:
            decrypted = bot._decrypt_content(transfer.encrypted_content)
            print(f"✅ Password protected text retrieved: {decrypted}")
        else:
            print("❌ Failed to retrieve with correct password")
    except Exception as e:
        print(f"❌ Password protected transfer failed: {e}")
    
    # Test 3: File transfer
    print("\n📁 Test 3: File Transfer")
    try:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("This is a test file content")
            temp_file_path = f.name
        
        transfer_id = await bot.create_file_transfer(12345, temp_file_path, "test.txt", 1024)
        print(f"✅ File transfer created: {transfer_id}")
        
        # Retrieve transfer
        transfer = bot.get_transfer(transfer_id)
        if transfer and transfer.file_path and os.path.exists(transfer.file_path):
            print(f"✅ File transfer retrieved: {transfer.file_name}")
        else:
            print("❌ Failed to retrieve file transfer")
        
        # Clean up temp file
        os.unlink(temp_file_path)
    except Exception as e:
        print(f"❌ File transfer failed: {e}")
    
    # Test 4: User limits
    print("\n👤 Test 4: User Limits")
    try:
        # Create multiple transfers to test limits
        for i in range(6):  # Should fail on 6th transfer
            transfer_id = await bot.create_text_transfer(12345, f"Message {i}")
            print(f"✅ Transfer {i+1} created: {transfer_id}")
    except ValueError as e:
        print(f"✅ Limit reached as expected: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    
    # Test 5: User statistics
    print("\n📊 Test 5: User Statistics")
    stats = bot.get_user_stats(12345)
    print(f"✅ User stats: {stats}")
    
    # Test 6: Transfer expiry
    print("\n⏰ Test 6: Transfer Expiry")
    try:
        # Create a transfer
        transfer_id = await bot.create_text_transfer(12345, "Expiry test")
        print(f"✅ Transfer created for expiry test: {transfer_id}")
        
        # Manually expire it by modifying the expiry time
        if transfer_id in bot.transfers:
            bot.transfers[transfer_id].expires_at = "2020-01-01T00:00:00"
            print("✅ Transfer manually expired")
        
        # Try to retrieve expired transfer
        transfer = bot.get_transfer(transfer_id)
        if transfer:
            print("❌ Expired transfer still accessible")
        else:
            print("✅ Expired transfer properly cleaned up")
    except Exception as e:
        print(f"❌ Expiry test failed: {e}")
    
    print("\n🎉 All tests completed!")

if __name__ == "__main__":
    asyncio.run(test_secshare_bot()) 