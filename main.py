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
from Utils.CONSTANTS import CONSTANTS
import queue
import json

def get_x_y():
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
        print(f"Error reading {file_path}: {e}")
        x_pos, y_pos = 0,0
        print("Home immediately, coordinates loaded incorrectly")
    print(f"Initial coords: X: {x_pos}, Y: {y_pos} [steps]")
    return x_pos,y_pos,file_path

def get_mode():
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
                print(f"Mode initially loaded as: {JellyTrackingFunctions.mode_string(mode)}")
            else:
                print("Incorrect formatting in the saved mode file, edit it and restart")
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        mode = multiprocessing.Value('i', 1)
        print("Assuming jellyfish mode. If incorrect microscope position, restart and edit jf_or_larvae_mode.txt file") 
    return mode, file_path

def wait_for_errorcheck_completion(ser,is_jf_mode):
    print("Waiting for error check to complete...")
    x_error_steps, y_error_steps = None, None
    x_error_mm, y_error_mm = None, None
    while True:
        if ser.in_waiting > 0:
            response = ser.readline().decode('utf-8').strip()
            print(f"Arduino: {response}")
            if "X Error in Motor Steps:" in response:
                x_error_steps = int(response.split(":")[1].strip())
            if "Y Error in Motor Steps:" in response:
                y_error_steps = int(response.split(":")[1].strip())
            if response == "Error check complete.":
                x_error_mm = JellyTrackingFunctions.steps_to_mm(x_error_steps,is_jf_mode)
                y_error_mm = JellyTrackingFunctions.steps_to_mm(y_error_steps,is_jf_mode)
                print(f"X Error [mm]: {x_error_mm}, Y Error [mm]: {y_error_mm}")
                print("*****Homing and Error check complete.*****")
                break
        else:
            time.sleep(0.1)

def serial_process(command_queue,homing_error_button,terminate_event,is_jf_mode, x_invalid_flag, y_invalid_flag, x_pos, y_pos,verbose):
    try:
        with open("config.json") as f:
            config = json.load(f)
        COM_PORT = config.get("COM_PORT", "COM5") # COM5 default
        ser = serial.Serial(COM_PORT, 500000, timeout=5)
        time.sleep(3)
        print("Serial connection established.")
    except Exception as e:
        print(f"Serial connection failed: {e}")
        print(f"##########")
        print(f"If access denied, make sure no other program is using the arduino, close arduino IDE if open, and restart this program. Other option, unplug and replug in the arduino.")
        print(f"##########")
        terminate_event.set()  # Signal other processes to terminate
        return  # Exit this process

    while True:    
        # Validate that the new positions are within the valid range
        if is_jf_mode.value == 1:
            xmax, ymax = CONSTANTS['JFmaxes']
        else:
            xmax, ymax = CONSTANTS['Lmaxes']
        try:
            if ser.in_waiting > 0:
                response = ser.readline().decode('utf-8').strip()
                
                if verbose.value:
                    print(f"Arduino (Limit): {response}")

                if "X Min Hit" in response:
                    x_invalid_flag.value = 1
                    print(f"X Min switch hit. Resetting X pos to 0. Prior X: {x_pos.value}")
                    x_pos.value = 0
                elif "X Max Hit" in response:
                    x_invalid_flag.value = 2
                    print(f"X Max switch hit. Current X pos: {x_pos.value}, Max: {xmax}")
                    x_pos.value = xmax  # You can update this later with accurate max
                elif "X Min Clear" in response or "X Max Clear" in response:
                    x_invalid_flag.value = 0

                if "Y Min Hit" in response:
                    y_invalid_flag.value = 1
                    print(f"Y Min switch hit. Resetting Y pos to 0. Prior Y: {y_pos.value}")
                    y_pos.value = 0
                elif "Y Max Hit" in response:
                    y_invalid_flag.value = 2
                    print(f"Y Max switch hit. Current Y pos: {y_pos.value}, Max: {ymax}")
                    y_pos.value = ymax
                elif "Y Min Clear" in response or "Y Max Clear" in response:
                    y_invalid_flag.value = 0

            try:
                command = command_queue.get(timeout=0.01)  # Wait only briefly
            except queue.Empty:
                continue  # No command yet, go back to top of loop

            if command.startswith('ERRORCHECK'):
                ser.write(command.encode())
                wait_for_errorcheck_completion(ser, is_jf_mode)
                homing_error_button.value = 0
                x_pos.value, y_pos.value = 0, 0
                continue

            if command == "EXIT":
                endcommand = "XVERBOSEFALSE"
                ser.write(endcommand.encode())
                print("Closing serial connection.")
                break

            ser.write(command.encode())

        except Exception as e:
            print(f"Error in serial_process: {e}")

    ser.close()

def timer_process(elapsed_time, reset_timer, running):
    time.sleep(3)
    start = time.time()
    while running.value:
        if reset_timer.value:
            start = time.time()
            reset_timer.value = False
        elapsed_time.value = time.time() - start
        time.sleep(0.1)  # update every 0.1 second

if __name__ == "__main__":
    x_pos, y_pos, file_path_xy = get_x_y()
    is_jf_mode, file_path_mode = get_mode()
    if is_jf_mode.value == 1:
        step_size = multiprocessing.Value('i', CONSTANTS['JellyStepSizeManual'])
    elif is_jf_mode.value == 0:
        step_size = multiprocessing.Value('i', CONSTANTS['LarvaeStepSizeManual'])
    step_to_mm_checking = multiprocessing.Value('i',0)
    x_pos = multiprocessing.Value('i', x_pos)
    y_pos = multiprocessing.Value('i', y_pos)
    command_queue = multiprocessing.Queue()
    homing_error_button = multiprocessing.Value('i', 0)  
    keybinds_flag = multiprocessing.Value('b', True)  # 'b' for boolean type
    pixelsCal_flag = multiprocessing.Value('i', 0) # integer, starting at 0
    terminate_event = multiprocessing.Event()
    running_flag = multiprocessing.Value('b', True)  # 'b' for boolean type
    x_invalid_flag = multiprocessing.Value('i', 0)
    y_invalid_flag = multiprocessing.Value('i', 0)
    verbose = multiprocessing.Value('b', False)
    testingMode = multiprocessing.Value('b',False)
    recording = multiprocessing.Value('b',False)
    tracking = multiprocessing.Value('b',False)
    motors = multiprocessing.Value('b',False)
    elapsed_time = multiprocessing.Value('d', 0.0)  # shared float
    reset_timer = multiprocessing.Value('b',False)

    serial_proc = multiprocessing.Process(target=serial_process,args=(command_queue,homing_error_button,terminate_event,is_jf_mode, x_invalid_flag, y_invalid_flag, x_pos, y_pos,verbose))
    serial_proc.start()
    motor_process = multiprocessing.Process(target=run_motor_input, args=(x_pos, y_pos, file_path_xy, command_queue,keybinds_flag,pixelsCal_flag,is_jf_mode,file_path_mode,terminate_event,running_flag, step_size,homing_error_button,x_invalid_flag, y_invalid_flag,testingMode,verbose))
    live_stream_process = multiprocessing.Process(target=run_live_stream_record, args=(x_pos, y_pos, command_queue,keybinds_flag,pixelsCal_flag,is_jf_mode, terminate_event, running_flag, step_size,step_to_mm_checking,homing_error_button,x_invalid_flag, y_invalid_flag,verbose,testingMode,recording, tracking,motors,elapsed_time,reset_timer))
    timer = multiprocessing.Process(target=timer_process, args=(elapsed_time, reset_timer, running_flag))
    timer.start()

    if terminate_event.is_set():
        sys.exit(0)  
    motor_process.start()
    live_stream_process.start()
    print("Arrow keys on keyboard to move camera")

    motor_process.join()
    live_stream_process.join()
    timer.join()

    command_queue.put("EXIT")
    serial_proc.join()
    print("File complete.")