import pygame

class Button:
    def __init__(self, x, y, width, height, text, callback=None, get_color=None, text_dependence=None, text_if_true=None, text_if_false=None,  visible=True, get_visible=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.callback = callback
        self.get_color = get_color
        self.text_dependence = text_dependence
        self.text_if_true = text_if_true
        self.text_if_false = text_if_false
        self.get_visible = get_visible
        self.visible = visible

        self.text_color = (255,255,255)
        self.base_color = (50, 50, 100)

        self.font = pygame.font.SysFont("consolas", 16)
        if self.text == 'Clear Term':
            self.font = pygame.font.SysFont("consolas", 16)
        self.text_surf = self.font.render(text, True, (255, 255, 255))
        self.text_rect = self.text_surf.get_rect(center=self.rect.center)

        self.mouse_down_inside = False
        self.prev_mouse_pressed = False

    def is_visible(self):
        if self.get_visible:
            return self.get_visible()
        return self.visible

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
        base_color = self.get_color() if self.get_color else self.base_color

        # Hover effect
        if self.rect.collidepoint(mouse_pos):
            dim_factor = 1.3 if self.mouse_down_inside else 0.7
            color = tuple(min(255, round(c * dim_factor)) for c in base_color)
        else:
            color = base_color

        # Draw the button rectangle
        pygame.draw.rect(surface, color, self.rect, border_radius=8)

        # --- Text wrapping ---
        font = self.font  # assume self.font exists
        padding = 5
        max_text_width = self.rect.width - 2 * padding
        dynamic_text = self.text
        if self.text_dependence:
            if self.text_dependence.value:
                dynamic_text = self.text_if_true
            else:
                dynamic_text = self.text_if_false

        words = dynamic_text.split()
        lines = []
        current_line = ""

        for word in words:
            test_line = current_line + (" " if current_line else "") + word
            if font.size(test_line)[0] <= max_text_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)

        # Render each line separately and compute real total text height
        text_surfs = [font.render(line, True, self.text_color) for line in lines]
        line_heights = [surf.get_height() for surf in text_surfs]
        total_text_height = sum(line_heights)

        start_y = self.rect.top + (self.rect.height - total_text_height) / 2

        y = start_y
        for surf, h in zip(text_surfs, line_heights):
            text_rect = surf.get_rect(centerx=self.rect.centerx, y=y)
            surface.blit(surf, text_rect)
            y += h