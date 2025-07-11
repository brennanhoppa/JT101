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

tolerance = 0.1  # example tolerance

# Find all indices where x or y is close to 0
idx_close_to_zero = track_df.index[
    (track_df['x'].abs() < tolerance) | (track_df['y'].abs() < tolerance)
]

if not idx_close_to_zero.empty:
    print(f"Found {len(idx_close_to_zero)} points where x or y ≈ 0:")
    
    for idx in idx_close_to_zero:
        t = track_df.loc[idx, 't']
        x = track_df.loc[idx, 'x']
        y = track_df.loc[idx, 'y']
        print(f"Index: {idx}, time: {t}, x: {x}, y: {y}")

    # Example: slice data up to the first such index
    first_idx = idx_close_to_zero[0]
    sliced_points = list(zip(track_df.loc[:first_idx, 'x'], track_df.loc[:first_idx, 'y']))

else:
    print("No x or y value close to 0 found.")
