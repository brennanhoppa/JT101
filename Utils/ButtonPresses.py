# functions for different button pressings
import time
from datetime import datetime
import cv2 #type: ignore
from Utils.Boundaries import save_boundaries, boundary_to_steps, boundary_to_mm_from_steps, boundary_to_pixels_from_steps, load_boundaries
from Utils.CONTROLS import CONTROLS
from Utils.CALIBRATIONPIECE_MM import CALIBRATIONPIECE_MM
from Utils.CONSTANTS import CONSTANTS

def homingSteps(is_jf_mode, command_queue,homing_flag,x_pos,y_pos):
    if is_jf_mode.value == 0: # means larvae mode
        print("Cannot home in larvae mode, need to switch to jellyfish mode.")
    else:
        command_queue.put('HOMING\n')
        homing_flag.value = True
        print("Homing process started...")
        while homing_flag.value:
            time.sleep(0.1)
        x_pos.value, y_pos.value = 0, 0

def homingStepsWithErrorCheck(is_jf_mode,command_queue,homing_flag,x_pos,y_pos):
    if is_jf_mode.value == 0: # means larvae mode
        print("Cannot error check in larvae mode, need to switch to jellyfish mode.")
    else:
        command_queue.put(f'ERRORCHECK_{x_pos.value}_{y_pos.value}\n')
        homing_flag.value = True
        print("Error process starting...")
        while homing_flag.value:
            time.sleep(0.1)
        x_pos.value, y_pos.value = 0, 0
        print("Error Check Completed.")

start_loc = (0,0)
steps_per_mm_list = []
def stepsCalibration(step_size, step_to_mm_checking, x_pos, y_pos,is_jf_mode):
    global start_loc, steps_per_mm_list
    if is_jf_mode.value == 1:
        steps_to_mm_ratio = CONSTANTS["JFStepsPerMm"]
    else:
        steps_to_mm_ratio = CONSTANTS["LStepsPerMm"]
    time.sleep(0.2)  # Short delay to prevent multiple triggers
    if step_to_mm_checking.value == 1:
        if len(steps_per_mm_list)==0 and is_jf_mode.value==1:
            print(f'Move center camera x to the end of the length of the calibration piece, and press {CONTROLS["steps_to_mm"][0]} again. ')
        elif len(steps_per_mm_list)==1 and is_jf_mode.value==1:
            print(f'Move center camera x to the end of the width of the calibration piece, and press {CONTROLS["steps_to_mm"][0]} again. ')
        elif len(steps_per_mm_list)==0 and is_jf_mode.value==0:
            print(f'Move center camera x to one edge of the calibration piece, and press {CONTROLS["steps_to_mm"][0]} again. ')
        else:
            print(f'Move center camera x to one edge of the calibration piece, and press {CONTROLS["steps_to_mm"][0]} again. ')
        step_size.value = 10 # normal is 95, try this / experiment 
        start_loc = (x_pos.value, y_pos.value)
        step_to_mm_checking.value = 2
    elif step_to_mm_checking.value == 2:
        steps_taken = (abs(x_pos.value - start_loc[0]),abs(y_pos.value - start_loc[1]))
        print("Steps taken: ", steps_taken)
        if is_jf_mode.value == 1:
            distance = CALIBRATIONPIECE_MM['Length']
            dim = "Length"
            if len(steps_per_mm_list)>0:
                distance = CALIBRATIONPIECE_MM['Width']
                dim = "Width"
            print("Distance of the", dim, "of the calibration piece [mm]: ", distance)
            ratio = round((steps_taken[0]**2+steps_taken[1]**2)**(1/2)/distance,3)
            print("Using Pythagorean th, measured steps/mm = ", ratio)
            print("Theoretical value: steps/mm = ", steps_to_mm_ratio)
            error = round(((ratio-steps_to_mm_ratio)/(steps_to_mm_ratio)*100),3)
            print("Percent Error = ", error,'%')        
            steps_per_mm_list.append((ratio, error))
            if len(steps_per_mm_list) == 2:
                avg_ratio = sum(item[0] for item in steps_per_mm_list) / 2
                avg_error = sum(item[1] for item in steps_per_mm_list) / 2
                print("Average Ratio of Steps/mm:", round(avg_ratio,2))
                print("Average Error:", round(avg_error,3),'%')
                print("If average percent error larger than 5 percent, consider changing theoretical steps/mm ratio (which is used as the conversion factor for saved data). ")
                step_to_mm_checking.value = 0
                steps_per_mm_list = []
                step_size.value = CONSTANTS["JellyStepSizeManual"] if is_jf_mode.value == 1 else CONSTANTS["LarvaeStepSizeManual"]
            else:
                step_to_mm_checking.value += 1
                print(f'Press {CONTROLS["steps_to_mm"][0]} again to measure the other dimension')
        else:
            distance = CALIBRATIONPIECE_MM['Thickness']
            dim = 'Thickness'
            if len(steps_per_mm_list)>0:
                distance = CALIBRATIONPIECE_MM['Thickness']
                dim = 'Thickness'
            print("Distance of the", dim, "of the calibration piece [mm]: ", distance)
            ratio = round((steps_taken[0]**2+steps_taken[1]**2)**(1/2)/distance,3)
            print("Using Pythagorean th, measured steps/mm = ", ratio)
            print("Theoretical value: steps/mm = ", steps_to_mm_ratio)
            error = round(((ratio-steps_to_mm_ratio)/(steps_to_mm_ratio)*100),3)
            print("Percent Error = ", error,'%')        
            steps_per_mm_list.append((ratio, error))
            if len(steps_per_mm_list) == 2:
                avg_ratio = sum(item[0] for item in steps_per_mm_list) / 2
                avg_error = sum(item[1] for item in steps_per_mm_list) / 2
                print("Average Ratio of Steps/mm:", round(avg_ratio,2))
                print("Average Error:", round(avg_error,3),'%')
                print("If average percent error larger than 5 percent, consider changing theoretical steps/mm ratio (which is used as the conversion factor for saved data). ")
                step_to_mm_checking.value = 0
                steps_per_mm_list = []
                step_size.value = CONSTANTS["JellyStepSizeManual"] if is_jf_mode.value == 1 else CONSTANTS["LarvaeStepSizeManual"]
            else:
                step_to_mm_checking.value += 1
                print(f'Press {CONTROLS["steps_to_mm"][0]} again to the thickness again')
    else:
        if is_jf_mode.value == 1:
            if len(steps_per_mm_list)==0:
                print(f'Move center camera x to the corner of calibration piece to measure the length of the piece. Press {CONTROLS["steps_to_mm"][0]} again when there.')
            else:
                print(f'Move center camera x to the corner of calibration piece to measure the width of the piece. Press {CONTROLS["steps_to_mm"][0]} again when there.')
        else:
            print(f'Move center camera x to one edge of calibration piece to measure the thickness. Press {CONTROLS["steps_to_mm"][0]} again when there.')
        step_to_mm_checking.value = 1
        step_size.value = 10 # normal is 95, try this / experiment 

pixel_start = (0,0)
def pixelsCalibration(pixelsCal_flag,crosshair_x,crosshair_y,window_width,window_height,is_jf_mode):
    global pixel_start
    if is_jf_mode.value == 1:
        pixels_to_mm_ratio = CONSTANTS["JFPixelsPerMm"]
    else:
        pixels_to_mm_ratio = CONSTANTS["LPixelsPerMm"]
    if pixelsCal_flag.value == 0:
        if is_jf_mode.value == 1:
            print(f'Move the camera so the entire width of calibration piece is within frame, then press {CONTROLS["pixels_to_mm"][0]} again.')
        else:
            print(f'Move the camera so the entire thickness of calibration piece is within frame, and the edge of it is visible, then press {CONTROLS["pixels_to_mm"][0]} again.')        
        pixelsCal_flag.value = 1
    elif pixelsCal_flag.value == 1:
        print(f'Use arrow keys to move curser on screen to one corner of the calibration piece, then press {CONTROLS["pixels_to_mm"][0]} again.')
        pixelsCal_flag.value = 2 
    elif pixelsCal_flag.value == 2:
        pixel_start = (crosshair_x,crosshair_y)
        print(f'Crosshair initial position: ({crosshair_x}, {crosshair_y})')
        print(f'Use arrow keys to move curser on screen to the opposite corner of the width of the calibration piece, then press {CONTROLS["pixels_to_mm"][0]} again.')
        pixelsCal_flag.value = 3
    elif pixelsCal_flag.value == 3:
        pixel_end = (crosshair_x,crosshair_y)
        print(f'Crosshair final position: ({crosshair_x}, {crosshair_y})')
        pixels_traveled = (abs(pixel_end[0]-pixel_start[0]),abs(pixel_end[1]-pixel_start[1]))
        pixel_distance = round((pixels_traveled[0]**2 + pixels_traveled[1]**2)**(1/2),3)
        print(f'Pythagoras pixel distance traveled: {pixel_distance}')
        if is_jf_mode.value == 1:
            print(f'Width of calibration piece [mm]: {CALIBRATIONPIECE_MM["Width"]}')
            ratio = round(pixel_distance / CALIBRATIONPIECE_MM['Width'],3)
        else:
            print(f'Thickness of calibration piece [mm]: {CALIBRATIONPIECE_MM["Thickness"]}')
            ratio = round(pixel_distance / CALIBRATIONPIECE_MM['Thickness'],3)
        print(f'Measured pixel to mm ratio: {ratio}')
        print(f'Accepted / stored pixel to mm ratio: {pixels_to_mm_ratio}')
        perror = round((ratio-pixels_to_mm_ratio)/pixels_to_mm_ratio*100,3)
        print(f'Percent Error from measured to stored value: {perror}%')
        print(f'If percent error greater than 2% consider remeasuring and changing stored value.')
        pixelsCal_flag.value = 0
        crosshair_x = window_width // 2
        crosshair_y = window_height // 2
    return crosshair_x, crosshair_y

def keyBindsControl(keybinds_flag):
    keybinds_flag.value = not keybinds_flag.value
    print(f"Turning keybinds {'on' if keybinds_flag.value else 'off'}.")
    # time.sleep(0.2)

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
        fourcc = cv2.VideoWriter_fourcc('H', '2', '6', '4')
    
    # Use original frame size from webcam, not the display size
    avi_recorder = cv2.VideoWriter(avi_filename, fourcc, fps, (width, height))
    print(f"Recording started: {avi_filename}")
    # Reset step tracking data
    step_tracking_data = []
    return recording,avi_recorder,step_tracking_data,timestamp,avi_filename

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

def boundaryControl(boundary_making, boundary,is_jf_mode):
    if boundary_making:
        print('Boundary Making Mode turned Off.')
        file_start = "C:\\Users\\JellyTracker\\Desktop\\JellyFishTrackingPC-main\\saved_boundaries_mm\\"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # Format: YYYYMMDD_HHMMSS
        filename = file_start + f"new_boundary_{timestamp}.csv"
        print(f'Boundary saved at: {filename}')
        save_boundaries(filename,boundary_to_mm_from_steps(boundary,is_jf_mode))
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

def change_mode(is_jf_mode,x_pos,y_pos,step_size):
    step_size.value = 0
    if is_jf_mode.value == 0: # switching from larvae to jf
        is_jf_mode.value = 1
        print("Move the microscope so it is all the way down on the platform.")
        print("Refocus microscope on corner border or other object.")
        print("Switch the motor controller switchs on both motors so switches 1,2,4,5 are on (3 and 6 off). This gives 2000 steps/revolution")
        print("Prepare boundary inside tank for jellyfish.")
        step_size.value = CONSTANTS['JellyStepSizeManual']
        print(x_pos.value, y_pos.value, 'intilai poses ')
        x_pos.value = int(x_pos.value * CONSTANTS['JFStepPerRev'] / CONSTANTS['LStepPerRev'])
        y_pos.value = int(y_pos.value * CONSTANTS['JFStepPerRev'] / CONSTANTS['LStepPerRev'])
        print(x_pos.value, y_pos.value, 'final poses ')

    elif is_jf_mode.value == 1: # switching from jf to larvae
        is_jf_mode.value = 0
        print("Move the microscope so it inside the tank boundary.")
        print("Move the microscope up on the platform to be the WD away from the glass. Use the 3d printed calibration piece (it's 0.407 inches thick).")
        print("Refocus microscope on corner border or other object.")
        print("Switch the motor controller switchs on both motors so switches 1,2,4,6 are on (3 and 5 off). This gives 12800 steps/revolution")
        print("Prepare boundary inside tank for larvae.")
        step_size.value = CONSTANTS['LarvaeStepSizeManual']
        x_pos.value = int(x_pos.value / CONSTANTS['JFStepPerRev'] * CONSTANTS['LStepPerRev'])
        y_pos.value = int(y_pos.value / CONSTANTS['JFStepPerRev'] * CONSTANTS['LStepPerRev'])
        # NEED TO TURN ON TANK BOUNDARY / DON'T LET IT TURN ON IF NOT INSIDE THE TANK BOUNDARY
        
    else:
        print("Error, mode is incorrect value")
    time.sleep(0.2)  # Short delay to prevent multiple triggers
