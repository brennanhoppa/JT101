import keyboard # type: ignore
import time
import Utils.JellyTrackingFunctions as JellyTrackingFunctions
from Utils.ButtonPresses import homingStepsWithErrorCheck
from Utils.CONSTANTS import CONSTANTS
from Utils.log import log

def move(x_pos, y_pos, x_direction, y_direction, command_queue, is_jf_mode, log_queue,x_invalid_flag, y_invalid_flag):       
        # Calculate new positions
        new_x = x_pos.value + x_direction
        new_y = y_pos.value + y_direction
        
        x_valid = True
        if x_invalid_flag.value == 1 and x_direction < 0:
            x_valid = False
        elif x_invalid_flag.value == 2 and x_direction > 0:
            x_valid = False
        y_valid = True
        if y_invalid_flag.value == 1 and y_direction < 0:
            y_valid = False
        elif y_invalid_flag.value == 2 and y_direction > 0:
            y_valid = False
        
        # x_valid = 0 <= new_x <= xmax
        # y_valid = 0 <= new_y <= ymax
        
        # Update positions and send movement commands
        if x_valid and x_direction != 0:
            x_pos.value = new_x
            command_queue.put(f'{"R" if x_direction > 0 else "L"}{abs(x_direction)}\n')
        if y_valid and y_direction != 0:
            y_pos.value = new_y
            command_queue.put(f'{"U" if y_direction > 0 else "D"}{abs(y_direction)}\n')
        
        return x_pos, y_pos

def save_position(x_pos, y_pos, file_path,log_queue):
    try:
        with open(file_path, "w") as file:
            file.write(f"{x_pos.value}, {y_pos.value}")
        log(f"Updated location saved: {x_pos.value}, {y_pos.value}",log_queue)
    except Exception as e:
        log(f"Error writing to {file_path}: {e}",log_queue)

def save_mode(mode, file_path,log_queue):
    try:
        with open(file_path, "w") as file:
            file.write(f"{mode.value} # 0 means larvae, 1 means jellyfish\n")
        log(f"Updated mode saved: {JellyTrackingFunctions.mode_string(mode)}",log_queue)
    except Exception as e:
        log(f"Error writing to {file_path}: {e}",log_queue)

def run_motor_input(x_pos,y_pos,file_path_xy,command_queue,homing_flag,keybinds_flag,pixelsCal_flag,is_jf_mode,file_path_mode,terminate_event,running_flag, step_size,homing_error_button,log_queue,x_invalid_flag, y_invalid_flag):
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
                        x_pos, y_pos = move(x_pos, y_pos, x_dir, y_dir, command_queue,is_jf_mode, log_queue, x_invalid_flag, y_invalid_flag)
                        time.sleep(.013)  # Small delay to prevent rapid commands
        
            if running_flag.value == False:
                log('Stopping program.',log_queue)
                break
            # GUI buttons pressed
            if homing_error_button.value == 1:
                homingStepsWithErrorCheck(is_jf_mode, command_queue,homing_flag,x_pos,y_pos, log_queue)
                homing_error_button.value = 0
            
    except KeyboardInterrupt:
        save_position(x_pos,y_pos,file_path_xy,log_queue)
        save_mode(is_jf_mode, file_path_mode,log_queue)
        log("Program terminated by user",log_queue)

    finally:
        save_position(x_pos,y_pos,file_path_xy,log_queue)
        save_mode(is_jf_mode, file_path_mode,log_queue)
        log("Serial connection closed",log_queue)
