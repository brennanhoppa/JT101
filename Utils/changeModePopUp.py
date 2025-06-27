import pygame
import os
from Utils.Button import Button
from Utils.log import log
import time
pygame.init()
from Utils.CONSTANTS import CONSTANTS

def changeModePopUp(is_jf_mode,x_pos,y_pos,step_size,log_queue, window, font):
    
    
    popup_width, popup_height = 1000, 400
    window_width, window_height = window.get_size()
    popup_rect = pygame.Rect(
        (window_width - popup_width) // 2,
        (window_height - popup_height) // 2,
        popup_width,
        popup_height
    )

    result = {"choice": None}

    # Button size
    button_width, button_height = 120, 40

    # Vertical position: some margin above bottom
    button_y = popup_rect.bottom - 20 - button_height

    # Horizontal positions: center them evenly
    space_between = 40
    total_width = 2 * button_width + space_between

    start_x = popup_rect.centerx - total_width // 2

    yes_button = Button(
        start_x, button_y, button_width, button_height, "Yes",
        lambda: result.update({"choice": "yes"})
    )
    no_button = Button(
        start_x + button_width + space_between, button_y, button_width, button_height, "No",
        lambda: result.update({"choice": "no"})
    )

    clock = pygame.time.Clock()
    running_popup = True
    
    if is_jf_mode.value == 0: # switching from larvae to jf
        msg = (
            "Steps to switching from larvae mode to jellyfish mode:\n"
            "1. Move the microscope so it is all the way down on the gantry.\n"
            "2. Refocus microscope on corner border or other object.\n"
            "3. Switch the motor controller switches on both motors so switches 1,2,4,5 are on (3 and 6 off).\n"
            "This gives 2000 steps/revolution.\n"
            "4. Prepare boundary inside tank for jellyfish.\n"
            f"Initial Pos: X: {x_pos.value}, Y: {y_pos.value}"
        )
    elif is_jf_mode.value == 1: # switching from jf to larvae
        msg = (
            "Steps to switching from jellyfish mode to larvae mode:\n"
            "1. Move the microscope so it is inside the tank boundary.\n"
            "2. Move the microscope up on the platform to be the WD away from the glass.\n "
            "Use the 3d printed calibration piece (it's 0.407 inches thick).\n"
            "4. Refocus microscope on corner border or other object.\n"
            "5. Switch the motor controller switches on both motors so switches 1,2,4,6 are on (3 and 5 off). \n"
            "This gives 12800 steps/revolution.\n"
            "6. Prepare boundary inside tank for larvae.\n"
            f"Initial Pos: X: {x_pos.value}, Y: {y_pos.value}"
        )
    else: 
        msg = (
            f"Mode incorrectly saved as: {is_jf_mode.value}.\n"
            "Please close program, edit C:\\Users\\JellyTracker\\Desktop\\JellyFishTrackingPC-main\\Utils\\jf_or_larvae_mode.txt \n "
            "to be 0 (Meaning larvae) or 1 (meaning JF)"
        )

    step_size.value = 0
    # Split message into lines
    msg_lines = msg.split('\n')
    step_size.value = 0

    while running_popup:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None

            mouse_pos = pygame.mouse.get_pos()
            mouse_pressed = pygame.mouse.get_pressed()

            yes_button.handle_event(event, mouse_pos, mouse_pressed)
            no_button.handle_event(event, mouse_pos, mouse_pressed)

        if result["choice"] == "yes":
            if is_jf_mode.value == 0: # switching from larvae to jf
                is_jf_mode.value = 1
                step_size.value = CONSTANTS['JellyStepSizeManual']
                x_pos.value = int(x_pos.value * CONSTANTS['JFStepPerRev'] / CONSTANTS['LStepPerRev'])
                y_pos.value = int(y_pos.value * CONSTANTS['JFStepPerRev'] / CONSTANTS['LStepPerRev'])
                log(f"Final Pos: X: {x_pos.value}, Y: {y_pos.value}",log_queue)
                return None
            elif is_jf_mode.value == 1: # switching from jf to larvae
                is_jf_mode.value = 0
                step_size.value = CONSTANTS['LarvaeStepSizeManual']
                x_pos.value = int(x_pos.value / CONSTANTS['JFStepPerRev'] * CONSTANTS['LStepPerRev'])
                y_pos.value = int(y_pos.value / CONSTANTS['JFStepPerRev'] * CONSTANTS['LStepPerRev'])
                log(f"Final Pos: X: {x_pos.value}, Y: {y_pos.value}",log_queue)
                # NEED TO TURN ON TANK BOUNDARY / DON'T LET IT TURN ON IF NOT INSIDE THE TANK BOUNDARY
                # MAKE THIS ONLY WORK IF ALREADY INSIDE THE CORRECT BOUNDARY FOR LARVAE
                return None
            else: 
                log("Mode is incorrect value, please close program and reset to 0 (larvae) or 1 (jellyfish)",log_queue)
        elif result["choice"] == "no":
            if is_jf_mode.value == 0: # switching from larvae to jf
                log("Maintaining larvae mode as not all steps required to switch to jellyfish mode fulfilled.",log_queue)
                return None
            elif is_jf_mode.value == 1: # switching from jf to larvae
                log("Maintaining jellyfish mode as not all steps required to switch to jellyfish mode fulfilled.",log_queue)
                return None
            else: 
                log("Mode is incorrect value, please close program and reset to 0 (larvae) or 1 (jellyfish)",log_queue)

         # Dim background
        dim_overlay = pygame.Surface((window_width, window_height), pygame.SRCALPHA)
        dim_overlay.fill((0, 0, 0, 180))  # semi-transparent black
        window.blit(dim_overlay, (0, 0))

        # Draw popup box
        pygame.draw.rect(window, (50, 50, 50), popup_rect, border_radius=10)
        pygame.draw.rect(window, (200, 200, 200), popup_rect, 2, border_radius=10)

        # Draw text
        line_height = font.get_height() + 5
        for i, line in enumerate(msg_lines):
            text_surf = font.render(line, True, (255, 255, 255))
            text_rect = text_surf.get_rect(topleft=(popup_rect.left + 100, popup_rect.top + 20 + i * line_height))
            window.blit(text_surf, text_rect)

        # Draw buttons
        yes_button.draw(window)
        no_button.draw(window)

        pygame.display.flip()
        clock.tick(30)
    return None
