import keyboard # type: ignore
import time, random
import Utils.JellyTrackingFunctions as JellyTrackingFunctions
from Utils.ButtonPresses import homingStepsWithErrorCheck
from Utils.CONSTANTS import CONSTANTS
from Utils.log import log
from Utils.moveFunctions import move

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

# for testing function
move_pattern = [
    (1000, 1000),
    (-1000, 1000),
    (-1000, -1000),
    (1000, -1000)
]
move_index = 0

def run_motor_input(x_pos,y_pos,file_path_xy,command_queue,keybinds_flag,pixelsCal_flag,is_jf_mode,file_path_mode,terminate_event,running_flag, step_size,homing_error_button,log_queue,x_invalid_flag, y_invalid_flag,testingMode,verbose):
    # Main loop for reading input and controlling motors
    global move_index, move_pattern
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

            if testingMode.value:
                
                # code for random movements - turned off for now
                xMove = random.randint(-100, 100)
                yMove = random.randint(-100, 100)

                # programmed movement
                # xMove, yMove = move_pattern[move_index]
                # move_index = (move_index + 1) % len(move_pattern)  # cycle back to start

                move(x_pos,y_pos,xMove,yMove,command_queue,is_jf_mode, log_queue, x_invalid_flag, y_invalid_flag)
                if verbose.value:
                    # log(f"Move (x,y) [steps]: ({xMove}, {yMove})",log_queue)
                    pass
                time.sleep(1)
                pass

            if running_flag.value == False:
                log('Stopping program.',log_queue)
                break                
            
    except KeyboardInterrupt:
        save_position(x_pos,y_pos,file_path_xy,log_queue)
        save_mode(is_jf_mode, file_path_mode,log_queue)
        log("Program terminated by user",log_queue)

    finally:
        save_position(x_pos,y_pos,file_path_xy,log_queue)
        save_mode(is_jf_mode, file_path_mode,log_queue)
        log("Serial connection closed",log_queue)
