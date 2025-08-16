import pandas as pd # type: ignore
import matplotlib.pyplot as plt # type: ignore
import numpy as np # type: ignore
from matplotlib.animation import FuncAnimation  # type: ignore
import os

script_dir = os.path.dirname(os.path.abspath(__file__))

# Load Tracking CSV
tracking_file = r"C:\Users\JellyTracker\Desktop\JellyFishTrackingPC-main\saved_runs\run_20250815_201825\tracking.csv"
track_df = pd.read_csv(tracking_file)

# Use all points
sliced_points = list(zip(track_df['x'], track_df['y']))

fig, ax = plt.subplots()
ax.set_xlabel('x [mm]')
ax.set_ylabel('y [mm]')
ax.set_title('Tracking JF')
# Compute bounds from the data
x_min, x_max = track_df['x'].min(), track_df['x'].max()
y_min, y_max = track_df['y'].min(), track_df['y'].max()

# Add some margin so the dot doesn’t hug the edges
margin = 10
ax.set_xlim(x_min - margin, x_max + margin)
ax.set_ylim(y_min - margin, y_max + margin)
# ax.axis('equal') #opt
# or do
# ax.set_xlim(xmin,xmax)
# ax.set_ylim(ymin,ymax)

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
output_path = os.path.join(run_folder, "path_vis.mp4")
ani.save(output_path, fps=20, dpi=80, extra_args=['-vcodec', 'libx264', '-crf', '28'])

# save a gif
# ani.save("gdp_life.gif", writer=PillowWriter(fps=1))   # fps=1 means 1 frame per second






