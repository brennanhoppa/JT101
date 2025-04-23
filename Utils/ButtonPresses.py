# functions for different button pressings
import time
from datetime import datetime
import cv2 #type: ignore
from Utils.Boundaries import save_boundaries, boundary_to_steps, boundary_to_mm_from_steps, boundary_to_pixels_from_steps, load_boundaries

def homingSteps(command_queue,homing_flag,x_pos,y_pos):
    command_queue.put('HOMING\n')
    homing_flag.value = True
    print("Homing process started...")
    while homing_flag.value:
        time.sleep(0.1)
    x_pos.value, y_pos.value = 0, 0

def homingStepsWithErrorCheck(command_queue,homing_flag,x_pos,y_pos):
    command_queue.put(f'ERRORCHECK_{x_pos.value}_{y_pos.value}\n')
    homing_flag.value = True
    print("Error process starting...")
    while homing_flag.value:
        time.sleep(0.1)
    x_pos.value, y_pos.value = 0, 0
    print("Error Check Completed.")

start_loc = (0,0)
def stepsCalibration(step_size, step_to_mm_checking, x_pos, y_pos,steps_to_mm_ratio,defaultStepSize):
    global start_loc
    time.sleep(0.2)  # Short delay to prevent multiple triggers
    if step_to_mm_checking == 1:
        print('Changing to precisiion step size, now move until the end of the piece, and press q again. ')
        step_size = 20 # normal is 95, try this / experiment 
        start_loc = (x_pos.value, y_pos.value)
        step_to_mm_checking = 2
    elif step_to_mm_checking == 2:
        steps_taken = (abs(x_pos.value - start_loc[0]),abs(y_pos.value - start_loc[1]))
        distance = 25.4 # mm - right now for testing
        print("Steps taken: ", steps_taken)
        print("Distance: ", distance)
        ratio = (steps_taken[0]**2+steps_taken[1]**2)**(1/2)/distance
        print("Using Pythagorean th, measured steps/mm = ", round(ratio,3))
        print("Theoretical value: steps/mm = ", steps_to_mm_ratio)
        print("Percent Error = ", round(((ratio-steps_to_mm_ratio)/(steps_to_mm_ratio)*100),3),'%')
        print("If percent error larger than 1 percent, consider changing theoretical value. ")
        step_to_mm_checking = 0
        step_size = defaultStepSize
    else:
        print('Move to location with piece of known dimension. Move camera center to one edge of piece. Press q again when there.')
        step_to_mm_checking = 1
        step_size = 35 # normal is 95, try this / experiment 
    return step_size, step_to_mm_checking

def keyBindsControl(keybinds_flag):
    keybinds_flag.value = not keybinds_flag.value
    print(f"Turning keybinds {'on' if keybinds_flag.value else 'off'}.")
    time.sleep(0.2)

class AviType:
        UNCOMPRESSED = 0
        MJPG = 1
        H264 = 2
    
def recordingStart(recording,chosenAviType,fps,width,height):
    recording = True
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    avi_filename = f'saved_tracking_videos/JellyTracking_{timestamp}'

    # Create video writer with more reliable settings
    if chosenAviType == AviType.MJPG:
        avi_filename += '.avi'
        fourcc = cv2.VideoWriter_fourcc('M', 'J', 'P', 'G')
    elif chosenAviType == AviType.UNCOMPRESSED:
        avi_filename += '.avi'
        fourcc = cv2.VideoWriter_fourcc('I', '4', '2', '0')
    elif chosenAviType == AviType.H264:
        avi_filename += '.mp4'
        fourcc = cv2.VideoWriter_fourcc('m', 'p', '4', 'v')
    
    # Use original frame size from webcam, not the display size
    avi_recorder = cv2.VideoWriter(avi_filename, fourcc, fps, (width, height))
    print(f"Recording started: {avi_filename}")
    # Reset step tracking data
    step_tracking_data = []
    return recording,avi_recorder,step_tracking_data,timestamp

def recordingSave(recording,avi_recorder,timestamp,step_tracking_data):
    recording = False
    if avi_recorder:
        avi_recorder.release()
        avi_recorder = None
    print("Recording stopped and saved")
    
    # Save tracking data
    tracking_filename = f'saved_tracking_csvs/JellyTracking_{timestamp}_tracking.csv'
    with open(tracking_filename, 'w') as f:
        f.write("x,y,t\n")
        for x, y, t in step_tracking_data:
            f.write(f"{x},{y},{t}\n")
    print(f"Tracking data saved to {tracking_filename}")
    return recording

def boundaryControl(boundary_making, boundary):
    if boundary_making:
        print('Boundary Making Mode turned Off.')
        file_start = "C:\\Users\\JellyTracker\\Desktop\\JellyFishTrackingPC-main\\saved_boundaries_mm\\"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # Format: YYYYMMDD_HHMMSS
        filename = file_start + f"new_boundary_{timestamp}.csv"
        print(f'Boundary saved at: {filename}')
        save_boundaries(filename,boundary_to_mm_from_steps(boundary))
        boundary_making = False
    else:
        print('Boundary Making Mode turned On. Move to record boundary. Finish and save by pressing b again. Press x to cancel/start over.')
        boundary_making = True
        boundary = []
    return boundary_making, boundary

def boundaryCancel(boundary_making, boundary):
    if boundary_making:
        boundary_making = False
        boundary = [] # reset boundary
        print('Boundary making turned off, and reset, with nothing saved.')
    else: # do nothing
        pass
    return boundary_making, boundary