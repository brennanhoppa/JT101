import pandas as pd # type: ignore
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation
import os

script_dir = os.path.dirname(os.path.abspath(__file__))

# Load Tracking CSV
tracking_file = r"C:\Users\JellyTracker\Desktop\JellyFishTrackingPC-main\saved_analysis\track_run_711\JellyTracking_20250711_130005_tracking.csv"
track_df = pd.read_csv(tracking_file)

# Load Boundary
boundary_file = r"C:\Users\JellyTracker\Desktop\JellyFishTrackingPC-main\saved_analysis\track_run_711\new_boundary_20250711_150914_petri.csv"
b_df = pd.read_csv(boundary_file)

# Convert to list of (x, y) tuples
points = list(zip(b_df['x'], b_df['y']))

# Add first point to end to close the shape
if points:
    points.append(points[0])

# Unpack x and y for plotting
x_vals, y_vals = zip(*points)

tolerance = 1
idx_close_to_zero = track_df.index[track_df['x'].abs() < tolerance]
if not idx_close_to_zero.empty:
    first_idx = idx_close_to_zero[0]
    first_t = track_df.loc[first_idx, 't']
    print(f"First x ≈ 0 at index {first_idx}, time: {first_t}")

    # Slice data up to that index
    sliced_points = list(zip(track_df.loc[:first_idx, 'x'], track_df.loc[:first_idx, 'y']))

    
else:
    print("No x value close to 0 found.")

fig, ax = plt.subplots()
ax.set_xlabel('x [mm]')
ax.set_ylabel('y [mm]')
ax.set_title('Tracking JF 7/11/2025 in Petri Dish')
ax.axis('equal') #opt
# or do
# ax.set_xlim(xmin,xmax)
# ax.set_ylim(ymin,ymax)

boundary_line, = ax.plot(*zip(*points), color='blue', linewidth=1)
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
output_path = os.path.join(os.path.dirname(__file__), "path_vis.mp4")
ani.save(output_path, fps=20, dpi=80, extra_args=['-vcodec', 'libx264', '-crf', '28'])

# save a gif
# ani.save("gdp_life.gif", writer=PillowWriter(fps=1))   # fps=1 means 1 frame per second






