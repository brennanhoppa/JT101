import serial # type: ignore
import keyboard # type: ignore
import time
import Utils.JellyTrackingFunctions as JellyTrackingFunctions
import os

# Function to send a command to the Arduino and read feedback
def send_command(ser, command):
    ser.write((command + '\n').encode())
    print(f"Sent command: {command}")

def move(ser, x_pos, y_pos, x_direction, y_direction):
        # Maximum range for both X and Y after home is set
        X_MAX = 212230
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
            send_command(ser, f'{"R" if x_direction > 0 else "L"}{abs(x_direction)}')
        if y_valid and y_direction != 0:
            y_pos.value = new_y
            send_command(ser, f'{"U" if y_direction > 0 else "D"}{abs(y_direction)}')
        
        # Print current position or axis limit warnings
        if x_valid and y_valid:
            # print(f"Current position: X={JellyTrackingFunctions.steps_to_mm(x_pos,y_pos)}, Y={JellyTrackingFunctions.steps_to_mm(x_pos,y_pos)}")
            print(f"Position: X={x_pos.value}, Y={y_pos.value}")
        else:
            if not x_valid:
                print(f"X axis limit reached. Current position: X={x_pos.value}, Y={y_pos.value}")
            if not y_valid:
                print(f"Y axis limit reached. Current position: X={x_pos.value}, Y={y_pos.value}")
        return x_pos, y_pos

# Function to wait for the Arduino to confirm that homing is complete
def wait_for_homing_completion(ser):
    print("Waiting for homing to complete...")
    while True:
        if ser.in_waiting > 0:
            response = ser.readline().decode('utf-8').strip()
            print(f"Arduino: {response}")
            if response == "Homing complete":
                print("Homing completed successfully.")
                break

def wait_for_errorcheck_completion(ser):
    print("Waiting for error check to complete...")
    x_error_steps, y_error_steps = None, None
    x_error_mm, y_error_mm = None, None
    while True:
        if ser.in_waiting > 0:
            response = ser.readline().decode('utf-8').strip()
            print(f"Arduino: {response}")
            if "X Error in Motor Steps:" in response:
                x_error_steps = int(response.split(":")[1].strip())
                print(f"X Error stored: {x_error_steps}")
            if "Y Error in Motor Steps:" in response:
                y_error_steps = int(response.split(":")[1].strip())
                print(f"Y Error stored: {y_error_steps}")
            if response == "Error check complete.":
                x_error_mm, y_error_mm = JellyTrackingFunctions.steps_to_mm(x_error_steps,y_error_steps)
                print(f"X Error [mm]: {x_error_mm}, Y Error [mm]: {y_error_mm}")
                print("Error check complete.")
                break


def save_position(x_pos, y_pos, file_path):
    try:
        with open(file_path, "w") as file:
            file.write(f"{x_pos.value}, {y_pos.value}")
        print(f"Updated location saved: {x_pos.value}, {y_pos.value}")
    except Exception as e:
        print(f"Error writing to {file_path}: {e}")

 # def move_to_z_position():
    #     global x_pos, y_pos
    #     if x_pos is None:
    #         x_pos = 0
    #     if y_pos is None:
    #         y_pos = 0
        
    #     print("Moving to Z position (X=0, Y=69350)...")
        
    #     # Move X axis to 0
    #     while x_pos != 0:
    #         time.sleep(.02)  # Small delay between steps
    #         steps = min(abs(x_pos), 95)  # Use smaller steps for precision
    #         direction = 'L' if x_pos > 0 else 'R'
    #         send_command(ser, f'{direction}{steps}')
    #         x_pos -= steps if x_pos > 0 else -steps  # Update current position
        
    #     # Move Y axis to 69350
    #     while y_pos != 69350:
    #         time.sleep(.02)  # Small delay between steps
    #         steps = min(abs(y_pos - 69350), 95)  # Use smaller steps for precision
    #         direction = 'U' if y_pos < 69350 else 'D'
    #         send_command(ser, f'{direction}{steps}')
    #         y_pos += steps if y_pos < 69350 else -steps  # Update current position

    #     print(f"Reached Z position: X={x_pos}, Y={y_pos}")

def run_motor_input(x_pos,y_pos,file_path):
    
    # Set up the serial connection to the Arduino
    ser = serial.Serial('COM5', 500000, timeout=5)  
    time.sleep(.5)  # Give the connection a moment to set up

    # Flag to check if home has been set
    home_set = False

    # Inform user of controls
    print("Arrow keys to move")
    print("Press 'h' to start the homing process")
    # print("Press 'z' to move to Z position")
    print("Press 't' to terminate the program")
    print("Press 'e' to check the current error and home")


    # Main loop for reading input and controlling motors
    try:
        while True:
            x_dir, y_dir = 0, 0
            step_size = 95  # Default step size
            
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
                x_pos, y_pos = move(ser, x_pos, y_pos, x_dir, y_dir)
                time.sleep(.013)  # Small delay to prevent rapid commands
            
            # Check for other key presses
            if keyboard.is_pressed('h'):
                send_command(ser, 'HOMING')  # Start the homing process
                print("Homing process started...")
                wait_for_homing_completion(ser)  # Wait for the homing to complete
                home_set = True  # Home is set after homing process
                x_pos.value, y_pos.value = 0, 0
                print("Set Tank Home by moving camera to bottom left of tank, then press 'g'.")
            if keyboard.is_pressed('e'): # error checking process
                send_command(ser, f'ERRORCHECK_{x_pos}_{y_pos}')
                print("Error process starting...")
                wait_for_errorcheck_completion(ser)
                home_set = True  # Home is set after error checking process too
                x_pos.value, y_pos.value = 0, 0
                print("Error Check Completed.")

            # elif keyboard.is_pressed('g') and home_set:
            #     print(f"Current position: X={x_pos}, Y={y_pos}")
                
            # elif keyboard.is_pressed('z'):
            #     if home_set:
            #         move_to_z_position()  # Call the function to move to Z position
            #     else:
            #         print("Error: Home not set. Unable to move to Z position.")
            
            # Check for the termination key 't'
            if keyboard.is_pressed('t'):
                print("Termination key pressed. Stopping the program...")
                break

    except KeyboardInterrupt:
        print("Program terminated by user")
        save_position(x_pos,y_pos,file_path)
        
    finally:
        ser.close()
        save_position(x_pos,y_pos,file_path)
        print("Serial connection closed")
