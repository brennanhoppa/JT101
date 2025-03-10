import subprocess
import threading

# Function to run ManualMotorInput.py
def run_motor_input():
    subprocess.run(["python", "Utils/ManualMotorInput.py"])

# Function to run LiveStreamRecord.py
def run_live_stream_record():
    subprocess.run(["python", "Utils/LiveStreamRecord.py"])

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
