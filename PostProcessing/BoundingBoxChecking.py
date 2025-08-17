import pygame
import cv2
import csv
import tkinter as tk
from tkinter import filedialog

def timestamp_to_seconds(tstr):
    h, m, s = map(int, tstr.split(':'))
    return h*3600 + m*60 + s

# Hide the root Tk window
root = tk.Tk()
root.withdraw()

# Ask for video file
video_path = filedialog.askopenfilename(
    title="Select Video File",
    filetypes=[("Video Files", "*.mp4;*.avi;*.mov;*.mkv"), ("All Files", "*.*")]
)

# Ask for tracking CSV file
csv_path = filedialog.askopenfilename(
    title="Select Tracking File (CSV)",
    filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
)

# Group all entries (SuccTrack or not) by second
tracking_by_second = {}

with open(csv_path, newline='') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        t_seconds = timestamp_to_seconds(row["timestamp"])
        typ = row["status"]

        # Parse flashlight_pos "(676, 333)"
        cx_str, cy_str = row["flashlight_pos"].strip("()").split(",")
        cx, cy = float(cx_str), float(cy_str)
        

        # Parse bbox "(492, 861, 206, 461)"
        x1, x2, y1, y2 = map(int, row["bbox"].strip("()").split(","))

        if t_seconds not in tracking_by_second:
            tracking_by_second[t_seconds] = []

        tracking_by_second[t_seconds].append({
            "type": typ,
            "cx": int(cx),
            "cy": int(cy),
            "bbox": (x1, x2, y1, y2)
        })

# Open video
cap = cv2.VideoCapture(video_path)
fps = cap.get(cv2.CAP_PROP_FPS)
frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

pygame.init()
window = pygame.display.set_mode((video_width, video_height + 30))  # extra space for slider
clock = pygame.time.Clock()

frame_idx = 0
playing = True
slider_height = 30
running = True

while running:
    mouse_x = None
    click_on_slider = False
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # left click
                mx, my = event.pos
                if my >= video_height:  # click is on slider
                    click_on_slider = True
                    mouse_x = mx
                else:  # click is on video -> toggle play/pause
                    playing = not playing
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RIGHT:
                frame_idx = min(frame_idx + 1, frame_count - 1)
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            elif event.key == pygame.K_LEFT:
                frame_idx = max(frame_idx - 1, 0)
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)

    # Slider jump only if clicked on slider
    if click_on_slider and mouse_x is not None:
        video_pos = mouse_x / video_width
        frame_idx = int(video_pos * frame_count)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)

    if playing:
        ret, frame = cap.read()
        if not ret:
            break
        frame_idx += 1
    else:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret:
            break

    current_time = frame_idx / fps
    current_sec = int(current_time)
    frame_in_second = current_time - current_sec

    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame_surface = pygame.surfarray.make_surface(frame.swapaxes(0, 1))

    # Draw overlay for current second
    if current_sec in tracking_by_second:
        entries = tracking_by_second[current_sec]
        num_entries = len(entries)
        duration_per_entry = 1.0 / num_entries
        entry_idx = int(frame_in_second / duration_per_entry)
        entry_idx = min(entry_idx, num_entries - 1)
        entry = entries[entry_idx]

        if entry["type"] == "SuccTrack":
            pygame.draw.circle(frame_surface, (0, 255, 0), (entry["cx"], entry["cy"]), 8)
            x1, x2, y1, y2 = entry["bbox"]
            top_left = (min(x1, x2), min(y1, y2))
            width = abs(x2 - x1)
            height = abs(y2 - y1)
            pygame.draw.rect(frame_surface, (0, 255, 255), (top_left[0], top_left[1], width, height), 2)

    # Draw video and slider
    window.fill((0, 0, 0))
    window.blit(frame_surface, (0, 0))

    # Draw slider background
    pygame.draw.rect(window, (50, 50, 50), (0, video_height, video_width, slider_height))
    # Draw slider progress
    progress = frame_idx / frame_count
    pygame.draw.rect(window, (0, 200, 0), (0, video_height, int(video_width * progress), slider_height))

    # Draw play icon if paused
    if not playing:
        play_size = 60
        play_color = (255, 255, 255, 150)  # semi-transparent
        overlay = pygame.Surface((play_size, play_size), pygame.SRCALPHA)
        pygame.draw.polygon(overlay, play_color, [(0, 0), (0, play_size), (play_size, play_size // 2)])
        window.blit(overlay, (video_width//2 - play_size//2, video_height//2 - play_size//2))

    pygame.display.flip()
    clock.tick(fps)

cap.release()
pygame.quit()
