import os
from datetime import datetime

log_file_path = os.path.join(os.path.dirname(__file__), "log.txt")
with open(log_file_path, "w", encoding="utf-8") as f:
    f.write("")  # Just truncate the file

def log(msg, queue):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {msg}"

    # Send the timestamped message to the queue
    queue.put(msg)
    
    # Append the timestamped message to the log file
    with open(log_file_path, "a", encoding="utf-8") as f:
        f.write(log_entry + "\n")