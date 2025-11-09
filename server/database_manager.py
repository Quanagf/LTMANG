# Server/database_manager.py

import mysql.connector
import bcrypt
from config import DB_CONFIG # Import cấu hình từ file config.py
from datetime import datetime # Cần import để lấy thời gian hiện tại cho log_match
# --- HÀM TIỆN ÍCH KẾT NỐI ---

def get_db_connection():
    """Tạo và trả về một kết nối đến DB."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"Lỗi kết nối Database: {err}")
        return None

# --- HÀM THIẾT LẬP BAN ĐẦU ---

def create_tables():
    """Chạy một lần để tạo các bảng users và match_history nếu chúng chưa tồn tại."""
    conn = get_db_connection()
    if conn is None:
        return

    cursor = conn.cursor()
    try:
        # Lệnh tạo bảng users
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id     INT AUTO_INCREMENT PRIMARY KEY,
                username    VARCHAR(50) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                wins        INT DEFAULT 0,
                losses      INT DEFAULT 0,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Lệnh tạo bảng match_history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS match_history (
                match_id    INT AUTO_INCREMENT PRIMARY KEY,
                player_x_id INT NOT NULL,
                player_o_id INT NOT NULL,
                winner_id   INT,
                start_time  DATETIME NOT NULL,
                end_time    DATETIME,
                move_log    TEXT,
                FOREIGN KEY (player_x_id) REFERENCES users(user_id),
                FOREIGN KEY (player_o_id) REFERENCES users(user_id),
                FOREIGN KEY (winner_id) REFERENCES users(user_id)
            );
        """)
        
        conn.commit()
        print("Đã tạo bảng thành công (hoặc bảng đã tồn tại).")
        
    except mysql.connector.Error as err:
        print(f"Lỗi khi tạo bảng: {err}")
    finally:
        cursor.close()
        conn.close()

# --- HÀM XỬ LÝ XÁC THỰC (Authentication) ---

def register_user(username, password):
    """Đăng ký một người dùng mới với mật khẩu đã được băm."""
    
    # Băm mật khẩu (Hashing)
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    conn = get_db_connection()
    if conn is None:
        return {"status": "ERROR", "message": "Lỗi kết nối server."}

    cursor = conn.cursor()
    try:
        # Thêm người dùng mới vào bảng
        sql = "INSERT INTO users (username, password_hash) VALUES (%s, %s)"
        cursor.execute(sql, (username, hashed_password))
        conn.commit()
        return {"status": "SUCCESS", "message": "Đăng ký thành công."}
        
    except mysql.connector.Error as err:
        # Bắt lỗi nếu trùng tên (UNIQUE)
        if err.errno == 1062: # 1062 là mã lỗi 'Duplicate entry'
            return {"status": "ERROR", "message": "Tên đăng nhập đã tồn tại."}
        else:
            return {"status": "ERROR", "message": f"Lỗi không xác định: {err}"}
    finally:
        cursor.close()
        conn.close()


def login_user(username, password_attempt):
    """Kiểm tra đăng nhập của người dùng."""
    conn = get_db_connection()
    if conn is None:
        return {"status": "ERROR", "message": "Lỗi kết nối server."}

    cursor = conn.cursor(dictionary=True) # dictionary=True để trả về kết quả dạng dict
    try:
        # Lấy thông tin user từ DB
        sql = "SELECT user_id, username, password_hash, wins, losses FROM users WHERE username = %s"
        cursor.execute(sql, (username,))
        user_data = cursor.fetchone()
        
        if user_data is None:
            # Không tìm thấy user
            return {"status": "ERROR", "message": "Tên đăng nhập không tồn tại."}

        # Lấy mật khẩu đã băm từ DB
        password_hash_from_db = user_data['password_hash'].encode('utf-8')
        
        # So sánh mật khẩu người dùng nhập với mật khẩu đã băm
        if bcrypt.checkpw(password_attempt.encode('utf-8'), password_hash_from_db):
            # Mật khẩu ĐÚNG!
            # Xóa mật khẩu hash khỏi dữ liệu trả về cho client
            del user_data['password_hash'] 
            return {"status": "SUCCESS", "user_data": user_data}
        else:
            # Mật khẩu SAI!
            return {"status": "ERROR", "message": "Sai mật khẩu."}
            
    except mysql.connector.Error as err:
        return {"status": "ERROR", "message": f"Lỗi DB: {err}"}
    finally:
        cursor.close()
        conn.close()

# --- CÁC HÀM KHÁC (Bạn sẽ thêm sau) ---

def update_game_stats(winner_id, loser_id):
    """Cập nhật wins/losses cho người chơi sau khi kết thúc trận."""
    conn = get_db_connection()
    if conn is None:
        print("[DB_ERROR] Không thể kết nối để cập nhật tỉ số.")
        return False

    cursor = conn.cursor()
    try:
        # +1 Thắng cho người thắng
        sql_win = "UPDATE users SET wins = wins + 1 WHERE user_id = %s"
        cursor.execute(sql_win, (winner_id,))
        
        # +1 Thua cho người thua
        sql_lose = "UPDATE users SET losses = losses + 1 WHERE user_id = %s"
        cursor.execute(sql_lose, (loser_id,))
        
        conn.commit()
        print(f"[DB_UPDATE] Đã cập nhật tỉ số: {winner_id} thắng, {loser_id} thua.")
        return True
        
    except mysql.connector.Error as err:
        print(f"[DB_ERROR] Lỗi khi cập nhật tỉ số: {err}")
        conn.rollback() # Hủy bỏ thay đổi nếu có lỗi
        return False
    finally:
        cursor.close()
        conn.close()

def log_match(player_x_id, player_o_id, winner_id, move_log):
    """
    Lưu lại lịch sử trận đấu vào bảng match_history.
    - player_x_id, player_o_id: ID của 2 người chơi.
    - winner_id: ID của người thắng (hoặc NULL nếu là hòa).
    - move_log: Chuỗi JSON hoặc TEXT ghi lại các nước đi.
    """
    conn = get_db_connection()
    if conn is None:
        print("[DB_ERROR] Không thể kết nối để lưu lịch sử trận đấu.")
        return False

    cursor = conn.cursor()
    try:
        current_time = datetime.now()
        
        # Lệnh INSERT INTO match_history
        sql = """
            INSERT INTO match_history 
            (player_x_id, player_o_id, winner_id, start_time, end_time, move_log) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        # start_time có thể được lấy từ logic game, ở đây dùng end_time làm giá trị cho cả 2 để đơn giản.
        # Hoặc bạn có thể truyền thêm start_time từ ngoài vào nếu cần.
        cursor.execute(sql, (player_x_id, player_o_id, winner_id, current_time, current_time, move_log))
        
        conn.commit()
        print(f"[DB_LOG] Đã lưu lịch sử trận đấu mới: Match ID {cursor.lastrowid}")
        return True
        
    except mysql.connector.Error as err:
        print(f"[DB_ERROR] Lỗi khi lưu lịch sử trận đấu: {err}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

# --- [MỚI] HÀM CẬP NHẬT TỈ SỐ ---
def update_game_stats(winner_id, loser_id):
    """
    Cập nhật wins/losses cho người chơi sau khi kết thúc trận.
    """
    conn = get_db_connection()
    if conn is None:
        print("[DB_ERROR] Không thể kết nối để cập nhật tỉ số.")
        return

    cursor = conn.cursor()
    try:
        # +1 Thắng cho người thắng
        sql_win = "UPDATE users SET wins = wins + 1 WHERE user_id = %s"
        cursor.execute(sql_win, (winner_id,))
        
        # +1 Thua cho người thua
        sql_lose = "UPDATE users SET losses = losses + 1 WHERE user_id = %s"
        cursor.execute(sql_lose, (loser_id,))
        
        conn.commit()
        print(f"[DB_UPDATE] Đã cập nhật tỉ số: {winner_id} thắng, {loser_id} thua.")
        
    except mysql.connector.Error as err:
        print(f"Lỗi khi cập nhật tỉ số: {err}")
        conn.rollback() # Hủy bỏ thay đổi nếu có lỗi
    finally:
        cursor.close()
        conn.close()

# --- Dùng để chạy thử nghiệm file này ---
if __name__ == "__main__":
    # Chạy lệnh này một lần duy nhất để tạo bảng
    print("Đang khởi tạo CSDL (tạo bảng nếu cần)...")
    create_tables()
    print("Hoàn tất.")
    
    # Bạn có thể test thử các hàm
    # print(register_user("testuser", "testpass123"))
    # print(login_user("testuser", "testpass123"))
