import pygame # type: ignore
import os
from Utils.Button import Button
import time
pygame.init()
from Utils.CONSTANTS import CONSTANTS
from Utils.ButtonPresses import homingStepsWithErrorCheck
from Utils.moveFunctions import autoMove

vertical = os.path.exists(r"C:\Users\weiss\Desktop\JT101\Utils\vertical.txt")

def changeModePopUp(is_jf_mode,x_pos,y_pos,step_size, window, font, homing_error_button, command_queue, x_invalid_flag, y_invalid_flag, changeModeFlag,xy_LHpos,LH_flag):
    
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
    phase = "ready"  # new: start in ready phase
    
    if is_jf_mode.value == 0: # switching from larvae to jf
        ready_msg_lines = [
        "Steps to switch from larvae mode to jellyfish mode (manually):",
        "1. Move the microscope so it is all the way down on the gantry.",
        "2. Refocus the microscope as needed or afterwards. ",
        "3. Switch the motor controller switches on both motors so switches 1,2,4,5 are on (3 and 6 off).",
        "This gives 2000 steps/revolution.",
        "4. Prepare boundary inside tank for jellyfish.",
        "Once these steps are completed click yes."
        ]
        msg = (
            "Now, guarantee the microscope is low enough, then homing will commence.\n"
            "It will automatically complete if yes selected.\n"
            )
        final_msg = [
            "Click yes to complete mode change to jf.",
        ]
    elif is_jf_mode.value == 1: # switching from jf to larvae
        ready_msg_lines = [
        "Ready for the following steps to happen automatically?",
        "They will automatically complete if yes selected.",
        "- Home motors",
        "- Move to Larvae Home"
        ]
        msg = (
            "Now do the following steps manually:\n"
            "1. Move the microscope up on the platform to be the WD away from the glass.\n "
            "Use the 3d printed calibration piece (it's 0.407 inches thick, on the counter somewhere).\n"
            "2. Refocus microscope on corner border or other object.\n"
            "3. Switch the motor controller switches on both motors so switches 1,2,4,6 are on (3 and 5 off). \n"
            "This gives 12800 steps/revolution.\n"
            "4. Prepare boundary inside tank for larvae.\n"
        )
        final_msg = [
            "After clicking yes here, immediately manually move motors to",
            "site near larvae boundary, then click the button that says Set Larvae Home,",
            "to set the home location for this mode.",
            "Click yes to complete mode change to larve.",
            "If using vertical, just click set larvae home immediately to keep larvae home at 0 with the limit switch."
        ]
    else: 
        msg = (
            f"Mode incorrectly saved as: {is_jf_mode.value}.\n"
            "Please close program, edit Utils\\jf_or_larvae_mode.txt \n "
            "to be 0 (Meaning larvae) or 1 (meaning JF)"
        )

    # Split message into lines
    msg_lines = msg.split('\n')

    while running_popup:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None

            mouse_pos = pygame.mouse.get_pos()
            mouse_pressed = pygame.mouse.get_pressed()

            yes_button.handle_event(event, mouse_pos, mouse_pressed)
            no_button.handle_event(event, mouse_pos, mouse_pressed)

        if result["choice"] == "yes":
            if phase == "ready":
                if is_jf_mode.value == 0: # switching from larvae to jf
                    pass
                elif is_jf_mode.value == 1: # switching from jf to larvae
                    homingStepsWithErrorCheck(homing_error_button, is_jf_mode,command_queue,x_pos,y_pos, xy_LHpos,  x_invalid_flag, y_invalid_flag,LH_flag)
                    while homing_error_button.value == 1:
                        time.sleep(0.1)
                    if not vertical:
                        autoMove(x_pos,y_pos,CONSTANTS["LarvaeHome"],command_queue, is_jf_mode, x_invalid_flag, y_invalid_flag)
                else:
                    pass
                result["choice"] = None
                phase = "instructions"
            elif phase == "instructions":
                if is_jf_mode.value == 0: # switching from larvae to jf
                    is_jf_mode.value = 1
                    step_size.value = CONSTANTS['JellyStepSizeManual']
                    homingStepsWithErrorCheck(homing_error_button, is_jf_mode,command_queue,x_pos,y_pos, xy_LHpos,  x_invalid_flag, y_invalid_flag,LH_flag)
                elif is_jf_mode.value == 1: # switching from jf to larvae
                    is_jf_mode.value = 0
                    step_size.value = CONSTANTS['LarvaeStepSizeManual']
                    x_pos.value, y_pos.value = 0, 0
                else: 
                    print("Mode is incorrect value, please close program and reset to 0 (larvae) or 1 (jellyfish)")
                result["choice"] = None
                phase = "final"
            elif phase == "final":
                if is_jf_mode.value == 0:
                    changeModeFlag.value = True
                    return None
                elif is_jf_mode.value == 1:
                    return None
                else: 
                    print("Mode is incorrect value, please close program and reset to 0 (larvae) or 1 (jellyfish)")
        elif result["choice"] == "no":                
            if is_jf_mode.value == 0: # switching from larvae to jf
                print("Maintaining larvae mode as not all steps required to switch to jellyfish mode fulfilled.")
                return None
            elif is_jf_mode.value == 1: # switching from jf to larvae
                print("Maintaining jellyfish mode as not all steps required to switch to jellyfish mode fulfilled.")
                return None
            else: 
                print("Mode is incorrect value, please close program and reset to 0 (larvae) or 1 (jellyfish)")

         # Dim background
        dim_overlay = pygame.Surface((window_width, window_height), pygame.SRCALPHA)
        dim_overlay.fill((0, 0, 0, 180))  # semi-transparent black
        window.blit(dim_overlay, (0, 0))

        # Draw popup box
        pygame.draw.rect(window, (50, 50, 50), popup_rect, border_radius=10)
        pygame.draw.rect(window, (200, 200, 200), popup_rect, 2, border_radius=10)

        # Draw text
        if phase == 'ready':
            lines = ready_msg_lines
        elif phase == 'instructions':
            lines = msg_lines
        else:
            lines = final_msg
        
        line_height = font.get_height() + 5
        for i, line in enumerate(lines):
            text_surf = font.render(line, True, (255, 255, 255))
            text_rect = text_surf.get_rect(topleft=(popup_rect.left + 100, popup_rect.top + 20 + i * line_height))
            window.blit(text_surf, text_rect)

        # Draw buttons
        yes_button.draw(window)
        if phase != "final":
            no_button.draw(window)

        pygame.display.flip()
        clock.tick(30)
    return None
