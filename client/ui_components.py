# Client/ui_components.py

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
    """Tạo một class Ô Nhập Liệu (InputBox) cho Pygame."""
    def __init__(self, x, y, width, height, font, text=''):
        self.rect = pygame.Rect(x, y, width, height)
        self.font = font
        self.text = text
        self.color_inactive = (100, 100, 100) # Màu xám mờ
        self.color_active = (200, 200, 200)   # Màu xám sáng
        self.current_color = self.color_inactive
        self.active = False
        
        # Tạo bề mặt (surface) cho text
        self.txt_surface = self.font.render(text, True, self.current_color)
        self.txt_rect = self.txt_surface.get_rect(center=self.rect.center)

    def handle_event(self, event):
        """Xử lý sự kiện cho ô input."""
        if event.type == pygame.MOUSEBUTTONDOWN:
            # Nếu click vào ô
            if self.rect.collidepoint(event.pos):
                self.active = not self.active
            else:
                self.active = False
            # Đổi màu dựa trên trạng thái active
            self.current_color = self.color_active if self.active else self.color_inactive
        
        if event.type == pygame.KEYDOWN:
            if self.active:
                if event.key == pygame.K_RETURN:
                    # (Tùy chọn) Nhấn Enter để gửi
                    return "enter" 
                elif event.key == pygame.K_BACKSPACE:
                    # Xóa ký tự
                    self.text = self.text[:-1]
                else:
                    # Thêm ký tự (chỉ nhận a-z, 0-9, _, -)
                    if event.unicode.isalnum() or event.unicode in ('_', '-'):
                         self.text += event.unicode
                
                # Cập nhật lại surface text
                self.update_text_surface()

    def update_text_surface(self):
        """Cập nhật surface text mỗi khi text thay đổi."""
        self.txt_surface = self.font.render(self.text, True, (255, 255, 255)) # Chữ màu trắng
        # Căn lề trái cho text
        self.txt_rect = self.txt_surface.get_rect(midleft=(self.rect.x + 10, self.rect.centery))
        # Tự động co dãn chiều rộng (nếu cần, nhưng tạm thời bỏ qua)
        # new_width = max(self.rect.width, self.txt_surface.get_width() + 20)
        # self.rect.w = new_width

    def draw(self, screen):
        """Vẽ ô input lên màn hình."""
        # Vẽ hình chữ nhật
        pygame.draw.rect(screen, self.current_color, self.rect, border_radius=10)
        # Vẽ chữ
        screen.blit(self.txt_surface, self.txt_rect)