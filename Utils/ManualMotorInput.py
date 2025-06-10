import keyboard # type: ignore
import time
import Utils.JellyTrackingFunctions as JellyTrackingFunctions
import os
from Utils.ButtonPresses import stepsCalibration, homingSteps, homingStepsWithErrorCheck,keyBindsControl, change_mode
from Utils.CONTROLS import CONTROLS
from Utils.CONSTANTS import CONSTANTS

def move(x_pos, y_pos, x_direction, y_direction, command_queue, is_jf_mode):       
        # Calculate new positions
        new_x = x_pos.value + x_direction
        new_y = y_pos.value + y_direction
        
        # Validate that the new positions are within the valid range
        if is_jf_mode.value == 1:
            xmax, ymax = CONSTANTS['JFmaxes']
        else:
            xmax, ymax = CONSTANTS['Lmaxes']
        x_valid = 0 <= new_x <= xmax
        y_valid = 0 <= new_y <= ymax
        
        # Update positions and send movement commands
        if x_valid and x_direction != 0:
            x_pos.value = new_x
            # send_command(ser, f'{"R" if x_direction > 0 else "L"}{abs(x_direction)}')
            command_queue.put(f'{"R" if x_direction > 0 else "L"}{abs(x_direction)}\n')
        if y_valid and y_direction != 0:
            y_pos.value = new_y
            # send_command(ser, f'{"U" if y_direction > 0 else "D"}{abs(y_direction)}')
            command_queue.put(f'{"U" if y_direction > 0 else "D"}{abs(y_direction)}\n')
        # Print current position or axis limit warnings
        if x_valid and y_valid:
            # print(f"Current position: X={JellyTrackingFunctions.steps_to_mm(x_pos,y_pos)}, Y={JellyTrackingFunctions.steps_to_mm(x_pos,y_pos)}")
            # print(f"Position: X={x_pos.value}, Y={y_pos.value}")
            pass
        else:
            if not x_valid:
                print(f"X axis limit reached. Current position: X={x_pos.value}, Y={y_pos.value}")
            if not y_valid:
                print(f"Y axis limit reached. Current position: X={x_pos.value}, Y={y_pos.value}")
        return x_pos, y_pos

def save_position(x_pos, y_pos, file_path):
    try:
        with open(file_path, "w") as file:
            file.write(f"{x_pos.value}, {y_pos.value}")
        print(f"Updated location saved: {x_pos.value}, {y_pos.value}")
    except Exception as e:
        print(f"Error writing to {file_path}: {e}")

def save_mode(mode, file_path):
    try:
        with open(file_path, "w") as file:
            file.write(f"{mode.value} # 0 means larvae, 1 means jellyfish\n")
        print(f"Updated mode saved: {JellyTrackingFunctions.mode_string(mode)}")
    except Exception as e:
        print(f"Error writing to {file_path}: {e}")

def run_motor_input(x_pos,y_pos,file_path_xy,command_queue,homing_flag,keybinds_flag,pixelsCal_flag,is_jf_mode,file_path_mode,terminate_event,running_flag, step_size,homing_button,homing_error_button):
    # Main loop for reading input and controlling motors
    try:
        while True:
            x_dir, y_dir = 0, 0
            
            if keybinds_flag.value:
                # Check for arrow key inputs
                if pixelsCal_flag.value == 0 or pixelsCal_flag.value == 1:
                    if keyboard.is_pressed('up'):
                        y_dir = step_size.value
                    if keyboard.is_pressed('down'):
                        y_dir = -step_size.value
                    if keyboard.is_pressed('left'):
                        x_dir = -step_size.value
                    if keyboard.is_pressed('right'):
                        x_dir = step_size.value
                
                    # Move if any direction is pressed
                    if x_dir != 0 or y_dir != 0:
                        x_pos, y_pos = move(x_pos, y_pos, x_dir, y_dir, command_queue,is_jf_mode)
                        time.sleep(.013)  # Small delay to prevent rapid commands
        
            if running_flag.value == False:
                print('Stopping program.')
                break
            # GUI buttons pressed
            if homing_button.value == 1:
                homingSteps(is_jf_mode, command_queue,homing_flag,x_pos,y_pos)
                homing_button.value = 0
            if homing_error_button.value == 1:
                homingStepsWithErrorCheck(is_jf_mode, command_queue,homing_flag,x_pos,y_pos)
                homing_error_button.value = 0
            
    except KeyboardInterrupt:
        save_position(x_pos,y_pos,file_path_xy)
        save_mode(is_jf_mode, file_path_mode)
        print("Program terminated by user")
        
    finally:
        save_position(x_pos,y_pos,file_path_xy)
        save_mode(is_jf_mode, file_path_mode)
        print("Serial connection closed")