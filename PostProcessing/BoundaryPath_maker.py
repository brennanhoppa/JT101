import pandas as pd # type: ignore
import matplotlib.pyplot as plt # type: ignore
import numpy as np # type: ignore
from matplotlib.animation import FuncAnimation  # type: ignore
import os
import tkinter as tk
from tkinter import filedialog

# Hide the root Tk window
root = tk.Tk()
root.withdraw()

script_dir = os.path.dirname(os.path.abspath(__file__))

# Load Tracking CSV
# Ask for tracking CSV file
tracking_file = filedialog.askopenfilename(
    title="Select Tracking File (CSV)",
    filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
)
track_df = pd.read_csv(tracking_file)

# Ask for boundary CSV file
boundary_file = filedialog.askopenfilename(
    title="Select Boundary File (CSV)",
    filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
)
boundary_df = pd.read_csv(boundary_file)
# Extract boundary points
boundary_points = list(zip(boundary_df['x'], boundary_df['y']))

# Close the loop by connecting first and last points
boundary_points.append(boundary_points[0])

# Unzip for plotting
bx, by = zip(*boundary_points)
fig, ax = plt.subplots()

# Plot the boundary as solid blue line
ax.plot(bx, by, color='blue', linestyle='-', linewidth=2, label='Boundary')

# Use all points
sliced_points = list(zip(track_df['x_mm'], track_df['y_mm']))

ax.set_xlabel('x [mm]')
ax.set_ylabel('y [mm]')
ax.set_title('Tracking JF')

# Combine all points: tracking + boundary
all_x = list(track_df['x_mm']) + list(boundary_df['x'])
all_y = list(track_df['y_mm']) + list(boundary_df['y'])

x_min, x_max = min(all_x), max(all_x)
y_min, y_max = min(all_y), max(all_y)

margin = 10
ax.set_xlim(x_min - margin, x_max + margin)
ax.set_ylim(y_min - margin, y_max + margin)

# Make the scaling equal
ax.set_aspect('equal', adjustable='box')

# Create empty line and dot for updating
track_line, = ax.plot([], [], color='gray', linestyle='-')
curr_dot = ax.scatter([], [], color='red', s=40)

def init():
    track_line.set_data([], [])
    curr_dot.set_offsets(np.empty((0, 2)))
    return track_line, curr_dot


skip = 10
sliced_points_downsampled = sliced_points[::skip]

frames = len(sliced_points_downsampled)

# --- Animate function ---
def animate(frame):
    if frame % 1000 == 0:  # print every 100 frames (adjust as needed)
        print(f"Saving frame {frame+1} / {frames}")

    if frame >= 1:
        x_vals, y_vals = zip(*sliced_points_downsampled[:frame])
        track_line.set_data(x_vals, y_vals)
    else:
        track_line.set_data([], [])

    # Update current dot
    x_curr, y_curr = sliced_points_downsampled[frame]
    curr_dot.set_offsets([x_curr, y_curr])

    return track_line, curr_dot

# --- Make animation ---
# frames = len(sliced_points)
ani = FuncAnimation(
    fig, animate, init_func=init,
    frames=frames, interval=50, blit=True, repeat=True
)

# plt.show()

# Save fast:
run_folder = os.path.dirname(tracking_file)
output_path = os.path.join(run_folder, "path_vis_with_border.mp4")
ani.save(output_path, fps=20, dpi=80, extra_args=['-vcodec', 'libx264', '-crf', '28'])

# save a gif
# ani.save("gdp_life.gif", writer=PillowWriter(fps=1))   # fps=1 means 1 frame per second






