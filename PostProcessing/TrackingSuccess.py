import pandas as pd # type:ignore
import matplotlib.pyplot as plt
import os

# File path
tracking_file = r"C:\Users\JellyTracker\Desktop\JellyFishTrackingPC-main\saved_runs\run_20250816_121252\tracking.csv"

# Load
df = pd.read_csv(tracking_file)

# --- Convert time column to timedelta ---
df['t'] = pd.to_timedelta(df['t'])

# ================= Plot 1: Counts per second (x in hours) =================
counts_per_sec = df.groupby(df['t'].dt.total_seconds().astype(int)).size()

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
df_filtered = df[df['type'].isin(['SuccTrack', 'FailTrackMotorPos'])].copy()
df_filtered['minute'] = df_filtered['t'].dt.total_seconds().astype(int) // 60

# Count per minute + type
counts = df_filtered.groupby(['minute','type']).size().unstack(fill_value=0)

# Compute success %
counts['success_pct'] = counts['SuccTrack'] / (counts['SuccTrack'] + counts['FailTrackMotorPos']) * 100

plt.figure(figsize=(8,4))
# plt.scatter(counts.index, counts['success_pct'], label="Success %")
plt.plot(counts.index, counts['success_pct'], linestyle='-', alpha=0.7)
plt.xlabel("Time [minutes]")
plt.ylabel("Success Percentage [%]")
plt.title("Success Rate per Minute")
plt.ylim(0, 100)
plt.grid(True)
plt.tight_layout()
plt.show()
