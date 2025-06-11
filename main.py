import subprocess
import threading
import multiprocessing
import time
import os
import serial # type: ignore
import time
import sys
import logging
logging.getLogger('matplotlib').setLevel(logging.ERROR)
import Utils.JellyTrackingFunctions as JellyTrackingFunctions
from Utils.ManualMotorInput import run_motor_input
from Utils.LiveStreamRecord import run_live_stream_record
from Utils.CONTROLS import CONTROLS
from Utils.CONSTANTS import CONSTANTS
from Utils.log import log
log_queue = multiprocessing.Queue()

def get_x_y(log_queue):
    x_pos, y_pos = None, None
    # File containing the position data
    script_dir = os.path.dirname(os.path.abspath(__file__))  
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
        log(f"Error reading {file_path}: {e}",log_queue)
        x_pos, y_pos = 0,0
        log("Home immediately, coordinates loaded incorrectly",log_queue)
    log(f"Initial coords: X: {x_pos}, Y: {y_pos} [steps]",log_queue)
    return x_pos,y_pos,file_path

def get_mode(log_queue):
    mode = 0 # just to initialize
    # File containing the position data
    script_dir = os.path.dirname(os.path.abspath(__file__))  
    file_path = os.path.join(script_dir, "Utils","jf_or_larvae_mode.txt")
    try:
        with open(file_path, "r") as file:
            line = file.readline().strip()
            label = int(line.split()[0])  # Get the first token and convert to int
            if label == 0 or label == 1:
                mode = multiprocessing.Value('i', label)
                log(f"Mode initially loaded as: {JellyTrackingFunctions.mode_string(mode)}",log_queue)
            else:
                log("Incorrect formatting in the saved mode file, edit it and restart",log_queue)
    except (FileNotFoundError, ValueError) as e:
        log(f"Error reading {file_path}: {e}",log_queue)
        mode = multiprocessing.Value('i', 1)
        log("Assuming jellyfish mode. If incorrect microscope position, restart and edit jf_or_larvae_mode.txt file",log_queue) 
    return mode, file_path

# Function to wait for the Arduino to confirm that homing is complete
def wait_for_homing_completion(ser, log_queue):
    log("Waiting for homing to complete...",log_queue)
    while True:
        if ser.in_waiting > 0:
            response = ser.readline().decode('utf-8').strip()
            log(f"Arduino: {response}",log_queue)
            if response == "Homing complete":
                log("Homing completed successfully.",log_queue)
                break
        else:
            time.sleep(0.1)

def wait_for_errorcheck_completion(ser,is_jf_mode, log_queue):
    log("Waiting for error check to complete...",log_queue)
    x_error_steps, y_error_steps = None, None
    x_error_mm, y_error_mm = None, None
    while True:
        if ser.in_waiting > 0:
            response = ser.readline().decode('utf-8').strip()
            log(f"Arduino: {response}",log_queue)
            if "X Error in Motor Steps:" in response:
                x_error_steps = int(response.split(":")[1].strip())
                log(f"X Error stored: {x_error_steps}",log_queue)
            if "Y Error in Motor Steps:" in response:
                y_error_steps = int(response.split(":")[1].strip())
                log(f"Y Error stored: {y_error_steps}",log_queue)
            if response == "Error check complete.":
                x_error_mm = JellyTrackingFunctions.steps_to_mm(x_error_steps,is_jf_mode)
                y_error_mm = JellyTrackingFunctions.steps_to_mm(y_error_steps,is_jf_mode)
                log(f"X Error [mm]: {x_error_mm}, Y Error [mm]: {y_error_mm}",log_queue)
                log("Error check complete.",log_queue)
                break
        else:
            time.sleep(0.1)

def serial_process(command_queue,homing_flag,terminate_event,is_jf_mode, log_queue):
    try:
        ser = serial.Serial('COM5', 500000, timeout=5)
        time.sleep(0.5)
        log("Serial connection established.",log_queue)
    except Exception as e:
        log(f"Serial connection failed: {e}",log_queue)
        terminate_event.set()  # Signal other processes to terminate
        return  # Exit this process

    while True:    
        command = command_queue.get()
        
        if command == 'HOMING\n':
            ser.write(command.encode())  # Send command
            wait_for_homing_completion(ser, log_queue)
            homing_flag.value = False
            continue
        if command.startswith('ERRORCHECK'):
            ser.write(command.encode())
            wait_for_errorcheck_completion(ser,is_jf_mode, log_queue)
            homing_flag.value = False
            continue
        if command == "EXIT":
            log("Closing serial connection.",log_queue)
            break
        ser.write(command.encode())  # Send command
    ser.close()

if __name__ == "__main__":
    x_pos, y_pos, file_path_xy = get_x_y(log_queue)
    is_jf_mode, file_path_mode = get_mode(log_queue)
    if is_jf_mode.value == 1:
        step_size = multiprocessing.Value('i', CONSTANTS['JellyStepSizeManual'])
    elif is_jf_mode.value == 0:
        step_size = multiprocessing.Value('i', CONSTANTS['LarvaeStepSizeManual'])
    step_to_mm_checking = multiprocessing.Value('i',0)
    x_pos = multiprocessing.Value('i', x_pos)
    y_pos = multiprocessing.Value('i', y_pos)
    command_queue = multiprocessing.Queue()
    homing_flag = multiprocessing.Value('b', False)  # 'b' for boolean type
    homing_button = multiprocessing.Value('i', 0)  
    homing_error_button = multiprocessing.Value('i', 0)  
    keybinds_flag = multiprocessing.Value('b', True)  # 'b' for boolean type
    pixelsCal_flag = multiprocessing.Value('i', 0) # integer, starting at 0
    terminate_event = multiprocessing.Event()
    running_flag = multiprocessing.Value('b', True)  # 'b' for boolean type

    serial_proc = multiprocessing.Process(target=serial_process,args=(command_queue,homing_flag,terminate_event,is_jf_mode, log_queue))
    serial_proc.start()
    motor_process = multiprocessing.Process(target=run_motor_input, args=(x_pos, y_pos, file_path_xy, command_queue,homing_flag,keybinds_flag,pixelsCal_flag,is_jf_mode,file_path_mode,terminate_event,running_flag, step_size, homing_button,homing_error_button,log_queue))
    live_stream_process = multiprocessing.Process(target=run_live_stream_record, args=(x_pos, y_pos, command_queue,homing_flag,keybinds_flag,pixelsCal_flag,is_jf_mode, terminate_event, running_flag, step_size,step_to_mm_checking,homing_button,homing_error_button,log_queue))
    
    time.sleep(3) # wait for serial connection happen
    if terminate_event.is_set():
        sys.exit(0)  
    motor_process.start()
    live_stream_process.start()
    log("Arrow keys on keyboard to move camera",log_queue)

    motor_process.join()
    live_stream_process.join()

    command_queue.put("EXIT")
    serial_proc.join()

    print("Both scripts have finished executing.")
