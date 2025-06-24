#!/usr/bin/env python3
"""
Test script for SecShare bot admin functionality
"""

import asyncio
import os
from SecShare import SecShareBot

async def test_admin_functionality():
    """Test admin functionality"""
    print("🔐 Testing SecShare Bot Admin Functionality...")
    
    # Initialize bot with dummy admin ID
    bot = SecShareBot("test_token")
    
    # Test admin ID (999999999)
    admin_id = 999999999
    regular_user_id = 12345
    
    print(f"\n👑 Admin ID: {admin_id}")
    print(f"👤 Regular User ID: {regular_user_id}")
    
    # Test 1: Admin status
    print("\n🔍 Test 1: Admin Status")
    is_admin = bot.is_admin(admin_id)
    is_regular_admin = bot.is_admin(regular_user_id)
    print(f"✅ Admin {admin_id} is admin: {is_admin}")
    print(f"✅ Regular user {regular_user_id} is admin: {is_regular_admin}")
    
    # Test 2: Admin unlimited transfers
    print("\n📤 Test 2: Admin Unlimited Transfers")
    try:
        for i in range(10):  # Should work for admin
            transfer_id = await bot.create_text_transfer(admin_id, f"Admin message {i}")
            print(f"✅ Admin transfer {i+1} created: {transfer_id}")
    except Exception as e:
        print(f"❌ Admin transfer failed: {e}")
    
    # Test 3: Admin premium status
    print("\n⭐ Test 3: Admin Premium Status")
    admin_user = bot._get_user(admin_id)
    print(f"✅ Admin premium status: {admin_user.is_premium}")
    
    # Test 4: Admin file size limits
    print("\n💾 Test 4: Admin File Size Limits")
    large_file_size = 2 * 1024 * 1024 * 1024  # 2GB
    size_ok, error_msg = bot._check_file_size_limit(large_file_size, admin_id)
    print(f"✅ Admin can upload 2GB file: {size_ok}")
    
    # Test 5: Regular user limits (should be limited)
    print("\n🚫 Test 5: Regular User Limits")
    try:
        transfer_id = await bot.create_text_transfer(regular_user_id, "Regular user message")
        print(f"✅ Regular user transfer created: {transfer_id}")
    except Exception as e:
        print(f"✅ Regular user properly limited: {e}")
    
    # Test 6: Add superuser
    print("\n👥 Test 6: Add Superuser")
    superuser_id = 888888888
    bot.add_superuser(superuser_id)
    is_superuser = bot.is_admin(superuser_id)
    print(f"✅ Superuser {superuser_id} added and is admin: {is_superuser}")
    
    # Test 7: Superuser unlimited transfers
    print("\n📤 Test 7: Superuser Unlimited Transfers")
    try:
        transfer_id = await bot.create_text_transfer(superuser_id, "Superuser message")
        print(f"✅ Superuser transfer created: {transfer_id}")
    except Exception as e:
        print(f"❌ Superuser transfer failed: {e}")
    
    print("\n🎉 All admin tests completed!")

if __name__ == "__main__":
    asyncio.run(test_admin_functionality()) 