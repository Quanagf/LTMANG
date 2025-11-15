import json
import random
import string
import database_manager as db_manager 
import asyncio 

ACTIVE_ROOMS = {}
# Dictionary để lưu hàng đợi cho từng game mode
QUICK_JOIN_WAITING_PLAYERS = {}  # {game_mode: websocket} 

# --- HELPER FUNCTION ---
def _is_websocket_connected(ws):
    """
    Kiểm tra xem websocket có còn kết nối không.
    Tương thích với cả websockets cũ và mới.
    """
    if not ws:
        return False
    try:
        # Thử gửi ping để kiểm tra kết nối
        return True  # Nếu websocket tồn tại, coi như connected
    except:
        return False

# --- HÀM DỌN DẸP DỮ LIỆU ---
# --- HÀM DỌN DẸP DỮ LIỆU ---
def _get_clean_room_data(room):
    """
    Tạo một bản sao (copy) của "room" an toàn để gửi qua JSON.
    Nó loại bỏ các đối tượng websocket không thể gửi đi.
    """
    if not room: return None
    
    # [SỬA LỖI] Dùng deep copy (copy sâu) cho player
    # để tránh lỗi tham chiếu khi cập nhật P1, P2
    clean_room = {
        "room_id": room.get("room_id"),
        "password": room.get("password"),
        "board": room.get("board"),
        "turn": room.get("turn"),
        "settings": room.get("settings"),
        "score": room.get("score"),
        "game_mode": room.get("game_mode", 5),  # Thêm game mode
        "timer_task": None # Không bao giờ gửi task
    }
    
    # Xử lý Player 1
    if room.get("player1"):
        clean_room["player1"] = room["player1"].copy()
        clean_room["player1"].pop("websocket", None) # Xóa key 'websocket'
        
    # Xử lý Player 2
    if room.get("player2"):
        clean_room["player2"] = room["player2"].copy()
        clean_room["player2"].pop("websocket", None) # Xóa key 'websocket'
        
    return clean_room


# --- HELPER: SAFE SEND ---
async def _safe_send(ws, payload):
    """Gửi payload (dictionary) tới websocket một cách an toàn.
    Trả về True nếu gửi thành công, False nếu lỗi hoặc ws là None.
    """
    if not ws:
        return False
    try:
        await ws.send(json.dumps(payload))
        return True
    except Exception as e:
        print(f"[SAFE_SEND ERROR] {e}")
        return False

# --- Hàm Tạo mã ---
def generate_room_code(length=5):
    """Tạo một mã phòng ngẫu nhiên (ví dụ: 'A5K2P') và đảm bảo nó là duy nhất."""
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
        if code not in ACTIVE_ROOMS:
            return code

# --- Chức năng 1: TẠO PHÒNG ---
async def handle_create_room(websocket, payload):
    """
    Xử lý khi một client yêu cầu tạo phòng.
    """
    try:
        user_id = websocket.user_id
        username = websocket.username
        password = payload.get("password", "") 
        settings = payload.get("settings", { "time_limit": 120 }) 
        game_mode = payload.get("game_mode", 5)  # Mặc định 5 quân
        room_code = generate_room_code()
        
        print(f"[TẠO PHÒNG] User {username} (ID: {user_id}) đã tạo phòng: {room_code}, Game mode: {game_mode}")
        
        ACTIVE_ROOMS[room_code] = {
            "room_id": room_code,
            "password": password,
            "player1": {
                "websocket": websocket, "user_id": user_id,
                "username": username, "is_ready": False 
            },
            "player2": None, "board": None, "turn": None,
            "settings": settings,
            "timer_task": None,
            "consecutive_timeouts": 0,
            "game_mode": game_mode  # Thêm game mode vào room
        }
        
        websocket.room_code = room_code 
        
        await websocket.send(json.dumps({
            "status": "ROOM_CREATED",
            "message": "Tạo phòng thành công!",
            "room_id": room_code,
            # [SỬA LỖI] Gửi data SẠCH
            "room_data": _get_clean_room_data(ACTIVE_ROOMS[room_code]) 
        }))
        
    except AttributeError:
        await websocket.send(json.dumps({"status": "ERROR", "message": "Bạn phải đăng nhập."}))
    except Exception as e:
        print(f"[LỖI TẠO PHÒNG] {e}")
        await websocket.send(json.dumps({"status": "ERROR", "message": "Lỗi khi tạo phòng."}))

# --- Chức năng 2: THAM GIA PHÒNG (Nhập mã) ---
async def handle_join_room(websocket, payload):
    """
    Xử lý khi một client yêu cầu tham gia phòng bằng mã.
    """
    try:
        # Kiểm tra thông tin người chơi
        server_user_id = websocket.user_id
        server_username = websocket.username
        room_code = payload.get("room_id")  # Don't use default empty string
        password = payload.get("password", "")
        client_game_mode = payload.get("game_mode", 5)  # Mặc định 5 quân
        
        print(f"[DEBUG] Nhận yêu cầu vào phòng. Payload: {payload}")
        print(f"[DEBUG] Client game mode: {client_game_mode}")
        
        if not room_code:  # Kiểm tra riêng trường hợp room_code trống
            await websocket.send(json.dumps({"status": "ERROR", "message": "Vui lòng nhập mã phòng."}))
            return
        
        # Kiểm tra tính hợp lệ của phòng
        print(f"[DEBUG] Đang kiểm tra phòng '{room_code}'. Các phòng hiện tại: {list(ACTIVE_ROOMS.keys())}")
        if not room_code:
            await websocket.send(json.dumps({
                "status": "ERROR", 
                "message": "Vui lòng nhập mã phòng"
            }))
            return
            
        if room_code not in ACTIVE_ROOMS:
            await websocket.send(json.dumps({
                "status": "ERROR", 
                "message": "Phòng này không tồn tại hoặc đã bị đóng"
            }))
            return
            
        room = ACTIVE_ROOMS[room_code]
        
        # Kiểm tra trạng thái phòng
        if room["player2"] is not None:
            await websocket.send(json.dumps({
                "status": "ERROR", 
                "message": "Phòng này đã đầy"
            }))
            return
            
        # Kiểm tra mật khẩu
        if room["password"] and room["password"] != password:
            await websocket.send(json.dumps({
                "status": "ERROR", 
                "message": "Sai mật khẩu phòng"
            }))
            return
            
        # Kiểm tra game mode có khớp không (bỏ qua nếu client_game_mode = "ANY")
        room_game_mode = room.get("game_mode", 5)
        if client_game_mode != "ANY" and client_game_mode != room_game_mode:
            await websocket.send(json.dumps({
                "status": "ERROR", 
                "message": f"Chế độ game không khớp. Phòng: {room_game_mode} quân, Bạn chọn: {client_game_mode} quân"
            }))
            return
            
        print(f"[VÀO PHÒNG] User {server_username} (ID: {server_user_id}) đã vào phòng: {room_code}, Game mode: {room_game_mode}")
        room["player2"] = {
            "websocket": websocket, "user_id": server_user_id,
            "username": server_username, "is_ready": False 
        }
        websocket.room_code = room_code
        
        print(f"[DEBUG] Player2 đã được gán: {room['player2']}")
        print(f"[DEBUG] Chuẩn bị lấy clean_room_data...")
        
        # Lấy dữ liệu phòng sạch để gửi
        clean_room_data = _get_clean_room_data(room)
        
        print(f"[DEBUG] Đã lấy clean_room_data, chuẩn bị gửi JOIN_SUCCESS...")
        
        # Gửi thông tin cho người chơi mới (player2)
        await websocket.send(json.dumps({
            "status": "JOIN_SUCCESS",
            "message": "Tham gia phòng thành công!",
            "room_data": clean_room_data
        }))
        
        print(f"[DEBUG] Đã gửi JOIN_SUCCESS, chuẩn bị gửi OPPONENT_JOINED...")
        
        # Gửi thông báo cho chủ phòng (player1)
        player1_ws = room["player1"]["websocket"]
        try:
            # Gửi cả 'opponent' (tách riêng) và 'room_data' để client có thể cập nhật an toàn
            payload = {
                "status": "OPPONENT_JOINED",
                "message": f"{server_username} đã vào phòng.",
                "opponent": clean_room_data.get("player2"),
                "room_data": clean_room_data
            }
            # Dùng hàm an toàn để gửi
            await _safe_send(player1_ws, payload)
            print(f"[DEBUG] Đã gửi OPPONENT_JOINED cho player1 (payload includes opponent + room_data)")
        except Exception as send_error:
            print(f"[DEBUG] Không thể gửi OPPONENT_JOINED cho player1: {send_error}")
        
        print(f"[DEBUG] Chuẩn bị gửi OPPONENT_JOINED cho player1...")
        
        # [THAY ĐỔI] Không tự động bắt đầu game nữa, chờ cả hai ready
        print(f"[JOIN ROOM] Player2 đã join, chờ cả hai ready để bắt đầu game...")
        
    except AttributeError as ae:
        print(f"[LỖI VÀO PHÒNG - AttributeError] {ae}")
        await websocket.send(json.dumps({"status": "ERROR", "message": "Bạn phải đăng nhập."}))
    except Exception as e:
        print(f"[LỖI VÀO PHÒNG] {e}")
        import traceback
        traceback.print_exc()
        await websocket.send(json.dumps({"status": "ERROR", "message": "Lỗi khi vào phòng."}))

# --- Chức năng 3: TÌM PHÒNG ---
async def handle_find_room(websocket, payload):
    """
    Gửi cho client danh sách các phòng đang chờ, lọc theo game_mode nếu có.
    """
    try:
        # Lấy game_mode từ payload để lọc phòng
        client_game_mode = payload.get("game_mode") if payload else None
        
        waiting_rooms = []
        for code, room in ACTIVE_ROOMS.items():
            if room["player2"] is None and room["board"] is None:
                room_game_mode = room.get("game_mode", 5)
                
                # Chỉ thêm phòng nếu game_mode khớp hoặc không có yêu cầu lọc
                if client_game_mode is None or room_game_mode == client_game_mode:
                    # Clean room data cho danh sách
                    waiting_rooms.append({
                        "room_id": code,
                        "host_name": room["player1"]["username"],
                        "has_password": bool(room["password"]),
                        "settings": room["settings"],
                        "game_mode": room_game_mode,  # Thêm game_mode để client hiển thị
                        "created_time": room.get("created_time", "")
                    })
        
        print(f"[FIND_ROOM] Client game_mode: {client_game_mode}, Found {len(waiting_rooms)} rooms")
        await websocket.send(json.dumps({
            "status": "ROOM_LIST",
            "rooms": waiting_rooms
        }))
    except Exception as e:
        print(f"[LỖI TÌM PHÒNG] {e}")
        await websocket.send(json.dumps({"status": "ERROR", "message": "Lỗi khi tải danh sách phòng."}))

# --- Chức năng 4: VÀO NHANH ---
async def handle_quick_join(websocket, payload):
    """
    Tự động tìm phòng chờ hoặc tạo phòng mới.
    """
    global QUICK_JOIN_WAITING_PLAYERS
    try:
        user_id = websocket.user_id
        username = websocket.username
        client_game_mode = payload.get("game_mode", 5) if payload else 5
        
        print(f"[QUICK JOIN] {username} muốn chơi chế độ {client_game_mode}")

        # [SỬA LỖI] Cấm tự chơi - kiểm tra trong hàng đợi
        if client_game_mode != "ANY":
            waiting_player = QUICK_JOIN_WAITING_PLAYERS.get(client_game_mode)
            if waiting_player and waiting_player.user_id == user_id:
                await websocket.send(json.dumps({"status": "ERROR", "message": "Bạn đã đang trong hàng đợi."})) 
                return
        else:
            # Với mode "ANY", kiểm tra tất cả các hàng đợi
            for mode_players in QUICK_JOIN_WAITING_PLAYERS.values():
                if mode_players and mode_players.user_id == user_id:
                    await websocket.send(json.dumps({"status": "ERROR", "message": "Bạn đã đang trong hàng đợi."})) 
                    return

        # [LOGIC MỚI] 1. Quét các phòng "Tạo phòng" (ACTIVE_ROOMS) đang chờ
        found_room = None
        for room_code, room in ACTIVE_ROOMS.items():
            if (room["player2"] is None and 
                not room["password"] and 
                room["board"] is None and 
                room["player1"]["user_id"] != user_id):
                
                # Nếu client_game_mode = "ANY", ghép với bất kỳ phòng nào
                # Nếu không, chỉ ghép với phòng cùng game mode
                if (client_game_mode == "ANY" or 
                    room.get("game_mode", 5) == client_game_mode):
                    found_room = room
                    break

        if found_room:
            # 2. NẾU TÌM THẤY PHÒNG -> Tham gia phòng đó
            room_code = found_room["room_id"]
            print(f"[VÀO NHANH] User {username} đã tìm thấy và tham gia phòng {room_code}")
            
            found_room["player2"] = {
                "websocket": websocket, "user_id": user_id,
                "username": username, "is_ready": False
            }
            websocket.room_code = room_code

            player1_ws = found_room["player1"]["websocket"]
            clean_room_data = _get_clean_room_data(found_room)

            await websocket.send(json.dumps({
                "status": "JOIN_SUCCESS",
                "message": "Đã tìm thấy phòng!",
                "room_data": clean_room_data
            }))
            
            await player1_ws.send(json.dumps({
                "status": "OPPONENT_JOINED",
                "message": f"{username} đã vào phòng.",
                "opponent": clean_room_data.get("player2")
            }))
            
            # [BỎ AUTO START] Không tự động bắt đầu game, cần cả 2 người sẵn sàng
            return

        # 3. NẾU KHÔNG TÌM THẤY PHÒNG -> Dùng logic hàng đợi (queue) theo game_mode
        print(f"[VÀO NHANH] Không tìm thấy phòng trống cho {client_game_mode}. User {username} vào hàng đợi...")

        # Với mode "ANY", tìm bất kỳ người chờ nào
        matched_player = None
        matched_mode = None
        
        if client_game_mode == "ANY":
            # Tìm bất kỳ người chờ nào trong các mode
            for mode, waiting_player in QUICK_JOIN_WAITING_PLAYERS.items():
                if waiting_player and mode != "ANY":
                    matched_player = waiting_player
                    matched_mode = mode
                    break
        else:
            # Tìm người chờ cùng mode hoặc mode "ANY" 
            if client_game_mode in QUICK_JOIN_WAITING_PLAYERS and QUICK_JOIN_WAITING_PLAYERS[client_game_mode]:
                matched_player = QUICK_JOIN_WAITING_PLAYERS[client_game_mode]
                matched_mode = client_game_mode
            elif "ANY" in QUICK_JOIN_WAITING_PLAYERS and QUICK_JOIN_WAITING_PLAYERS["ANY"]:
                matched_player = QUICK_JOIN_WAITING_PLAYERS["ANY"]
                matched_mode = client_game_mode  # Dùng mode của người join sau

        if matched_player:
            del QUICK_JOIN_WAITING_PLAYERS[matched_mode if matched_mode != "ANY" else "ANY"]  # Xóa khỏi hàng đợi
            
            room_code = generate_room_code()
            final_game_mode = matched_mode if matched_mode != "ANY" else client_game_mode
            print(f"[VÀO NHANH] Ghép 2 người chờ {matched_player.username} và {websocket.username} vào phòng {room_code} (chế độ {final_game_mode})")
            
            room = {
                "room_id": room_code, "password": "",
                "player1": {
                    "websocket": matched_player, "user_id": matched_player.user_id,
                    "username": matched_player.username, "is_ready": False
                },
                "player2": {
                    "websocket": websocket, "user_id": websocket.user_id,
                    "username": websocket.username, "is_ready": False
                },
                "board": None, "turn": None, "settings": {"time_limit": 120},
                "timer_task": None,
                "consecutive_timeouts": 0,
                "game_mode": final_game_mode  # Thêm game mode
            }
            ACTIVE_ROOMS[room_code] = room
            
            matched_player.room_code = room_code
            websocket.room_code = room_code
            
            # [SỬA LỖI] Gửi data sạch
            clean_room_data = _get_clean_room_data(room) 
            # Gửi JOIN_SUCCESS cho cả 2 người kèm room_data
            await _safe_send(matched_player, {"status": "JOIN_SUCCESS", "message": "Đã tìm thấy đối thủ!", "room_data": clean_room_data})
            await _safe_send(websocket, {"status": "JOIN_SUCCESS", "message": "Đã tìm thấy đối thủ!", "room_data": clean_room_data})
            
            # [BỎ AUTO START] Không tự động bắt đầu game, cần cả 2 người sẵn sàng
        
        else:
            # Thêm vào hàng đợi theo game_mode
            QUICK_JOIN_WAITING_PLAYERS[client_game_mode] = websocket
            
            wait_message = "Đang tìm đối thủ (mọi chế độ)..." if client_game_mode == "ANY" else f"Đang tìm đối thủ cho chế độ {client_game_mode} quân..."
            await websocket.send(json.dumps({
                "status": "WAITING_FOR_MATCH",
                "message": wait_message
            }))
            print(f"[QUICK JOIN] {username} đã vào hàng đợi chế độ {client_game_mode}")
    
    except Exception as e:
        print(f"[LỖI VÀO NHANH] {e}")
        await websocket.send(json.dumps({"status": "ERROR", "message": "Lỗi khi vào nhanh."}))

# --- [MỚI] Chức năng: HỦY VÀO NHANH ---
async def handle_cancel_quick_join(websocket):
    """
    Xử lý khi client chủ động hủy tìm trận 'Vào nhanh'.
    """
    global QUICK_JOIN_WAITING_PLAYERS
    try:
        # Tìm và xóa khỏi hàng đợi của game_mode tương ứng
        removed = False
        for game_mode, waiting_player in list(QUICK_JOIN_WAITING_PLAYERS.items()):
            if waiting_player == websocket:
                del QUICK_JOIN_WAITING_PLAYERS[game_mode]
                removed = True
                if hasattr(websocket, 'username'):
                    print(f"[DỌN DẸP] User {websocket.username} đã hủy chờ 'Vào nhanh' chế độ {game_mode} quân.")
                break
        
        if removed:
            await websocket.send(json.dumps({
                "status": "CANCEL_QUICK_JOIN_SUCCESS"
            }))
            
    except Exception as e:
        print(f"[LỖI HỦY VÀO NHANH] {e}")

# --- Chức năng 5: RỜI PHÒNG (Tự nguyện) ---
async def handle_leave_room(websocket):
    """
    Xử lý khi client chủ động nhấn nút "Rời phòng".
    """
    await handle_disconnect(websocket, reason="LEAVE")

# --- Chức năng 6: NGẮT KẾT NỐI (Bị động) ---
async def handle_disconnect(websocket, reason="DISCONNECT"):
    """
    Xử lý dọn dẹp khi một client ngắt kết nối.
    """
    try:
        global QUICK_JOIN_WAITING_PLAYERS
        
        # Dọn dẹp hàng đợi quick join theo game mode
        for game_mode, waiting_player in list(QUICK_JOIN_WAITING_PLAYERS.items()):
            if waiting_player == websocket:
                del QUICK_JOIN_WAITING_PLAYERS[game_mode]
                if hasattr(websocket, 'username'):
                    print(f"[DỌN DẸP] User {websocket.username} đã hủy chờ 'Vào nhanh' chế độ {game_mode} quân.")
                break

        if not hasattr(websocket, 'room_code'):
            return 

        room_code = websocket.room_code
        if room_code not in ACTIVE_ROOMS:
            return 
            
        room = ACTIVE_ROOMS[room_code]
        
        # [SỬA LỖI] Đảm bảo user đã đăng nhập
        if not hasattr(websocket, 'user_id'):
             return
             
        user_id = websocket.user_id
        username = websocket.username
        
        print(f"[RỜI PHÒNG] User {username} đã rời/mất kết nối khỏi phòng {room_code}")
        
        if hasattr(websocket, 'room_code'):
            del websocket.room_code 
        
        if room.get("timer_task"):
            room["timer_task"].cancel()
            room["timer_task"] = None
        
        opponent_ws = None
        opponent_id = None
        
        if room["player1"] and room["player1"]["user_id"] == user_id:
            if room["player2"]: 
                opponent_ws = room["player2"]["websocket"]
                opponent_id = room["player2"]["user_id"]
                room["player1"] = room["player2"]
                room["player2"] = None
                room["player1"]["is_ready"] = False 
            else:
                del ACTIVE_ROOMS[room_code]
                print(f"[DỌN DẸP] Phòng {room_code} bị xóa (chủ phòng thoát khi 1 mình).")
                return 
        
        elif room["player2"] and room["player2"]["user_id"] == user_id:
            opponent_ws = room["player1"]["websocket"]
            opponent_id = room["player1"]["user_id"]
            room["player2"] = None 
            room["player1"]["is_ready"] = False 
        
        if opponent_ws:
            print(f"-> Thông báo cho người chơi còn lại (ID: {opponent_id})")
            try:
                if room.get("board") is not None:
                    await _handle_game_over(room, winner_id=opponent_id, loser_id=user_id, reason="OPPONENT_LEFT")
                else:
                    # [SỬA LỖI] Gửi data sạch
                    await _safe_send(opponent_ws, {
                        "status": "OPPONENT_LEFT",
                        "message": f"{username} đã rời phòng. Bạn quay về phòng chờ.",
                        "room_data": _get_clean_room_data(room)
                    })
            except Exception as e:
                print(f"[ERROR_NOTIFY_OPPONENT] {e}")
        
    except AttributeError:
        print(f"[THOÁT] Một client chưa đăng nhập đã thoát.")
    except Exception as e:
        print(f"[LỖI RỜI PHÒNG] {e}")

# --- Chức năng 7: SẴN SÀNG ---
async def handle_ready(websocket, payload=None):
    """
    Xử lý khi client nhấn nút Sẵn sàng / Hủy sẵn sàng.
    """
    try:
        if not hasattr(websocket, 'room_code'): 
            print(f"[LỖI READY] Websocket {websocket.username} không có room_code")
            return 
        room_code = websocket.room_code
        if room_code not in ACTIVE_ROOMS: 
            print(f"[LỖI READY] Phòng {room_code} không tồn tại")
            return 
            
        room = ACTIVE_ROOMS[room_code]
        user_id = websocket.user_id
        
        # Kiểm tra nếu có tham số toggle_ready để chuyển đổi trạng thái
        if payload and payload.get("toggle_ready"):
            player_key = None
            if room["player1"] and room["player1"]["user_id"] == user_id:
                player_key = "player1"
            elif room["player2"] and room["player2"]["user_id"] == user_id:
                player_key = "player2"
            
            if player_key:
                current_ready = room[player_key]["is_ready"]
                is_ready = not current_ready  # Chuyển đổi trạng thái
            else:
                return
        else:
            # Mặc định là sẵn sàng (để tương thích ngược)
            is_ready = True
            if payload:
                is_ready = payload.get("is_ready", True)

        if room.get("board") is not None:
            return

        player_key = None
        opponent_ws = None
        
        if room["player1"] and room["player1"]["user_id"] == user_id:
            player_key = "player1"
            if room["player2"]: opponent_ws = room["player2"]["websocket"]
        elif room["player2"] and room["player2"]["user_id"] == user_id:
            player_key = "player2"
            opponent_ws = room["player1"]["websocket"]
        
        if not player_key: return 

        room[player_key]["is_ready"] = is_ready
        ready_text = "sẵn sàng" if is_ready else "hủy sẵn sàng"
        print(f"[SẴN SÀNG] User {websocket.username} (phòng {room_code}) đã {ready_text}")

        # Tạo dữ liệu phòng an toàn để gửi (loại bỏ websocket)
        safe_player1 = None
        safe_player2 = None
        
        if room["player1"]:
            safe_player1 = {
                "user_id": room["player1"]["user_id"],
                "username": room["player1"]["username"],
                "is_ready": room["player1"]["is_ready"]
            }
            
        if room["player2"]:
            safe_player2 = {
                "user_id": room["player2"]["user_id"],
                "username": room["player2"]["username"],
                "is_ready": room["player2"]["is_ready"]
            }

        # Gửi cập nhật trạng thái phòng cho cả hai người chơi
        room_update = {
            "status": "ROOM_UPDATE",
            "payload": {
                "room_id": room_code,
                "player1": safe_player1,
                "player2": safe_player2
            }
        }
        
        await _safe_send(websocket, room_update)
        if opponent_ws:
            await _safe_send(opponent_ws, room_update)
        
        # Chỉ bắt đầu game khi cả hai đều sẵn sàng
        if (room["player1"] and room["player1"]["is_ready"] and
            room["player2"] and room["player2"]["is_ready"]):
            
            print(f"[BẮT ĐẦU GAME] Cả hai người chơi phòng {room_code} đã sẵn sàng!")
            await _start_game(room) 

    except Exception as e:
        print(f"[LỖI READY] {e}")
        await websocket.send(json.dumps({"status": "ERROR", "message": "Lỗi khi xử lý sẵn sàng."}))

# --- Hàm nội bộ: LẤY KÍCH THƯỚC BOARD ---
def _get_board_size(game_mode):
    """
    Trả về kích thước board theo game mode
    3 quân = 3x3, 4 quân = 6x6, 5 quân = 9x9, 6 quân = 12x12
    """
    board_sizes = {
        3: 3,
        4: 6, 
        5: 9,
        6: 12
    }
    return board_sizes.get(game_mode, 9)  # Mặc định 9x9

def _is_board_full(board):
    """Kiểm tra xem bàn cờ đã đầy chưa (không còn ô trống)"""
    for row in board:
        for cell in row:
            if cell == 0:  # Còn ô trống
                return False
    return True  # Bàn cờ đã đầy

# --- Hàm nội bộ: BẮT ĐẦU GAME ---
async def _start_game(room):
    """
    Hàm này khởi tạo ván đấu, random X/O, và gửi tin nhắn.
    """
    print(f"[_START_GAME] ===== BẮT ĐẦU TẠO GAME =====")
    
    game_mode = room.get("game_mode", 5)
    board_size = _get_board_size(game_mode)
    room["board"] = [[0 for _ in range(board_size)] for _ in range(board_size)]
    
    print(f"[_START_GAME] Tạo board {board_size}x{board_size} cho game mode {game_mode} quân")
    
    player1 = room["player1"]
    player2 = room["player2"]
    
    print(f"[_START_GAME] Player1: {player1['username']} (ID: {player1['user_id']})")
    print(f"[_START_GAME] Player2: {player2['username']} (ID: {player2['user_id']})")
    
    if "score" not in room:
        room["score"] = {
            player1["user_id"]: 0, 
            player2["user_id"]: 0
        }
        
    room["player1"]["is_ready"] = False
    room["player2"]["is_ready"] = False

    first_player_info = random.choice([player1, player2])
    
    if first_player_info["user_id"] == player1["user_id"]:
        playerX = player1
        playerO = player2
    else:
        playerX = player2
        playerO = player1

    room["turn"] = playerX["user_id"] 
    
    # [SỬA LỖI] Gửi data sạch (board, score)
    clean_board = room["board"]
    clean_score = room["score"]
    
    print(f"[_START_GAME] Gửi GAME_START cho playerX ({playerX['username']})")
    await playerX["websocket"].send(json.dumps({
        "status": "GAME_START", "role": "X", "turn": "YOU", 
        "board": clean_board, "score": clean_score, "game_mode": room.get("game_mode", 5),
        "settings": room.get("settings", {})
    }))
    
    print(f"[_START_GAME] Gửi GAME_START cho playerO ({playerO['username']})")
    await playerO["websocket"].send(json.dumps({
        "status": "GAME_START", "role": "O", "turn": "OPPONENT", 
        "board": clean_board, "score": clean_score, "game_mode": room.get("game_mode", 5),
        "settings": room.get("settings", {})
    }))
    
    print(f"[_START_GAME] ===== ĐÃ GỬI GAME_START CHO CẢ 2 PLAYERS =====")
    
    # Sử dụng thời gian giới hạn theo settings của phòng (mặc định 30s nếu không có)
    time_limit = room.get("settings", {}).get("time_limit", 30)
    
    if room.get("timer_task"):
        room["timer_task"].cancel()
        
    timer_task = asyncio.create_task(
        _start_turn_timer(room, playerX["user_id"], time_limit)
    )
    room["timer_task"] = timer_task 

# --- Hàm nội bộ: BỘ ĐẾM GIỜ ---
async def _start_turn_timer(room, player_id_on_turn, time_limit):
    """
    Hàm chạy nền, ngủ trong 'time_limit' giây.
    """
    try:
        # Lưu lại turn hiện tại khi bắt đầu timer
        original_turn = room.get("turn")
        await asyncio.sleep(time_limit)
        
        # [SỬA LỖI] Kiểm tra lại xem phòng còn tồn tại và game còn diễn ra
        if room_code := room.get("room_id"):
            if room_code not in ACTIVE_ROOMS:
                return # Phòng đã bị hủy
            if room.get("board") is None:
                return # Game đã kết thúc

        # Kiểm tra xem turn có còn là của người này không (có thể đã chuyển lượt rồi)
        if room.get("turn") != player_id_on_turn or room.get("turn") != original_turn:
            print(f"[TIMER] Turn đã thay đổi, bỏ qua timeout cho user {player_id_on_turn}")
            return

        if room.get("turn") == player_id_on_turn:
            print(f"[TIMEOUT] User ID {player_id_on_turn} (phòng {room.get('room_id')}) đã hết giờ! Người này thua trận.")
            
            # Tìm đối thủ (người thắng)
            current_player_id = player_id_on_turn  # Người thua
            opponent_id = None
            
            if not room.get("player1") or not room.get("player2"): return
            
            if room["player1"]["user_id"] == current_player_id:
                opponent_id = room["player2"]["user_id"]  # Đối thủ thắng
            else:
                opponent_id = room["player1"]["user_id"]  # Đối thủ thắng
            
            print(f"[TIMEOUT] Player thua (timeout): {current_player_id}, Player thắng: {opponent_id}")
            
            # Kết thúc game, người timeout thua
            await _handle_game_over(room, winner_id=opponent_id, loser_id=current_player_id, reason="TIMEOUT")

    except asyncio.CancelledError:
        print(f"[TIMER] Đã hủy timer cho User ID {player_id_on_turn} (đã đi).")
        raise 
    except Exception as e:
        print(f"[LỖI TIMER] {e}")

# --- Chức năng 8: XỬ LÝ NƯỚC ĐI ---
async def handle_move(websocket, payload):
    """
    Xử lý khi một người chơi gửi nước đi.
    """
    try:
        if not hasattr(websocket, 'room_code'): return
        room_code = websocket.room_code
        if room_code not in ACTIVE_ROOMS: return
            
        room = ACTIVE_ROOMS[room_code]
        user_id = websocket.user_id

        if room.get("board") is None:
            await websocket.send(json.dumps({"status": "ERROR", "message": "Game chưa bắt đầu."}))
            return

        if room.get("turn") != user_id:
            await websocket.send(json.dumps({"status": "ERROR", "message": "Chưa đến lượt của bạn."}))
            return
            
        row = payload.get("row"); col = payload.get("col")

        if (row is None or col is None or 
            not (0 <= row < len(room["board"])) or 
            not (0 <= col < len(room["board"][0]))):
            await websocket.send(json.dumps({"status": "ERROR", "message": "Tọa độ không hợp lệ."}))
            return

        if room["board"][row][col] != 0:
            await websocket.send(json.dumps({"status": "ERROR", "message": "Ô này đã được đánh."}))
            return
            
        # --- Nước đi hợp lệ ---
        if room.get("timer_task"):
            room["timer_task"].cancel()
            room["timer_task"] = None
            
        print(f"[NƯỚC ĐI] User {websocket.username} (phòng {room_code}) đánh: ({row}, {col})")
        
        room["board"][row][col] = user_id
        
        # Reset consecutive timeout khi có người thực sự đánh
        room["consecutive_timeouts"] = 0
        
        opponent_ws = None
        opponent_id = None
        
        if not room.get("player1") or not room.get("player2"): return # Lỗi
        
        if room["player1"]["user_id"] == user_id:
            opponent_ws = room["player2"]["websocket"]
            opponent_id = room["player2"]["user_id"]
        else:
            opponent_ws = room["player1"]["websocket"]
            opponent_id = room["player1"]["user_id"]

        if opponent_ws:
            await _safe_send(opponent_ws, {
                "status": "OPPONENT_MOVE",
                "move": {"row": row, "col": col},
                "player_id": user_id  # Gửi ID của người đánh để client cập nhật board
            })

        game_mode = room.get("game_mode", 5)  # Lấy game mode từ room
        if _check_win(room["board"], row, col, user_id, game_mode):
            print(f"[GAME KẾT THÚC] User {websocket.username} (ID: {user_id}) thắng phòng {room_code} với {game_mode} quân.")
            await _handle_game_over(room, winner_id=user_id, loser_id=opponent_id, reason="WIN")
            return 

        # Kiểm tra hòa (bàn cờ đầy nhưng không có ai thắng)
        if _is_board_full(room["board"]):
            print(f"[GAME HÒA] Phòng {room_code} hòa do bàn cờ đã đầy.")
            await _handle_game_over(room, winner_id=None, loser_id=None, reason="DRAW_BOARD_FULL")
            return 

        room["turn"] = opponent_id
        
        if opponent_id:
            # Sử dụng time_limit theo settings phòng (mặc định 30 giây)
            next_time_limit = room.get("settings", {}).get("time_limit", 30)
            timer_task = asyncio.create_task(
                _start_turn_timer(room, opponent_id, next_time_limit)
            )
            room["timer_task"] = timer_task

    except Exception as e:
        print(f"[LỖI MOVE] {e}")
        await websocket.send(json.dumps({"status": "ERROR", "message": "Lỗi khi xử lý nước đi."}))

# --- Hàm nội bộ: KIỂM TRA THẮNG ---
def _check_win(board, r, c, player_id, win_count=5):
    """
    Kiểm tra xem nước đi tại (r, c) của player_id có tạo ra chiến thắng không.
    win_count: số quân thẳng hàng cần để thắng (3, 5, 6)
    """
    board_size = len(board)
    directions = [(0, 1), (1, 0), (1, 1), (1, -1)]

    for dr, dc in directions:
        count = 0
        for i in range(-(win_count-1), win_count):
            nr, nc = r + i * dr, c + i * dc
            
            if 0 <= nr < board_size and 0 <= nc < board_size:
                if board[nr][nc] == player_id:
                    count += 1
                    if count >= win_count:
                        return True 
                else:
                    count = 0 
            else:
                count = 0 
                
    return False 

# --- Hàm nội bộ: XỬ LÝ KẾT THÚC GAME ---
async def _handle_game_over(room, winner_id, loser_id, reason="WIN"):
    """
    Xử lý khi có người thắng cuộc.
    """
    if room.get("timer_task"):
        room["timer_task"].cancel()
        room["timer_task"] = None

    if "score" not in room:
        if room.get("player1") and room.get("player2"):
             room["score"] = {room["player1"]["user_id"]: 0, room["player2"]["user_id"]: 0}
        else:
             room["score"] = {} # Lỗi, không có người chơi
            
    if reason in ["WIN", "TIMEOUT"]:
        if winner_id in room["score"]:
            room["score"][winner_id] += 1
        
        if winner_id and loser_id: # Chỉ update DB nếu có đủ 2 người
            db_manager.update_game_stats(winner_id, loser_id)
        
        # Lưu lịch sử trận đấu
        _save_match_to_history(room, winner_id, reason)
    elif reason == "DRAW":
        # Trường hợp hòa - không cập nhật điểm
        # Nhưng vẫn lưu lịch sử trận đấu
        _save_match_to_history(room, None, reason)
        pass
    
    winner_ws = None
    loser_ws = None
    
    if room.get("player1"):
        if room["player1"]["user_id"] == winner_id:
            winner_ws = room["player1"]["websocket"]
        elif room["player1"]["user_id"] == loser_id:
            loser_ws = room["player1"]["websocket"]

    if room.get("player2"):
        if room["player2"]["user_id"] == winner_id:
            winner_ws = room["player2"]["websocket"]
        elif room["player2"]["user_id"] == loser_id:
            loser_ws = room["player2"]["websocket"]

    if reason in ["DRAW_TIMEOUT", "DRAW_BOARD_FULL"]:
        # Trường hợp hòa - gửi thông báo cho cả hai với lý do cụ thể
        draw_message = {
            "status": "GAME_OVER",
            "result": "DRAW",
            "draw_reason": "TIMEOUT" if reason == "DRAW_TIMEOUT" else "BOARD_FULL",
            "score": room["score"]
        }
        
        # Lưu lịch sử trận đấu cho trường hợp hòa
        _save_match_to_history(room, None, reason)
        
        if room.get("player1") and room.get("player1", {}).get("websocket"):
            await _safe_send(room["player1"]["websocket"], draw_message)
        
        if room.get("player2") and room.get("player2", {}).get("websocket"):
            await _safe_send(room["player2"]["websocket"], draw_message)
    
    elif winner_ws:
        result_type = "WIN"
        if reason == "TIMEOUT": result_type = "TIMEOUT_WIN"
        elif reason == "OPPONENT_LEFT": result_type = "OPPONENT_LEFT_WIN"
        
        await _safe_send(winner_ws, {
            "status": "GAME_OVER",
            "result": result_type,
            "score": room["score"]
        })
        
        # Gửi thông báo đến người thua (trừ khi đã gửi ở trên cho timeout)
        if loser_ws: 
            loser_result = "TIMEOUT_LOSE" if reason == "TIMEOUT" else "LOSE"
            await _safe_send(loser_ws, {
                "status": "GAME_OVER",
                "result": loser_result,
                "score": room["score"]
            })
        
    # Reset phòng
    room["board"] = None 
    room["turn"] = None
    room["consecutive_timeouts"] = 0  # Reset timeout counter
    if room["player1"]:
        room["player1"]["is_ready"] = False
    if room["player2"]:
        room["player2"]["is_ready"] = False

# --- Chức năng 9: CHAT TRONG PHÒNG ---
async def handle_chat(websocket, payload):
    """
    Xử lý khi một người chơi gửi tin nhắn chat.
    """
    try:
        if not hasattr(websocket, 'room_code'): return 
        room_code = websocket.room_code
        if room_code not in ACTIVE_ROOMS: return 
            
        room = ACTIVE_ROOMS[room_code]
        user_id = websocket.user_id
        username = websocket.username
        
        message = payload.get("message")
        if not message: return 

        opponent_ws = None
        if room["player1"] and room["player1"]["user_id"] == user_id:
            if room["player2"]:
                opponent_ws = room["player2"]["websocket"]
        elif room["player2"] and room["player2"]["user_id"] == user_id:
            opponent_ws = room["player1"]["websocket"]

        if opponent_ws:
            print(f"[CHAT] {username} (phòng {room_code}) gửi: {message}")
            await _safe_send(opponent_ws, {
                "status": "OPPONENT_CHAT",
                "sender": username,
                "message": message
            })
        else:
            await websocket.send(json.dumps({
                "status": "ERROR",
                "message": "Đang không có ai trong phòng để chat."
            }))

    except Exception as e:
        print(f"[LỖI CHAT] {e}")
        await websocket.send(json.dumps({"status": "ERROR", "message": "Lỗi khi gửi tin nhắn."}))

# --- Chức năng 10: CHƠI LẠI (REMATCH) ---
async def handle_rematch(websocket, payload):
    """
    Xử lý khi client yêu cầu chơi lại (sau khi game kết thúc).
    """
    try:
        if not hasattr(websocket, 'room_code'): return 
        room_code = websocket.room_code
        if room_code not in ACTIVE_ROOMS: return 
            
        room = ACTIVE_ROOMS[room_code]
        user_id = websocket.user_id
        
        if room.get("board") is not None:
            await websocket.send(json.dumps({"status": "ERROR", "message": "Không thể chơi lại khi ván đấu đang diễn ra."}))
            return

        player_key = None
        opponent_ws = None
        
        if room["player1"] and room["player1"]["user_id"] == user_id:
            player_key = "player1"
            if room["player2"]: opponent_ws = room["player2"]["websocket"]
        elif room["player2"] and room["player2"]["user_id"] == user_id:
            player_key = "player2"
            opponent_ws = room["player1"]["websocket"]
        
        if not player_key: return

        room[player_key]["is_ready"] = True
        print(f"[CHƠI LẠI] User {websocket.username} (phòng {room_code}) muốn chơi lại.")

        if opponent_ws:
            await _safe_send(opponent_ws, {
                "status": "OPPONENT_REMATCH",
                "is_ready": True
            })
        
        if (room["player1"] and room["player1"]["is_ready"] and
            room["player2"] and room["player2"]["is_ready"]):
            
            print(f"[BẮT ĐẦU VÁN MỚI] Cả hai người chơi phòng {room_code} đồng ý chơi lại!")
            await _start_game(room) 

    except Exception as e:
        print(f"[LỖI REMATCH] {e}")
        await websocket.send(json.dumps({"status": "ERROR", "message": "Lỗi khi xử lý chơi lại."}))

# --- Chức năng 11: CẬP NHẬT CÀI ĐẶT PHÒNG ---
async def handle_update_settings(websocket, payload):
    """
    Xử lý khi chủ phòng (P1) thay đổi cài đặt phòng.
    """
    try:
        if not hasattr(websocket, 'room_code'): return
        room_code = websocket.room_code
        if room_code not in ACTIVE_ROOMS: return
            
        room = ACTIVE_ROOMS[room_code]
        user_id = websocket.user_id
        
        if not room["player1"] or room["player1"]["user_id"] != user_id:
            await websocket.send(json.dumps({
                "status": "ERROR",
                "message": "Chỉ chủ phòng mới có thể thay đổi cài đặt."
            }))
            return
            
        if room.get("board") is not None:
            await websocket.send(json.dumps({
                "status": "ERROR",
                "message": "Không thể thay đổi cài đặt khi ván đấu đang diễn ra."
            }))
            return

        if "password" in payload:
            room["password"] = payload["password"]
            print(f"[CÀI ĐẶT] Phòng {room_code} đổi mật khẩu thành: '{payload['password']}'")
            
        if "time_limit" in payload:
            try:
                room["settings"]["time_limit"] = int(payload["time_limit"])
                print(f"[CÀI ĐẶT] Phòng {room_code} đổi thời gian thành: {payload['time_limit']}s")
            except ValueError:
                pass 
        
        clean_room_data = _get_clean_room_data(room)
        
        await websocket.send(json.dumps({
            "status": "SETTINGS_UPDATED",
            "room_data": clean_room_data
        }))
        
        if room["player2"]:
            opponent_ws = room["player2"]["websocket"]
            if opponent_ws:
                await _safe_send(opponent_ws, {
                    "status": "SETTINGS_CHANGED_BY_HOST",
                    "room_data": clean_room_data
                })
                
    except Exception as e:
        print(f"[LỖI SETTINGS] {e}")
        await websocket.send(json.dumps({"status": "ERROR", "message": "Lỗi khi cập nhật cài đặt."}))


# --- Chức năng: ĐẦUHÀNG ---
async def handle_surrender(websocket, payload=None):
    """
    Xử lý khi người chơi đầu hàng.
    Người đầu hàng thua, đối thủ thắng.
    """
    try:
        if not hasattr(websocket, 'room_code'):
            await websocket.send(json.dumps({"status": "ERROR", "message": "Bạn không ở trong phòng nào."}))
            return
            
        room_code = websocket.room_code
        if room_code not in ACTIVE_ROOMS:
            await websocket.send(json.dumps({"status": "ERROR", "message": "Phòng không tồn tại."}))
            return
            
        room = ACTIVE_ROOMS[room_code]
        
        # Kiểm tra game đang diễn ra
        if not room.get("board"):
            await websocket.send(json.dumps({"status": "ERROR", "message": "Game chưa bắt đầu."}))
            return
            
        user_id = websocket.user_id
        username = websocket.username
        
        # Tìm người chơi và đối thủ
        surrendering_player = None
        opponent_ws = None
        opponent_username = None
        
        if room["player1"] and room["player1"]["user_id"] == user_id:
            surrendering_player = "player1"
            if room["player2"]:
                opponent_ws = room["player2"]["websocket"]
                opponent_username = room["player2"]["username"]
        elif room["player2"] and room["player2"]["user_id"] == user_id:
            surrendering_player = "player2"
            opponent_ws = room["player1"]["websocket"]
            opponent_username = room["player1"]["username"]
            
        if not surrendering_player:
            await websocket.send(json.dumps({"status": "ERROR", "message": "Không tìm thấy thông tin người chơi."}))
            return
            
        print(f"[ĐẦUHÀNG] User {username} (phòng {room_code}) đã đầu hàng")
        
        # Kết thúc game - người đầu hàng thua
        await _safe_send(websocket, {
            "status": "GAME_OVER",
            "result": "LOSE",
            "message": f"Bạn đã đầu hàng. {opponent_username} thắng!",
            "reason": "SURRENDER"
        })
        
        if opponent_ws:
            await _safe_send(opponent_ws, {
                "status": "GAME_OVER", 
                "result": "WIN",
                "message": f"{username} đã đầu hàng. Bạn thắng!",
                "reason": "OPPONENT_SURRENDER"
            })
        
        # Dọn dẹp phòng và reset trạng thái
        await _cleanup_room_after_game(room, room_code)
        
    except Exception as e:
        print(f"[LỖI ĐẦUHÀNG] {e}")
        await websocket.send(json.dumps({"status": "ERROR", "message": "Lỗi khi xử lý đầu hàng."}))


# --- Hàm hỗ trợ: Dọn dẹp phòng sau game ---
async def _cleanup_room_after_game(room, room_code):
    """
    Dọn dẹp phòng sau khi game kết thúc (thắng/thua/đầu hàng).
    Reset board, timer, trạng thái sẵn sàng.
    """
    try:
        # Dừng timer nếu có
        if room.get("timer_task"):
            room["timer_task"].cancel()
            room["timer_task"] = None
            
        # Reset board và game state
        room["board"] = None
        room["current_turn"] = None
        room["game_start_time"] = None
        
        # Reset trạng thái sẵn sàng
        if room["player1"]:
            room["player1"]["is_ready"] = False
        if room["player2"]:
            room["player2"]["is_ready"] = False
            
        print(f"[CLEANUP] Đã dọn dẹp phòng {room_code} sau game")
        
    except Exception as e:
        print(f"[LỖI CLEANUP] {e}")

def _save_match_to_history(room, winner_id, reason):
    """
    Lưu kết quả trận đấu vào database
    """
    try:
        print(f"[HISTORY DEBUG] Đang lưu trận đấu: winner_id={winner_id}, reason={reason}")
        
        if not room.get("player1") or not room.get("player2"):
            print("[HISTORY] Không đủ thông tin người chơi để lưu lịch sử")
            return
            
        player_x_id = room["player1"]["user_id"] 
        player_o_id = room["player2"]["user_id"]
        game_mode = room.get("game_mode", 5)
        
        print(f"[HISTORY DEBUG] player_x_id={player_x_id}, player_o_id={player_o_id}, game_mode={game_mode}")
        
        # Xác định loại kết thúc
        result_type = "normal"
        if reason == "TIMEOUT":
            result_type = "timeout"
        elif reason == "OPPONENT_LEFT":
            result_type = "disconnect"
        elif reason in ["DRAW_TIMEOUT", "DRAW_BOARD_FULL"]:
            result_type = "draw"
        elif reason == "SURRENDER":
            result_type = "surrender"
            
        print(f"[HISTORY DEBUG] result_type={result_type}")
            
        # Tạo move log từ board hiện tại (đơn giản)
        move_log = ""
        if room.get("board"):
            move_log = str(room["board"])
            
        # Lưu vào database
        success = db_manager.save_match_result(
            player_x_id=player_x_id,
            player_o_id=player_o_id, 
            winner_id=winner_id,
            game_mode=game_mode,
            result_type=result_type,
            move_log=move_log
        )
        
        if success:
            print(f"[HISTORY] Đã lưu lịch sử trận đấu: {player_x_id} vs {player_o_id}, winner: {winner_id}")
        else:
            print(f"[HISTORY] Lỗi khi lưu lịch sử trận đấu")
            
    except Exception as e:
        print(f"[HISTORY ERROR] {e}")
        import traceback
        traceback.print_exc()