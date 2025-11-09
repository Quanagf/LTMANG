# Server/server.py

import asyncio
import websockets
import json
from config import SERVER_HOST, SERVER_PORT

# Import các hàm xử lý từ các file khác
import database_manager as db_manager
import game_logic # Import file logic

# ----- Quản lý Trạng thái Server -----
CONNECTED_CLIENTS = {}
# ACTIVE_ROOMS đã được chuyển sang game_logic.py

# -----------------------------------

async def handle_message(websocket, message):
    """
    Hàm này nhận và phân tích mọi tin nhắn từ Client.
    """
    try:
        data = json.loads(message)
        action = data.get('action') 
        payload = data.get('payload', {}) 

        # [CẬP NHẬT] Kiểm tra các hành động yêu cầu đăng nhập
        if action not in ["LOGIN", "REGISTER"]:
             if not hasattr(websocket, 'user_id'): # Kiểm tra xem đã đăng nhập chưa
                await websocket.send(json.dumps({
                    "status": "ERROR", 
                    "message": "Bạn phải đăng nhập để thực hiện hành động này."
                }))
                return
        
        # 2. [CẬP NHẬT] Điều phối tất cả các hành động
        if action == "LOGIN":
            await handle_login(websocket, payload)
        
        elif action == "REGISTER":
            await handle_register(websocket, payload)
            
        elif action == "CREATE_ROOM":
            await game_logic.handle_create_room(websocket, payload)
        
        # --- [MỚI] Thêm các chức năng Lobby ---
        elif action == "JOIN_ROOM":
            await game_logic.handle_join_room(websocket, payload)

        elif action == "CANCEL_QUICK_JOIN":
            await game_logic.handle_cancel_quick_join(websocket)           
            
        elif action == "FIND_ROOM":
            await game_logic.handle_find_room(websocket)
            
        elif action == "QUICK_JOIN":
            await game_logic.handle_quick_join(websocket)

        # --- [MỚI] Thêm các chức năng Phòng chờ & Game (Sẽ làm sau) ---
        elif action == "UPDATE_SETTINGS":
            await game_logic.handle_update_settings(websocket, payload)
        elif action == "READY": # Thay cho "Bắt đầu game"
             await game_logic.handle_ready(websocket, payload)
        elif action == "LEAVE_ROOM":
             await game_logic.handle_leave_room(websocket)
        
        elif action == "MOVE" or action == "MAKE_MOVE":
             await game_logic.handle_move(websocket, payload)
        elif action == "CHAT":
             await game_logic.handle_chat(websocket, payload)
        elif action == "REMATCH":
             await game_logic.handle_rematch(websocket, payload)

        
        # --- Hết ---
            
        else:
            await websocket.send(json.dumps({
                "status": "ERROR", 
                "message": f"Hành động '{action}' không được hỗ trợ."
            }))

    except json.JSONDecodeError:
        print("[LỖI] Nhận được tin nhắn không phải JSON.")
        await websocket.send(json.dumps({ "status": "ERROR", "message": "Tin nhắn không đúng định dạng JSON."}))
    except Exception as e:
        print(f"[LỖI NGOẠI LỆ] {e}")
        await websocket.send(json.dumps({ "status": "ERROR", "message": "Có lỗi xảy ra phía server."}))

# ----- Các Hàm Xử lý Logic -----

async def handle_login(websocket, payload):
    """Xử lý logic đăng nhập."""
    try:
        username = payload['username']
        password = payload['password']
        result = db_manager.login_user(username, password)
        
        if result["status"] == "SUCCESS":
            user_id = result['user_data']['user_id']
            username = result['user_data']['username']
            
            # GÁN THÔNG TIN USER VÀO WEBSOCKET
            websocket.user_id = user_id
            websocket.username = username
            
            # Lưu lại kết nối
            CONNECTED_CLIENTS[user_id] = websocket
            print(f"[ĐĂNG NHẬP] User {username} (ID: {user_id}) đã kết nối.")
            
            result["status"] = "LOGIN_SUCCESS"
            await websocket.send(json.dumps(result))
        else:
            await websocket.send(json.dumps(result))

    except KeyError:
        print("[LỖI ĐĂNG NHẬP] Tin nhắn LOGIN thiếu username hoặc password.")
        await websocket.send(json.dumps({"status": "ERROR", "message": "Yêu cầu đăng nhập thiếu thông tin."}))

async def handle_register(websocket, payload):
    """Xử lý logic đăng ký."""
    try:
        username = payload['username']
        password = payload['password']
        result = db_manager.register_user(username, password)
        await websocket.send(json.dumps(result))
    except KeyError:
        print("[LỖI ĐĂNG KÝ] Tin nhắn REGISTER thiếu username hoặc password.")
        await websocket.send(json.dumps({"status": "ERROR", "message": "Yêu cầu đăng ký thiếu thông tin."}))

# ----- Hàm Chính của Server -----

async def main_handler(websocket):
    """
    Hàm này được gọi cho MỖI client kết nối vào.
    """
    print(f"[KẾT NỐI MỚI] Một client đã kết nối từ {websocket.remote_address}")
    
    try:
        async for message in websocket:
            print(f"[NHẬN] {message}") 
            await handle_message(websocket, message)
            
    except websockets.exceptions.ConnectionClosedError:
        print(f"[NGẮT KẾT NỐI] Client {websocket.remote_address} đã ngắt kết nối (lỗi).")
    except websockets.exceptions.ConnectionClosedOK:
        print(f"[NGẮT KẾT NỐI] Client {websocket.remote_address} đã ngắt kết nối (bình thường).")
    finally:
        # [CẬP NHẬT] Xử lý dọn dẹp khi client ngắt kết nối
        
        # 1. Gọi hàm dọn dẹp phòng game (nếu có)
        await game_logic.handle_disconnect(websocket)
        
        # 2. Xóa khỏi danh sách CONNECTED_CLIENTS (nếu đã đăng nhập)
        if hasattr(websocket, 'user_id') and websocket.user_id in CONNECTED_CLIENTS:
            del CONNECTED_CLIENTS[websocket.user_id]
            print(f"[DỌN DẸP] Đã xóa User ID {websocket.user_id} khỏi CONNECTED_CLIENTS.")

# ... (Hàm start_server và if __name__ == "__main__" giữ nguyên) ...
async def start_server():
    """Khởi động WebSocket server."""
    async with websockets.serve(main_handler, SERVER_HOST, SERVER_PORT):
        print(f"✅ Server WebSocket đang lắng nghe tại ws://{SERVER_HOST}:{SERVER_PORT}")
        await asyncio.Future()

if __name__ == "__main__":
    print("Đang kiểm tra/khởi tạo CSDL...")
    db_manager.create_tables()
    
    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        print("\nĐã tắt server.")