import pygame

class Button:
    """Tạo một class Button đơn giản cho Pygame"""
    def __init__(self, x, y, width, height, text, font, color_normal, color_hover):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = font
        self.color_normal = color_normal
        self.color_hover = color_hover
        self.current_color = color_normal
        
        # Tạo bề mặt (surface) cho text
        self.text_surf = self.font.render(text, True, (0, 0, 0)) # Màu chữ đen
        self.text_rect = self.text_surf.get_rect(center=self.rect.center)

    def draw(self, screen):
        """Vẽ nút lên màn hình."""
        # Vẽ hình chữ nhật của nút
        pygame.draw.rect(screen, self.current_color, self.rect, border_radius=10)
        # Vẽ chữ lên trên
        screen.blit(self.text_surf, self.text_rect)

    def check_hover(self, mouse_pos):
        """Kiểm tra xem chuột có đang di lên nút không."""
        if self.rect.collidepoint(mouse_pos):
            self.current_color = self.color_hover
            return True
        else:
            self.current_color = self.color_normal
            return False

    def is_clicked(self, event):
        """Kiểm tra xem nút có được nhấn không."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                return True
        return False
    

class InputBox:
    """Tạo một class Ô Nhập Liệu (InputBox) đã nâng cấp."""
    def __init__(self, x, y, width, height, font, text='', is_password=False):
        self.rect = pygame.Rect(x, y, width, height)
        self.font = font
        self.text = text
        self.is_password = is_password # [MỚI] Biến để che mật khẩu
        
        self.color_inactive = (100, 100, 100)
        self.color_active = (200, 200, 200)
        self.current_color = self.color_inactive
        self.active = False
        
        # [MỚI] Thêm con trỏ nhấp nháy
        self.cursor_visible = True
        self.cursor_timer = 0
        
        self.update_text_surface() # Gọi hàm cập nhật

    def handle_event(self, event):
        """Xử lý sự kiện cho ô input."""
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.active = not self.active
            else:
                self.active = False
            self.current_color = self.color_active if self.active else self.color_inactive
            self.cursor_visible = self.active # Hiện con trỏ khi active
        
        if event.type == pygame.KEYDOWN:
            if self.active:
                if event.key == pygame.K_RETURN:
                    return "enter" 
                elif event.key == pygame.K_BACKSPACE:
                    self.text = self.text[:-1]
                else:
                    # [THAY ĐỔI] Cho phép mọi ký tự in được (bao gồm @, !, .)
                    if event.unicode.isprintable() and len(self.text) < 50:
                         self.text += event.unicode
                
                self.update_text_surface()

    def update_text_surface(self):
        """Cập nhật surface text mỗi khi text thay đổi."""
        
        # [MỚI] Che mật khẩu
        display_text = self.text
        if self.is_password:
            display_text = '*' * len(self.text)
            
        self.txt_surface = self.font.render(display_text, True, (255, 255, 255))
        
        # [MỚI] Xử lý cuộn (scroll)
        # Căn lề trái, có 10px đệm
        self.txt_rect = self.txt_surface.get_rect(midleft=(self.rect.x + 10, self.rect.centery))
        
        # Nếu chữ dài hơn ô (trừ 20px đệm 2 bên)
        if self.txt_surface.get_width() > self.rect.width - 20:
            # Căn lề phải
            self.txt_rect.midright = (self.rect.right - 10, self.rect.centery)

    # [MỚI] Thêm hàm update (dùng cho con trỏ)
    def update(self, clock):
        """Cập nhật con trỏ nhấp nháy (chạy mỗi frame)."""
        if self.active:
            # clock.get_time() lấy thời gian (ms) từ frame trước
            self.cursor_timer += clock.get_time() 
            if self.cursor_timer >= 500: # 500ms (nửa giây)
                self.cursor_timer = 0
                self.cursor_visible = not self.cursor_visible

    def draw(self, screen):
        """Vẽ ô input lên màn hình."""
        # 1. Vẽ hình chữ nhật
        pygame.draw.rect(screen, self.current_color, self.rect, border_radius=10)
        
        # 2. [MỚI] Tạo vùng "cắt" (clipping area)
        # Chỉ vẽ chữ bên trong ô (thụt vào 5px)
        clip_rect = self.rect.inflate(-10, -10)
        screen.set_clip(clip_rect)
        
        # 3. Vẽ chữ (đã được căn lề trong update_text_surface)
        screen.blit(self.txt_surface, self.txt_rect)
        
        # 4. [MỚI] Vẽ con trỏ nhấp nháy
        if self.active and self.cursor_visible:
            cursor_x = self.txt_rect.right + 2 # Vị trí con trỏ
            # Đảm bảo con trỏ không tràn ra ngoài
            if cursor_x > self.rect.right - 8:
                cursor_x = self.rect.right - 8
            
            cursor_y_start = self.rect.top + 10
            cursor_y_end = self.rect.bottom - 10
            pygame.draw.line(screen, (255, 255, 255), (cursor_x, cursor_y_start), (cursor_x, cursor_y_end), 2)

        # 5. [MỚI] Tắt vùng "cắt"
        screen.set_clip(None)