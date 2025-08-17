# live stream util funcs
import os
import pygame # type: ignore
import cv2 #type: ignore
import numpy as np #type: ignore

def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def webcam_image_to_pygame(frame):
    # Convert BGR to RGB for pygame
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    # Convert to contiguous array
    rgb_frame = np.ascontiguousarray(rgb_frame.astype(np.uint8))
    # Create pygame surface
    return pygame.surfarray.make_surface(rgb_frame.swapaxes(0, 1))

# drawing funcs
def draw_log_terminal(surface, rolling_log, scroll_offset=0, margin=10, top=50,
                      line_height=18, bg_color=(0, 0, 0, 180), text_color=(255, 255, 255),
                      font_size=16, scrollbar_width=8):

    font = pygame.font.SysFont("consolas", font_size)
    screen_width = surface.get_width()
    screen_height = surface.get_height()
    column_start_x = 970
    column_width = screen_width - column_start_x
    panel_height = screen_height - top

    # Draw translucent background
    panel_surface = pygame.Surface((column_width, panel_height), pygame.SRCALPHA)
    panel_surface.fill(bg_color)
    surface.blit(panel_surface, (column_start_x, 0))
    
    separator_rect = pygame.Rect(column_start_x, 0, 2, screen_height)
    pygame.draw.rect(surface, (150, 150, 150), separator_rect)
    horiz_bar = pygame.Rect(column_start_x, 35, screen_width-column_width, 2)
    pygame.draw.rect(surface, (150,150,150), horiz_bar)

    label_surf = font.render("Terminal", True, (255, 255, 255))
    surface.blit(label_surf, (column_start_x + margin, 10))

    x = column_start_x + margin
    y = top

    # Calculate how many lines fit in the panel
    visible_lines_count = panel_height // line_height
    total_lines = rolling_log.total_lines()

    # Clamp scroll_offset
    max_scroll = max(0, total_lines - visible_lines_count)
    scroll_offset = max(0, min(scroll_offset, max_scroll))

    # Get visible lines
    lines = rolling_log.get_visible_lines(scroll_offset, visible_lines_count)

    for line in lines:
        i = 0
        while i < len(line):
            max_width = column_width - 2 * margin - scrollbar_width
            j = i + 1
            while j <= len(line):
                slice = line[i:j]
                width = font.render(slice, True, text_color).get_width()
                if width > max_width:
                    # Render up to character before it exceeds
                    if j == i + 1:
                        # Even one character doesn't fit (very narrow terminal)
                        slice = line[i:j]
                    else:
                        slice = line[i:j-1]
                        j -= 1
                    break
                j += 1

            text_surf = font.render(slice, True, text_color)
            surface.blit(text_surf, (x, y))
            y += line_height
            i = j

    # Draw the scrollbar
    if total_lines > visible_lines_count:
        # Scrollbar track starts at y = 35 (the horiz_bar position) and ends at bottom
        scrollbar_track_top = 35
        scrollbar_track_bottom = screen_height
        scrollbar_track_height = scrollbar_track_bottom - scrollbar_track_top

        scrollbar_height = int((visible_lines_count / total_lines) * scrollbar_track_height)
        max_scroll_offset = total_lines - visible_lines_count

        if max_scroll_offset > 0:
            scrollbar_pos = int((scroll_offset / max_scroll_offset) * (scrollbar_track_height - scrollbar_height))
        else:
            scrollbar_pos = 0  # no scrolling needed

        scrollbar_rect = pygame.Rect(
            screen_width - scrollbar_width,
            scrollbar_track_top + scrollbar_pos,
            scrollbar_width,
            scrollbar_height
        )
        pygame.draw.rect(surface, (180, 180, 180), scrollbar_rect)