import cv2 #type: ignore
import numpy as np # type:ignore
import csv
import os
import time
from tkinter import Tk
from tkinter.filedialog import askopenfilename
import multiprocessing
from JellyTrackingFunctions import detect_jellyfish, steps_to_mm, pixels_to_mm, calculate_delta_Pixels

def process_video(video_path, is_jf_mode, verbose=multiprocessing.Value('b',False)):
    # Prepare CSV file
    video_folder = os.path.dirname(video_path)
    video_name = os.path.splitext(os.path.basename(video_path))[0]
    mode_str = "Jellyfish" if is_jf_mode.value == 1 else "Larvae"
    csv_file_path = os.path.join(video_folder, f"{video_name}_{mode_str}_tracking.csv")

    csv_writer = None
    with open(csv_file_path, "w", newline="") as tracking_data_file:
        csv_writer = csv.writer(tracking_data_file)
        csv_writer.writerow(["x_mm", "y_mm", "timestamp", "status", "flashlight_pos", "bbox"])

        # Open video
        cap = cv2.VideoCapture(video_path)
        frame_index = 0
        x_pos = 0
        y_pos = 0
        detect_light = False  # normal setting

        start_time = time.time()
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Ensure frame is RGB
            if frame.ndim == 2:
                frame = np.stack((frame,) * 3, axis=-1)
            elif frame.shape[2] != 3:
                frame = frame[:, :, :3]

            flashlight_pos, (x1, x2, y1, y2) = detect_jellyfish(frame, detect_light, is_jf_mode, verbose=verbose, trackingStartEnd=multiprocessing.Value('i',0))
            if frame_index % 100 == 0:
                print(f"Processing frame {frame_index} / {total_frames}")
            # timestamp based on frame number
            total_seconds = frame_index / fps
            hours, remainder = divmod(int(total_seconds), 3600)
            minutes, seconds = divmod(remainder, 60)
            timestamp = f'{hours:02}:{minutes:02}:{seconds:02}'

            if flashlight_pos:
                dx, dy = calculate_delta_Pixels(flashlight_pos, frame.shape[1]//2, frame.shape[0]//2)
                x = steps_to_mm(x_pos, is_jf_mode) - pixels_to_mm(dx, is_jf_mode)
                y = steps_to_mm(y_pos, is_jf_mode) + pixels_to_mm(dy, is_jf_mode)
                csv_writer.writerow([round(x,3), round(y,3), timestamp, 'SuccTrack', flashlight_pos, (x1,x2,y1,y2)])
            else:
                x = steps_to_mm(x_pos, is_jf_mode)
                y = steps_to_mm(y_pos, is_jf_mode)
                csv_writer.writerow([x, y, timestamp, 'FailTrackMotorPos', (x,y), (0,0,0,0)])

            frame_index += 1

        cap.release()
    print(f"Tracking complete. CSV saved to: {csv_file_path}")


if __name__ == "__main__":
    # Hide the main tkinter window
    Tk().withdraw()
    video_path = askopenfilename(title="Select video file", filetypes=[("Video files", "*.mp4;*.avi;*.mov")])
    if video_path:
        parent_folder = os.path.basename(os.path.dirname(video_path)).lower()
        if "jellyfish" in parent_folder:
            is_jf_mode = multiprocessing.Value('i', 1)
        elif "larvae" in parent_folder:
            is_jf_mode = multiprocessing.Value('i', 0)
        else:
            raise ValueError(f"Parent folder name must contain 'jellyfish' or 'larvae', got '{parent_folder}'")
        process_video(video_path, is_jf_mode)
    else:
        print("No video selected. Exiting.")
