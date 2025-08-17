import pygame #type: ignore
import time
import os
from Utils.Button import Button
import shutil

pygame.init()

def popup_save_recording(window, font, recordingSave, avi_recorder, timestamp, recording, avi_filename, log_queue, is_jf_mode, recordingStartEnd):
    popup_width, popup_height = 400, 150
    window_width, window_height = window.get_size()
    popup_rect = pygame.Rect(
        (window_width - popup_width) // 2,
        (window_height - popup_height) // 2,
        popup_width,
        popup_height
    )

    result = {"choice": None}

    yes_button = Button(
        popup_rect.left + 40, popup_rect.top + 80, 120, 40, "Yes",
        lambda: result.update({"choice": "yes"})
    )
    no_button = Button(
        popup_rect.left + 240, popup_rect.top + 80, 120, 40, "No",
        lambda: result.update({"choice": "no"})
    )

    clock = pygame.time.Clock()
    running_popup = True

    while running_popup:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            mouse_pos = pygame.mouse.get_pos()
            mouse_pressed = pygame.mouse.get_pressed()

            yes_button.handle_event(event, mouse_pos, mouse_pressed)
            no_button.handle_event(event, mouse_pos, mouse_pressed)

        if result["choice"] == "yes":
            recordingStartEnd.value = 2
            recordingSave(recording, avi_recorder,timestamp,log_queue, is_jf_mode)
            return False
        elif result["choice"] == "no":
            recordingStartEnd.value = 2
            timeout = time.time() + 5  # 5 seconds timeout
            while recordingStartEnd.value != 0:
                if time.time() > timeout:
                    break
                time.sleep(0.1)            
            if avi_recorder:
                avi_recorder.release()
                avi_recorder = None
            timestamp_text = timestamp.value.decode('utf-8').rstrip('\x00')
            mode_str = "Jellyfish" if is_jf_mode.value == 1 else "Larvae"
            folder_path = f'saved_runs/run_{timestamp_text}_{mode_str}'
            if os.path.exists(folder_path):
                shutil.rmtree(folder_path)
            return False

        # Dim background
        dim_overlay = pygame.Surface((window_width, window_height), pygame.SRCALPHA)
        dim_overlay.fill((0, 0, 0, 180))  # semi-transparent black
        window.blit(dim_overlay, (0, 0))

        # Draw popup box
        pygame.draw.rect(window, (50, 50, 50), popup_rect, border_radius=10)
        pygame.draw.rect(window, (200, 200, 200), popup_rect, 2, border_radius=10)

        # Draw text
        text_surf = font.render("Save current recording?", True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=(popup_rect.centerx, popup_rect.top + 40))
        window.blit(text_surf, text_rect)

        # Draw buttons
        yes_button.draw(window)
        no_button.draw(window)

        pygame.display.flip()
        clock.tick(30)

    return True