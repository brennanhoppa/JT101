import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation, FFMpegWriter
from matplotlib import animation
import shutil
import os
import subprocess

# --- FFmpeg path setup ---
ffmpeg_path = shutil.which("ffmpeg")
if not ffmpeg_path:
    ffmpeg_path = r"C:\ffmpeg\bin\ffmpeg.exe"  # hardcoded fallback

# Test that FFmpeg is callable
try:
    subprocess.run([ffmpeg_path, "-version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
except Exception as e:
    raise RuntimeError(f"FFmpeg executable not found or not working: {ffmpeg_path}") from e

# Set FFmpeg path for Matplotlib
animation.ffmpeg_path = ffmpeg_path
print(f"Using FFmpeg from: {animation.ffmpeg_path}")

# --- Load CSV ---
tracking_file = r"C:\Users\weiss\Desktop\JT101\saved_runs\run_20250815_190951\tracking.csv"
track_df = pd.read_csv(tracking_file)

# Ensure numeric data
track_df['x'] = pd.to_numeric(track_df['x'], errors='coerce')
track_df['y'] = pd.to_numeric(track_df['y'], errors='coerce')
track_df = track_df.dropna(subset=['x', 'y'])

# --- Downsample points for faster animation ---
skip = 10
sliced_points = list(zip(track_df['x'], track_df['y']))[::skip]
frames = len(sliced_points)

# --- Set up plot ---
fig, ax = plt.subplots()
ax.set_xlabel('x [mm]')
ax.set_ylabel('y [mm]')
ax.set_title('Tracking Path')
ax.axis('equal')

track_line, = ax.plot([], [], color='gray', linestyle='-')
curr_dot = ax.scatter([], [], color='red', s=40)

def init():
    track_line.set_data([], [])
    curr_dot.set_offsets(np.empty((0, 2)))
    return track_line, curr_dot

def animate(frame):
    if frame >= 1:
        x_vals, y_vals = zip(*sliced_points[:frame])
        track_line.set_data(x_vals, y_vals)
    else:
        track_line.set_data([], [])
    
    x_curr, y_curr = sliced_points[frame]
    curr_dot.set_offsets([x_curr, y_curr])
    return track_line, curr_dot

ani = FuncAnimation(fig, animate, init_func=init,
                    frames=frames, interval=50, blit=True, repeat=True)

# --- Save animation ---
output_path = os.path.join(os.path.dirname(__file__), "path_vis.mp4")
writer = FFMpegWriter(fps=20, codec="libx264", extra_args=['-crf', '28'])
ani.save(output_path, writer=writer, dpi=80)

print(f"Animation saved to {output_path}")
