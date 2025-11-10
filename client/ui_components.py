import pygame
import theme


class Button:
    """Simple stylable Button for Pygame using theme defaults."""
    def __init__(self, x, y, width, height, text, font, color_normal=None, color_hover=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = font
        # Use theme if no color provided
        self.color_normal = color_normal if color_normal is not None else theme.SURFACE
        self.color_hover = color_hover if color_hover is not None else theme.ACCENT_HOVER
        self.current_color = self.color_normal

        # text color comes from theme
        self.text_color = theme.TEXT

    def draw(self, screen):
        """Draw button with rounded corners and centered text."""
        # shadow (subtle)
        shadow_rect = self.rect.move(0, 3)
        pygame.draw.rect(screen, (0, 0, 0, 30), shadow_rect, border_radius=theme.RADIUS)

        pygame.draw.rect(screen, self.current_color, self.rect, border_radius=theme.RADIUS)

        # Render text each frame to ensure color and centering
        text_surf = self.font.render(self.text, True, self.text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

    def check_hover(self, mouse_pos):
        if self.rect.collidepoint(mouse_pos):
            self.current_color = self.color_hover
            return True
        else:
            self.current_color = self.color_normal
            return False

    def is_clicked(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                return True
        return False


class InputBox:
    """Enhanced InputBox with themed colors and blinking cursor."""
    def __init__(self, x, y, width, height, font, text='', is_password=False):
        self.rect = pygame.Rect(x, y, width, height)
        self.font = font
        self.text = text
        self.is_password = is_password

        self.color_inactive = theme.SURFACE
        self.color_active = theme.ACCENT
        self.current_color = self.color_inactive
        self.active = False

        # Cursor
        self.cursor_visible = True
        self.cursor_timer = 0

        # text surface
        self.update_text_surface()

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.active = not self.active
            else:
                self.active = False
            self.current_color = self.color_active if self.active else self.color_inactive
            self.cursor_visible = self.active

        if event.type == pygame.KEYDOWN:
            if self.active:
                if event.key == pygame.K_RETURN:
                    return "enter"
                elif event.key == pygame.K_BACKSPACE:
                    self.text = self.text[:-1]
                else:
                    if event.unicode.isprintable() and len(self.text) < 50:
                        self.text += event.unicode
                self.update_text_surface()

    def update_text_surface(self):
        display_text = self.text
        if self.is_password:
            display_text = '*' * len(self.text)

        self.txt_surface = self.font.render(display_text, True, theme.TEXT)
        self.txt_rect = self.txt_surface.get_rect(midleft=(self.rect.x + 10, self.rect.centery))

        if self.txt_surface.get_width() > self.rect.width - 20:
            self.txt_rect.midright = (self.rect.right - 10, self.rect.centery)

    def update(self, clock):
        if self.active:
            self.cursor_timer += clock.get_time()
            if self.cursor_timer >= 500:
                self.cursor_timer = 0
                self.cursor_visible = not self.cursor_visible

    def draw(self, screen):
        # background
        pygame.draw.rect(screen, self.current_color, self.rect, border_radius=theme.RADIUS)

        # border
        border_color = theme.MUTED if not self.active else theme.ACCENT
        pygame.draw.rect(screen, border_color, self.rect, width=2, border_radius=theme.RADIUS)

        # clipping and text
        clip_rect = self.rect.inflate(-10, -10)
        screen.set_clip(clip_rect)
        screen.blit(self.txt_surface, self.txt_rect)

        # cursor
        if self.active and self.cursor_visible:
            cursor_x = self.txt_rect.right + 2
            if cursor_x > self.rect.right - 8:
                cursor_x = self.rect.right - 8
            cursor_y_start = self.rect.top + 10
            cursor_y_end = self.rect.bottom - 10
            pygame.draw.line(screen, theme.TEXT, (cursor_x, cursor_y_start), (cursor_x, cursor_y_end), 2)

        screen.set_clip(None)