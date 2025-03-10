import serial
import time
import random
import threading

# Set up the serial connection to the Arduino
try:
    ser = serial.Serial('COM5', 500000, timeout=1, write_timeout=1)
    time.sleep(2)  # Give the connection a moment to set up
except serial.SerialException as e:
    print(f"Error opening serial port: {e}")
    exit(1)

# Current position (initially set as home)
x_pos, y_pos = 0, 0

# Maximum range for both X and Y
X_MAX = Y_MAX = 678000

# Track number of moves
move_count = 0

# Constant speed and acceleration
SPEED = 10000
ACCELERATION = 5000

# Function to send a command to the Arduino
def send_command(command):
    try:
        ser.write((command + '\n').encode())
        ser.flush()  # Ensure the command is sent immediately
        print(f"Sent command: {command}")
    except serial.SerialTimeoutException:
        print(f"Timeout sending command: {command}")
    except serial.SerialException as e:
        print(f"Error sending command: {e}")

# Function to move the stepper motors based on direction input
def move(x_direction, y_direction):
    global x_pos, y_pos, move_count
    
    new_x = x_pos + x_direction
    new_y = y_pos + y_direction
    
    # Check if the new positions are within valid bounds
    x_valid = 0 <= new_x <= X_MAX
    y_valid = 0 <= new_y <= Y_MAX
    
    # Move X if within bounds
    if x_valid and x_direction != 0:
        x_pos = new_x
        send_command(f'{"R" if x_direction > 0 else "L"}{abs(x_direction)}')
    
    # Move Y if within bounds
    if y_valid and y_direction != 0:
        y_pos = new_y
        send_command(f'{"U" if y_direction > 0 else "D"}{abs(y_direction)}')
    
    move_count += 1
    print(f"Current position: X={x_pos}, Y={y_pos}, Moves made: {move_count}")

    # Return to home after 1000 moves
    if move_count >= 1000:
        return_to_zero()

# Function to return to home position (0, 0)
def return_to_zero():
    global x_pos, y_pos, move_count
    
    print("Returning to home position (0, 0)...")
    
    # Move X axis to home (0)
    while x_pos != 0:
        time.sleep(.02) 
        steps = min(abs(x_pos), 95)  # Use smaller steps for precision
        direction = 'L' if x_pos > 0 else 'R'
        send_command(f'{direction}{steps}')
        x_pos -= steps if x_pos > 0 else -steps
    
    # Move Y axis to home (0)
    while y_pos != 0:
        time.sleep(.02) 
        steps = min(abs(y_pos), 95)  # Use smaller steps for precision
        direction = 'D' if y_pos > 0 else 'U'
        send_command(f'{direction}{steps}')
        y_pos -= steps if y_pos > 0 else -steps

    move_count = 0  # Reset move counter after returning to home
    print("Returned to home position (0, 0)")

# Function to generate random movements
def random_move():
    while True:
        try:
            x_dir = random.choice([0, 1]) * random.randint(1, 95)
            y_dir = random.choice([0, 1]) * random.randint(1, 95)
            
            if x_dir != 0 or y_dir != 0:
                move(x_dir, y_dir)
            
            time.sleep(.013)  # Delay between movements
        except Exception as e:
            print(f"Error in random move: {e}")
            time.sleep(5)

# Set initial speed and acceleration
send_command(f'S{SPEED}')
send_command(f'A{ACCELERATION}')
print(f"Set initial speed to {SPEED} and acceleration to {ACCELERATION}")

# Start the random movement thread
move_thread = threading.Thread(target=random_move, daemon=True)
move_thread.start()

print("Random Stepper Motor Control Started")
print("Press Ctrl+C to quit")

try:
    while True:
        time.sleep(1)  # Keep the main thread alive

except KeyboardInterrupt:
    print("Program terminated")

finally:
    ser.close()
    print("Serial connection closed")