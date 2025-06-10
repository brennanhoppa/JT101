import pygame

class Button:
    def __init__(self, x, y, width, height, text, callback=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.callback = callback

        self.base_color = (0, 0, 255)
        self.hover_color = (100, 100, 255)
        self.active_color = (0, 200, 0)

        self.font = pygame.font.SysFont(None, 28)
        self.text_surf = self.font.render(text, True, (255, 255, 255))
        self.text_rect = self.text_surf.get_rect(center=self.rect.center)

        self.mouse_down_inside = False
        self.prev_mouse_pressed = False

    def handle_event(self, event, mouse_pos, mouse_pressed):
        # Detect mouse press start
        if mouse_pressed[0] and not self.prev_mouse_pressed:
            if self.rect.collidepoint(mouse_pos):
                self.mouse_down_inside = True
            else:
                self.mouse_down_inside = False

        # Detect mouse release
        if not mouse_pressed[0] and self.prev_mouse_pressed:
            if self.mouse_down_inside and self.rect.collidepoint(mouse_pos):
                if self.callback:
                    self.callback()
            self.mouse_down_inside = False
        self.prev_mouse_pressed = mouse_pressed[0]

    def draw(self, surface):
        mouse_pos = pygame.mouse.get_pos()
        if self.rect.collidepoint(mouse_pos):
            color = self.active_color if self.mouse_down_inside else self.hover_color
        else:
            color = self.base_color

        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        surface.blit(self.text_surf, self.text_rect)
