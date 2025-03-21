import subprocess
import threading
import multiprocessing
import time
import os

from Utils.ManualMotorInput import run_motor_input
from Utils.LiveStreamRecord import run_live_stream_record

def get_x_y():
    x_pos, y_pos = None, None
    # File containing the position data
    script_dir = os.path.dirname(os.path.abspath(__file__))  # Directory of ManualMotorInput.py
    file_path = os.path.join(script_dir, "Utils","motor_location.txt")
    print('trying to open:', file_path)
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

if __name__ == "__main__":
    
    x_pos, y_pos,file_path = get_x_y()
    x_pos = multiprocessing.Value('i', x_pos)
    y_pos = multiprocessing.Value('i', y_pos)

    motor_process = multiprocessing.Process(target=run_motor_input, args=(x_pos, y_pos,file_path))
    live_stream_process = multiprocessing.Process(target=run_live_stream_record, args=(x_pos, y_pos))
    motor_process.start()
    live_stream_process.start()
    motor_process.join()
    live_stream_process.join()

    # # Create threads to run both scripts simultaneously
    # motor_thread = threading.Thread(target=run_motor_input)
    # live_stream_thread = threading.Thread(target=run_live_stream_record)

    # # Start both threads
    # motor_thread.start()
    # live_stream_thread.start()

    # # Join threads to wait for them to finish
    # motor_thread.join()
    # live_stream_thread.join()

    print("Both scripts have finished executing.")
