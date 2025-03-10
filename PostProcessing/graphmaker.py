import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import PillowWriter

# Load the array from the CSV file
loaded_array = np.loadtxt(r"C:\Users\JellyTracker\Desktop\JellyFishTrackingPC-main\saved_tracking_csvs\JellyTracking_20241031_102257_tracking.csv", delimiter=",", skiprows=1)

# Extract x and y columns
x = loaded_array[:, 0]
y = loaded_array[:, 1]

# Set up the plot
fig, ax = plt.subplots()
line, = ax.plot([], [], 'bo-', label="Points")

# Set axis limits based on the data range
ax.set_xlim([-20000, 1000])
ax.set_ylim([-20000, 1000])
plt.xlabel("x")
plt.ylabel("y")
plt.title("Plotting points with 0.1s delay")
plt.legend()

# Initialize empty lists to store the points to plot
x_data, y_data = [],[]

# Set up the writer for saving the animation as a GIF
writer = PillowWriter(fps=.5)  # 10 frames per second

# Start the writer to record the animation to a GIF file
with writer.saving(fig, "saved_tracking_gifs\\output_animation1.gif", dpi=100):
    # Loop through the rows of the array
    for i in range(len(x)):
        # Append the new points to the list
        x_data.append(x[i])
        y_data.append(y[i])

        # Update the line data and plot
        line.set_data(x_data, y_data)
        fig.canvas.draw()

        # Add a frame to the GIF file
        writer.grab_frame()

# use this link to conver the gif to an mp4
# https://ezgif.com/gif-to-mp4/ezgif-5-af107c03f5.gif