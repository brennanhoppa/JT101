import subprocess
import threading
import time
import tkinter as tk
import os

def run_main():
    subprocess.call(['python', 'C:\\Users\\JellyTracker\\Desktop\\JellyFishTrackingPC-main\\main.py'])

# Create splash window
root = tk.Tk()
root.title("Loading Jelly Tracker...")
root.geometry("600x150")
root.resizable(False, False)

# Center the window on screen
root.update_idletasks()
width = 600
height = 150
x = (root.winfo_screenwidth() // 2) - (width // 2)
y = (root.winfo_screenheight() // 2) - (height // 2)
root.geometry(f"{width}x{height}+{x}+{y}")

# Left-aligned label with indent
label_text = (
    "    Loading Jelly Tracker...\n"
    "    Please wait....\n"
    "    If it's been 15+ seconds, restart,\n"
    "    and if problem persists, use VS Code Terminal to debug."
)
label = tk.Label(root, text=label_text, font=("consolas", 12), anchor="w", justify="left")
label.pack(pady=20, fill='both', padx=20)

# Start main program in a thread
thread = threading.Thread(target=run_main)
thread.start()

def check_if_done():
    if os.path.exists("ready.txt"):
        root.destroy()
    elif not thread.is_alive():
        # main.py ended but didn't create ready.txt -> error
        label.config(text=(
            "    Failed to load Jelly Tracker.\n"
            "    Please run from VS Code Terminal to see error."
        ))
        # Optional: close splash after a few seconds
        root.after(5000, root.destroy)
    else:
        root.after(200, check_if_done)


root.after(500, check_if_done)

# Start splash loop
root.mainloop()
