# Server/game_logic.py

import json
import random
import string
import database_manager as db_manager 
import asyncio 

ACTIVE_ROOMS = {}
QUICK_JOIN_WAITING_PLAYER = None 

# --- HÀM DỌN DẸP DỮ LIỆU ---
def _get_clean_room_data(room):
    """
    Tạo một bản sao (copy) của "room" an toàn để gửi qua JSON.
    """
    if not room: return None
    clean_room = room.copy()
    
    if clean_room.get("player1"):
        clean_room["player1"] = clean_room["player1"].copy()
        clean_room["player1"].pop("websocket", None)
        
    if clean_room.get("player2"):
        clean_room["player2"] = clean_room["player2"].copy()
        clean_room["player2"].pop("websocket", None)
        
    return clean_room

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
        room_code = generate_room_code()
        
        print(f"[TẠO PHÒNG] User {username} (ID: {user_id}) đã tạo phòng: {room_code}")
        
        ACTIVE_ROOMS[room_code] = {
            "room_id": room_code,
            "password": password,
            "player1": {
                "websocket": websocket, "user_id": user_id,
                "username": username, "is_ready": False 
            },
            "player2": None, "board": None, "turn": None,
            "settings": settings,
            "timer_task": None # [MỚI] Thêm key timer_task
        }
        
        websocket.room_code = room_code 
        
        await websocket.send(json.dumps({
            "status": "ROOM_CREATED",
            "message": "Tạo phòng thành công!",
            "room_id": room_code,
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
        room_code = payload.get("room_id")
        password = payload.get("password", "")
        user_id = websocket.user_id
        username = websocket.username

        if not room_code:
            await websocket.send(json.dumps({"status": "ERROR", "message": "Vui lòng nhập mã phòng."}))
            return

        if room_code not in ACTIVE_ROOMS:
            await websocket.send(json.dumps({"status": "ERROR", "message": "Mã phòng không tồn tại."}))
            return

        room = ACTIVE_ROOMS[room_code]

        if room["player2"] is not None:
            await websocket.send(json.dumps({"status": "ERROR", "message": "Phòng đã đầy."}))
            return
            
        if room["password"] and room["password"] != password:
            await websocket.send(json.dumps({"status": "ERROR", "message": "Sai mật khẩu phòng."}))
            return
            
        print(f"[VÀO PHÒNG] User {username} (ID: {user_id}) đã vào phòng: {room_code}")
        
        room["player2"] = {
            "websocket": websocket, "user_id": user_id,
            "username": username, "is_ready": False
        }
        websocket.room_code = room_code

        player1_ws = room["player1"]["websocket"]
        clean_room_data = _get_clean_room_data(room)

        await websocket.send(json.dumps({
            "status": "JOIN_SUCCESS",
            "message": "Vào phòng thành công!",
            "room_data": clean_room_data
        }))
        
        await player1_ws.send(json.dumps({
            "status": "OPPONENT_JOINED",
            "message": f"{username} đã vào phòng.",
            "opponent": clean_room_data.get("player2")
        }))

    except AttributeError:
        await websocket.send(json.dumps({"status": "ERROR", "message": "Bạn phải đăng nhập."}))
    except Exception as e:
        print(f"[LỖI VÀO PHÒNG] {e}")
        await websocket.send(json.dumps({"status": "ERROR", "message": "Lỗi khi vào phòng."}))

# --- Chức năng 3: TÌM PHÒNG ---
async def handle_find_room(websocket):
    """
    Gửi cho client danh sách các phòng đang chờ.
    """
    try:
        waiting_rooms = []
        for code, room in ACTIVE_ROOMS.items():
            if room["player2"] is None and room["board"] is None:
                waiting_rooms.append({
                    "room_id": code,
                    "host_name": room["player1"]["username"],
                    "has_password": bool(room["password"]),
                    "settings": room["settings"]
                })
        
        await websocket.send(json.dumps({
            "status": "ROOM_LIST",
            "rooms": waiting_rooms
        }))
    except Exception as e:
        print(f"[LỖI TÌM PHÒNG] {e}")
        await websocket.send(json.dumps({"status": "ERROR", "message": "Lỗi khi tải danh sách phòng."}))

# --- Chức năng 4: VÀO NHANH ---
async def handle_quick_join(websocket):
    """
    Tự động tìm phòng chờ hoặc tạo phòng mới.
    """
    global QUICK_JOIN_WAITING_PLAYER
    try:
        if QUICK_JOIN_WAITING_PLAYER:
            player1_ws = QUICK_JOIN_WAITING_PLAYER
            QUICK_JOIN_WAITING_PLAYER = None 
            
            room_code = generate_room_code()
            print(f"[VÀO NHANH] Ghép cặp {player1_ws.username} và {websocket.username} vào phòng {room_code}")
            
            room = {
                "room_id": room_code, "password": "",
                "player1": {
                    "websocket": player1_ws, "user_id": player1_ws.user_id,
                    "username": player1_ws.username, "is_ready": False
                },
                "player2": {
                    "websocket": websocket, "user_id": websocket.user_id,
                    "username": websocket.username, "is_ready": False
                },
                "board": None, "turn": None, "settings": {"time_limit": 120},
                "timer_task": None # [MỚI] Thêm key timer_task
            }
            ACTIVE_ROOMS[room_code] = room
            
            player1_ws.room_code = room_code
            websocket.room_code = room_code
            
            clean_room_data = _get_clean_room_data(room)
            await player1_ws.send(json.dumps({"status": "JOIN_SUCCESS", "message": "Đã tìm thấy đối thủ!", "room_data": clean_room_data}))
            await websocket.send(json.dumps({"status": "JOIN_SUCCESS", "message": "Đã tìm thấy đối thủ!", "room_data": clean_room_data}))
        
        else:
            QUICK_JOIN_WAITING_PLAYER = websocket
            print(f"[VÀO NHANH] User {websocket.username} đang chờ...")
            await websocket.send(json.dumps({
                "status": "WAITING_FOR_MATCH",
                "message": "Đang tìm đối thủ..."
            }))
    
    except Exception as e:
        print(f"[LỖI VÀO NHANH] {e}")
        await websocket.send(json.dumps({"status": "ERROR", "message": "Lỗi khi vào nhanh."}))

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
        global QUICK_JOIN_WAITING_PLAYER
        if QUICK_JOIN_WAITING_PLAYER == websocket:
            QUICK_JOIN_WAITING_PLAYER = None
            if hasattr(websocket, 'username'):
                print(f"[DỌN DẸP] User {websocket.username} đã hủy chờ 'Vào nhanh'.")

        if not hasattr(websocket, 'room_code'):
            return 

        room_code = websocket.room_code
        if room_code not in ACTIVE_ROOMS:
            return 
            
        room = ACTIVE_ROOMS[room_code]
        user_id = websocket.user_id
        username = websocket.username
        
        print(f"[RỜI PHÒNG] User {username} đã rời/mất kết nối khỏi phòng {room_code}")
        
        # [SỬA LỖI 1] Xóa room_code khỏi websocket (chỉ khi nó tồn tại)
        if hasattr(websocket, 'room_code'):
            del websocket.room_code 
        
        # [MỚI] Hủy timer nếu có
        if room.get("timer_task"):
            room["timer_task"].cancel()
            room["timer_task"] = None
        
        opponent_ws = None
        opponent_id = None
        
        if room["player1"] and room["player1"]["user_id"] == user_id:
            if room["player2"]: 
                opponent_ws = room["player2"]["websocket"]
                opponent_id = room["player2"]["user_id"]
                # P2 trở thành chủ phòng mới
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
            print(f"-> Thông báo cho người chơi còn lại (ID: {opponent_ws.user_id})")
            
            # [MỚI] Xử lý thắng do đối thủ thoát (nếu đang chơi)
            if room.get("board") is not None:
                # Nếu đang trong ván (board tồn tại) -> người ở lại thắng
                await _handle_game_over(room, winner_id=opponent_id, loser_id=user_id, reason="OPPONENT_LEFT")
            else:
                # Nếu đang ở phòng chờ -> chỉ thông báo
                await opponent_ws.send(json.dumps({
                    "status": "OPPONENT_LEFT",
                    "message": f"{username} đã rời phòng. Bạn quay về phòng chờ.",
                    "room_data": _get_clean_room_data(room)
                }))
        
    except AttributeError:
        print(f"[THOÁT] Một client chưa đăng nhập đã thoát.")
    except Exception as e:
        print(f"[LỖI RỜI PHÒNG] {e}")

# --- Chức năng 7: SẴN SÀNG ---
async def handle_ready(websocket, payload):
    """
    Xử lý khi client nhấn nút Sẵn sàng / Hủy sẵn sàng.
    """
    try:
        if not hasattr(websocket, 'room_code'): return 
        room_code = websocket.room_code
        if room_code not in ACTIVE_ROOMS: return 
            
        room = ACTIVE_ROOMS[room_code]
        user_id = websocket.user_id
        is_ready = payload.get("is_ready", True) 

        # [SỬA LỖI 2] Không cho phép READY nếu game đã bắt đầu
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
        print(f"[SẴN SÀNG] User {websocket.username} (phòng {room_code}) đặt trạng thái: {is_ready}")

        if opponent_ws:
            await opponent_ws.send(json.dumps({
                "status": "OPPONENT_READY",
                "is_ready": is_ready
            }))
        
        if (room["player1"] and room["player1"]["is_ready"] and
            room["player2"] and room["player2"]["is_ready"]):
            
            print(f"[BẮT ĐẦU GAME] Cả hai người chơi phòng {room_code} đã sẵn sàng!")
            await _start_game(room) 

    except Exception as e:
        print(f"[LỖI READY] {e}")
        await websocket.send(json.dumps({"status": "ERROR", "message": "Lỗi khi xử lý sẵn sàng."}))

# --- Hàm nội bộ: BẮT ĐẦU GAME ---
async def _start_game(room):
    """
    Hàm nội bộ để khởi tạo ván đấu, random X/O, và gửi tin nhắn.
    """
    board_size = 20
    room["board"] = [[0 for _ in range(board_size)] for _ in range(board_size)]
    
    player1 = room["player1"]
    player2 = room["player2"]
    
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
    
    await playerX["websocket"].send(json.dumps({
        "status": "GAME_START", "role": "X", "turn": "YOU", 
        "board": room["board"], "score": room["score"]
    }))
    
    await playerO["websocket"].send(json.dumps({
        "status": "GAME_START", "role": "O", "turn": "OPPONENT", 
        "board": room["board"], "score": room["score"]
    }))
    
    time_limit = room["settings"].get("time_limit", 120)
    
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
        await asyncio.sleep(time_limit)
        
        if room.get("turn") == player_id_on_turn:
            print(f"[TIMEOUT] User ID {player_id_on_turn} (phòng {room.get('room_id')}) đã hết giờ!")
            
            loser_id = player_id_on_turn
            winner_id = None
            if room["player1"]["user_id"] == loser_id:
                winner_id = room["player2"]["user_id"]
            else:
                winner_id = room["player1"]["user_id"]
                
            loser_ws = room["player1"]["websocket"] if room["player1"]["user_id"] == loser_id else room["player2"]["websocket"]
            
            if loser_ws.open:
                await loser_ws.send(json.dumps({
                    "status": "GAME_OVER",
                    "result": "TIMEOUT_LOSE",
                    "score": room["score"]
                }))
            
            await _handle_game_over(room, winner_id, loser_id, reason="TIMEOUT")

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
        
        # [CẬP NHẬT] HỦY TIMER CŨ
        if room.get("timer_task"):
            room["timer_task"].cancel()
            room["timer_task"] = None
            
        print(f"[NƯỚC ĐI] User {websocket.username} (phòng {room_code}) đánh: ({row}, {col})")
        
        room["board"][row][col] = user_id
        
        opponent_ws = None
        opponent_id = None
        if room["player1"]["user_id"] == user_id:
            if room["player2"]:
                opponent_ws = room["player2"]["websocket"]
                opponent_id = room["player2"]["user_id"]
        else:
            opponent_ws = room["player1"]["websocket"]
            opponent_id = room["player1"]["user_id"]

        if opponent_ws:
            await opponent_ws.send(json.dumps({
                "status": "OPPONENT_MOVE",
                "move": {"row": row, "col": col}
            }))

        if _check_win(room["board"], row, col, user_id):
            print(f"[GAME KẾT THÚC] User {websocket.username} (ID: {user_id}) thắng phòng {room_code}.")
            await _handle_game_over(room, winner_id=user_id, loser_id=opponent_id, reason="WIN")
            return 

        room["turn"] = opponent_id
        
        # [CẬP NHẬT] KHỞI ĐỘNG TIMER MỚI (cho đối thủ)
        if opponent_id: # Chỉ khởi động nếu có đối thủ
            time_limit = room["settings"].get("time_limit", 120)
            timer_task = asyncio.create_task(
                _start_turn_timer(room, opponent_id, time_limit)
            )
            room["timer_task"] = timer_task

    except Exception as e:
        print(f"[LỖI MOVE] {e}")
        await websocket.send(json.dumps({"status": "ERROR", "message": "Lỗi khi xử lý nước đi."}))

# --- Hàm nội bộ: KIỂM TRA THẮNG ---
def _check_win(board, r, c, player_id):
    """
    Kiểm tra xem nước đi tại (r, c) của player_id có tạo ra chiến thắng không.
    """
    board_size = len(board)
    directions = [(0, 1), (1, 0), (1, 1), (1, -1)]

    for dr, dc in directions:
        count = 0
        for i in range(-4, 5):
            nr, nc = r + i * dr, c + i * dc
            
            if 0 <= nr < board_size and 0 <= nc < board_size:
                if board[nr][nc] == player_id:
                    count += 1
                    if count >= 5:
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
    # [CẬP NHẬT] Hủy mọi timer đang chạy
    if room.get("timer_task"):
        room["timer_task"].cancel()
        room["timer_task"] = None

    if "score" not in room:
        room["score"] = {room["player1"]["user_id"]: 0, room["player2"]["user_id"]: 0}
        
    # [CẬP NHẬT] Chỉ cập nhật tỉ số nếu thắng (không phải do thoát)
    if reason in ["WIN", "TIMEOUT"]:
        if winner_id in room["score"]:
            room["score"][winner_id] += 1
        
        # Cập nhật tỉ số trong Database
        db_manager.update_game_stats(winner_id, loser_id)
    
    winner_ws = None
    loser_ws = None
    
    if room["player1"] and room["player1"]["user_id"] == winner_id:
        winner_ws = room["player1"]["websocket"]
        if room["player2"]: loser_ws = room["player2"]["websocket"]
    elif room["player2"] and room["player2"]["user_id"] == winner_id:
        winner_ws = room["player2"]["websocket"]
        if room["player1"]: loser_ws = room["player1"]["websocket"]
    elif room["player1"] and room["player1"]["user_id"] == loser_id: # Trường hợp P2 thắng P1 (P1 là loser)
        loser_ws = room["player1"]["websocket"]
        if room["player2"]: winner_ws = room["player2"]["websocket"]
    elif room["player2"] and room["player2"]["user_id"] == loser_id: # Trường hợp P1 thắng P2 (P2 là loser)
        loser_ws = room["player2"]["websocket"]
        if room["player1"]: winner_ws = room["player1"]["websocket"]


    # [CẬP NHẬT] Gửi thông báo kết quả (linh hoạt hơn)
    if winner_ws and winner_ws.open:
        result_type = "WIN"
        if reason == "TIMEOUT": result_type = "TIMEOUT_WIN"
        elif reason == "OPPONENT_LEFT": result_type = "OPPONENT_LEFT_WIN"
        
        await winner_ws.send(json.dumps({
            "status": "GAME_OVER",
            "result": result_type,
            "score": room["score"]
        }))
        
    if loser_ws and loser_ws.open and reason != "TIMEOUT": 
        await loser_ws.send(json.dumps({
            "status": "GAME_OVER",
            "result": "LOSE",
            "score": room["score"]
        }))
        
    # 5. Reset phòng về trạng thái chờ
    room["board"] = None 
    room["turn"] = None
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
            await opponent_ws.send(json.dumps({
                "status": "OPPONENT_CHAT",
                "sender": username, 
                "message": message
            }))
        else:
            await websocket.send(json.dumps({
                "status": "ERROR",
                "message": "Đang không có ai trong phòng để chat."
            }))

    except Exception as e:
        print(f"[LỖI CHAT] {e}")
        await websocket.send(json.dumps({"status": "ERROR", "message": "Lỗi khi gửi tin nhắn."}))

# --- [MỚI] Chức năng 10: CHƠI LẠI (REMATCH) ---
async def handle_rematch(websocket, payload):
    """
    Xử lý khi client yêu cầu chơi lại (sau khi game kết thúc).
    Logic này gần giống hệt handle_ready.
    """
    try:
        # 1. Kiểm tra phòng
        if not hasattr(websocket, 'room_code'): return 
        room_code = websocket.room_code
        if room_code not in ACTIVE_ROOMS: return 
            
        room = ACTIVE_ROOMS[room_code]
        user_id = websocket.user_id
        
        # 2. [Kiểm tra] Không cho phép "Chơi lại" khi game ĐANG diễn ra
        if room.get("board") is not None:
            await websocket.send(json.dumps({"status": "ERROR", "message": "Không thể chơi lại khi ván đấu đang diễn ra."}))
            return

        # 3. Xác định là P1 hay P2
        player_key = None
        opponent_ws = None
        
        if room["player1"] and room["player1"]["user_id"] == user_id:
            player_key = "player1"
            if room["player2"]: opponent_ws = room["player2"]["websocket"]
        elif room["player2"] and room["player2"]["user_id"] == user_id:
            player_key = "player2"
            opponent_ws = room["player1"]["websocket"]
        
        if not player_key: return # Lỗi

        # 4. Cập nhật trạng thái (dùng lại cờ 'is_ready')
        room[player_key]["is_ready"] = True
        print(f"[CHƠI LẠI] User {websocket.username} (phòng {room_code}) muốn chơi lại.")

        # 5. Thông báo cho đối thủ (nếu có)
        if opponent_ws and opponent_ws.open:
            await opponent_ws.send(json.dumps({
                "status": "OPPONENT_REMATCH", # [MỚI] Gửi action riêng
                "is_ready": True
            }))
        
        # 6. Kiểm tra xem cả hai đã sẵn sàng chưa
        if (room["player1"] and room["player1"]["is_ready"] and
            room["player2"] and room["player2"]["is_ready"]):
            
            print(f"[BẮT ĐẦU VÁN MỚI] Cả hai người chơi phòng {room_code} đồng ý chơi lại!")
            await _start_game(room) # Gọi hàm bắt đầu game

    except Exception as e:
        print(f"[LỖI REMATCH] {e}")
        await websocket.send(json.dumps({"status": "ERROR", "message": "Lỗi khi xử lý chơi lại."}))

# --- [MỚI] Chức năng 11: CẬP NHẬT CÀI ĐẶT PHÒNG ---
async def handle_update_settings(websocket, payload):
    """
    Xử lý khi chủ phòng (P1) thay đổi cài đặt phòng (mật khẩu, thời gian,...)
    """
    try:
        # 1. Kiểm tra phòng
        if not hasattr(websocket, 'room_code'): return
        room_code = websocket.room_code
        if room_code not in ACTIVE_ROOMS: return
            
        room = ACTIVE_ROOMS[room_code]
        user_id = websocket.user_id
        
        # 2. Xác thực: Chỉ P1 (chủ phòng) mới được đổi
        if not room["player1"] or room["player1"]["user_id"] != user_id:
            await websocket.send(json.dumps({
                "status": "ERROR",
                "message": "Chỉ chủ phòng mới có thể thay đổi cài đặt."
            }))
            return
            
        # 3. Xác thực: Không cho đổi khi game đang diễn ra
        if room.get("board") is not None:
            await websocket.send(json.dumps({
                "status": "ERROR",
                "message": "Không thể thay đổi cài đặt khi ván đấu đang diễn ra."
            }))
            return

        # 4. Cập nhật các cài đặt
        # Client có thể gửi một phần hoặc toàn bộ
        if "password" in payload:
            room["password"] = payload["password"]
            print(f"[CÀI ĐẶT] Phòng {room_code} đổi mật khẩu thành: '{payload['password']}'")
            
        if "time_limit" in payload:
            # Đảm bảo time_limit là một số nguyên
            try:
                room["settings"]["time_limit"] = int(payload["time_limit"])
                print(f"[CÀI ĐẶT] Phòng {room_code} đổi thời gian thành: {payload['time_limit']}s")
            except ValueError:
                pass # Bỏ qua nếu gửi time_limit không phải là số
        
        # 5. Lấy dữ liệu phòng "sạch" để gửi
        clean_room_data = _get_clean_room_data(room)
        
        # 6. Gửi thông báo "ĐÃ CẬP NHẬT" cho P1 (người vừa đổi)
        await websocket.send(json.dumps({
            "status": "SETTINGS_UPDATED",
            "room_data": clean_room_data
        }))
        
        # 7. Gửi thông báo "BỊ THAY ĐỔI" cho P2 (nếu có)
        if room["player2"]:
            opponent_ws = room["player2"]["websocket"]
            if opponent_ws.open:
                await opponent_ws.send(json.dumps({
                    "status": "SETTINGS_CHANGED_BY_HOST", # [MỚI] Tên status khác
                    "room_data": clean_room_data
                }))
                
    except Exception as e:
        print(f"[LỖI SETTINGS] {e}")
        await websocket.send(json.dumps({"status": "ERROR", "message": "Lỗi khi cập nhật cài đặt."}))