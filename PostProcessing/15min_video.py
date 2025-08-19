import os
import tkinter as tk
from tkinter import filedialog
from moviepy import VideoFileClip # type: ignore

# Hide Tkinter root window
root = tk.Tk()
root.withdraw()

# Ask the user to select a video file
file_path = filedialog.askopenfilename(
    title="Select a Video",
    filetypes=[("Video Files", "*.mp4;*.avi;*.mov;*.mkv"), ("All Files", "*.*")]
)

if file_path:
    print("Selected:", file_path)

    video = VideoFileClip(file_path)

    # Choose duration: first 15 minutes (900 sec) or full length if shorter
    duration = min(900, video.duration)

    # Option 1: Using subclipped
    trimmed = video.subclipped(0, duration)

    # Option 2: Using slicing (alternative)
    # trimmed = video[0:duration]

    # Build output path
    folder, filename = os.path.split(file_path)
    name, _ = os.path.splitext(filename)
    output_path = os.path.join(folder, f"{name}_15min.mp4")

    trimmed.write_videofile(output_path, codec="libx264", audio_codec="aac")
    print("Saved trimmed video:", output_path)
else:
    print("No video selected")
