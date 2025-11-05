# Client/main.py

import pygame
import os
from network import Network
from ui_components import Button, InputBox 

# --- Cài đặt ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
SERVER_URL = "ws://localhost:8765"

# --- Khởi tạo Pygame ---
pygame.init()
pygame.font.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Game Cờ Caro")
clock = pygame.time.Clock()

# --- Tải Font ---
try:
    font_path = os.path.join('Client', 'assets', 'arial.ttf')
    font_large = pygame.font.Font(font_path, 50)
    font_medium = pygame.font.Font(font_path, 30)
    font_small = pygame.font.Font(font_path, 20)
except FileNotFoundError:
    print(f"LỖI: Không tìm thấy font tại '{font_path}'. Dùng font mặc định.")
    font_large = pygame.font.Font(None, 50)
    font_medium = pygame.font.Font(None, 30)
    font_small = pygame.font.Font(None, 20)

# --- Khởi tạo Mạng ---
network = Network(SERVER_URL)

# --- Tạo UI Components ---
comp_width = 300
comp_x = (SCREEN_WIDTH - comp_width) / 2

# === Màn hình WELCOME ===
play_button = Button(
    x=comp_x, y=250, width=comp_width, height=60, 
    text="Chơi Online", font=font_medium,
    color_normal=(0, 200, 0), color_hover=(0, 255, 0)
)
quit_button = Button(
    x=comp_x, y=330, width=comp_width, height=60, 
    text="Thoát Game", font=font_medium,
    color_normal=(200, 0, 0), color_hover=(255, 0, 0)
)

# === Màn hình LOGIN ===
username_input = InputBox(
    x=comp_x, y=200, width=comp_width, height=50, 
    font=font_medium, text="" # Xóa chữ mờ
)
password_input = InputBox(
    x=comp_x, y=270, width=comp_width, height=50, 
    font=font_medium, text="" # Xóa chữ mờ
)
login_button = Button(
    x=comp_x, y=340, width=comp_width, height=60, 
    text="Đăng nhập", font=font_medium,
    color_normal=(0, 150, 200), color_hover=(0, 200, 255)
)
register_button = Button(
    x=comp_x, y=420, width=comp_width, height=60, 
    text="Đăng ký", font=font_medium,
    color_normal=(200, 150, 0), color_hover=(255, 200, 0)
)
back_button = Button( # Nút quay lại chung
    x=20, y=SCREEN_HEIGHT - 70, width=150, height=50, 
    text="< Quay lại", font=font_medium,
    color_normal=(100, 100, 100), color_hover=(150, 150, 150)
)

# === [MỚI] Màn hình LOBBY ===
btn_lobby_width = 280
col1_x = (SCREEN_WIDTH / 2) - btn_lobby_width - 30 # Cột 1
col2_x = (SCREEN_WIDTH / 2) + 30                    # Cột 2
row1_y = 200
row2_y = 300

quick_join_button = Button(
    x=col1_x, y=row1_y, width=btn_lobby_width, height=80, 
    text="Vào nhanh", font=font_medium,
    color_normal=(0, 200, 0), color_hover=(0, 255, 0)
)
create_room_button = Button(
    x=col2_x, y=row1_y, width=btn_lobby_width, height=80, 
    text="Tạo phòng", font=font_medium,
    color_normal=(0, 150, 200), color_hover=(0, 200, 255)
)
join_room_button = Button(
    x=col1_x, y=row2_y, width=btn_lobby_width, height=80, 
    text="Nhập mã phòng", font=font_medium,
    color_normal=(200, 150, 0), color_hover=(255, 200, 0)
)
find_room_button = Button(
    x=col2_x, y=row2_y, width=btn_lobby_width, height=80, 
    text="Tìm phòng", font=font_medium,
    color_normal=(150, 0, 200), color_hover=(200, 0, 255)
)
logout_button = Button(
    x=SCREEN_WIDTH - 170, y=SCREEN_HEIGHT - 70, width=150, height=50, 
    text="Đăng xuất", font=font_medium,
    color_normal=(100, 100, 100), color_hover=(150, 150, 150)
)

# === (Sẽ thêm UI cho IN_ROOM, IN_GAME sau) ===


# --- Quản lý Trạng thái Game ---
# [CẬP NHẬT] Thêm các trạng thái mới
game_state = "WELCOME" # WELCOME, LOGIN, LOBBY, IN_ROOM_WAITING, IN_GAME, ...

# --- Biến Toàn cục của Client ---
user_data = None       
current_room = None    # [Rất quan trọng] Sẽ lưu thông tin phòng khi tham gia
feedback_msg = ""      
feedback_color = (255, 50, 50)



# --- Hàm trợ giúp ---
def draw_text(text, font, x, y, color=(255, 255, 255), center=True):
    # ... (code hàm này giữ nguyên) ...
    img = font.render(text, True, color)
    if center:
        rect = img.get_rect(center=(x, y))
    else:
        rect = img.get_rect(topleft=(x, y))
    screen.blit(img, rect)

def send_login_register(action_type, username, password):
    # ... (code hàm này giữ nguyên) ...
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
                    network.start()
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

        # --- [MỚI] Xử lý Input: LOBBY ---
        elif game_state == "LOBBY":
            if logout_button.is_clicked(event):
                # (Server sẽ tự xử lý ngắt kết nối, chúng ta chỉ cần reset client)
                game_state = "WELCOME"
                user_data = None
                network.ws.close() # Đóng kết nối
                network = Network(SERVER_URL) # Tạo lại đối tượng network mới
            
            if quick_join_button.is_clicked(event):
                print("[GAME] Gửi yêu cầu 'Vào nhanh'...")
                network.send_message({"action": "QUICK_JOIN"})
                feedback_msg = "Đang tìm trận..."
                feedback_color = (255, 255, 255)
            
            if create_room_button.is_clicked(event):
                print("[GAME] Gửi yêu cầu 'Tạo phòng'...")
                # Tạo phòng không mật khẩu
                network.send_message({"action": "CREATE_ROOM", "payload": {"password": ""}})
                # (Chúng ta sẽ làm form nhập pass sau)
                
            if join_room_button.is_clicked(event):
                print("[GAME] Chuyển sang màn hình 'Nhập mã phòng'...")
                # game_state = "JOIN_ROOM_FORM" # Sẽ làm ở bước sau
                feedback_msg = "Chức năng 'Nhập mã' sẽ làm ở bước sau."
            
            if find_room_button.is_clicked(event):
                print("[GAME] Chuyển sang màn hình 'Tìm phòng'...")
                # game_state = "FIND_ROOM_LIST" # Sẽ làm ở bước sau
                feedback_msg = "Chức năng 'Tìm phòng' sẽ làm ở bước sau."
                
        # --- [MỚI] Xử lý Input: IN_ROOM_WAITING (Phòng chờ) ---
        elif game_state == "IN_ROOM_WAITING":
            # (Sẽ thêm nút Sẵn sàng, Rời phòng ở đây)
            pass

    # 2. [CẬP NHẬT] Xử lý Logic Mạng (Nhận tin nhắn)
    message = network.get_message()
    if message:
        print(f"[NHẬN TỪ SERVER] {message}")
        status = message.get("status")
        
        # --- Xử lý phản hồi LOGIN/REGISTER ---
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
            
        # --- [MỚI] Xử lý phản hồi LOBBY ---
        
        elif status == "WAITING_FOR_MATCH": # Phản hồi từ "Vào nhanh"
            feedback_msg = "Đang tìm đối thủ..."
            feedback_color = (255, 255, 255)

        elif status == "ROOM_CREATED": # Phản hồi từ "Tạo phòng"
            current_room = message.get("room_data")
            game_state = "IN_ROOM_WAITING" # <-- CHUYỂN SANG PHÒNG CHỜ
            feedback_msg = ""
            
        elif status == "JOIN_SUCCESS": # Phản hồi từ "Vào nhanh" hoặc "Nhập mã"
            current_room = message.get("room_data")
            game_state = "IN_ROOM_WAITING" # <-- CHUYỂN SANG PHÒNG CHỜ
            feedback_msg = ""
            
        elif status == "OPPONENT_JOINED": # Tin nhắn cho chủ phòng
            current_room["player2"] = message.get("opponent")
            feedback_msg = f"{message.get('opponent', {}).get('username')} đã vào phòng!"
            feedback_color = (50, 255, 50)
            
        # --- (Sẽ thêm xử lý GAME_START, OPPONENT_MOVE... sau) ---


    # 3. Vẽ (Render)
    screen.fill((30, 30, 30))
    
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
            
    # --- [CẬP NHẬT] Vẽ Màn hình LOBBY ---
    elif game_state == "LOBBY":
        if user_data:
            welcome_text = f"Xin chào, {user_data.get('username')}! (Thắng: {user_data.get('wins', 0)})"
            draw_text(welcome_text, font_medium, SCREEN_WIDTH / 2, 50)
        
        draw_text("Sảnh Chờ", font_large, SCREEN_WIDTH / 2, 120)

        # Vẽ các nút
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
        
        # Hiển thị thông báo (ví dụ: "Đang tìm trận...")
        if feedback_msg:
            draw_text(feedback_msg, font_medium, SCREEN_WIDTH / 2, 450, feedback_color)
            
    # --- [CẬP NHẬT] Vẽ Màn hình IN_ROOM_WAITING (Phòng chờ) ---
    elif game_state == "IN_ROOM_WAITING":
        draw_text("Phòng chờ", font_large, SCREEN_WIDTH / 2, 100)
        
        if current_room:
            # Hiển thị mã phòng
            draw_text(f"Mã phòng: {current_room.get('room_id')}", font_medium, SCREEN_WIDTH / 2, 180)
            
            # --- [SỬA LỖI] ---
            # 1. Lấy dữ liệu P1
            player1_data = current_room.get("player1") 
            # 2. Kiểm tra P1 có None không, rồi mới lấy username
            p1_name = player1_data.get("username", "Lỗi tên") if player1_data else "Đang tải..."
            draw_text(f"Người chơi 1: {p1_name}", font_medium, SCREEN_WIDTH / 2, 250, (0, 255, 255))
            
            # --- [SỬA LỖI] ---
            # 1. Lấy dữ liệu P2
            player2_data = current_room.get("player2") # Sẽ là None hoặc một dict
            # 2. Kiểm tra P2 có None không, rồi mới lấy username
            p2_name = player2_data.get("username", "Lỗi tên") if player2_data else "Đang chờ đối thủ..."
            draw_text(f"Người chơi 2: {p2_name}", font_medium, SCREEN_WIDTH / 2, 300, (255, 165, 0))
            # --- HẾT SỬA LỖI ---

        # Hiển thị thông báo (ví dụ: "Đối thủ đã vào")
        if feedback_msg:
            draw_text(feedback_msg, font_medium, SCREEN_WIDTH / 2, 450, feedback_color)
        # (Sẽ thêm nút Sẵn sàng, Rời phòng ở đây)

    # --- Cập nhật màn hình chung ---
    pygame.display.flip()
    clock.tick(60)

# --- Kết thúc ---
if network.is_connected:
    network.ws.close()
pygame.quit()
print("[GAME] Đã đóng game.")