# Cấu hình kết nối đến MySQL

DB_CONFIG = {
    'host': 'localhost',      # Giữ nguyên nếu MySQL chạy ở máy bạn
    'user': 'root',           # User mặc định, có thể bạn đã đổi
    'password': 'lht2505', # <-- THAY ĐỔI DÒNG NÀY
    'database': 'caro',        # Tên database bạn đã tạo
    'auth_plugin': 'mysql_native_password'
}

# Cấu hình Server WebSocket
SERVER_HOST = 'localhost' # Hoặc '0.0.0.0' để máy khác kết nối
SERVER_PORT = 8766  # Đổi port để tránh conflict