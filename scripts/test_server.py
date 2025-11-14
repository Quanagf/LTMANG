#!/usr/bin/env python3
"""
Server Testing Script
Test server functionality without GUI client
"""

import asyncio
import websockets
import json
import time

SERVER_URL = "ws://localhost:8766"

class TestClient:
    def __init__(self, name):
        self.name = name
        self.ws = None
        self.user_data = None
        
    async def connect(self):
        """Connect to server"""
        try:
            self.ws = await websockets.connect(SERVER_URL)
            print(f"✅ {self.name} connected to server")
            return True
        except Exception as e:
            print(f"❌ {self.name} connection failed: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from server"""
        if self.ws:
            await self.ws.close()
            print(f"👋 {self.name} disconnected")
    
    async def send_message(self, action, payload=None):
        """Send message to server"""
        message = {
            "action": action,
            "payload": payload or {}
        }
        await self.ws.send(json.dumps(message))
        print(f"📤 {self.name} sent: {action}")
    
    async def receive_message(self):
        """Receive message from server"""
        try:
            message = await asyncio.wait_for(self.ws.recv(), timeout=10.0)  # Tăng từ 5s lên 10s
            data = json.loads(message)
            print(f"📥 {self.name} received: {data.get('status', 'UNKNOWN')}")
            return data
        except asyncio.TimeoutError:
            print(f"⏰ {self.name} receive timeout")
            return None
        except Exception as e:
            print(f"❌ {self.name} receive error: {e}")
            return None
    
    async def register_and_login(self):
        """Register and login user"""
        import random
        # Tạo username ngắn hơn để tránh vượt quá 20 ký tự
        timestamp_short = str(int(time.time()))[-6:]  # Chỉ lấy 6 số cuối
        random_suffix = random.randint(100, 999)  # 3 chữ số
        base_name = self.name.lower()[:8]  # Giới hạn base name 8 ký tự
        username = f"{base_name}{timestamp_short}{random_suffix}"  # Tối đa ~17 ký tự
        password = "test123"
        
        # Register
        await self.send_message("REGISTER", {
            "username": username,
            "password": password
        })
        
        response = await self.receive_message()
        if not response or response.get("status") != "SUCCESS":
            print(f"❌ {self.name} registration failed: {response}")
            print(f"   Username attempted: {username}")
            return False
        
        # Login  
        await self.send_message("LOGIN", {
            "username": username,
            "password": password
        })
        
        response = await self.receive_message()
        if not response or response.get("status") != "LOGIN_SUCCESS":
            print(f"❌ {self.name} login failed")
            return False
            
        self.user_data = response.get("user_data")
        print(f"✅ {self.name} logged in as {username}")
        return True

async def test_basic_connection():
    """Test basic server connectivity"""
    print("\n🔌 Testing basic connection...")
    
    client = TestClient("TestUser")
    if await client.connect():
        print("✅ Server is running and accepting connections")
        await client.disconnect()
        return True
    else:
        print("❌ Server is not running or not accessible")
        return False

async def test_authentication():
    """Test user registration and login"""
    print("\n🔐 Testing authentication...")
    
    client = TestClient("AuthTest")
    if not await client.connect():
        return False
    
    success = await client.register_and_login()
    await client.disconnect()
    
    if success:
        print("✅ Authentication system works")
    else:
        print("❌ Authentication system failed")
    
    return success

async def test_room_creation():
    """Test room creation and management"""
    print("\n🏠 Testing room management...")
    
    client = TestClient("RoomTest")
    if not await client.connect() or not await client.register_and_login():
        await client.disconnect()
        return False
    
    # Create room
    await client.send_message("CREATE_ROOM", {
        "password": "",
        "settings": {"time_limit": 120},
        "game_mode": 5
    })
    
    response = await client.receive_message()
    if not response or response.get("status") != "ROOM_CREATED":
        print("❌ Room creation failed")
        await client.disconnect()
        return False
    
    room_id = response.get("room_id")
    print(f"✅ Room created: {room_id}")
    
    # Find rooms
    await client.send_message("FIND_ROOM")
    response = await client.receive_message()
    if response and response.get("status") == "ROOM_LIST":
        rooms = response.get("rooms", [])
        print(f"✅ Found {len(rooms)} rooms")
    
    await client.disconnect()
    return True

async def test_matchmaking():
    """Test quick join system"""
    print("\n🎯 Testing matchmaking...")
    
    # Create two clients
    client1 = TestClient("Player1")
    client2 = TestClient("Player2")
    
    # Connect both
    if not await client1.connect() or not await client2.connect():
        await client1.disconnect()
        await client2.disconnect()
        return False
    
    # Login both
    if not await client1.register_and_login() or not await client2.register_and_login():
        await client1.disconnect()
        await client2.disconnect()
        return False
    
    # Player1 starts quick join
    await client1.send_message("QUICK_JOIN", {"game_mode": 5})
    response1 = await client1.receive_message()
    
    if response1 and response1.get("status") == "WAITING_FOR_MATCH":
        print("✅ Player1 entered matchmaking queue")
        
        # Player2 joins queue (should match)
        await client2.send_message("QUICK_JOIN", {"game_mode": 5})
        
        # Both should receive JOIN_SUCCESS
        response1 = await client1.receive_message()
        response2 = await client2.receive_message()
        
        if (response1 and response1.get("status") == "JOIN_SUCCESS" and
            response2 and response2.get("status") == "JOIN_SUCCESS"):
            print("✅ Matchmaking successful - players matched")
            success = True
        else:
            print("❌ Matchmaking failed - no match found")
            success = False
    else:
        print("❌ Quick join failed")
        success = False
    
    await client1.disconnect()
    await client2.disconnect()
    return success

async def test_gameplay():
    """Test basic gameplay flow"""
    print("\n🎮 Testing gameplay...")
    
    # Create two clients for a match
    client1 = TestClient("GamePlayer1")
    client2 = TestClient("GamePlayer2")
    
    # Setup both clients
    for client in [client1, client2]:
        if not await client.connect() or not await client.register_and_login():
            await client1.disconnect()
            await client2.disconnect()
            return False
    
    # Client1 creates room
    await client1.send_message("CREATE_ROOM", {
        "password": "",
        "game_mode": 3  # Use 3x3 for quick test
    })
    
    response = await client1.receive_message()
    if not response or response.get("status") != "ROOM_CREATED":
        print("❌ Game test: Room creation failed")
        await client1.disconnect()
        await client2.disconnect()
        return False
    
    room_id = response.get("room_id")
    
    # Client2 joins room
    await client2.send_message("JOIN_ROOM", {
        "room_id": room_id,
        "password": "",
        "game_mode": 3
    })
    
    response2 = await client2.receive_message()
    response1 = await client1.receive_message()  # Should get OPPONENT_JOINED
    
    if (response2 and response2.get("status") == "JOIN_SUCCESS" and
        response1 and response1.get("status") == "OPPONENT_JOINED"):
        print("✅ Players joined room successfully")
        
        # Both players ready up
        await client1.send_message("PLAYER_READY", {"toggle_ready": True})
        await client2.send_message("PLAYER_READY", {"toggle_ready": True})
        
        # Consume ready responses
        for _ in range(4):  # Each player gets 2 room updates
            await client1.receive_message()
            await client2.receive_message()
        
        # Should receive GAME_START
        start1 = await client1.receive_message()
        start2 = await client2.receive_message()
        
        if (start1 and start1.get("status") == "GAME_START" and
            start2 and start2.get("status") == "GAME_START"):
            print("✅ Game started successfully")
            success = True
        else:
            print("❌ Game failed to start")
            success = False
    else:
        print("❌ Failed to setup game room")
        success = False
    
    await client1.disconnect()
    await client2.disconnect()
    return success

async def test_server_load():
    """Test server with multiple concurrent connections"""
    print("\n🔥 Testing server load (10 concurrent clients)...")
    
    clients = []
    for i in range(10):
        client = TestClient(f"LoadTest{i}")
        clients.append(client)
    
    try:
        # Connect all clients
        connect_tasks = [client.connect() for client in clients]
        results = await asyncio.gather(*connect_tasks, return_exceptions=True)
        
        connected_count = sum(1 for r in results if r is True)
        print(f"✅ Connected {connected_count}/10 clients")
        
        # Test rapid message sending
        if connected_count >= 5:
            login_tasks = [client.register_and_login() for client in clients[:5]]
            login_results = await asyncio.gather(*login_tasks, return_exceptions=True)
            
            logged_in = sum(1 for r in login_results if r is True)
            print(f"✅ Logged in {logged_in}/5 clients")
            
            if logged_in >= 2:
                print("✅ Server handles concurrent load well")
                success = True
            else:
                print("⚠️ Server struggled with concurrent authentication")
                success = False
        else:
            print("❌ Server failed to handle multiple connections")
            success = False
    
    except Exception as e:
        print(f"❌ Load test failed: {e}")
        success = False
    
    finally:
        # Cleanup
        disconnect_tasks = [client.disconnect() for client in clients]
        await asyncio.gather(*disconnect_tasks, return_exceptions=True)
    
    return success

async def main():
    """Run all tests"""
    print("🧪 CARO GAME - Server Testing Suite")
    print("=" * 50)
    
    tests = [
        ("Basic Connection", test_basic_connection),
        ("Authentication", test_authentication), 
        ("Room Management", test_room_creation),
        ("Matchmaking", test_matchmaking),
        ("Gameplay Flow", test_gameplay),
        ("Server Load", test_server_load)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            if await test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"💥 {test_name} CRASHED: {e}")
    
    print(f"\n🏁 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! Server is working perfectly.")
    elif passed >= total * 0.8:
        print("⚠️ Most tests passed. Minor issues detected.")
    else:
        print("🚨 Multiple failures detected. Check server configuration.")
    
    return passed == total

if __name__ == "__main__":
    print("🔍 Make sure server is running: python server/server.py")
    print("⏳ Starting tests in 3 seconds...")
    time.sleep(3)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user")
    except Exception as e:
        print(f"\n💥 Test suite crashed: {e}")