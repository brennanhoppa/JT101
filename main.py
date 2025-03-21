import subprocess
import threading

from Utils.ManualMotorInput import run_motor_input
from Utils.LiveStreamRecord import run_live_stream_record

if __name__ == "__main__":
    # Create threads to run both scripts simultaneously
    motor_thread = threading.Thread(target=run_motor_input)
    live_stream_thread = threading.Thread(target=run_live_stream_record)

    # Start both threads
    motor_thread.start()
    live_stream_thread.start()

    # Join threads to wait for them to finish
    motor_thread.join()
    live_stream_thread.join()

    print("Both scripts have finished executing.")
