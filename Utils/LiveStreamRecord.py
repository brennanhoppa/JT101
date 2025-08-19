import sys
import numpy as np # type: ignore
import multiprocessing
import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame # type: ignore
import threading
import queue
from datetime import datetime
import time
from Utils.JellyTrackingFunctions import detect_jellyfish,calculate_movement, calculate_delta_Pixels, mm_to_pixels, pixels_to_mm, mm_to_steps, steps_to_mm, mode_string
from Utils.moveFunctions import move
import cv2 #type: ignore
from Utils.ButtonPresses import recordingStart, recordingSave, boundaryControl, boundaryCancel,pixelsCalibration, keyBindsControl, stepsCalibration
from Utils.Button import Button
from Utils.savePopUp import popup_save_recording
from Utils.LiveStreamUtilFuncs import ensure_dir
from Utils.Boundaries import load_boundary
from Utils import states
from Utils.ButtonPresses import homingStepsWithErrorCheck, saveHelper, trackingHelper, trackingMotors, borderShowHelper, testingHelper, verboseHelper, openHelp
from Utils.changeModePopUp import changeModePopUp
import ctypes
import shutil
import csv

boundary = []
# or write filename to load in a boundary
# e.g.
# boundary_filename = "C:\\Users\\JellyTracker\\Desktop\\JellyFishTrackingPC-main\\saved_boundaries_mm\\new_bounds.csv"
# boundary_mm = load_boundaries(boundary_filename)
# boundary = boundary_to_steps(boundary_mm)

# Tracking settings
TRACKING_INTERVAL = 1 / 50  # 50Hz tracking rate

# Queue for inter-thread communication
image_queue = queue.Queue(maxsize=5)
recording_queue = queue.Queue(maxsize=100)
tracking_result_queue = queue.Queue(maxsize=5)

def run_live_stream_record(x_pos,y_pos,command_queue,keybinds_flag,pixelsCal_flag,is_jf_mode, terminate_event, running_flag,step_size,step_to_mm_checking,homing_error_button,x_invalid_flag, y_invalid_flag,verbose,testingMode,recording,tracking,motors,elapsed_time,reset_timer):
    if main(x_pos,y_pos,command_queue,keybinds_flag,pixelsCal_flag,is_jf_mode, terminate_event, running_flag, step_size,step_to_mm_checking,homing_error_button,x_invalid_flag, y_invalid_flag,verbose,testingMode,recording,tracking,motors,elapsed_time,reset_timer):
        sys.exit(0)
    else:
        sys.exit(1)

def recording_writer_thread(recording):
    while states.running:
        if recording.value and states.avi_recorder is not None:
            try:
                while True:  # flush queue
                    frame = recording_queue.get_nowait()
                    try:
                        states.avi_recorder.write(frame)
                    except ValueError as e:
                        if 'write to closed file' in str(e):
                            break
                        else:
                            raise
            except queue.Empty:
                time.sleep(0.001)

        else:
            time.sleep(0.01)


last_time = time.time()
frames = 0
def imageacq(cam, recording, fps):
    global frames, last_time
    cam.set(cv2.CAP_PROP_FPS, fps)

    while states.running:
        try:
            ret, frame = cam.read()
            if ret:
                frames += 1
                if frames % 100 == 0:
                    now = time.time()
                    # print(f"Capture FPS: {100 / (now - last_time):.2f}")
                    last_time = now
                
                # Save for display
                states.shared_image = frame

                # Put frame into tracking queue
                if isinstance(frame, np.ndarray):
                    try:
                        image_queue.put(frame, block=False)
                    except queue.Full:
                        try:
                            image_queue.get_nowait()  # drop oldest
                            image_queue.put(frame, block=False)
                        except queue.Empty:
                            pass
                else:
                    print("Warning: Frame is not a valid NumPy array.")

                # If recording is active, put frame into recording queue too
                if recording.value:
                    try:
                        recording_queue.put(frame, block=False)
                    except queue.Full:
                        try:
                            recording_queue.get_nowait()  # drop oldest
                            recording_queue.put(frame, block=False)
                        except queue.Empty:
                            pass
            else:
                print("Failed to capture frame from camera")

        except Exception as ex:
            print(f'Error in image acquisition: {ex}')

    # Clean up on exit
    if states.avi_recorder is not None:
        states.avi_recorder.release()


def active_tracking_thread(center_x, center_y, command_queue, x_pos, y_pos, is_jf_mode,x_invalid_flag, y_invalid_flag,verbose,recording, tracking,motors, testingMode, elapsed_time,recordingTimeStamp,recordingStartEnd,trackingStartEnd):    
    last_tracking_time = time.time()
    csv_writer = None
    tracking_data_file = None

    while states.running:
        current_time = time.time()
        if current_time - last_tracking_time >= TRACKING_INTERVAL:
            if recordingStartEnd.value == 1:
                recordingtimestamp_text = recordingTimeStamp.value.decode('utf-8').rstrip('\x00')
                mode_str = "Jellyfish" if is_jf_mode.value == 1 else "Larvae"
                tracking_data_file = open(f"saved_runs/run_{recordingtimestamp_text}_{mode_str}/tracking.csv", "a",newline="")
                csv_writer = csv.writer(tracking_data_file)
                csv_writer.writerow(["x_mm", "y_mm", "timestamp", "status", "flashlight_pos", "bbox"])
                recordingStartEnd.value = 0 
            elif recordingStartEnd.value == 2:
                if tracking_data_file:
                    tracking_data_file.close()
                    tracking_data_file = None
                    csv_writer = None
                recordingStartEnd.value = 0

            if tracking.value or trackingStartEnd.value == 2:
                try:
                    image = image_queue.get(timeout=1)  # Wait for the next frame

                    # Verify that the image is a valid NumPy array
                    if not isinstance(image, np.ndarray):
                        print("Warning: Image from queue is not a valid NumPy array.")
                        continue
                    
                    # Check the shape consistency
                    if image.ndim != 3 or image.shape[2] != 3:
                        print(f"Warning: Unexpected image shape {image.shape}, converting to RGB.")
                        if image.ndim == 2:  # Grayscale image
                            image = np.stack((image,) * 3, axis=-1)
                        else:
                            continue
                    
                    # testing feature
                    detect_light = False # normal setting to track jf
                    # detect_light = True # testing mode - returns x,y of brightest spot in frame

                    # Use YOLO to detect jellyfish position
                    flashlight_pos, (x1,x2,y1,y2) = detect_jellyfish(image, detect_light, is_jf_mode,verbose,trackingStartEnd)                    
                    total = int(elapsed_time.value)
                    hours, remainder = divmod(total, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    timestamp = f'{hours:02}:{minutes:02}:{seconds:02}'
                    if flashlight_pos:
                        # Calculate deltas
                        dx, dy = calculate_delta_Pixels(flashlight_pos, center_x, center_y)
                        if recording.value:
                            # mm position of jf in the global coords
                            x = steps_to_mm(x_pos.value, is_jf_mode)
                            y = steps_to_mm(y_pos.value, is_jf_mode)
                            x -= pixels_to_mm(dx,is_jf_mode) # matching to the inverting of the x axis with the camera
                            y += pixels_to_mm(dy,is_jf_mode) # same as above
                            csv_writer.writerow([round(x,3), round(y,3), timestamp, 'SuccTrack', flashlight_pos, (x1,x2,y1,y2)])

                        if motors.value:
                            step_x, step_y = calculate_movement(dx,dy,is_jf_mode)
                            # Send movement command
                            x_pos, y_pos = move(x_pos, y_pos, step_x, step_y, command_queue,is_jf_mode, x_invalid_flag, y_invalid_flag)
                        # Communicate tracking results for display
                        tracking_result_queue.put((flashlight_pos,(x1,x2,y1,y2)), block=False)
                    elif recording.value:    
                        x = steps_to_mm(x_pos.value, is_jf_mode)
                        y = steps_to_mm(y_pos.value, is_jf_mode)
                        csv_writer.writerow([x, y, timestamp, 'FailTrackMotorPos', (x,y), (0,0,0,0)])


                    # Update tracking timestamp
                    last_tracking_time = current_time
                except queue.Empty:
                    # Handle case where no frame is available
                    print("Warning: Frame queue is empty; skipping tracking update.")
                except Exception as e:
                    pass
                    # print(f"Error in tracking thread: {e}")
            elif testingMode.value:
                total = int(elapsed_time.value)
                hours, remainder = divmod(total, 3600)
                minutes, seconds = divmod(remainder, 60)
                timestamp = f'{hours:02}:{minutes:02}:{seconds:02}'

                x = steps_to_mm(x_pos.value, is_jf_mode)
                y = steps_to_mm(y_pos.value, is_jf_mode)
                csv_writer.writerow([x, y, timestamp, 'MotorPos', (x,y), (0,0,0,0)])

            time.sleep(0.001)  # Sleep briefly to prevent excessive CPU usage

def main(x_pos,y_pos,command_queue,keybinds_flag,pixelsCal_flag,is_jf_mode, terminate_event, running_flag, step_size,step_to_mm_checking, homing_error_button,x_invalid_flag, y_invalid_flag,verbose,testingMode,recording,tracking,motors,elapsed_time,reset_timer):
    global boundary
    timestamp = multiprocessing.Array(ctypes.c_char, 100)
    holder = datetime.now().strftime("%Y%m%d_%H%M%S")
    timestamp.value = holder.encode('utf-8')

    recordingStartEnd = multiprocessing.Value('i',0) # 0 is just running. 1 means just started a recording, 2 means just saved a recording
    trackingStartEnd = multiprocessing.Value('i',0) # 0 is just running. 1 means just started tracking. 2 means just ended.

    # Initialize webcam
    cap = cv2.VideoCapture(0)  # Use default webcam (index 0)
    # cap.set(cv2.CAP_PROP_FPS, 30)

    if not cap.isOpened():
        print("Error: Could not open webcam")
        states.running = False
        terminate_event.set()
        running_flag.value = False
        cap.release()
        pygame.quit()
        print("Done")
        return False
    
    # Get camera properties
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = 30 # change if camera settings change
    
    os.environ['SDL_VIDEO_WINDOW_POS'] = "0,30"

    pygame.init()
    text_panel_height = 460
    window_width, window_height = width, height+text_panel_height
    window = pygame.display.set_mode((window_width, window_height))
    pygame.display.set_caption("Tracker")

    ensure_dir('saved_runs')
    
    acq_thread = threading.Thread(target=imageacq, args=(cap,recording, fps))
    acq_thread.start()
    
    tracking_thread = threading.Thread(target=active_tracking_thread, args=(width // 2, height // 2, command_queue, x_pos, y_pos, is_jf_mode,x_invalid_flag, y_invalid_flag,verbose,recording, tracking, motors, testingMode, elapsed_time, timestamp,recordingStartEnd,trackingStartEnd))
    tracking_thread.start()

    writer_thread = threading.Thread(target=recording_writer_thread, args=(recording,), daemon=True)
    writer_thread.start()
    
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 36)

    last_frame_time = time.time()
    frame_count = 0
    missed_tracks = 0 

    crosshair_x = width // 2
    crosshair_y = height // 2
    move_delay = 2  # How many frames to wait between moves
    move_counter = 0  # Frame counter
    
    def recordingHelper(recording,reset_timer,tracking, timestamp, is_jf_mode,recordingStartEnd,verbose):
        global avi_filename
        if not recording.value:
            old_state = tracking.value
            tracking.value = False
            # time.sleep(3)  # Optional: give GPU time to settle

            states.avi_recorder,avi_filename = recordingStart(recording,states.chosenAviType,fps,width,height,timestamp, is_jf_mode,recordingStartEnd,verbose)
            states.start_time = datetime.now()
            reset_timer.value = True
            tracking.value = old_state
        elif recording.value: # deleting
            recordingStartEnd.value = 2
            timeout = time.time() + 5  # 5 seconds timeout
            while recordingStartEnd.value != 0:
                if time.time() > timeout:
                    print("Timeout waiting for tracking process to release files.")
                    break
                time.sleep(0.1)
            
            if states.avi_recorder:
                states.avi_recorder.release()
                states.avi_recorder = None
            timestamp_text = timestamp.value.decode('utf-8').rstrip('\x00')
            mode_str = "Jellyfish" if is_jf_mode.value == 1 else "Larvae"
            folder_path = f'saved_runs/run_{timestamp_text}_{mode_str}'
            if os.path.exists(folder_path):
                shutil.rmtree(folder_path)
            recording.value = False
            print("$$Recording deleted.$$")
            states.start_time = datetime.now()
            reset_timer.value = True

    def setLarvaeHome(x_pos,y_pos, xy_LHpos,is_jf_mode,changeModeFlag):
        if is_jf_mode.value == 0:
            changeModeFlag.value = False
            xy_LHpos[:] = [x_pos.value, y_pos.value]
            print(f"Larvae Home set to ({x_pos.value},{y_pos.value})")
        else:
            print("Cannot set or change larvae home in JF mode.")


    def borderHelper(is_jf_mode,step_size):
        global boundary
        states.boundary_making,boundary = boundaryControl(states.boundary_making,boundary,is_jf_mode,step_size)

    def borderCancelHelper(is_jf_mode, step_size):
        global boundary
        states.boundary_making, boundary = boundaryCancel(states.boundary_making, boundary, is_jf_mode, step_size)

    def borderLoadHelper():
        global boundary
        boundary = load_boundary(is_jf_mode)

    def pixelsCalHelper(pixelsCal_flag,width,height,is_jf_mode):
        nonlocal crosshair_x, crosshair_y
        crosshair_x,crosshair_y = pixelsCalibration(pixelsCal_flag,crosshair_x,crosshair_y,width,height,is_jf_mode)

    changeModeFlag = multiprocessing.Value('b',False)
    xy_LHpos = multiprocessing.Array('i',[-1,-1])
    LH_flag = multiprocessing.Value('b',False)

    button_x = window.get_width() - 130  # inside terminal panel left margin
    button_y = 5
    button_width = 120
    button_height = 20
    onOffColors = [(50, 50, 100),(0, 150, 255)]
    RecordingColors =  [(50, 50, 100),(255, 80, 80)]
    saverColors = [(50, 50, 100),(80, 200, 80)]
    calColors = [(50, 50, 100),(38, 75, 139),(25, 100, 178),(13, 125, 216),(0, 150, 255)]

    buttons = [
        #first col
       Button(320, 570, 150, 50, "Start Recording", lambda: recordingHelper(recording,reset_timer,tracking, timestamp, is_jf_mode, recordingStartEnd,verbose),get_color=lambda: (50, 50, 100),text_dependence=recording,text_if_true="Delete Recording",text_if_false="Start Recording", get_visible=lambda: not recording.value),
       Button(320, 570, 70, 50, "Save Video", 
           lambda: saveHelper(timestamp, recording,reset_timer, tracking, is_jf_mode, recordingStartEnd),
           get_color=lambda: (80, 200, 80),
           get_visible=lambda: recording.value),
       Button(400, 570, 70, 50, "Delete Video", 
           lambda: recordingHelper(recording,reset_timer,tracking, timestamp, is_jf_mode,recordingStartEnd,verbose),
           get_color=lambda: (255, 80, 80),
           get_visible=lambda: recording.value),
       Button(320, 630, 150, 50, "Turn Tracking On", lambda: trackingHelper(tracking, trackingStartEnd), get_color=lambda: onOffColors[tracking.value], text_dependence=tracking,text_if_true="Turn Tracking Off",text_if_false="Turn Tracking On" ),
       Button(320, 690, 150, 50, "Motors on for Tracking", lambda: trackingMotors(motors),get_color=lambda: onOffColors[motors.value], text_dependence=motors,text_if_true="Turn Tracking Motors Off",text_if_false="Turn Tracking Motors On"),
       Button(320, 750, 150, 50, "Arrow Manual Control", lambda: keyBindsControl(keybinds_flag), get_color=lambda: onOffColors[not keybinds_flag.value], text_dependence=keybinds_flag,text_if_true="Turn Motors Arrow Control Off",text_if_false="Turn Motors Arrow Control On"),
       
       #second col
       Button(480, 570, 150, 50, "Home with Error Check", lambda: homingStepsWithErrorCheck(homing_error_button, is_jf_mode, command_queue,x_pos,y_pos, xy_LHpos, x_invalid_flag, y_invalid_flag,LH_flag),get_color = lambda: onOffColors[homing_error_button.value] if is_jf_mode.value == 1 else onOffColors[LH_flag.value]),
       Button(480, 630, 150, 50, "Change Mode", lambda: changeModePopUp(is_jf_mode,x_pos,y_pos,step_size, window, font, homing_error_button, command_queue, x_invalid_flag, y_invalid_flag, changeModeFlag,xy_LHpos,LH_flag), get_visible=lambda: not changeModeFlag.value),
       Button(480, 630, 150, 50, "Set Larvae Home", lambda: setLarvaeHome(x_pos,y_pos, xy_LHpos,is_jf_mode,changeModeFlag), get_color=lambda: (255, 165, 0), get_visible=lambda: changeModeFlag.value),
       Button(480, 690, 150, 50, "Change Larvae Home", lambda: setLarvaeHome(x_pos,y_pos, xy_LHpos,is_jf_mode,changeModeFlag), get_color=None),
       Button(480, 750, 150, 50, "Pixels Calibration", lambda: pixelsCalHelper(pixelsCal_flag,width,height,is_jf_mode),get_color=lambda: calColors[pixelsCal_flag.value]),

       #third col
       Button(640, 570, 150, 50, "Make Border", lambda: borderHelper(is_jf_mode, step_size),get_color=lambda: onOffColors[states.boundary_making], get_visible=lambda: not states.boundary_making),
       Button(640, 570, 70, 50, "Save Border", 
           lambda: borderHelper(is_jf_mode, step_size),
           get_color=lambda: (80, 200, 80),
           get_visible=lambda: states.boundary_making),
       Button(720, 570, 70, 50, "Delete Border", 
           lambda: borderCancelHelper(is_jf_mode, step_size),
           get_color=lambda: (255, 80, 80),
           get_visible=lambda: states.boundary_making),
       Button(640, 630, 150, 50, "Show Border", lambda: borderShowHelper(),get_color=lambda: onOffColors[states.show_boundary]),
       Button(640, 690, 150, 50, "Load Border", lambda: borderLoadHelper()),
       Button(640, 750, 150, 50, "Steps Calibration", lambda: stepsCalibration(step_size, step_to_mm_checking, x_pos, y_pos,is_jf_mode),get_color=lambda: calColors[step_to_mm_checking.value]),

        #fourth col
       Button(800, 570, 150, 50, "Help", lambda: openHelp()),       
       Button(800, 630, 150, 50, "Verbose Mode", lambda: verboseHelper(command_queue,verbose),get_color=lambda: onOffColors[verbose.value]),
       Button(800, 690, 150, 50, "Testing Function", lambda: testingHelper(testingMode), get_color=lambda: onOffColors[testingMode.value]),
       Button(800, 750, 150, 50, "", lambda: None),

    ]

    with open("ready.txt", "w") as f:
        f.write("ready")

    while states.running:
        window.fill((0, 0, 0))  # Clear full window

        mouse_pos = pygame.mouse.get_pos()
        mouse_pressed = pygame.mouse.get_pressed()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if recording.value:
                    cont = popup_save_recording(window, font, recordingSave, states.avi_recorder, timestamp, recording, avi_filename, is_jf_mode,recordingStartEnd)
                    if not cont:
                        states.running = False
                        terminate_event.set()
                        running_flag.value = False
                        os.remove("ready.txt")
                else:
                    states.running = False
                    terminate_event.set()
                    running_flag.value = False
                    os.remove("ready.txt")
                    break

                
        if pixelsCal_flag.value in (2,3):
            keys = pygame.key.get_pressed()
            move_counter += 1
            if move_counter >= move_delay:
                if keys[pygame.K_LEFT]:
                    crosshair_x = max(0, crosshair_x - 1)
                if keys[pygame.K_RIGHT]:
                    crosshair_x = min(width - 1, crosshair_x + 1)
                if keys[pygame.K_UP]:
                    crosshair_y = max(0, crosshair_y - 1)
                if keys[pygame.K_DOWN]:
                    crosshair_y = min(height - 1, crosshair_y + 1)
                if move_counter >= move_delay + 1:
                    move_counter = 0  # Reset after moving

        font = pygame.font.SysFont("consolas", 16)
    
        # BUTTON LOGIC
        for button in buttons:
            if button.is_visible():
                button.handle_event(event, mouse_pos, mouse_pressed)
                button.draw(window)

        if states.boundary_making:
            boundary.append((x_pos.value,y_pos.value))
        if states.shared_image is not None:
            # Handle recording
            # if recording.value and states.avi_recorder is not None:
            #     states.avi_recorder.write(states.shared_image)

            # Convert webcam image for pygame display
            rgb_frame = cv2.cvtColor(states.shared_image, cv2.COLOR_BGR2RGB)
            height, width, channels = rgb_frame.shape
            py_image = pygame.surfarray.make_surface(rgb_frame.swapaxes(0, 1))
            # py_image = pygame.transform.scale(py_image, (window_width, window_height))
            # py_image_mirror = pygame.transform.flip(py_image, True, False) # mirrored to have live stream make more
            window.blit(py_image, (0, 0))   
            
            # Draw crosshair at the center of the screen
            center_x = width // 2
            center_y = height // 2
            line_length = 20  # Length of each line segment
            line_color = (255, 0, 0)  # Red color
            line_thickness = 1

            # Draw horizontal line centered at crosshair_x, crosshair_y
            pygame.draw.line(window, line_color, 
                            (crosshair_x - line_length, crosshair_y),
                            (crosshair_x + line_length, crosshair_y),
                            line_thickness)

            # Draw vertical line centered at crosshair_x, crosshair_y
            pygame.draw.line(window, line_color,
                            (crosshair_x, crosshair_y - line_length),
                            (crosshair_x, crosshair_y + line_length),
                            line_thickness)

            try:
                (flashlight_pos,(x1,x2,y1,y2)) = tracking_result_queue.get_nowait()
                if flashlight_pos:
                    pygame.draw.circle(window, (0, 255, 0), flashlight_pos, 10)
                    
                    # First calculate the top-left corner, width, and height - test this out!!!
                    top_left_x = min(x1, x2)
                    top_left_y = min(y1, y2)
                    boxwidth = abs(x2 - x1)
                    boxheight = abs(y2 - y1)

                    # Draw the rectangle outline
                    pygame.draw.rect(window, (0, 255, 255), (top_left_x, top_left_y, boxwidth, boxheight), 2)  # last '2' is the line thickness
                    
                    # pygame.draw.circle(window, (0, 255, 255), (x1,y1), 10)
                    # pygame.draw.circle(window, (0, 255, 255), (x2,y2), 10)
                    trackingFoundSomething = True
                    missed_tracks = 0
            except queue.Empty:
                missed_tracks += 1
                if missed_tracks >= 5:
                    trackingFoundSomething = False


            if states.show_boundary: 
                if boundary != []: # boundary is currently in steps
                    xs, ys = x_pos.value, y_pos.value
                    dx = mm_to_steps(pixels_to_mm(width//2, is_jf_mode), is_jf_mode)
                    dy = mm_to_steps(pixels_to_mm(height//2, is_jf_mode), is_jf_mode)
                    viewing_window_s = (xs-dx,xs+dx,ys-dy,ys+dy)
                    x_min_s, x_max_s, y_min_s, y_max_s = viewing_window_s
                    boundary_within_window = [
                        (x, y) for x, y in boundary if x_min_s <= x <= x_max_s and y_min_s <= y <= y_max_s
                    ] # list of pts that are in the window
                    boundary_shifted = [(dx+xs-x,dy+ys-y) for x,y in boundary_within_window]
                    boundary_pixels_shifted = [(mm_to_pixels(steps_to_mm(x, is_jf_mode), is_jf_mode),mm_to_pixels(steps_to_mm(y, is_jf_mode), is_jf_mode)) for x,y in boundary_shifted]
                    for b in boundary_pixels_shifted:
                        pygame.draw.circle(window, (0, 0, 255), (b[0], b[1]), 5)  
    

            total = int(elapsed_time.value)
            hours, remainder = divmod(total, 3600)
            minutes, seconds = divmod(remainder, 60)
            if recording.value:
                pygame.draw.circle(window, (255, 0, 0), (width-20,20), 8)

            # Determine status values
            if tracking.value:
                if trackingFoundSomething:
                    tracking_status = "Tracking On | Status: [OK]"
                else:
                    tracking_status = "Tracking On | Status: [FAIL]" 
            else:
                tracking_status = "Tracking Off"

            status_text = (
                f"{'● Recording' if recording.value else 'Not Recording'}\n"
                f"Duration: {hours:02}:{minutes:02}:{seconds:02}\n"
                f"{tracking_status}\n"
                f" \n"
                f"{'Tracking Motors: On' if motors.value else 'Tracking Motors: Off'}\n"
                f"{'Border Visualization: On' if states.show_boundary else 'Border Visualization: Off'}\n"
                f"Mode: {mode_string(is_jf_mode)}\n"
                f"{f'X Pos (steps): {x_pos.value}' if verbose.value else ''}\n"
                f"{f'Y Pos (steps): {y_pos.value}' if verbose.value else ''}\n"
            )

            lines = status_text.split('\n')
            y_offset = 570

            for line in lines:
                if ("Recording" in line) or ("Duration" in line):
                    color = (255, 80, 80) if recording.value else (173, 216, 230)  # red if recording else light blue
                elif "[OK]" in line:
                    color = (0, 180, 0)  # green
                elif "[FAIL]" in line:
                    color = (180, 0, 0)  # red
                else:
                    color = (173, 216, 230)  # light blue for everything else

                line_surface = font.render(line, True, color)
                window.blit(line_surface, (10, y_offset))
                y_offset += font.get_linesize()
            pygame.display.flip()
        
        clock.tick(30)  # Keep at 60 FPS for smooth display
        
        frame_count += 1
        if frame_count == 900: # should display roughly every 30 sec
            current_time = time.time()
            frames = 900 / (current_time - last_frame_time)
            frame_count = 0
            last_frame_time = current_time
            print(f"[{hours:02}:{minutes:02}:{seconds:02}] AVG GUI FPS: {frames:.1f}")
    
    if recording.value and states.avi_recorder:
        states.avi_recorder.release()
        states.avi_recorder = None
    
    acq_thread.join()
    tracking_thread.join()
    writer_thread.join()
    cap.release()
    pygame.quit()
    print("Done")
    return True