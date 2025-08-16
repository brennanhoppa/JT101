import pandas as pd # type: ignore
import numpy as np # type: ignore
import matplotlib.pyplot as plt # type: ignore
import cv2 #type: ignore

# Read data from CSV file
csv_file = r'C:\Users\JellyTracker\Desktop\JellyFishTrackingPC-main\saved_tracking_csvs\sara_pilot_20141212_tracking.csv'
data = pd.read_csv(csv_file)

# Extract x, y, and t values
x_values = data['x'].tolist()
y_values = data['y'].tolist()
t_values = data['t'].tolist()

# Normalize the timestamps for plotting
t_min = min(t_values)
t_values = [t - t_min for t in t_values]


## OUTPUT THINGS TO CHANGE
# Need to know x is steps or mm or what -> convert to mm -> this will make axis's correct
# need to know x min, x max, y min, y max -> get this from measuring the tanks
# initialize the data by shifting relative to x min, y min step or mm

# Center data by shifting the first x and y coordinate to (0,0)
x_origin, y_origin = x_values[0], y_values[0]
# x_values = [x - x_origin for x in x_values]
# y_values = [y - y_origin for y in y_values]

# Downsample data if needed (every nth point), adjust 'step' for more/less detail
# step = 100 # use for long vids
step = 20  # Change this value to control downsampling
x_values = x_values[::step]
y_values = y_values[::step]
t_values = t_values[::step]

# Create the plot (faster with OpenCV)
width, height = 1280, 720  # Resolution of the video
output_file = 'saved_tracking_paths\sara_pilot_20241212_path.mp4'
fps = 200  # Higher fps to speed up the video

# Initialize OpenCV video writer
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
video_writer = cv2.VideoWriter(output_file, fourcc, fps, (width, height))

# Set up the plot with Matplotlib
fig, ax = plt.subplots()
ax.set_xlim(min(x_values), max(x_values))
ax.set_ylim(min(y_values), max(y_values))
line, = ax.plot([], [], 'bo-', lw=2)
plt.close(fig)  # Do not display interactive plot

# Create frames for the video
for i in range(len(x_values)):
    fig, ax = plt.subplots(figsize=(width / 100, height / 100), dpi=100)
    ax.set_xlim(min(x_values), max(x_values))
    ax.set_ylim(min(y_values), max(y_values))
    ax.plot(x_values[:i+1], y_values[:i+1], 'bo-', lw=2)
    
    # Convert Matplotlib plot to OpenCV frame
    fig.canvas.draw()
    img = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
    img = img.reshape(fig.canvas.get_width_height()[::-1] + (3,))
    
    # Resize image to desired output size
    img = cv2.resize(img, (width, height))

    # Attempt to put time in not quite working
    # time_str = f"t = {t_values[i]:.2f}"  # Format time with 2 decimal places
    # cv2.putText(img, time_str, (width - 200, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)


    # Write frame to video
    video_writer.write(cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    
    plt.close(fig)  # Close figure to save memory
    
    percent = (i/len(x_values))*100 
    if (abs(round(percent) - percent)) < 0.01:
        print('Percent complete:', round(percent), '%')

# Release video writer
video_writer.release()

print("Video saved as", output_file)
