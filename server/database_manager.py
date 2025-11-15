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
                draws       INT DEFAULT 0,
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
                game_mode   INT NOT NULL DEFAULT 5,
                result_type VARCHAR(20) DEFAULT 'normal',
                start_time  DATETIME NOT NULL,
                end_time    DATETIME,
                move_log    TEXT,
                FOREIGN KEY (player_x_id) REFERENCES users(user_id),
                FOREIGN KEY (player_o_id) REFERENCES users(user_id),
                FOREIGN KEY (winner_id) REFERENCES users(user_id)
            );
        """)
        
        # Thêm các cột mới nếu bảng đã tồn tại (bỏ qua lỗi nếu cột đã tồn tại)
        try:
            cursor.execute("ALTER TABLE match_history ADD COLUMN game_mode INT NOT NULL DEFAULT 5")
        except mysql.connector.Error:
            pass  # Cột đã tồn tại
        
        try:
            cursor.execute("ALTER TABLE match_history ADD COLUMN result_type VARCHAR(20) DEFAULT 'normal'")
        except mysql.connector.Error:
            pass  # Cột đã tồn tại
        # Thêm cột draws cho bảng users nếu chưa có (dùng để tính tổng trận)
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN draws INT DEFAULT 0")
        except mysql.connector.Error:
            pass  # Cột đã tồn tại
        
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

def get_match_history(user_id, limit=50):
    """Lấy lịch sử trận đấu của người chơi."""
    conn = get_db_connection()
    if conn is None:
        return []
        
    cursor = conn.cursor(dictionary=True)
    try:
        sql = """
            SELECT 
                mh.match_id,
                mh.game_mode,
                mh.result_type,
                mh.end_time as match_date,
                CASE 
                    WHEN mh.winner_id = %s THEN 'Thắng'
                    WHEN mh.winner_id IS NULL THEN 'Hòa'
                    ELSE 'Thua'
                END as result,
                CASE 
                    WHEN mh.player_x_id = %s THEN u_o.username
                    ELSE u_x.username
                END as opponent
            FROM match_history mh
            LEFT JOIN users u_x ON mh.player_x_id = u_x.user_id
            LEFT JOIN users u_o ON mh.player_o_id = u_o.user_id
            WHERE mh.player_x_id = %s OR mh.player_o_id = %s
            ORDER BY mh.end_time DESC
            LIMIT %s
        """
        
        cursor.execute(sql, (user_id, user_id, user_id, user_id, limit))
        matches = cursor.fetchall()
        
        # Format thời gian cho dễ đọc
        formatted_matches = []
        for match in matches:
            formatted_match = {
                "match_id": match["match_id"],
                "opponent": match["opponent"],
                "result": match["result"],
                "game_mode": match["game_mode"],
                "time": match["match_date"].strftime("%d/%m/%Y %H:%M") if match["match_date"] else "N/A"
            }
            formatted_matches.append(formatted_match)
            
        return formatted_matches
        
    except mysql.connector.Error as err:
        print(f"Lỗi khi lấy lịch sử trận đấu: {err}")
        return []
    finally:
        cursor.close()
        conn.close()

def save_match_result(player_x_id, player_o_id, winner_id, game_mode, result_type="normal", move_log=""):
    """
    Lưu kết quả trận đấu vào database
    
    Args:
        player_x_id: ID người chơi X
        player_o_id: ID người chơi O  
        winner_id: ID người thắng (None nếu hòa)
        game_mode: Chế độ game (3, 4, 5, 6)
        result_type: Loại kết thúc ('normal', 'surrender', 'timeout', 'disconnect')
        move_log: Chuỗi lưu các nước đi
    """
    conn = get_db_connection()
    if conn is None:
        return False
        
    cursor = conn.cursor()
    try:
        # Lưu kết quả trận đấu
        cursor.execute("""
            INSERT INTO match_history (
                player_x_id, player_o_id, winner_id, game_mode, result_type,
                start_time, end_time, move_log
            ) VALUES (%s, %s, %s, %s, %s, NOW(), NOW(), %s)
        """, (player_x_id, player_o_id, winner_id, game_mode, result_type, move_log))
        
        # Cập nhật thống kê wins/losses cho cả 2 người chơi
        if winner_id is not None:
            # Có người thắng
            cursor.execute("UPDATE users SET wins = wins + 1 WHERE user_id = %s", (winner_id,))
            loser_id = player_o_id if winner_id == player_x_id else player_x_id
            cursor.execute("UPDATE users SET losses = losses + 1 WHERE user_id = %s", (loser_id,))
        # Nếu hòa thì không cập nhật wins/losses
            
        conn.commit()
        print(f"[DATABASE] Đã lưu kết quả trận đấu: {player_x_id} vs {player_o_id}, winner: {winner_id}")
        return True
        
    except mysql.connector.Error as err:
        print(f"Lỗi khi lưu kết quả trận đấu: {err}")
        return False
    finally:
        cursor.close()
        conn.close()

def get_leaderboard(limit=50):
    """
    Lấy bảng xếp hạng người chơi theo số trận thắng.
    
    Args:
        limit (int): Số lượng người chơi tối đa trả về (mặc định 50)
    
    Returns:
        list: Danh sách người chơi với thông tin username, wins, total_games
    """
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT username, IFNULL(wins,0) as wins, 
                   (IFNULL(wins,0) + IFNULL(losses,0) + IFNULL(draws,0)) as total_games
            FROM users 
            ORDER BY wins DESC, username ASC
            LIMIT %s
        """, (limit,))
        
        result = cursor.fetchall()
        
        leaderboard = []
        for row in result:
            leaderboard.append({
                "username": row[0],
                "wins": row[1],
                "total_games": row[2]
            })
        
        return leaderboard
        
    except mysql.connector.Error as e:
        print(f"Lỗi database khi lấy bảng xếp hạng: {e}")
        return []
    finally:
        if 'conn' in locals() and conn and conn.is_connected():
            cursor.close()
            conn.close()

def get_user_rank(user_id):
    """
    Lấy thông tin hạng của user hiện tại.
    
    Args:
        user_id (int): ID của user
    
    Returns:
        dict: Thông tin user gồm username, wins, total_games, rank
    """
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Lấy thông tin user hiện tại
        cursor.execute("""
            SELECT username, IFNULL(wins,0) as wins, IFNULL(losses,0) as losses, IFNULL(draws,0) as draws
            FROM users 
            WHERE user_id = %s
        """, (user_id,))
        
        user_data = cursor.fetchone()
        if not user_data:
            return None
            
        username, wins, losses, draws = user_data
        total_games = wins + losses + draws
        
        # Tính rank của user (đếm số người có wins > user hiện tại + 1)
        cursor.execute("""
            SELECT COUNT(*) + 1 as user_rank
            FROM users 
            WHERE wins > %s 
               OR (wins = %s AND username < %s)
        """, (wins, wins, username))
        
        rank_result = cursor.fetchone()
        rank = rank_result[0] if rank_result else 1
        
        return {
            "username": username,
            "wins": wins,
            "total_games": total_games,
            "rank": rank
        }
        
    except mysql.connector.Error as e:
        print(f"Lỗi database khi lấy rank user: {e}")
        return None
    finally:
        if 'conn' in locals() and conn and conn.is_connected():
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
