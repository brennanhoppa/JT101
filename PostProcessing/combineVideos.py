import os
import tkinter as tk
from tkinter import filedialog
import subprocess
import re
from pathlib import Path

def numerical_sort(value):
    """Sort filenames containing numbers in correct order."""
    numbers = re.findall(r'\d+', value)
    return int(numbers[0]) if numbers else -1

def main():
    # Hide the main Tkinter window
    root = tk.Tk()
    root.withdraw()

    script_path = Path(__file__).resolve()
    script_parent = script_path.parent
    project_root = script_parent.parent

    # Open folder picker
    folder = filedialog.askdirectory(
        title="Select folder with video segments",
        initialdir=project_root / "saved_runs"
    )
    if not folder:
        print("No folder selected. Exiting.")
        return

    # Get all .mp4 files (just filenames)
    mp4_files = [f for f in os.listdir(folder) if f.lower().endswith(".mp4")]
    if not mp4_files:
        print("No MP4 files found in the folder.")
        return

    if len(mp4_files) == 1:
        print("Only one video found. Nothing to combine.")
        os.startfile(folder)
        return


    # Sort files numerically
    mp4_files.sort(key=numerical_sort)

    # Write the concat list (relative paths)
    list_file_path = os.path.join(folder, "segments.txt").replace("\\", "/")
    with open(list_file_path, "w") as f:
        for seg in mp4_files:
            f.write(f"file '{seg}'\n")

    # Final output filename
    output_file = os.path.join(folder, "video.mp4").replace("\\", "/")

    # Run FFmpeg concat demuxer (lossless)
    cmd = [
        "ffmpeg",
        "-f", "concat",
        "-safe", "0",
        "-i", list_file_path,
        "-c", "copy",
        output_file
    ]

    print("Combining segments...")
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        print("FFmpeg failed. Make sure all segment files are valid and have the same codec/parameters.")
        return

    print(f"Final video saved as: {output_file}")

    # Delete segments and temporary list file
    for seg in mp4_files:
        os.remove(os.path.join(folder, seg))
    os.remove(list_file_path)
    print("Original segments deleted.")
    os.startfile(folder)


if __name__ == "__main__":
    main()
