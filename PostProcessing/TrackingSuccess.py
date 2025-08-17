import pandas as pd # type:ignore
import matplotlib.pyplot as plt #type: ignore
import os
import tkinter as tk
from tkinter import filedialog

# Hide the root Tk window
root = tk.Tk()
root.withdraw()

# File path
tracking_file = filedialog.askopenfilename(
    title="Select Tracking File (CSV)",
    filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
)
# Load
df = pd.read_csv(tracking_file)

# --- Convert time column to timedelta ---
df['timestamp'] = pd.to_timedelta(df['timestamp'])

# ================= Plot 1: Counts per second (x in hours) =================
counts_per_sec = df.groupby(df['timestamp'].dt.total_seconds().astype(int)).size()

# Convert x-axis to hours
x_hours = counts_per_sec.index / 3600  

plt.figure(figsize=(8,4))
plt.plot(x_hours, counts_per_sec.values, linestyle='-', alpha=0.7) # , marker='o'
plt.xlabel("Time [hours]")
plt.ylabel("Entries per second")
plt.title("Entries per Second (x-axis in hours)")
plt.grid(True)
plt.tight_layout()
plt.show()

# ================= Plot 2: Success % per minute =================
# Filter only SuccTrack and FailTrackMotorPos
df_filtered = df[df['status'].isin(['SuccTrack', 'FailTrackMotorPos'])].copy()

# Check the time span of the data
time_span_seconds = (df_filtered['timestamp'].max() - df_filtered['timestamp'].min()).total_seconds()

# If the time span is less than one minute, group by seconds
if time_span_seconds < 60:
    df_filtered['time_group'] = df_filtered['timestamp'].dt.total_seconds().astype(int)  # Group by seconds
    time_label = 'Time [seconds]'
else:
    # Create a 'minute' column for grouping by minute if the time span is >= 1 minute
    df_filtered['time_group'] = (df_filtered['timestamp'].dt.total_seconds() // 60).astype(int)  # Group by minutes
    time_label = 'Time [minutes]'

# Count per time group + status
counts = df_filtered.groupby(['time_group', 'status']).size().unstack(fill_value=0)

# Ensure both columns exist for every time group, fill missing with 0
counts = counts.reindex(columns=['SuccTrack', 'FailTrackMotorPos'], fill_value=0)

# Compute success %: Avoid division by zero
total = counts['SuccTrack'] + counts['FailTrackMotorPos']
counts['success_pct'] = (counts['SuccTrack'] / total.replace(0, 1)) * 100  # Avoid dividing by zero
# Plot the success percentage (even if it's 100% for all intervals)
plt.figure(figsize=(8, 4))
plt.plot(counts.index, counts['success_pct'], linestyle='-', alpha=1, label="Success %")

# Add grid lines for clarity
plt.xlabel(time_label)
plt.ylabel("Success Percentage [%]")
plt.title("Success Rate per Time Interval")
plt.ylim(0, 110)
plt.grid(True)

# Ensure everything is tight and visible
plt.tight_layout()

# Show the plot
plt.show()






