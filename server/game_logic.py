import json
import random
import string
import database_manager as db_manager 
import asyncio 

ACTIVE_ROOMS = {}
QUICK_JOIN_WAITING_PLAYER = None 

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
            "timer_task": None
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
        
        print(f"[DEBUG] Nhận yêu cầu vào phòng. Payload: {payload}")
        
        if not room_code:  # Kiểm tra riêng trường hợp room_code trống
            await websocket.send(json.dumps({"status": "ERROR", "message": "Vui lòng nhập mã phòng."}))
            return
        
        # Kiểm tra tính hợp lệ của phòng
        print(f"[DEBUG] Đang kiểm tra phòng '{room_code}'. Các phòng hiện tại: {list(ACTIVE_ROOMS.keys())}")
        if not room_code:
            await websocket.send(json.dumps({
                "status": "ERROR", 
                "message": "❌ Vui lòng nhập mã phòng"
            }))
            return
            
        if room_code not in ACTIVE_ROOMS:
            await websocket.send(json.dumps({
                "status": "ERROR", 
                "message": "❌ Phòng này không tồn tại hoặc đã bị đóng"
            }))
            return
            
        room = ACTIVE_ROOMS[room_code]
        
        # Kiểm tra trạng thái phòng
        if room["player2"] is not None:
            await websocket.send(json.dumps({
                "status": "ERROR", 
                "message": "❌ Phòng này đã đầy"
            }))
            return
            
        # Kiểm tra mật khẩu
        if room["password"] and room["password"] != password:
            await websocket.send(json.dumps({
                "status": "ERROR", 
                "message": "❌ Sai mật khẩu phòng"
            }))
            return
        print(f"[VÀO PHÒNG] User {server_username} (ID: {server_user_id}) đã vào phòng: {room_code}")
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
            await player1_ws.send(json.dumps({
                "status": "OPPONENT_JOINED",
                "message": f"{server_username} đã vào phòng.",
                "room_data": clean_room_data
            }))
            print(f"[DEBUG] Đã gửi OPPONENT_JOINED cho player1")
        except Exception as send_error:
            print(f"[DEBUG] Không thể gửi OPPONENT_JOINED cho player1: {send_error}")
        
        print(f"[DEBUG] Chuẩn bị gọi _start_game()...")
        
        # [TỰ ĐỘNG BẮT ĐẦU GAME] Ngay sau khi thông báo
        print(f"[AUTO START] ========================================")
        print(f"[AUTO START] Bắt đầu game tự động cho phòng {room_code}")
        print(f"[AUTO START] Player1: {room['player1']['username']}")
        print(f"[AUTO START] Player2: {room['player2']['username']}")
        print(f"[AUTO START] ========================================")
        
        try:
            await _start_game(room)
        except Exception as start_game_error:
            print(f"[LỖI _START_GAME] {start_game_error}")
            import traceback
            traceback.print_exc()
            
    except AttributeError as ae:
        print(f"[LỖI VÀO PHÒNG - AttributeError] {ae}")
        await websocket.send(json.dumps({"status": "ERROR", "message": "Bạn phải đăng nhập."}))
    except Exception as e:
        print(f"[LỖI VÀO PHÒNG] {e}")
        import traceback
        traceback.print_exc()
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
                # Clean room data cho danh sách
                waiting_rooms.append({
                    "room_id": code,
                    "host_name": room["player1"]["username"],
                    "has_password": bool(room["password"]),
                    "settings": room["settings"],
                    "created_time": room.get("created_time", "")  # Thêm thời gian tạo phòng nếu có
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
        user_id = websocket.user_id
        username = websocket.username

        # [SỬA LỖI] Cấm tự chơi
        if QUICK_JOIN_WAITING_PLAYER and QUICK_JOIN_WAITING_PLAYER.user_id == user_id:
            await websocket.send(json.dumps({"status": "ERROR", "message": "Bạn đã đang trong hàng đợi."}))
            return

        # [LOGIC MỚI] 1. Quét các phòng "Tạo phòng" (ACTIVE_ROOMS) đang chờ
        found_room = None
        for room_code, room in ACTIVE_ROOMS.items():
            if (room["player2"] is None and 
                not room["password"] and 
                room["board"] is None and 
                room["player1"]["user_id"] != user_id):
                
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
            return

        # 3. NẾU KHÔNG TÌM THẤY PHÒNG -> Dùng logic hàng đợi (queue) cũ
        print(f"[VÀO NHANH] Không tìm thấy phòng trống. User {username} vào hàng đợi...")

        if QUICK_JOIN_WAITING_PLAYER:
            player1_ws = QUICK_JOIN_WAITING_PLAYER
            QUICK_JOIN_WAITING_PLAYER = None 
            
            room_code = generate_room_code()
            print(f"[VÀO NHANH] Ghép 2 người chờ {player1_ws.username} và {websocket.username} vào phòng {room_code}")
            
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
                "timer_task": None
            }
            ACTIVE_ROOMS[room_code] = room
            
            player1_ws.room_code = room_code
            websocket.room_code = room_code
            
            # [SỬA LỖI] Gửi data sạch
            clean_room_data = _get_clean_room_data(room) 
            await player1_ws.send(json.dumps({"status": "JOIN_SUCCESS", "message": "Đã tìm thấy đối thủ!", "room_data": clean_room_data}))
            await websocket.send(json.dumps({"status": "JOIN_SUCCESS", "message": "Đã tìm thấy đối thủ!", "room_data": clean_room_data}))
        
        else:
            QUICK_JOIN_WAITING_PLAYER = websocket
            await websocket.send(json.dumps({
                "status": "WAITING_FOR_MATCH",
                "message": "Đang tìm đối thủ..."
            }))
    
    except Exception as e:
        print(f"[LỖI VÀO NHANH] {e}")
        await websocket.send(json.dumps({"status": "ERROR", "message": "Lỗi khi vào nhanh."}))

# --- [MỚI] Chức năng: HỦY VÀO NHANH ---
async def handle_cancel_quick_join(websocket):
    """
    Xử lý khi client chủ động hủy tìm trận 'Vào nhanh'.
    """
    global QUICK_JOIN_WAITING_PLAYER
    try:
        if QUICK_JOIN_WAITING_PLAYER == websocket:
            QUICK_JOIN_WAITING_PLAYER = None
            if hasattr(websocket, 'username'):
                print(f"[DỌN DẸP] User {websocket.username} đã hủy chờ 'Vào nhanh'.")
            
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
        
        if opponent_ws and opponent_ws.open:
            print(f"-> Thông báo cho người chơi còn lại (ID: {opponent_id})")
            
            if room.get("board") is not None:
                await _handle_game_over(room, winner_id=opponent_id, loser_id=user_id, reason="OPPONENT_LEFT")
            else:
                # [SỬA LỖI] Gửi data sạch
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

        if opponent_ws and opponent_ws.open:
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
    Hàm này khởi tạo ván đấu, random X/O, và gửi tin nhắn.
    """
    print(f"[_START_GAME] ===== BẮT ĐẦU TẠO GAME =====")
    
    board_size = 20
    room["board"] = [[0 for _ in range(board_size)] for _ in range(board_size)]
    
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
        "board": clean_board, "score": clean_score
    }))
    
    print(f"[_START_GAME] Gửi GAME_START cho playerO ({playerO['username']})")
    await playerO["websocket"].send(json.dumps({
        "status": "GAME_START", "role": "O", "turn": "OPPONENT", 
        "board": clean_board, "score": clean_score
    }))
    
    print(f"[_START_GAME] ===== ĐÃ GỬI GAME_START CHO CẢ 2 PLAYERS =====")
    
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
        
        # [SỬA LỖI] Kiểm tra lại xem phòng còn tồn tại và game còn diễn ra
        if room_code := room.get("room_id"):
            if room_code not in ACTIVE_ROOMS:
                return # Phòng đã bị hủy
            if room.get("board") is None:
                return # Game đã kết thúc

        if room.get("turn") == player_id_on_turn:
            print(f"[TIMEOUT] User ID {player_id_on_turn} (phòng {room.get('room_id')}) đã hết giờ!")
            
            loser_id = player_id_on_turn
            winner_id = None
            if not room.get("player1") or not room.get("player2"): return # Lỗi, không tìm thấy người chơi
            
            if room["player1"]["user_id"] == loser_id:
                winner_id = room["player2"]["user_id"]
            else:
                winner_id = room["player1"]["user_id"]
                
            loser_ws = room["player1"]["websocket"] if room["player1"]["user_id"] == loser_id else room["player2"]["websocket"]
            
            if loser_ws and loser_ws.open:
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
        if room.get("timer_task"):
            room["timer_task"].cancel()
            room["timer_task"] = None
            
        print(f"[NƯỚC ĐI] User {websocket.username} (phòng {room_code}) đánh: ({row}, {col})")
        
        room["board"][row][col] = user_id
        
        opponent_ws = None
        opponent_id = None
        
        if not room.get("player1") or not room.get("player2"): return # Lỗi
        
        if room["player1"]["user_id"] == user_id:
            opponent_ws = room["player2"]["websocket"]
            opponent_id = room["player2"]["user_id"]
        else:
            opponent_ws = room["player1"]["websocket"]
            opponent_id = room["player1"]["user_id"]

        if opponent_ws and opponent_ws.open:
            await opponent_ws.send(json.dumps({
                "status": "OPPONENT_MOVE",
                "move": {"row": row, "col": col}
            }))

        if _check_win(room["board"], row, col, user_id):
            print(f"[GAME KẾT THÚC] User {websocket.username} (ID: {user_id}) thắng phòng {room_code}.")
            await _handle_game_over(room, winner_id=user_id, loser_id=opponent_id, reason="WIN")
            return 

        room["turn"] = opponent_id
        
        if opponent_id: 
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
        
    # Reset phòng
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

        if opponent_ws and opponent_ws.open:
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

        if opponent_ws and opponent_ws.open:
            await opponent_ws.send(json.dumps({
                "status": "OPPONENT_REMATCH",
                "is_ready": True
            }))
        
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
            if opponent_ws.open:
                await opponent_ws.send(json.dumps({
                    "status": "SETTINGS_CHANGED_BY_HOST", 
                    "room_data": clean_room_data
                }))
                
    except Exception as e:
        print(f"[LỖI SETTINGS] {e}")
        await websocket.send(json.dumps({"status": "ERROR", "message": "Lỗi khi cập nhật cài đặt."}))