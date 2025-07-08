# functions for different button pressings
import time
from datetime import datetime
import cv2 #type: ignore
from Utils.Boundaries import save_boundaries, boundary_to_mm_from_steps
from Utils.CALIBRATIONPIECE_MM import CALIBRATIONPIECE_MM
from Utils.CONSTANTS import CONSTANTS, AviType
from Utils.log import log
import webbrowser
from Utils import states
import os

def homingStepsWithErrorCheck(homing_error_button, is_jf_mode,command_queue,x_pos,y_pos,log_queue):
    
    if is_jf_mode.value == 0: # means larvae mode
        log("Cannot home and error check in larvae mode, need to switch to jellyfish mode.",log_queue)
    else:
        command_queue.put(f'ERRORCHECK_{x_pos.value}_{y_pos.value}\n')
        homing_error_button.value = 1
        log("*****Homing and Error process starting...*****",log_queue)

start_loc = (0,0)
steps_per_mm_list = []
def stepsCalibration(step_size, step_to_mm_checking, x_pos, y_pos,is_jf_mode,log_queue):
    global start_loc, steps_per_mm_list
    if is_jf_mode.value == 1:
        steps_to_mm_ratio = CONSTANTS["JFStepsPerMm"]
    else:
        steps_to_mm_ratio = CONSTANTS["LStepsPerMm"]
    time.sleep(0.2)  # Short delay to prevent multiple triggers
    if step_to_mm_checking.value == 1:
        if len(steps_per_mm_list)==0 and is_jf_mode.value==1:
            log(f'*Move center camera cross to the end of the length of the calibration piece, and click Steps Cal button again.',log_queue)
        elif len(steps_per_mm_list)==1 and is_jf_mode.value==1:
            log(f'*Move center camera cross to the end of the width of the calibration piece, and click Steps Cal button again.',log_queue)
        elif len(steps_per_mm_list)==0 and is_jf_mode.value==0:
            log(f'*Move center camera cross to one edge of the calibration piece, and click Steps Cal button again. ',log_queue)
        else:
            log(f'*Move center camera cross to one edge of the calibration piece, and click Steps Cal button again. ',log_queue)
        step_size.value = 10 # normal is 95, try this / experiment 
        start_loc = (x_pos.value, y_pos.value)
        step_to_mm_checking.value = 2
    elif step_to_mm_checking.value == 2:
        steps_taken = (abs(x_pos.value - start_loc[0]),abs(y_pos.value - start_loc[1]))
        log(f"Steps taken: {steps_taken}",log_queue)
        if is_jf_mode.value == 1:
            distance = CALIBRATIONPIECE_MM['Length']
            dim = "Length"
            if len(steps_per_mm_list)>0:
                distance = CALIBRATIONPIECE_MM['Width']
                dim = "Width"
            log(f"Distance of the {dim} of the calibration piece [mm]: {distance}", log_queue)
            ratio = round((steps_taken[0]**2+steps_taken[1]**2)**(1/2)/distance,3)
            log(f"Using Pythagorean th, measured steps/mm = {ratio}",log_queue)
            log(f"Theoretical value: steps/mm = {steps_to_mm_ratio}",log_queue)
            error = round(((ratio-steps_to_mm_ratio)/(steps_to_mm_ratio)*100),3)
            log(f"Percent Error = {error}%",log_queue)
            steps_per_mm_list.append((ratio, error))
            if len(steps_per_mm_list) == 2:
                avg_ratio = sum(item[0] for item in steps_per_mm_list) / 2
                avg_error = sum(item[1] for item in steps_per_mm_list) / 2
                log(f"Average Ratio of Steps/mm: {round(avg_ratio,2)}",log_queue)
                log(f"Average Error: {round(avg_error,3)}%",log_queue)
                log("If average percent error larger than 5 percent, consider changing theoretical steps/mm ratio (which is used as the conversion factor for saved data). ",log_queue)
                log("*****Steps Calibration Complete*****",log_queue)
                step_to_mm_checking.value = 0
                steps_per_mm_list = []
                step_size.value = CONSTANTS["JellyStepSizeManual"] if is_jf_mode.value == 1 else CONSTANTS["LarvaeStepSizeManual"]
            else:
                step_to_mm_checking.value += 1
                log(f'*Click Steps Cal button again to measure the other dimension',log_queue)
        else:
            distance = CALIBRATIONPIECE_MM['Thickness']
            dim = 'Thickness'
            if len(steps_per_mm_list)>0:
                distance = CALIBRATIONPIECE_MM['Thickness']
                dim = 'Thickness'
            log(f"Distance of the {dim} of the calibration piece [mm]: {distance}",log_queue)
            ratio = round((steps_taken[0]**2+steps_taken[1]**2)**(1/2)/distance,3)
            log(f"Using Pythagorean th, measured steps/mm = {ratio}",log_queue)
            log(f"Theoretical value: steps/mm = {steps_to_mm_ratio}",log_queue)
            error = round(((ratio-steps_to_mm_ratio)/(steps_to_mm_ratio)*100),3)
            log(f"Percent Error = {error}%",log_queue)
            steps_per_mm_list.append((ratio, error))
            if len(steps_per_mm_list) == 2:
                avg_ratio = sum(item[0] for item in steps_per_mm_list) / 2
                avg_error = sum(item[1] for item in steps_per_mm_list) / 2
                log(f"Average Ratio of Steps/mm: {round(avg_ratio,2)}",log_queue)
                log(f"Average Error: {round(avg_error,3)}%", log_queue)
                log("If average percent error larger than 5 percent, consider changing theoretical steps/mm ratio (which is used as the conversion factor for saved data). ",log_queue)
                log("*****Steps Calibration Complete*****",log_queue)
                step_to_mm_checking.value = 0
                steps_per_mm_list = []
                step_size.value = CONSTANTS["JellyStepSizeManual"] if is_jf_mode.value == 1 else CONSTANTS["LarvaeStepSizeManual"]
            else:
                step_to_mm_checking.value += 1
                log(f'*Click Steps Cal button again to the thickness again',log_queue)
    else:
        log("*****Steps Calibration Start*****",log_queue)
        if is_jf_mode.value == 1:
            if len(steps_per_mm_list)==0:
                log(f'*Move center camera cross to the corner of calibration piece to measure the length of the piece. Click Steps Cal button again when there.',log_queue)
            else:
                log(f'*Move center camera cross to the corner of calibration piece to measure the width of the piece. Click Steps Cal button again when there.',log_queue)
        else:
            log(f'*Move center camera cross to one edge of calibration piece to measure the thickness. Click Steps Cal button again when there.',log_queue)
        step_to_mm_checking.value = 1
        step_size.value = 10 # normal is 95, try this / experiment 

pixel_start = (0,0)
def pixelsCalibration(pixelsCal_flag,crosshair_x,crosshair_y,window_width,window_height,is_jf_mode,log_queue):
    global pixel_start
    if is_jf_mode.value == 1:
        pixels_to_mm_ratio = CONSTANTS["JFPixelsPerMm"]
    else:
        pixels_to_mm_ratio = CONSTANTS["LPixelsPerMm"]
    if pixelsCal_flag.value == 0:
        log('***** Pixels Calibration Mode *****',log_queue)
        if is_jf_mode.value == 1:
            log(f'*Move the camera so the entire width of calibration piece is within frame, then click the Pixels Cal button again.',log_queue)
        else:
            log(f'*Move the camera so the entire thickness of calibration piece is within frame, and the edge of it is visible, then click the Pixels Cal button again.',log_queue)
        pixelsCal_flag.value = 1
    elif pixelsCal_flag.value == 1:
        log(f'*Use arrow keys to move curser on screen to one corner of the calibration piece, then click the Pixels Cal button again.',log_queue)
        pixelsCal_flag.value = 2 
    elif pixelsCal_flag.value == 2:
        pixel_start = (crosshair_x,crosshair_y)
        log(f'Crosshair initial position: ({crosshair_x}, {crosshair_y})',log_queue)
        log(f'*Use arrow keys to move curser on screen to the opposite corner of the width of the calibration piece, then click the Pixels Cal button again.',log_queue)
        pixelsCal_flag.value = 3
    elif pixelsCal_flag.value == 3:
        pixel_end = (crosshair_x,crosshair_y)
        log(f'Crosshair final position: ({crosshair_x}, {crosshair_y})',log_queue)
        pixels_traveled = (abs(pixel_end[0]-pixel_start[0]),abs(pixel_end[1]-pixel_start[1]))
        pixel_distance = round((pixels_traveled[0]**2 + pixels_traveled[1]**2)**(1/2),3)
        log(f'Pythagoras pixel distance traveled: {pixel_distance}',log_queue)
        if is_jf_mode.value == 1:
            log(f'Width of calibration piece [mm]: {CALIBRATIONPIECE_MM["Width"]}',log_queue)
            ratio = round(pixel_distance / CALIBRATIONPIECE_MM['Width'],3)
        else:
            log(f'Thickness of calibration piece [mm]: {CALIBRATIONPIECE_MM["Thickness"]}',log_queue)
            ratio = round(pixel_distance / CALIBRATIONPIECE_MM['Thickness'],3)
        log(f'Measured pixel to mm ratio: {ratio}',log_queue)
        log(f'Accepted / stored pixel to mm ratio: {pixels_to_mm_ratio}',log_queue)
        perror = round((ratio-pixels_to_mm_ratio)/pixels_to_mm_ratio*100,3)
        log(f'Percent Error from measured to stored value: {perror}%',log_queue)
        log(f'If percent error greater than 2% consider remeasuring and changing stored value.',log_queue)
        log(f'***** Pixels Calibration Complete *****', log_queue)
        pixelsCal_flag.value = 0
        crosshair_x = window_width // 2
        crosshair_y = window_height // 2
    return crosshair_x, crosshair_y

def keyBindsControl(keybinds_flag,log_queue):
    keybinds_flag.value = not keybinds_flag.value
    log(f"-----Turning arrow motor control {'on' if keybinds_flag.value else 'off'}.-----",log_queue)
    # time.sleep(0.2)
    
def recordingStart(recording,chosenAviType,fps,width,height,log_queue,step_tracking_data):
    recording.value = True
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
        fourcc = cv2.VideoWriter_fourcc('H','2','6','4')

    
    # Use original frame size from webcam, not the display size
    avi_recorder = cv2.VideoWriter(avi_filename, fourcc, fps, (width, height))
    log(f"$$$$$ Recording started at: {avi_filename} $$$$$",log_queue)
    # Reset step tracking data
    step_tracking_data[:] = []
    return avi_recorder,timestamp,avi_filename

def recordingSave(recording,avi_recorder,timestamp,step_tracking_data,log_queue):
    recording.value = False
    if avi_recorder:
        avi_recorder.release()
        avi_recorder = None
    log("$$$$$ Recording stopped and saved $$$$$",log_queue)
    # Save tracking data
    tracking_filename = f'saved_tracking_csvs/JellyTracking_{timestamp}_tracking.csv'
    with open(tracking_filename, 'w') as f:
        f.write("x,y,t\n")
        local_steps = list(step_tracking_data)
        for x, y, t in local_steps:
            f.write(f"{x},{y},{t}\n")
    log(f"$$$$$ Tracking data saved to {tracking_filename} $$$$$",log_queue)
    return None

def boundaryControl(boundary_making, boundary,is_jf_mode,log_queue):
    if boundary_making:
        log('Boundary Making Mode turned Off.',log_queue)
        file_start = "C:\\Users\\JellyTracker\\Desktop\\JellyFishTrackingPC-main\\saved_boundaries_mm\\"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # Format: YYYYMMDD_HHMMSS
        filename = file_start + f"new_boundary_{timestamp}.csv"
        log(f'Boundary saved at: {filename}',log_queue)
        save_boundaries(filename,boundary_to_mm_from_steps(boundary,is_jf_mode),log_queue)
        boundary_making = False
    else:
        log('Boundary Making Mode turned On. Move to record boundary. Finish and save by clicking Make Border button again. Click Cancel Border button to cancel and start over.',log_queue)
        boundary_making = True
        boundary = []
    return boundary_making, boundary

def boundaryCancel(boundary_making, boundary,log_queue):
    if boundary_making:
        boundary_making = False
        boundary = [] # reset boundary
        log('Boundary making turned off, and reset, with nothing saved.',log_queue)
    else: # do nothing
        pass
    return boundary_making, boundary

# Button press direct function
def saveHelper(log_queue, timestamp, step_tracking_data, recording):
    if recording.value:
        recordingSave(recording,states.avi_recorder,timestamp,step_tracking_data,log_queue)
        states.start_time = datetime.now() 

def trackingHelper(tracking, log_queue):
    tracking.value = not tracking.value
    log(f"*Tracking turned {'on' if tracking.value else 'off'}*",log_queue)

def trackingMotors(motors, log_queue):
    motors.value = not motors.value
    log(f"*Motors controlled by tracking turned {'on' if motors.value else 'off'}*",log_queue)

def borderShowHelper():
        states.show_boundary = not states.show_boundary

def verboseHelper(log_queue,command_queue,verbose):
    verbose.value = not verbose.value
    command_queue.put('VERBOSE\n')
    if verbose.value:
        log("^^^ Turning on the verbose descriptions of output from tracking model and arduino. Only use for debugging. ^^^",log_queue)
    else:
        log("^^^ Turning off verbose mode ^^^", log_queue)

def testingHelper(log_queue,testingMode):
    testingMode.value = not testingMode.value
    if testingMode.value:
        log("**Turning Testing Mode on!**",log_queue)
    else:
        log("**Testing Mode off**", log_queue)

def openHelp(log_queue):
    webbrowser.open("https://docs.google.com/document/d/1KBQ-LmBlyk6xcm9JkfM5uCkn3D8vZ4zREsdYrj_VqAM/edit?usp=sharing")
    log("!!!! Opening help document pdf on the desktop. !!!!", log_queue)

def clear_log_callback(rolling_log, log_queue):
    rolling_log.clear()
    log("New Terminal:",log_queue)