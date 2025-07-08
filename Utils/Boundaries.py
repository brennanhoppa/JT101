try:
    from Utils.JellyTrackingFunctions import pixels_to_mm, mm_to_steps, mm_to_pixels, steps_to_mm
    from Utils.log import log
except:
    from JellyTrackingFunctions import pixels_to_mm, mm_to_steps, mm_to_pixels, steps_to_mm
    from log import log
import logging
# Logging setup
logging.getLogger('matplotlib').setLevel(logging.ERROR)

import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import filedialog

# boundaries
# saved as csv file w/ 2 columns, x,y in mm
# load in as list of (x,y) points in mm

def save_boundaries(filename, points,log_queue):
    """Save boundary points to a CSV file.
    saved in mm,mm
    """

    with open(filename, 'w') as f:
        f.write("x,y\n")
        for x, y in points:
            f.write(f"{x},{y}\n")
    log(f"Boundaries saved to {filename}",log_queue)

def load_boundary(is_jf_mode, log_queue):
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(title="Select a File", filetypes=[("CSV files", "*.csv"), ("All Files", "*.*")])
    if file_path:  # If a file was selected
        log(f"Selected file: {file_path}",log_queue)
        try:
            boundary_mm = load_boundaries(file_path)
            return boundary_to_steps(boundary_mm,is_jf_mode)
        except:
            log('Incorrect file loaded',log_queue)
    else:
        log("No file selected.",log_queue)
        return []

def load_boundaries(filename):
    """Load boundary points from a CSV file.
    loaded in as mm,mm
    """
    points = []
    with open(filename, 'r') as f:
        next(f)  # Skip header
        for line in f:
            x, y = map(float, line.strip().split(','))
            points.append((x, y))
    return points

def boundary_to_steps(boundary,is_jf_mode):
    return [(mm_to_steps(x,is_jf_mode), mm_to_steps(y,is_jf_mode)) for x, y in boundary]

def boundary_to_mm_from_steps(boundary,is_jf_mode):
    return [(steps_to_mm(x,is_jf_mode), steps_to_mm(y,is_jf_mode)) for x,y in boundary]

def boundary_to_pixels_from_steps(boundary,is_jf_mode):
    return [(mm_to_pixels(steps_to_mm(x,is_jf_mode),is_jf_mode),mm_to_pixels(steps_to_mm(y,is_jf_mode),is_jf_mode)) for x,y in boundary]

def plot_boundary(boundary):
    """Plot the boundary points and connect them with lines."""
    if not boundary:
        print("No boundary points to plot.")
        return
    
    x_vals, y_vals = [point[0] for point in boundary], [point[1] for point in boundary]  # Extract x and y values
    x_vals.append(boundary[0][0])  # Close the loop by adding the first point to the end
    y_vals.append(boundary[0][1])
    
    x_min, x_max = min(x_vals), max(x_vals)
    y_min, y_max = min(y_vals), max(y_vals)
    
    plt.figure(figsize=(8, 8))
    plt.plot(x_vals, y_vals, marker='o', linestyle='-')
    plt.xlim(x_min - 50, x_max + 50)
    plt.ylim(y_min - 50, y_max + 50)
    plt.xlabel("X (mm)")
    plt.ylabel("Y (mm)")
    plt.title("Boundary Plot")
    plt.gca().set_aspect('equal')  
    plt.grid(True)
    plt.show()

# Example usage
# file_path = "C:\\Users\\JellyTracker\\Desktop\\JellyFishTrackingPC-main\\saved_boundaries_mm\\new_boundary_20250708_120232.csv"
# loaded_boundaries = load_boundaries(file_path)

# plot_boundary(loaded_boundaries)
