import subprocess
import threading
import multiprocessing
import time
import os
import serial # type: ignore
import time
import logging
logging.getLogger('matplotlib').setLevel(logging.ERROR)
import Utils.JellyTrackingFunctions as JellyTrackingFunctions
from Utils.ManualMotorInput import run_motor_input
from Utils.LiveStreamRecord import run_live_stream_record

def get_x_y():
    x_pos, y_pos = None, None
    # File containing the position data
    script_dir = os.path.dirname(os.path.abspath(__file__))  # Directory of ManualMotorInput.py
    file_path = os.path.join(script_dir, "Utils","motor_location.txt")
    try:
        with open(file_path, "r") as file:
            content = file.read().strip()
            parts = content.split(",")
            
            if len(parts) == 2:
                x_pos, y_pos = map(str.strip, parts)  # Remove any extra spaces
                x_pos, y_pos = int(x_pos), int(y_pos)  # Convert to integers
            else:
                raise ValueError("Incorrect formatting")

    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        x_pos, y_pos = 0,0
        print("Home first, coordinates loaded incorrectly")
    print(f"x_pos: {x_pos}, y_pos: {y_pos}")
    return x_pos,y_pos,file_path

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
        else:
            time.sleep(0.1)

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
        else:
            time.sleep(0.1)

def serial_process(command_queue,homing_flag):
    ser = serial.Serial('COM5', 500000, timeout=5)  
    time.sleep(0.5)
    print("Serial connection established.")

    while True:    
        command = command_queue.get()
        
        if command == 'HOMING\n':
            ser.write(command.encode())  # Send command
            print(f"Sent command: {command}")
            wait_for_homing_completion(ser)
            homing_flag.value = False
            continue
        if command.startswith('ERRORCHECK'):
            ser.write(command.encode())
            print(f"Sent command: {command}")
            wait_for_errorcheck_completion(ser)
            homing_flag.value = False
            continue
        if command == "EXIT":
            print("Closing serial connection.")
            break
        ser.write(command.encode())  # Send command
        print(f"Sent command: {command.rstrip()}")

    ser.close()

if __name__ == "__main__":
    
    x_pos, y_pos,file_path = get_x_y()
    x_pos = multiprocessing.Value('i', x_pos)
    y_pos = multiprocessing.Value('i', y_pos)
    command_queue = multiprocessing.Queue()
    homing_flag = multiprocessing.Value('b', False)  # 'b' for boolean type

    serial_proc = multiprocessing.Process(target=serial_process,args=(command_queue,homing_flag))
    serial_proc.start()

    motor_process = multiprocessing.Process(target=run_motor_input, args=(x_pos, y_pos, file_path, command_queue,homing_flag))
    live_stream_process = multiprocessing.Process(target=run_live_stream_record, args=(x_pos, y_pos, command_queue,homing_flag))
    motor_process.start()
    live_stream_process.start()
    motor_process.join()
    live_stream_process.join()

    command_queue.put("EXIT")
    serial_proc.join()

    print("Both scripts have finished executing.")
