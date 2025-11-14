#!/usr/bin/env python3
"""
Database Setup and Testing Script
Helps initialize and verify database configuration
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'server'))

import mysql.connector
from config import DB_CONFIG
import database_manager as db

def test_connection():
    """Test basic database connection"""
    print("🔌 Testing database connection...")
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()
        print(f"✅ Connected to MySQL {version[0]}")
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

def create_database():
    """Create database if it doesn't exist"""
    print("🏗️ Creating database...")
    try:
        # Connect without database
        config = DB_CONFIG.copy()
        db_name = config.pop('database')
        
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        print(f"✅ Database '{db_name}' created/exists")
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Failed to create database: {e}")
        return False

def create_tables():
    """Create tables using database manager"""
    print("📋 Creating tables...")
    try:
        db.create_tables()
        print("✅ Tables created successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to create tables: {e}")
        return False

def test_operations():
    """Test basic CRUD operations"""
    print("🧪 Testing database operations...")
    
    try:
        # Test user registration
        test_username = "test_user_12345"
        test_password = "test_password"
        
        print("  → Testing user registration...")
        result = db.register_user(test_username, test_password)
        if result["status"] != "SUCCESS":
            print(f"     ❌ Registration failed: {result['message']}")
            return False
        print("     ✅ User registration works")
        
        # Test login
        print("  → Testing user login...")
        result = db.login_user(test_username, test_password)
        if result["status"] != "SUCCESS":
            print(f"     ❌ Login failed: {result['message']}")
            return False
        user_id = result["user_data"]["user_id"]
        print("     ✅ User login works")
        
        # Test match history (empty)
        print("  → Testing match history...")
        history = db.get_match_history(user_id)
        print(f"     ✅ Match history: {len(history)} matches")
        
        # Test leaderboard
        print("  → Testing leaderboard...")
        leaderboard = db.get_leaderboard()
        print(f"     ✅ Leaderboard: {len(leaderboard)} players")
        
        # Cleanup test user
        print("  → Cleaning up test data...")
        conn = db.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE username = %s", (test_username,))
        conn.commit()
        cursor.close()
        conn.close()
        print("     ✅ Test data cleaned")
        
        return True
        
    except Exception as e:
        print(f"❌ Operation test failed: {e}")
        return False

def show_stats():
    """Show database statistics"""
    print("📊 Database statistics:")
    try:
        conn = db.get_db_connection()
        cursor = conn.cursor()
        
        # User count
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        print(f"  👥 Total users: {user_count}")
        
        # Match count
        cursor.execute("SELECT COUNT(*) FROM match_history")
        match_count = cursor.fetchone()[0]
        print(f"  🎮 Total matches: {match_count}")
        
        # Top player
        cursor.execute("SELECT username, wins FROM users ORDER BY wins DESC LIMIT 1")
        top_player = cursor.fetchone()
        if top_player:
            print(f"  🏆 Top player: {top_player[0]} ({top_player[1]} wins)")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Failed to get stats: {e}")

def main():
    print("🎮 CARO GAME - Database Setup & Test")
    print("=" * 40)
    
    # Step 1: Test connection
    if not test_connection():
        print("\n💡 Check your database configuration in server/config.py")
        return False
    
    # Step 2: Create database
    if not create_database():
        return False
    
    # Step 3: Create tables  
    if not create_tables():
        return False
        
    # Step 4: Test operations
    if not test_operations():
        return False
    
    # Step 5: Show stats
    show_stats()
    
    print("\n🎉 Database setup completed successfully!")
    print("🚀 You can now start the server with: python server/server.py")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)