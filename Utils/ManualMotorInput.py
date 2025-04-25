import keyboard # type: ignore
import time
import Utils.JellyTrackingFunctions as JellyTrackingFunctions
import os
from Utils.ButtonPresses import stepsCalibration, homingSteps, homingStepsWithErrorCheck,keyBindsControl
from Utils.CONTROLS import CONTROLS

JellyStepSize = 95
LarveaStepSize = 35
defaultStepSize = JellyStepSize
step_size = defaultStepSize
step_to_mm_checking = 0

steps_to_mm_ratio = JellyTrackingFunctions.STEPS_PER_MM

def move(x_pos, y_pos, x_direction, y_direction, command_queue):
        # Maximum range for both X and Y after home is set
        X_MAX = 214530
        Y_MAX = 210900

        # Calculate new positions
        new_x = x_pos.value + x_direction
        new_y = y_pos.value + y_direction
        
        # Validate that the new positions are within the valid range
        x_valid = 0 <= new_x <= X_MAX
        y_valid = 0 <= new_y <= Y_MAX
        
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

def run_motor_input(x_pos,y_pos,file_path,command_queue,homing_flag,keybinds_flag):
    global step_size, step_to_mm_checking, steps_to_mm_ratio

    # Main loop for reading input and controlling motors
    try:
        while True:
            x_dir, y_dir = 0, 0
            
            if keybinds_flag.value:
                # Check for arrow key inputs
                if keyboard.is_pressed('up'):
                    y_dir = step_size
                if keyboard.is_pressed('down'):
                    y_dir = -step_size
                if keyboard.is_pressed('left'):
                    x_dir = -step_size
                if keyboard.is_pressed('right'):
                    x_dir = step_size
                
                # Move if any direction is pressed
                if x_dir != 0 or y_dir != 0:
                    x_pos, y_pos = move(x_pos, y_pos, x_dir, y_dir, command_queue)
                    time.sleep(.013)  # Small delay to prevent rapid commands
                
                # Check for other key presses
                if keyboard.is_pressed(CONTROLS["homing"][0]):
                    homingSteps(command_queue,homing_flag,x_pos,y_pos)
                if keyboard.is_pressed(CONTROLS["error_check"][0]): # error checking process
                    homingStepsWithErrorCheck(command_queue,homing_flag,x_pos,y_pos)
                if keyboard.is_pressed(CONTROLS["steps_to_mm"][0]): # check step to mm conversion
                    step_size, step_to_mm_checking = stepsCalibration(step_size, step_to_mm_checking, x_pos, y_pos,steps_to_mm_ratio,defaultStepSize)
                if keyboard.is_pressed(CONTROLS["toggle_keybinds"][2]) and keyboard.is_pressed(CONTROLS["toggle_keybinds"][3]): # turn keybinds on off wiht &
                    keyBindsControl(keybinds_flag)
                if keyboard.is_pressed(CONTROLS["terminate"][0]): # Check for the termination key 't'
                    print("Termination key pressed. Stopping the program...")
                    break
            else:
                if keyboard.is_pressed(CONTROLS["toggle_keybinds"][2]) and keyboard.is_pressed(CONTROLS["toggle_keybinds"][3]):
                    keyBindsControl(keybinds_flag)

                    
    except KeyboardInterrupt:
        print("Program terminated by user")
        save_position(x_pos,y_pos,file_path)
        
    finally:
        save_position(x_pos,y_pos,file_path)
        print("Serial connection closed")