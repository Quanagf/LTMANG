import mysql.connector

try:
    # Kết nối đến database
    conn = mysql.connector.connect(
        host="localhost",
        user="root", 
        password="toann01032005",
        database="caro"
    )
    cursor = conn.cursor()
    
    # Kiểm tra xem cột game_mode đã tồn tại chưa
    cursor.execute("SHOW COLUMNS FROM match_history LIKE 'game_mode'")
    if not cursor.fetchone():
        print("Thêm cột game_mode...")
        cursor.execute("ALTER TABLE match_history ADD COLUMN game_mode INT DEFAULT 5")
        print("✓ Đã thêm cột game_mode")
    else:
        print("Cột game_mode đã tồn tại")
    
    # Kiểm tra xem cột result_type đã tồn tại chưa
    cursor.execute("SHOW COLUMNS FROM match_history LIKE 'result_type'")
    if not cursor.fetchone():
        print("Thêm cột result_type...")
        cursor.execute("ALTER TABLE match_history ADD COLUMN result_type VARCHAR(20) DEFAULT 'win'")
        print("✓ Đã thêm cột result_type")
    else:
        print("Cột result_type đã tồn tại")
    
    conn.commit()
    print("✓ Database đã được cập nhật thành công!")
    
except Exception as e:
    print(f"❌ Lỗi: {e}")
finally:
    if 'conn' in locals():
        conn.close()