# Client/main.py

import pygame
import os
import string
from network import Network
from ui_components import Button, InputBox 
import theme

# --- Cài đặt ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
SERVER_URL = "ws://localhost:8765"
QUICK_JOIN_TIMEOUT = 15000 # 15 giây (tính bằng mili-giây)

# --- Khởi tạo Pygame ---
pygame.init()
pygame.font.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Game Cờ Caro")
clock = pygame.time.Clock()

# --- Tải Font ---
# Thử load font trong thư mục project -> nếu không có thì thử các font hệ thống phổ biến hỗ trợ tiếng Việt
def _load_fonts():
    assets_font = os.path.join(os.path.dirname(__file__), 'assets', 'arial.ttf')
    preferred_names = ['segoeui', 'arial', 'tahoma', 'timesnewroman', 'dejavusans']
    sizes = (50, 30, 20)

    # 1) Nếu có file font trong assets, thử dùng trước
    if os.path.isfile(assets_font):
        try:
            return (pygame.font.Font(assets_font, sizes[0]),
                    pygame.font.Font(assets_font, sizes[1]),
                    pygame.font.Font(assets_font, sizes[2]))
        except Exception:
            pass

    # 2) Thử các font hệ thống theo danh sách ưu tiên
    for name in preferred_names:
        match = pygame.font.match_font(name)
        if match:
            try:
                return (pygame.font.Font(match, sizes[0]),
                        pygame.font.Font(match, sizes[1]),
                        pygame.font.Font(match, sizes[2]))
            except Exception:
                continue

    # 3) Fallback: font mặc định (có thể không hiện dấu tiếng Việt)
    print("CẢNH BÁO: Không tìm được font phù hợp. Sẽ dùng font mặc định (có thể mất dấu tiếng Việt).")
    return (pygame.font.Font(None, sizes[0]),
            pygame.font.Font(None, sizes[1]),
            pygame.font.Font(None, sizes[2]))

font_large, font_medium, font_small = _load_fonts()

# --- Khởi tạo Mạng ---
network = Network(SERVER_URL)

# --- Tạo UI Components ---
comp_width = 300
comp_x = (SCREEN_WIDTH - comp_width) / 2

# === Màn hình WELCOME ===
play_button = Button(
    x=comp_x, y=250, width=comp_width, height=60, 
    text="Chơi Online", font=font_medium,
    color_normal=theme.ACCENT, color_hover=theme.ACCENT_HOVER
)
quit_button = Button(
    x=comp_x, y=330, width=comp_width, height=60, 
    text="Thoát Game", font=font_medium,
    color_normal=theme.DANGER, color_hover=(235, 80, 80)
)

# === Màn hình LOGIN ===
username_input = InputBox(
    x=comp_x, y=200, width=comp_width, height=50, 
    font=font_medium, text=""
)
password_input = InputBox( 
    x=comp_x, y=270, width=comp_width, height=50, 
    font=font_medium, text="", is_password=True
)
login_button = Button(
    x=comp_x, y=340, width=comp_width, height=60, 
    text="Đăng nhập", font=font_medium,
    color_normal=theme.ACCENT, color_hover=theme.ACCENT_HOVER
)
register_button = Button(
    x=comp_x, y=420, width=comp_width, height=60, 
    text="Đăng ký", font=font_medium,
    color_normal=theme.WARNING, color_hover=(255, 190, 60)
)
back_button = Button( # Nút quay lại chung
    x=20, y=SCREEN_HEIGHT - 70, width=150, height=50, 
    text="< Quay lại", font=font_medium,
    color_normal=theme.MUTED, color_hover=theme.SUBTEXT
)

# === Màn hình FIND_ROOM ===
refresh_button = Button(
    x=SCREEN_WIDTH - 180, y=20, width=160, height=40,
    text="Làm mới", font=font_small,
    color_normal=theme.ACCENT, color_hover=theme.ACCENT_HOVER
)

room_list_start_y = 150  # Vị trí bắt đầu của danh sách phòng
room_item_height = 100   # Chiều cao mỗi phòng trong danh sách
rooms_per_page = 4       # Số phòng hiển thị trên một trang
current_page = 0         # Trang hiện tại
available_rooms = []     # Danh sách phòng có sẵn

# Nút chuyển trang
prev_page_button = Button(
    x=20, y=SCREEN_HEIGHT - 70, width=150, height=50,
    text="< Trang trước", font=font_medium,
    color_normal=theme.MUTED, color_hover=theme.SUBTEXT
)
next_page_button = Button(
    x=SCREEN_WIDTH - 170, y=SCREEN_HEIGHT - 70, width=150, height=50,
    text="Trang sau >", font=font_medium,
    color_normal=theme.MUTED, color_hover=theme.SUBTEXT
)

# === Màn hình LOBBY ===
btn_lobby_width = 280
col1_x = (SCREEN_WIDTH / 2) - btn_lobby_width - 30 
col2_x = (SCREEN_WIDTH / 2) + 30
row1_y = 200
row2_y = 300
quick_join_button = Button(
    x=col1_x, y=row1_y, width=btn_lobby_width, height=80, 
    text="Vào nhanh", font=font_medium,
    color_normal=theme.LIME_GREEN, color_hover=(50, 255, 120)
)
create_room_button = Button(
    x=col2_x, y=row1_y, width=btn_lobby_width, height=80, 
    text="Tạo phòng", font=font_medium,
    color_normal=theme.CYAN_BLUE, color_hover=(50, 220, 255)
)
join_room_button = Button(
    x=col1_x, y=row2_y, width=btn_lobby_width, height=80, 
    text="Nhập mã phòng", font=font_medium,
    color_normal=theme.GOLD_ORANGE, color_hover=(255, 200, 50)
)
find_room_button = Button(
    x=col2_x, y=row2_y, width=btn_lobby_width, height=80, 
    text="Tìm phòng", font=font_medium,
    color_normal=theme.MAGENTA_PURPLE, color_hover=(240, 100, 240)
)
logout_button = Button(
    x=SCREEN_WIDTH - 170, y=SCREEN_HEIGHT - 70, width=150, height=50, 
    text="Đăng xuất", font=font_medium,
    color_normal=theme.MUTED, color_hover=theme.SUBTEXT
)

# === Màn hình QUICK_JOIN_WAITING ===
cancel_quick_join_button = Button(
    x=comp_x, y=300, width=comp_width, height=60, 
    text="Hủy", font=font_medium,
    color_normal=theme.DANGER, color_hover=(235, 80, 80)
)

# === Màn hình CREATE_ROOM_FORM ===
create_room_password_input = InputBox( 
    x=comp_x, y=200, width=comp_width, height=50, 
    font=font_medium, is_password=True
)
create_room_time_input = InputBox(
    x=comp_x, y=300, width=comp_width, height=50, 
    font=font_medium
)
create_room_confirm_button = Button(
    x=comp_x, y=420, width=comp_width, height=60, 
    text="Tạo phòng", font=font_medium,
    color_normal=theme.ACCENT, color_hover=theme.ACCENT_HOVER
)

# === Màn hình NHẬP MÃ PHÒNG (JOIN_ROOM_FORM) ===
join_room_code_input = InputBox(
    x=comp_x, y=200, width=comp_width, height=50, 
    font=font_medium, text=""
)
join_room_password_input = InputBox( 
    x=comp_x, y=300, width=comp_width, height=50, 
    font=font_medium, text="", is_password=True
)
join_room_confirm_button = Button(
    x=comp_x, y=420, width=comp_width, height=60, 
    text="Vào phòng", font=font_medium,
    color_normal=theme.ACCENT, color_hover=theme.ACCENT_HOVER
)

# --- Quản lý Trạng thái Game ---
game_state = "WELCOME" # WELCOME, LOGIN, LOBBY, CREATE_ROOM_FORM, JOIN_ROOM_FORM, QUICK_JOIN_WAITING, IN_ROOM_WAITING, PLAYING

# --- Biến Toàn cục của Client ---
user_data = None       
current_room = None    
feedback_msg = ""      
feedback_color = (255, 50, 50)
client_is_ready = False 
quick_join_start_time = None 
last_click_time = 0  # Thời gian click cuối cùng
click_cooldown = 500  # Thời gian chờ giữa các lần click (0.5 giây)
is_processing_join = False  # Đang xử lý yêu cầu join room
join_room_origin = "LOBBY"  # Màn hình gốc khi vào form join room

# --- Biến Game Playing ---
game_board = None  # Ma trận bàn cờ
player_role = None  # "X" hoặc "O"
is_my_turn = False  # Lượt của mình
board_size = 20  # Kích thước bàn cờ 20x20
cell_size = 25  # Kích thước mỗi ô
board_offset_x = 50  # Vị trí bàn cờ trên màn hình
board_offset_y = 100
my_user_id = None  # ID của mình
opponent_user_id = None  # ID của đối thủ
my_username = None  # Username của mình
opponent_username = None  # Username của đối thủ

# --- Biến Game Over ---
game_result = None  # WIN, LOSE, TIMEOUT_WIN, etc.
game_score = {}  # {user_id: score}

# --- Hàm trợ giúp ---
def draw_text(text, font, x, y, color=theme.TEXT, center=True):
    img = font.render(text, True, color)
    if center:
        rect = img.get_rect(center=(x, y))
    else:
        rect = img.get_rect(topleft=(x, y))
    screen.blit(img, rect)


def get_score_for_user(score_dict, uid):
    """Return the score for uid from score_dict handling str/int key mismatches.

    Tries direct lookup, then stringified key, then scans keys comparing string forms.
    Returns 0 if no match found or score_dict is falsy.
    """
    if not score_dict:
        return 0

    # direct lookup
    try:
        if uid in score_dict:
            return score_dict[uid]
    except Exception:
        pass

    s_uid = str(uid)
    if s_uid in score_dict:
        return score_dict[s_uid]

    # fallback: compare stringified keys
    for k, v in score_dict.items():
        try:
            if str(k) == s_uid:
                return v
        except Exception:
            continue

    return 0


def find_opponent_id_from_score(score_dict, my_uid):
    """Find and return the opponent id key from a score dict given my_uid.

    Returns the first key that does not match my_uid (compares string forms).
    Returns None if not found.
    """
    if not score_dict:
        return None

    s_my = str(my_uid)
    for k in score_dict.keys():
        try:
            if str(k) != s_my:
                return k
        except Exception:
            continue
    return None

def send_login_register(action_type, username, password):
    global feedback_msg, feedback_color
    if not username or not password:
        feedback_msg = "Vui lòng nhập tên và mật khẩu."
        feedback_color = (255, 50, 50)
        return

    network.send_message({
        "action": action_type,
        "payload": {"username": username, "password": password}
    })
    feedback_msg = "Đang xử lý..."
    feedback_color = (255, 255, 255)

# --- Vòng lặp Game Chính ---
running = True
while running:
    # 1. Xử lý Input (Sự kiện)
    mouse_pos = pygame.mouse.get_pos()
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        # --- Xử lý Input: WELCOME ---
        if game_state == "WELCOME":
            if play_button.is_clicked(event):
                if not network.is_connected:
                    try:
                        network.start()
                    except Exception as e:
                        print(f"Lỗi network: {e}")
                game_state = "LOGIN"
                feedback_msg = "" 
            if quit_button.is_clicked(event):
                running = False
        
        # --- Xử lý Input: LOGIN ---
        elif game_state == "LOGIN":
            username_input.handle_event(event)
            password_input.handle_event(event)
            
            if back_button.is_clicked(event):
                game_state = "WELCOME"
            if login_button.is_clicked(event):
                send_login_register("LOGIN", username_input.text, password_input.text)
            if register_button.is_clicked(event):
                send_login_register("REGISTER", username_input.text, password_input.text)

        # --- [SỬA LẠI CẤU TRÚC] Xử lý Input: LOBBY ---
        elif game_state == "LOBBY":
            if logout_button.is_clicked(event):
                game_state = "WELCOME"
                user_data = None
                if network.is_connected:
                    try: network.ws.close() 
                    except: pass
                network = Network(SERVER_URL)
            
            if quick_join_button.is_clicked(event):
                print("[GAME] Gửi yêu cầu 'Vào nhanh'...")
                network.send_message({"action": "QUICK_JOIN"})
                game_state = "QUICK_JOIN_WAITING" 
                quick_join_start_time = pygame.time.get_ticks()
                feedback_msg = ""
            
            if create_room_button.is_clicked(event):
                print("[GAME] Chuyển sang màn hình 'Cài đặt phòng'...")
                game_state = "CREATE_ROOM_FORM"
                feedback_msg = ""
                create_room_password_input.text = "" 
                create_room_time_input.text = "120"
                
            if join_room_button.is_clicked(event):
                print("[GAME] Chuyển sang màn hình 'Nhập mã phòng'...")
                game_state = "JOIN_ROOM_FORM"
                join_room_origin = "LOBBY"  # Đánh dấu là từ màn hình lobby
                join_room_code_input.text = "" # Xóa input cũ
                join_room_password_input.text = ""
                feedback_msg = "🎮 Nhập mã phòng 5 ký tự để tham gia"
                feedback_color = (255, 255, 255)
            
            if find_room_button.is_clicked(event):
                print("[GAME] Chuyển sang màn hình 'Tìm phòng'...")
                game_state = "FIND_ROOM"
                feedback_msg = ""
                network.send_message({"action": "FIND_ROOM"})

        # --- [ĐÃ DI CHUYỂN] Xử lý Input: CREATE_ROOM_FORM ---
        elif game_state == "CREATE_ROOM_FORM":
            create_room_password_input.handle_event(event)
            create_room_time_input.handle_event(event)

            if back_button.is_clicked(event):
                game_state = "LOBBY"
                feedback_msg = ""
            
            if create_room_confirm_button.is_clicked(event):
                password = create_room_password_input.text
                time_limit_str = create_room_time_input.text
                try:
                    time_limit_int = int(time_limit_str) if time_limit_str else 120
                    if time_limit_int < 30:
                         feedback_msg = "Thời gian phải ít nhất 30 giây."
                         feedback_color = (255, 50, 50)
                    else:
                        network.send_message({
                            "action": "CREATE_ROOM", 
                            "payload": {
                                "password": password,
                                "settings": {"time_limit": time_limit_int}
                            }
                        })
                        feedback_msg = "Đang tạo phòng..."
                        feedback_color = (255, 255, 255)
                except ValueError:
                    feedback_msg = "Thời gian (giây) phải là một con số."
                    feedback_color = (255, 50, 50)

        # --- Xử lý Input: FIND_ROOM ---
        elif game_state == "FIND_ROOM":
            if back_button.is_clicked(event):
                game_state = "LOBBY"
                feedback_msg = ""
            
            if refresh_button.is_clicked(event):
                network.send_message({"action": "FIND_ROOM"})
                
            if prev_page_button.is_clicked(event) and current_page > 0:
                current_page -= 1
                
            if next_page_button.is_clicked(event):
                if current_page < (len(available_rooms) - 1) // rooms_per_page:
                    current_page += 1
                    
            # Xử lý click nút Join trong danh sách phòng
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = pygame.mouse.get_pos()
                # Kiểm tra click trên từng nút Join
                start_idx = current_page * rooms_per_page
                end_idx = min(start_idx + rooms_per_page, len(available_rooms))
                
                for i in range(start_idx, end_idx):
                    room = available_rooms[i]
                    y_pos = 120 + (i - start_idx) * 60
                    join_btn_rect = pygame.Rect(SCREEN_WIDTH - 200, y_pos + 5, 80, 40)
                    
                    if join_btn_rect.collidepoint(mouse_pos):
                        # Gửi yêu cầu tham gia phòng trực tiếp
                        room_id = room.get('room_id')
                        has_password = room.get('has_password', False)
                        
                        if has_password:
                            # Nếu phòng có mật khẩu, chuyển sang form nhập mật khẩu
                            game_state = "JOIN_ROOM_FORM"
                            join_room_origin = "FIND_ROOM"  # Đánh dấu là từ màn hình tìm phòng
                            join_room_code_input.text = room_id
                            join_room_password_input.text = ""
                            feedback_msg = ""  # Xóa message cũ
                            feedback_color = (255, 255, 255)
                        else:
                            # Nếu không có mật khẩu, join trực tiếp
                            network.send_message({
                                "action": "JOIN_ROOM",
                                "payload": {
                                    "room_id": room_id,
                                    "password": ""
                                }
                            })
                            print(f"[GAME] Gửi yêu cầu vào phòng {room_id}")
                            feedback_msg = "⌛ Đang vào phòng..."
                            feedback_color = (255, 255, 255)
                total_pages = (len(available_rooms) - 1) // rooms_per_page + 1
                if current_page < total_pages - 1:
                    current_page += 1

        # --- Xử lý Input: JOIN_ROOM_FORM ---
        elif game_state == "JOIN_ROOM_FORM":
            join_room_code_input.handle_event(event)
            join_room_password_input.handle_event(event)

            if back_button.is_clicked(event):
                game_state = "LOBBY"
                feedback_msg = ""
            
            if join_room_confirm_button.is_clicked(event):
                room_code = join_room_code_input.text.strip().upper()  # Chuyển mã phòng về chữ hoa
                password = join_room_password_input.text.strip()
                
                if not room_code:
                    feedback_msg = "⚠️ Vui lòng nhập mã phòng"
                    feedback_color = (255, 50, 50)
                elif len(room_code) != 5:  # Kiểm tra độ dài mã phòng
                    feedback_msg = "⚠️ Mã phòng phải có đúng 5 ký tự"
                    feedback_color = (255, 50, 50)
                elif not all(c in string.ascii_uppercase + string.digits for c in room_code):
                    feedback_msg = "⚠️ Mã phòng chỉ gồm chữ cái và số"
                    feedback_color = (255, 50, 50)
                else:
                    try:
                        print(f"[GAME] Gửi yêu cầu vào phòng: {room_code}")
                        network.send_message({
                            "action": "JOIN_ROOM",
                            "payload": {
                                "room_id": room_code,
                                "password": password
                            }
                        })
                        feedback_msg = "⌛ Đang kiểm tra phòng..."
                        feedback_color = (255, 255, 255)
                    except Exception as e:
                        print(f"[ERROR] Lỗi khi gửi yêu cầu vào phòng: {e}")
                        feedback_msg = "Lỗi kết nối! Vui lòng thử lại."
                        feedback_color = (255, 50, 50)        # --- [ĐÃ DI CHUYỂN] Xử lý Input: QUICK_JOIN_WAITING ---
        elif game_state == "QUICK_JOIN_WAITING":
            if cancel_quick_join_button.is_clicked(event):
                network.send_message({"action": "CANCEL_QUICK_JOIN"})
                game_state = "LOBBY"
                feedback_msg = "Đã hủy tìm trận."
                feedback_color = (255, 255, 255)
                quick_join_start_time = None 

        # --- Xử lý Input: IN_ROOM_WAITING (Phòng chờ) ---
        elif game_state == "IN_ROOM_WAITING":
            # (Chúng ta sẽ thêm nút Sẵn sàng/Rời phòng ở đây)
            pass
        
        # --- Xử lý Input: PLAYING (Đang chơi) ---
        elif game_state == "PLAYING":
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if is_my_turn and game_board:
                    mouse_x, mouse_y = event.pos
                    
                    # Tính toán centered board offset (giống như phần render)
                    board_width = board_size * cell_size
                    centered_board_offset_x = (SCREEN_WIDTH - board_width) // 2
                    centered_board_offset_y = 160
                    
                    # Tính toán ô được click
                    col = (mouse_x - centered_board_offset_x) // cell_size
                    row = (mouse_y - centered_board_offset_y) // cell_size
                    
                    # Kiểm tra click hợp lệ
                    if 0 <= row < board_size and 0 <= col < board_size:
                        if game_board[row][col] == 0:  # Ô trống
                            print(f"[GAME] Đánh cờ tại ({row}, {col})")
                            
                            # Cập nhật board ngay lập tức (optimistic update)
                            if my_user_id:
                                game_board[row][col] = my_user_id
                                is_my_turn = False  # Chuyển lượt
                            
                            # Gửi nước đi lên server
                            network.send_message({
                                "action": "MAKE_MOVE",
                                "payload": {
                                    "row": row,
                                    "col": col
                                }
                            })
                        else:
                            print(f"[GAME] Ô ({row}, {col}) đã có quân cờ")
                    else:
                        print(f"[GAME] Click ngoài bàn cờ: ({row}, {col})")
        
        # --- Xử lý Input: GAME_OVER_SCREEN ---
        elif game_state == "GAME_OVER_SCREEN":
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Check nếu click vào vùng button (sẽ xử lý ở render)
                mouse_x, mouse_y = event.pos
                
                # Tính vị trí button (phải match với code render)
                rematch_rect = pygame.Rect((SCREEN_WIDTH / 2) - 160, 370, 140, 50)
                lobby_rect = pygame.Rect((SCREEN_WIDTH / 2) + 20, 370, 140, 50)
                
                if rematch_rect.collidepoint(mouse_x, mouse_y):
                    network.send_message({"action": "REMATCH", "payload": {}})
                    feedback_msg = "Đã gửi lời mời chơi lại đến đối thủ..."
                    feedback_color = (255, 255, 0)
                    print("[REMATCH] Đã gửi yêu cầu chơi lại")
                elif lobby_rect.collidepoint(mouse_x, mouse_y):
                    network.send_message({"action": "LEAVE_ROOM", "payload": {}})
                    game_state = "LOBBY"
                    game_board = None
                    player_role = None
                    is_my_turn = False
                    my_user_id = None
                    opponent_user_id = None
                    game_result = None
                    game_score = {}
                    feedback_msg = "Đã rời phòng"
                    feedback_color = (255, 255, 255)
                    print("[LOBBY] Đã rời phòng về lobby")

    # --- [SỬA LẠI CẤU TRÚC] 2. Cập nhật trạng thái (cho con trỏ nhấp nháy) ---
    if game_state == "LOGIN":
        username_input.update(clock) 
        password_input.update(clock)
    elif game_state == "CREATE_ROOM_FORM":
        create_room_password_input.update(clock)
        create_room_time_input.update(clock)
    # [MỚI]
    elif game_state == "JOIN_ROOM_FORM":
        join_room_code_input.update(clock)
        join_room_password_input.update(clock)

    # 2.5. Xử lý Logic Hẹn giờ (Timeout)
    if game_state == "QUICK_JOIN_WAITING":
        if quick_join_start_time is not None: 
            current_time = pygame.time.get_ticks()
            elapsed_time = current_time - quick_join_start_time
            
            if elapsed_time > QUICK_JOIN_TIMEOUT: 
                print("[GAME] Hết 15s chờ. Tự động hủy.")
                game_state = "LOBBY" 
                feedback_msg = "Không tìm thấy trận. Thử lại sau."
                feedback_color = (255, 50, 50) 
                network.send_message({"action": "CANCEL_QUICK_JOIN"})
                quick_join_start_time = None 

    # 3. Xử lý Logic Mạng (Nhận tin nhắn)
    message = network.get_message()
    if message:
        print(f"[NHẬN TỪ SERVER] {message}")
        status = message.get("status")
        
        if status == "LOGIN_SUCCESS":
            game_state = "LOBBY"
            user_data = message.get("user_data")
            feedback_msg = ""
            username_input.text = ""
            password_input.text = ""
        
        elif status == "SUCCESS": # Đăng ký thành công
            feedback_msg = message.get("message", "Đăng ký thành công!")
            feedback_color = (50, 255, 50) 
        
        elif status == "ERROR": # Bất kỳ lỗi nào
            feedback_msg = message.get("message", "Lỗi không xác định.")
            feedback_color = (255, 50, 50)
            if game_state == "QUICK_JOIN_WAITING":
                game_state = "LOBBY" 
                quick_join_start_time = None
            # [MỚI] Nếu lỗi khi đang nhập mã, thì vẫn ở lại form
            elif game_state == "JOIN_ROOM_FORM":
                pass
            
        elif status == "WAITING_FOR_MATCH": 
            if game_state == "QUICK_JOIN_WAITING":
                feedback_msg = "Đang tìm đối thủ..."
                feedback_color = (255, 255, 255)

        elif status == "CANCEL_QUICK_JOIN_SUCCESS":
            game_state = "LOBBY"
            feedback_msg = "Đã hủy tìm trận."
            feedback_color = (255, 255, 255)
            quick_join_start_time = None 

        elif status in ["ROOM_CREATED", "JOIN_SUCCESS", "ROOM_UPDATED"]:
            new_room_data = message.get("room_data")
            print(f"[DEBUG] Cập nhật thông tin phòng: {new_room_data}")
            current_room = new_room_data
            game_state = "IN_ROOM_WAITING"
            feedback_msg = message.get("message", "Vào phòng thành công!")
            feedback_color = (50, 255, 50)
            quick_join_start_time = None
            is_processing_join = False  # Reset trạng thái xử lý
            # Luôn cập nhật danh sách phòng sau khi có thay đổi
            network.send_message({"action": "FIND_ROOM"})

        elif status == "OPPONENT_JOINED":
            # Server may send either 'opponent' (single player) or full 'room_data'.
            # Accept both to avoid desyncs that can kick player out.
            if message.get("room_data"):
                current_room = message.get("room_data")
            elif current_room and message.get("opponent"):
                current_room["player2"] = message.get("opponent")
            feedback_msg = message.get("message", "")
            
        elif status == "ROOM_LIST":
            available_rooms = message.get("rooms", [])
            print(f"[DEBUG] Nhận được danh sách phòng: {available_rooms}")
            current_page = 0  # Reset về trang đầu tiên khi nhận danh sách mới
            feedback_msg = "Đã cập nhật danh sách phòng" # Hiển thị thông báo
            feedback_color = (255, 255, 255)


        elif status == "ERROR":  # Thay vì JOIN_ROOM_FAILED, server sẽ gửi ERROR
            error_msg = message.get("message", "Lỗi không xác định.")
            print(f"[ERROR] {error_msg}")
            feedback_msg = error_msg
            feedback_color = (255, 50, 50)
            is_processing_join = False  # Reset trạng thái xử lý

            # Nếu đang ở màn hình tìm phòng và có thông báo lỗi liên quan đến phòng
            if game_state == "FIND_ROOM" and ("phòng" in error_msg.lower() or "room" in error_msg.lower()):
                network.send_message({"action": "FIND_ROOM"})
        
        # [MỚI] Xử lý khi game bắt đầu
        elif status == "GAME_START":
            print(f"[DEBUG] ===== NHẬN GAME_START =====")
            print(f"[DEBUG] Message: {message}")
            
            game_state = "PLAYING"
            game_board = message.get("board")
            player_role = message.get("role")  # "X" hoặc "O"
            turn_status = message.get("turn")  # "YOU" hoặc "OPPONENT"
            is_my_turn = (turn_status == "YOU")
            score_data = message.get("score")
            
            # Lưu my_user_id
            my_user_id = user_data.get("user_id") if user_data else None
            my_username = user_data.get("username") if user_data else None
            # opponent_user_id sẽ được set khi nhận OPPONENT_MOVE đầu tiên
            opponent_user_id = None
            opponent_username = None
            
            # Lấy opponent_username từ current_room
            if current_room:
                player1_data = current_room.get("player1", {})
                player2_data = current_room.get("player2", {})
                
                if my_user_id:
                    if player1_data.get("user_id") == my_user_id:
                        opponent_username = player2_data.get("username")
                    elif player2_data.get("user_id") == my_user_id:
                        opponent_username = player1_data.get("username")
            
            print(f"[GAME START] Role: {player_role}, Turn: {turn_status}, My Turn: {is_my_turn}")
            print(f"[DEBUG] My ID: {my_user_id}, Username: {my_username}")
            print(f"[DEBUG] Opponent Username: {opponent_username}")
            print(f"[DEBUG] game_state đã đổi thành: {game_state}")
            print(f"[DEBUG] game_board có {len(game_board)} rows" if game_board else "[DEBUG] game_board is None")
            
            feedback_msg = ""  # Xóa message cũ
            feedback_color = (50, 255, 50)
        
        # [MỚI] Xử lý nước đi của đối thủ
        elif status == "OPPONENT_MOVE":
            move_data = message.get("move", {})
            row = move_data.get("row")
            col = move_data.get("col")
            player_id = message.get("player_id")  # ID của người đánh
            
            if game_board and row is not None and col is not None and player_id:
                # Cập nhật bàn cờ với ID của đối thủ
                game_board[row][col] = player_id
                is_my_turn = True
                
                # Lưu opponent_user_id nếu chưa có
                if opponent_user_id is None:
                    opponent_user_id = player_id
                
                print(f"[OPPONENT MOVE] Đối thủ (ID: {player_id}) đánh tại ({row}, {col}), Lượt của tôi: {is_my_turn}")
        
        # [MỚI] Xử lý khi game kết thúc
        elif status == "GAME_OVER":
            game_state = "GAME_OVER_SCREEN"
            game_result = message.get("result")  # WIN, LOSE, TIMEOUT_WIN, TIMEOUT_LOSE, OPPONENT_LEFT_WIN
            game_score = message.get("score", {})

            # Tự động tìm opponent_user_id từ score nếu chưa có
            if opponent_user_id is None and game_score and my_user_id is not None:
                opponent_user_id = find_opponent_id_from_score(game_score, my_user_id)
                if opponent_user_id is not None:
                    print(f"[GAME OVER] Tự động phát hiện opponent_user_id: {opponent_user_id}")
            
            print(f"[GAME OVER] Kết quả: {game_result}")
            print(f"[GAME OVER] Score nhận từ server: {game_score}")
            print(f"[GAME OVER] My user_id: {my_user_id}")
            print(f"[GAME OVER] Opponent user_id: {opponent_user_id}")
            if game_score and my_user_id:
                my_score = get_score_for_user(game_score, my_user_id)
                opp_score = get_score_for_user(game_score, opponent_user_id)
                print(f"[GAME OVER] My score: {my_score}, Opponent score: {opp_score}")
            
            feedback_msg = ""
            feedback_color = (255, 255, 255)
        
        # [MỚI] Xử lý khi đối thủ muốn chơi lại
        elif status == "OPPONENT_REMATCH":
            feedback_msg = "Đối thủ muốn chơi lại!"
            feedback_color = (0, 255, 0)
            print("[REMATCH] Đối thủ đã gửi lời mời chơi lại") 

    # 4. Vẽ (Render)
    screen.fill(theme.BG)
    
    # Debug: In ra game_state hiện tại
    # print(f"[DEBUG RENDER] Current game_state: {game_state}")
    
    # --- Vẽ Màn hình WELCOME ---
    if game_state == "WELCOME":
        draw_text("GAME CỜ CARO", font_large, SCREEN_WIDTH / 2, 100)
        play_button.check_hover(mouse_pos)
        quit_button.check_hover(mouse_pos)
        play_button.draw(screen)
        quit_button.draw(screen)
    
    # --- Vẽ Màn hình LOGIN ---
    elif game_state == "LOGIN":
        draw_text("Đăng nhập / Đăng ký", font_large, SCREEN_WIDTH / 2, 100)
        username_input.draw(screen)
        password_input.draw(screen)
        login_button.check_hover(mouse_pos)
        register_button.check_hover(mouse_pos)
        back_button.check_hover(mouse_pos)
        login_button.draw(screen)
        register_button.draw(screen)
        back_button.draw(screen)
        if feedback_msg:
            draw_text(feedback_msg, font_medium, SCREEN_WIDTH / 2, 510, feedback_color)
            
    # --- Vẽ Màn hình LOBBY ---
    elif game_state == "LOBBY":
        if user_data:
            welcome_text = f"Xin chào, {user_data.get('username')}! (Thắng: {user_data.get('wins', 0)})"
            draw_text(welcome_text, font_medium, SCREEN_WIDTH / 2, 50)
        
        draw_text("Sảnh Chờ", font_large, SCREEN_WIDTH / 2, 120)
        quick_join_button.check_hover(mouse_pos)
        create_room_button.check_hover(mouse_pos)
        join_room_button.check_hover(mouse_pos)
        find_room_button.check_hover(mouse_pos)
        logout_button.check_hover(mouse_pos)
        quick_join_button.draw(screen)
        create_room_button.draw(screen)
        join_room_button.draw(screen)
        find_room_button.draw(screen)
        logout_button.draw(screen)
        if feedback_msg:
            draw_text(feedback_msg, font_medium, SCREEN_WIDTH / 2, 450, feedback_color)

    # --- Vẽ Màn hình CREATE_ROOM_FORM ---
    elif game_state == "CREATE_ROOM_FORM":
        draw_text("Cài đặt phòng", font_large, SCREEN_WIDTH / 2, 100)
        draw_text("Mật khẩu (bỏ trống nếu không cần):", font_small, comp_x, 180, center=False)
        create_room_password_input.draw(screen)
        draw_text("Thời gian mỗi lượt (giây):", font_small, comp_x, 280, center=False)
        create_room_time_input.draw(screen)
        create_room_confirm_button.check_hover(mouse_pos)
        create_room_confirm_button.draw(screen)
        back_button.check_hover(mouse_pos)
        back_button.draw(screen)
        if feedback_msg:
            draw_text(feedback_msg, font_medium, SCREEN_WIDTH / 2, 510, feedback_color)

    # --- Vẽ Màn hình FIND_ROOM ---
    elif game_state == "FIND_ROOM":
        draw_text("Danh sách phòng", font_large, SCREEN_WIDTH / 2, 50)
        
        # Vẽ nút làm mới và quay lại
        refresh_button.check_hover(mouse_pos)
        refresh_button.draw(screen)
        back_button.check_hover(mouse_pos)
        back_button.draw(screen)
        
        # Tính toán số trang
        if available_rooms:
            total_pages = (len(available_rooms) - 1) // rooms_per_page + 1
            start_idx = current_page * rooms_per_page
            end_idx = min(start_idx + rooms_per_page, len(available_rooms))
            
            # Hiển thị thông tin từng phòng
            for i in range(start_idx, end_idx):
                room = available_rooms[i]
                y_pos = 120 + (i - start_idx) * 60
                
                # Vẽ background cho phòng
                pygame.draw.rect(screen, (50, 50, 50), (50, y_pos, SCREEN_WIDTH - 100, 50))
                
                # Thông tin phòng và nút Join
                has_password = room.get('has_password', False)
                room_text = f"Room {room.get('room_id')} - Host: {room.get('host_name')} {'🔒' if has_password else ''}"
                join_btn_rect = pygame.Rect(SCREEN_WIDTH - 200, y_pos + 5, 80, 40)
                join_btn_color = (0, 200, 0) if join_btn_rect.collidepoint(mouse_pos) else (0, 150, 0)
                pygame.draw.rect(screen, join_btn_color, join_btn_rect)
                draw_text("Join", font_small, join_btn_rect.centerx, join_btn_rect.centery)
                draw_text(room_text, font_medium, SCREEN_WIDTH/2 - 150, y_pos + 25, center=False)
                if room.get('has_password'):
                    room_text += " 🔒"
                room_surface = font_medium.render(room_text, True, (255, 255, 255))
                screen.blit(room_surface, (60, y_pos + 15))

                # Vẽ nút Join
                join_btn_rect = pygame.Rect(SCREEN_WIDTH - 160, y_pos + 10, 100, 30)
                join_btn_color = (0, 255, 0) if join_btn_rect.collidepoint(mouse_pos) else (0, 200, 0)
                pygame.draw.rect(screen, join_btn_color, join_btn_rect)
                
                # Text "Join"
                join_text = font_small.render("Join", True, (255, 255, 255))
                text_rect = join_text.get_rect(center=join_btn_rect.center)
                screen.blit(join_text, text_rect)
                
                # Xử lý click
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and join_btn_rect.collidepoint(event.pos):
                    current_time = pygame.time.get_ticks()
                    
                    # Kiểm tra cooldown và trạng thái xử lý
                    if current_time - last_click_time >= click_cooldown and not is_processing_join:
                        last_click_time = current_time
                        is_processing_join = True
                        
                        room_id = str(room.get('room_id'))
                        if room.get('has_password'):
                            join_room_code_input.text = room_id
                            join_room_password_input.text = ""
                            game_state = "JOIN_ROOM_FORM"
                            feedback_msg = ""
                        else:
                            print(f"[GAME] Gửi yêu cầu vào phòng {room_id}")
                            try:
                                network.send_message({
                                    "action": "JOIN_ROOM",
                                    "room_id": room_id,
                                    "password": ""
                                })
                                feedback_msg = "Đang vào phòng..."
                                feedback_color = (255, 255, 255)
                            except Exception as e:
                                print(f"[ERROR] Lỗi khi gửi yêu cầu join room: {e}")
                                feedback_msg = "Lỗi kết nối! Vui lòng thử lại."
                                feedback_color = (255, 50, 50)
                                is_processing_join = False
            
            # Hiển thị điều hướng trang
            if current_page > 0:
                prev_page_button.check_hover(mouse_pos)
                prev_page_button.draw(screen)
            if current_page < total_pages - 1:
                next_page_button.check_hover(mouse_pos)
                next_page_button.draw(screen)
            
            # Hiển thị thông tin trang
            page_info = f"Page {current_page + 1}/{total_pages}"
            page_text = font_small.render(page_info, True, (255, 255, 255))
            screen.blit(page_text, (SCREEN_WIDTH//2 - page_text.get_width()//2, SCREEN_HEIGHT - 50))
        else:
            draw_text("No rooms available", font_medium, SCREEN_WIDTH//2, SCREEN_HEIGHT//2)
        
        if feedback_msg:
            draw_text(feedback_msg, font_medium, SCREEN_WIDTH//2, SCREEN_HEIGHT - 100, feedback_color)

    # --- Vẽ Màn hình JOIN_ROOM_FORM ---
    elif game_state == "JOIN_ROOM_FORM":
        # Title
        draw_text("🎮 Vào phòng chơi", font_large, SCREEN_WIDTH / 2, 80)

        # Panel card for inputs
        panel_x = 60
        panel_y = 120
        panel_w = SCREEN_WIDTH - 2 * panel_x
        panel_h = 360
        panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
        pygame.draw.rect(screen, theme.SURFACE, panel_rect, border_radius=theme.RADIUS)

        # Subtitle / helper bar inside panel
        hint_rect = pygame.Rect(panel_x + 20, panel_y + 12, panel_w - 40, 44)
        pygame.draw.rect(screen, theme.MUTED, hint_rect, border_radius=8)
        draw_text("Mã phòng có 5 ký tự (chữ in hoa và số)", font_small, hint_rect.centerx, hint_rect.centery, color=theme.SUBTEXT)

        # Position inputs inside panel (centered horizontally)
        input_x = (SCREEN_WIDTH - comp_width) // 2
        join_room_code_input.rect.topleft = (input_x, panel_y + 80)
        join_room_password_input.rect.topleft = (input_x, panel_y + 160)

        # Labels (left aligned to input)
        label_x = input_x
        draw_text("Mã phòng:", font_small, label_x, panel_y + 60, color=theme.SUBTEXT, center=False)
        join_room_code_input.draw(screen)

        draw_text("Mật khẩu (nếu có):", font_small, label_x, panel_y + 140, color=theme.SUBTEXT, center=False)
        join_room_password_input.draw(screen)

        # Confirm button (centered)
        join_room_confirm_button.rect.centerx = SCREEN_WIDTH // 2
        join_room_confirm_button.rect.y = panel_y + 240
        join_room_confirm_button.check_hover(mouse_pos)
        join_room_confirm_button.draw(screen)

        # Back button bottom-left (keep existing position)
        back_button.check_hover(mouse_pos)
        back_button.draw(screen)

        # Feedback
        if feedback_msg:
            draw_text(feedback_msg, font_medium, SCREEN_WIDTH / 2, panel_y + panel_h + 24, color=feedback_color)

    # --- Vẽ Màn hình QUICK_JOIN_WAITING ---
    elif game_state == "QUICK_JOIN_WAITING":
        draw_text("Đang tìm trận...", font_large, SCREEN_WIDTH / 2, 100)
        if quick_join_start_time is not None:
            current_time = pygame.time.get_ticks()
            elapsed_time_sec = (current_time - quick_join_start_time) // 1000
            remaining_time = max(0, 15 - elapsed_time_sec) 
            draw_text(f"Thời gian còn lại: {remaining_time} giây", font_medium, SCREEN_WIDTH / 2, 200)
        cancel_quick_join_button.check_hover(mouse_pos)
        cancel_quick_join_button.draw(screen)
            
    # --- Vẽ Màn hình IN_ROOM_WAITING (Phòng chờ) ---
    elif game_state == "IN_ROOM_WAITING":
        draw_text("Phòng chờ", font_large, SCREEN_WIDTH / 2, 100)
        
        if current_room:
            # Hiển thị mã phòng
            room_id = current_room.get('room_id', 'ERROR')
            draw_text(f"Mã phòng: {room_id}", font_medium, SCREEN_WIDTH / 2, 180)
            
            # Hiển thị thông tin người chơi 1 (Chủ phòng)
            player1_data = current_room.get("player1", {})
            if player1_data:
                p1_name = player1_data.get("username", "Đang tải...")
                p1_ready = "(Sẵn sàng)" if player1_data.get("is_ready") else ""
                draw_text(f"Người chơi 1: {p1_name} {p1_ready}", font_medium, 
                         SCREEN_WIDTH / 2, 250, (0, 255, 255))
            else:
                draw_text("Người chơi 1: Đang tải...", font_medium,
                         SCREEN_WIDTH / 2, 250, (0, 255, 255))
            
            # Hiển thị thông tin người chơi 2
            player2_data = current_room.get("player2", None)
            if player2_data:
                p2_name = player2_data.get("username", "Lỗi tên")
                p2_ready = "(Sẵn sàng)" if player2_data.get("is_ready") else ""
                draw_text(f"Người chơi 2: {p2_name} {p2_ready}", font_medium, 
                         SCREEN_WIDTH / 2, 300, (255, 165, 0))
            else:
                draw_text("Người chơi 2: Đang chờ đối thủ...", font_medium, 
                         SCREEN_WIDTH / 2, 300, (255, 165, 0))

        try:
            if feedback_msg:
                draw_text(feedback_msg, font_medium, SCREEN_WIDTH / 2, 450, feedback_color)
        except Exception as e:
            print(f"[ERROR] Lỗi khi hiển thị feedback: {e}")
        # (Sẽ thêm nút Sẵn sàng, Rời phòng ở đây)

    # --- Vẽ Màn hình PLAYING (Đang chơi) ---
    elif game_state == "PLAYING":
        # print(f"[DEBUG RENDER PLAYING] player_role={player_role}, is_my_turn={is_my_turn}, game_board={'exists' if game_board else 'None'}")
        
        # Vẽ background
        screen.fill(theme.BG)
        
        # Vẽ tiêu đề
        draw_text("ĐANG CHƠI", font_medium, SCREEN_WIDTH / 2, 30, (0, 255, 0))
        
        # === PHẦN HIỂN THỊ THÔNG TIN 2 NGƯỜI CHƠI ===
        # Layout: Avatar trên, tên/username dưới (cấu trúc dọc)
        player_panel_y = 55
        avatar_radius = 25
        
        # BẠN - Bên trái
        my_avatar_x = SCREEN_WIDTH // 4  # 25% từ trái
        my_avatar_y = player_panel_y + 10
        
        # Vẽ avatar (hình tròn)
        pygame.draw.circle(screen, (0, 150, 255), (my_avatar_x, my_avatar_y), avatar_radius)
        my_first_char = (my_username[0].upper() if my_username else "?")
        draw_text(my_first_char, font_medium, my_avatar_x, my_avatar_y, (255, 255, 255))
        
        # Username và Role trên cùng 1 dòng
        username_role_text = f"{my_username if my_username else 'Đang tải...'} ({player_role if player_role else '?'})"
        draw_text(username_role_text, font_small, my_avatar_x, my_avatar_y + 50, (150, 200, 255))
        
        # ĐỐI THỦ - Bên phải
        opp_avatar_x = (3 * SCREEN_WIDTH) // 4  # 75% từ trái
        opp_avatar_y = player_panel_y + 10
        opp_role = "X" if player_role == "O" else "O"
        
        # Vẽ avatar (hình tròn)
        pygame.draw.circle(screen, (255, 100, 100), (opp_avatar_x, opp_avatar_y), avatar_radius)
        opp_first_char = (opponent_username[0].upper() if opponent_username else "?")
        draw_text(opp_first_char, font_medium, opp_avatar_x, opp_avatar_y, (255, 255, 255))
        
        # Username dưới avatar
        draw_text(opponent_username if opponent_username else "Đang tải...", font_small, opp_avatar_x, opp_avatar_y + 50, (255, 180, 180))
        
        # Role (X hoặc O) dưới username
        draw_text(opp_role if opp_role else "?", font_small, opp_avatar_x, opp_avatar_y + 70, (255, 255, 100))
        
        # Hiển thị trạng thái lượt đi
        turn_text = "Lượt của bạn!" if is_my_turn else "Lượt đối thủ..."
        turn_color = (0, 255, 0) if is_my_turn else (255, 100, 100)
        draw_text(turn_text, font_small, SCREEN_WIDTH / 2, 145, turn_color)
        
        # Vẽ bàn cờ nếu có
        if game_board:
            # Tính toán vị trí board để căn giữa
            board_width = board_size * cell_size
            board_height = board_size * cell_size
            centered_board_offset_x = (SCREEN_WIDTH - board_width) // 2
            centered_board_offset_y = 160  # Khoảng cách từ trên xuống
            
            # Vẽ lưới với màu sáng hơn (200, 200, 200) thay vì (100, 100, 100)
            grid_color = (200, 200, 200)
            for row in range(board_size + 1):
                y = centered_board_offset_y + row * cell_size
                pygame.draw.line(screen, grid_color, 
                               (centered_board_offset_x, y), 
                               (centered_board_offset_x + board_width, y), 2)
            
            for col in range(board_size + 1):
                x = centered_board_offset_x + col * cell_size
                pygame.draw.line(screen, grid_color, 
                               (x, centered_board_offset_y), 
                               (x, centered_board_offset_y + board_height), 2)
            
            # Vẽ các quân cờ
            for row in range(board_size):
                for col in range(board_size):
                    cell_value = game_board[row][col]
                    if cell_value != 0:  # Có quân cờ
                        x = centered_board_offset_x + col * cell_size + cell_size // 2
                        y = centered_board_offset_y + row * cell_size + cell_size // 2

                        # Xác định ký hiệu (symbol) và màu (color)
                        # game_board có thể lưu user_id (chuỗi/số) hoặc 1/2 -> xử lý cả hai trường hợp
                        my_sym = player_role if player_role in ("X", "O") else "X"
                        opp_sym = "O" if my_sym == "X" else "X"

                        symbol = None
                        # So sánh với user_id nếu server lưu user_id lên board
                        if my_user_id is not None and cell_value == my_user_id:
                            symbol = my_sym
                        elif opponent_user_id is not None and cell_value == opponent_user_id:
                            symbol = opp_sym
                        else:
                            # Fallback: nếu server dùng 1/2
                            try:
                                if int(cell_value) == 1:
                                    symbol = "X"
                                elif int(cell_value) == 2:
                                    symbol = "O"
                                else:
                                    symbol = "?"
                            except Exception:
                                symbol = "?"

                        if symbol == "X":
                            color = (255, 0, 0)
                        elif symbol == "O":
                            color = (0, 100, 255)
                        else:
                            color = (255, 255, 0)

                        draw_text(symbol, font_small, x, y, color)
        else:
            draw_text("Đang tải bàn cờ...", font_medium, SCREEN_WIDTH / 2, 300)

    # --- Vẽ Màn hình GAME_OVER_SCREEN ---
    elif game_state == "GAME_OVER_SCREEN":
        screen.fill(theme.BG)
        
        # Tiêu đề dựa trên kết quả
        if game_result in ["WIN", "TIMEOUT_WIN", "OPPONENT_LEFT_WIN"]:
            title = "CHIẾN THẮNG! 🎉"
            title_color = (0, 255, 0)
            if game_result == "TIMEOUT_WIN":
                subtitle = "Đối thủ hết giờ"
            elif game_result == "OPPONENT_LEFT_WIN":
                subtitle = "Đối thủ đã rời game"
            else:
                subtitle = "Bạn đã thắng!"
        else:  # LOSE, TIMEOUT_LOSE
            title = "THUA CUỘC 😢"
            title_color = (255, 0, 0)
            if game_result == "TIMEOUT_LOSE":
                subtitle = "Bạn đã hết giờ"
            else:
                subtitle = "Đối thủ đã thắng"
        
        draw_text(title, font_large, SCREEN_WIDTH / 2, 150, title_color)
        draw_text(subtitle, font_medium, SCREEN_WIDTH / 2, 220, (255, 255, 255))
        
        # Hiển thị điểm số (dùng my_user_id và opponent_user_id)
        if game_score and my_user_id is not None:
            # Use robust lookup to handle string/int keys from server
            my_score = get_score_for_user(game_score, my_user_id)
            # If opponent id not known, try to infer from score dict
            if opponent_user_id is None:
                inferred = find_opponent_id_from_score(game_score, my_user_id)
                if inferred is not None:
                    opponent_user_id = inferred
            opponent_score = get_score_for_user(game_score, opponent_user_id) if opponent_user_id is not None else 0

            draw_text(f"Tỷ số: {my_score} - {opponent_score}", font_medium, SCREEN_WIDTH / 2, 280, (255, 255, 0))
        
        # Hiển thị thông báo (nếu có)
        if feedback_msg:
            draw_text(feedback_msg, font_small, SCREEN_WIDTH / 2, 320, feedback_color)
        
        # Nút chơi lại và quay về lobby
        rematch_button = Button(
            x=(SCREEN_WIDTH / 2) - 160, y=370, width=140, height=50,
            text="Chơi lại", font=font_medium,
            color_normal=(0, 200, 0), color_hover=(0, 255, 0)
        )
        lobby_button = Button(
            x=(SCREEN_WIDTH / 2) + 20, y=370, width=140, height=50,
            text="Về Lobby", font=font_medium,
            color_normal=(200, 0, 0), color_hover=(255, 0, 0)
        )
        
        rematch_button.check_hover(mouse_pos)
        lobby_button.check_hover(mouse_pos)
        rematch_button.draw(screen)
        lobby_button.draw(screen)

    # --- Cập nhật màn hình chung ---
    try:
        pygame.display.flip()
        clock.tick(60)
    except (KeyboardInterrupt, SystemExit):
        break
    except Exception as e:
        print(f"[ERROR] Lỗi trong game loop: {e}")
        break

# --- Kết thúc ---
print("[GAME] Đang đóng game...")
if network and network.is_connected:
    try:
        network.ws.close()
    except Exception as e:
        print(f"[ERROR] Lỗi khi đóng network: {e}")
pygame.quit()
print("[GAME] Đã đóng game thành công.")