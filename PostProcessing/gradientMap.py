import pandas as pd # type: ignore
import numpy as np 
import matplotlib.pyplot as plt
import cupy as cp # type: ignore
from scipy.stats import gaussian_kde # type: ignore
from joblib import Parallel, delayed # type: ignore
import tkinter as tk
from tkinter import filedialog

# Hide the root Tk window
root = tk.Tk()
root.withdraw()

# Load the CSV data
csv_file = filedialog.askopenfilename(
    title="Select Tracking File (CSV)",
    filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
)

data = pd.read_csv(csv_file, names=["x_mm","y_mm","timestamp"], skiprows=1)  # Adjust skiprows if needed

# Convert 't' column (Unix timestamp) to datetime and calculate time differences in minutes
data['timestamp'] = pd.to_datetime(data['timestamp'], unit='s', errors='coerce')  # Handle non-numeric values with 'coerce'
time_diffs = data['timestamp'].diff().dt.total_seconds().fillna(0) / 60  # Time differences in minutes

# Transfer x, y coordinates and time differences to GPU arrays
x_values = cp.array(data['x_mm'].values, dtype=cp.float32)
y_values = cp.array(data['y_mm'].values, dtype=cp.float32)
time_diffs = cp.array(time_diffs.values, dtype=cp.float32)  # Time differences as weights

# Optional: Center the data around (0,0)
x_values -= x_values[0]
y_values -= y_values[0]

# Set up grid for KDE density estimation
xmin, xmax = cp.min(x_values).get(), cp.max(x_values).get()
ymin, ymax = cp.min(y_values).get(), cp.max(y_values).get()
grid_size = 300  # Adjust for resolution vs. performance balance

# Create a grid for density estimation
x_grid = np.linspace(xmin, xmax, grid_size)  # Back to NumPy for KDE compatibility
y_grid = np.linspace(ymin, ymax, grid_size)
x_mesh, y_mesh = np.meshgrid(x_grid, y_grid)

# Define the KDE on CPU using time weights
kde = gaussian_kde(cp.asnumpy(cp.vstack([x_values, y_values])), weights=cp.asnumpy(time_diffs), bw_method=0.1)

# Function to evaluate a slice of the density grid
def evaluate_density(start, end):
    # Extract the slice and evaluate the density
    x_slice = x_mesh.ravel()[start:end].copy()
    y_slice = y_mesh.ravel()[start:end].copy()
    xy_slice = np.vstack([x_slice, y_slice])
    return kde(xy_slice)

# Increase the number of splits for finer parallelization
num_slices = 16  # Adjust this based on CPU cores and memory
grid_points = x_mesh.size
slice_indices = np.linspace(0, grid_points, num_slices + 1, dtype=int)

# Evaluate time-weighted density in parallel
density_slices = Parallel(n_jobs=-1, backend="threading")(
    delayed(evaluate_density)(start, end) for start, end in zip(slice_indices[:-1], slice_indices[1:])
)

# Concatenate the results and reshape to grid
density = np.concatenate(density_slices)
density = cp.array(density).reshape((grid_size, grid_size))  # Convert to CuPy array and reshape

# Plot the time-weighted density map
plt.figure(figsize=(10, 8))
plt.imshow(cp.asnumpy(density).T, origin='lower', extent=[xmin, xmax, ymin, ymax], cmap='inferno', alpha=0.75)
plt.colorbar(label='Time Density (Minutes)')
plt.title("Jellyfish Time-Spent Density Map in Tank")
plt.xlabel("X Position")
plt.ylabel("Y Position")
plt.show()

# import pandas as pd
# import numpy as np
# import matplotlib.pyplot as plt
# import cupy as cp
# from scipy.stats import gaussian_kde
# from joblib import Parallel, delayed

# # Load the CSV data
# csv_file = r'C:\Users\JellyTracker\Desktop\JellyFishTrackingPC-main\saved_tracking_csvs\JellyTracking_20241031_102422_tracking.csv'
# data = pd.read_csv(csv_file)

# # Transfer x and y coordinates to GPU arrays
# x_values = cp.array(data['x'].values)
# y_values = cp.array(data['y'].values)

# # Optional: Center the data around (0,0)
# x_values -= x_values[0]
# y_values -= y_values[0]

# # Set up grid for KDE density estimation
# xmin, xmax = cp.min(x_values).get(), cp.max(x_values).get()
# ymin, ymax = cp.min(y_values).get(), cp.max(y_values).get()
# grid_size = 300  # Adjust for resolution vs. performance balance

# # Create a grid for density estimation
# x_grid = np.linspace(xmin, xmax, grid_size)  # Back to NumPy for KDE compatibility
# y_grid = np.linspace(ymin, ymax, grid_size)
# x_mesh, y_mesh = np.meshgrid(x_grid, y_grid)

# # Define the KDE on CPU
# kde = gaussian_kde(cp.asnumpy(cp.vstack([x_values, y_values])), bw_method=0.1)

# # Function to evaluate a slice of the density grid
# def evaluate_density(start, end):
#     # Ensure a writable copy by using `.copy()` on the slices
#     x_slice = x_mesh.ravel()[start:end].copy()
#     y_slice = y_mesh.ravel()[start:end].copy()
#     xy_slice = np.vstack([x_slice, y_slice])
#     return kde(xy_slice)

# # Increase the number of splits for finer parallelization
# num_slices = 16  # Adjust this based on CPU cores and memory
# grid_points = x_mesh.size
# slice_indices = np.linspace(0, grid_points, num_slices + 1, dtype=int)

# # Evaluate density in parallel using threading backend to avoid memory issues
# density_slices = Parallel(n_jobs=-1, backend="threading")(
#     delayed(evaluate_density)(start, end) for start, end in zip(slice_indices[:-1], slice_indices[1:])
# )

# # Concatenate the results and reshape to grid
# density = np.concatenate(density_slices)
# density = cp.array(density).reshape((grid_size, grid_size))  # Convert to CuPy array and reshape

# # Plot the density map
# plt.figure(figsize=(10, 8))
# plt.imshow(cp.asnumpy(density).T, origin='lower', extent=[xmin, xmax, ymin, ymax], cmap='inferno', alpha=0.75)
# plt.colorbar(label='Density (Time Spent)')
# plt.title("Jellyfish Time-Spent Density Map in Tank")
# plt.xlabel("X Position")
# plt.ylabel("Y Position")
# plt.show()