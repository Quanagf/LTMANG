#!/usr/bin/env python3
"""
Development Helper Scripts
Quick commands for common development tasks
"""

import os
import sys
import subprocess
import platform

def run_command(cmd, description):
    """Run a shell command with description"""
    print(f"🔧 {description}...")
    try:
        if platform.system() == "Windows":
            result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        else:
            result = subprocess.run(cmd.split(), check=True, capture_output=True, text=True)
        print(f"✅ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        if e.stdout:
            print(f"STDOUT: {e.stdout}")
        if e.stderr:
            print(f"STDERR: {e.stderr}")
        return False

def setup_environment():
    """Setup development environment"""
    print("🚀 Setting up development environment...")
    
    # Check Python version
    python_version = platform.python_version()
    print(f"🐍 Python version: {python_version}")
    
    if tuple(map(int, python_version.split('.')[:2])) < (3, 8):
        print("❌ Python 3.8+ required")
        return False
    
    # Install requirements
    if not run_command("pip install -r requirements.txt", "Installing Python dependencies"):
        return False
    
    # Setup database
    print("🗄️ Setting up database...")
    if not run_command("python scripts/setup_database.py", "Database setup"):
        print("⚠️ Database setup failed. Check MySQL configuration.")
    
    print("✅ Development environment ready!")
    return True

def run_server():
    """Start the game server"""
    print("🖥️ Starting game server...")
    os.chdir("server")
    try:
        subprocess.run([sys.executable, "server.py"])
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")

def run_client():
    """Start the game client"""
    print("🎮 Starting game client...")
    os.chdir("client")
    try:
        subprocess.run([sys.executable, "main.py"])
    except KeyboardInterrupt:
        print("\n🛑 Client stopped by user")

def test_server():
    """Run server tests"""
    print("🧪 Running server tests...")
    if not run_command("python scripts/test_server.py", "Server testing"):
        print("❌ Some tests failed. Check server status.")
    else:
        print("✅ All tests passed!")

def clean_project():
    """Clean up generated files"""
    print("🧹 Cleaning project...")
    
    # Remove Python cache
    if run_command("find . -name '__pycache__' -type d -exec rm -rf {} +", "Removing Python cache"):
        pass
    elif platform.system() == "Windows":
        run_command("for /d /r . %d in (__pycache__) do @if exist \"%d\" rd /s /q \"%d\"", "Removing Python cache")
    
    # Remove log files
    run_command("rm -f *.log", "Removing log files")
    
    print("✅ Project cleaned!")

def backup_database():
    """Create database backup"""
    print("💾 Creating database backup...")
    
    timestamp = subprocess.check_output("date +%Y%m%d_%H%M%S", shell=True, text=True).strip()
    backup_file = f"backup_caro_{timestamp}.sql"
    
    # Read config to get database info
    sys.path.append("server")
    try:
        from config import DB_CONFIG
        cmd = (f"mysqldump -u{DB_CONFIG['user']} -p{DB_CONFIG['password']} "
               f"{DB_CONFIG['database']} > {backup_file}")
        
        if run_command(cmd, "Database backup"):
            print(f"✅ Backup saved as: {backup_file}")
        else:
            print("❌ Backup failed")
    except ImportError:
        print("❌ Could not load database config")

def show_logs():
    """Show recent server logs"""
    print("📋 Recent server activity:")
    
    log_files = ["server.log", "errors.log", "caro-server.log"]
    
    for log_file in log_files:
        if os.path.exists(log_file):
            print(f"\n--- {log_file} (last 20 lines) ---")
            run_command(f"tail -20 {log_file}", f"Reading {log_file}")
        elif os.path.exists(f"logs/{log_file}"):
            print(f"\n--- logs/{log_file} (last 20 lines) ---")
            run_command(f"tail -20 logs/{log_file}", f"Reading logs/{log_file}")

def monitor_server():
    """Monitor server resources"""
    print("📊 Server monitoring...")
    
    # Check if server process is running
    if platform.system() == "Windows":
        cmd = "tasklist | findstr python"
    else:
        cmd = "ps aux | grep python"
    
    run_command(cmd, "Checking Python processes")
    
    # Check port usage
    if platform.system() == "Windows":
        cmd = "netstat -an | findstr :8766"
    else:
        cmd = "netstat -tulpn | grep :8766"
    
    run_command(cmd, "Checking port 8766")
    
    # Check database connection
    try:
        sys.path.append("server")
        from config import DB_CONFIG
        import mysql.connector
        
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM match_history")
        match_count = cursor.fetchone()[0]
        
        print(f"📊 Database stats: {user_count} users, {match_count} matches")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ Database check failed: {e}")

def main():
    """Main menu"""
    commands = {
        "1": ("Setup Environment", setup_environment),
        "2": ("Start Server", run_server),
        "3": ("Start Client", run_client),
        "4": ("Test Server", test_server),
        "5": ("Clean Project", clean_project),
        "6": ("Backup Database", backup_database),
        "7": ("Show Logs", show_logs),
        "8": ("Monitor Server", monitor_server),
        "q": ("Quit", lambda: sys.exit(0))
    }
    
    while True:
        print("\n" + "="*50)
        print("🛠️  CARO GAME - Development Helper")
        print("="*50)
        
        for key, (description, _) in commands.items():
            print(f"  {key}. {description}")
        
        choice = input("\nEnter your choice: ").strip().lower()
        
        if choice in commands:
            try:
                commands[choice][1]()
            except KeyboardInterrupt:
                print("\n🛑 Operation interrupted")
            except Exception as e:
                print(f"\n💥 Error: {e}")
            
            if choice != "q":
                input("\nPress Enter to continue...")
        else:
            print("❌ Invalid choice")

if __name__ == "__main__":
    main()