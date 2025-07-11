import sys
import numpy as np
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
from Utils.log import log
from Utils.RollingLog import RollingLog
from Utils.LiveStreamUtilFuncs import ensure_dir, draw_log_terminal
from Utils.Boundaries import load_boundary
from Utils import states
from Utils.ButtonPresses import homingStepsWithErrorCheck, saveHelper, trackingHelper, trackingMotors, borderShowHelper, testingHelper, verboseHelper, openHelp, clear_log_callback
from Utils.changeModePopUp import changeModePopUp
from multiprocessing import Manager

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

def run_live_stream_record(x_pos,y_pos,command_queue,keybinds_flag,pixelsCal_flag,is_jf_mode, terminate_event, running_flag,step_size,step_to_mm_checking,homing_error_button,log_queue,x_invalid_flag, y_invalid_flag,verbose,testingMode,recording,tracking,motors):
    if main(x_pos,y_pos,command_queue,keybinds_flag,pixelsCal_flag,is_jf_mode, terminate_event, running_flag, step_size,step_to_mm_checking,homing_error_button,log_queue,x_invalid_flag, y_invalid_flag,verbose,testingMode,recording,tracking,motors):
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
                            print("Recorder closed while flushing queue.")
                            break
                        else:
                            raise
            except queue.Empty:
                time.sleep(0.001)

        else:
            time.sleep(0.01)


last_time = time.time()
frames = 0
def imageacq(cam, recording, fps, log_queue):
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
                    log("Warning: Frame is not a valid NumPy array.", log_queue)

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
                log("Failed to capture frame from camera", log_queue)

        except Exception as ex:
            log(f'Error in image acquisition: {ex}', log_queue)

    # Clean up on exit
    if states.avi_recorder is not None:
        states.avi_recorder.release()


def active_tracking_thread(center_x, center_y, command_queue, x_pos, y_pos, is_jf_mode,log_queue,x_invalid_flag, y_invalid_flag,verbose,step_tracking_data,recording, tracking,motors, testingMode):    
    last_tracking_time = time.time()
    while states.running:
        current_time = time.time()
        if current_time - last_tracking_time >= TRACKING_INTERVAL:
            if tracking.value:
                try:
                    image = image_queue.get(timeout=1)  # Wait for the next frame

                    # Verify that the image is a valid NumPy array
                    if not isinstance(image, np.ndarray):
                        log("Warning: Image from queue is not a valid NumPy array.",log_queue)
                        continue
                    
                    # Check the shape consistency
                    if image.ndim != 3 or image.shape[2] != 3:
                        log(f"Warning: Unexpected image shape {image.shape}, converting to RGB.",log_queue)
                        if image.ndim == 2:  # Grayscale image
                            image = np.stack((image,) * 3, axis=-1)
                        else:
                            continue
                    
                    # testing feature
                    detect_light = False # normal setting to track jf
                    # detect_light = True # testing mode - returns x,y of brightest spot in frame

                    # Use YOLO to detect jellyfish position
                    flashlight_pos, (x1,x2,y1,y2) = detect_jellyfish(image, detect_light, is_jf_mode,log_queue,verbose)
                    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-2] 
                    if flashlight_pos:
                        # Calculate deltas
                        dx, dy = calculate_delta_Pixels(flashlight_pos, center_x, center_y)
                        if recording.value:
                            # x_pos + dx thing and y !!!!!!!!!!!!!!
                            # mm position of jf in the global coords
                            x = steps_to_mm(x_pos.value, is_jf_mode)
                            y = steps_to_mm(y_pos.value, is_jf_mode)
                            x -= pixels_to_mm(dx,is_jf_mode) # matching to the inverting of the x axis with the camera
                            y += pixels_to_mm(dy,is_jf_mode) # same as above
                            step_tracking_data.append((round(x,3), round(y,3), timestamp, 'SuccTrack'))                        
                        if motors.value:
                            step_x, step_y = calculate_movement(dx,dy,is_jf_mode)
                            # Send movement command
                            x_pos, y_pos = move(x_pos, y_pos, step_x, step_y, command_queue,is_jf_mode,x_invalid_flag, y_invalid_flag)
                            
                        # Communicate tracking results for display
                        tracking_result_queue.put((flashlight_pos,(x1,x2,y1,y2)), block=False)
                    elif recording.value:    
                        x = steps_to_mm(x_pos.value, is_jf_mode)
                        y = steps_to_mm(y_pos.value, is_jf_mode)
                        step_tracking_data.append((x, y, timestamp, 'FailTrackMotorPos'))

                    # Update tracking timestamp
                    last_tracking_time = current_time
                except queue.Empty:
                    # Handle case where no frame is available
                    log("Warning: Frame queue is empty; skipping tracking update.",log_queue)
                except Exception as e:
                    pass
                    # log(f"Error in tracking thread: {e}",log_queue)
            elif testingMode.value:
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-2] 
                x = steps_to_mm(x_pos.value, is_jf_mode)
                y = steps_to_mm(y_pos.value, is_jf_mode)
                step_tracking_data.append((x, y, timestamp, 'MotorPos'))
            time.sleep(0.001)  # Sleep briefly to prevent excessive CPU usage

def main(x_pos,y_pos,command_queue,keybinds_flag,pixelsCal_flag,is_jf_mode, terminate_event, running_flag, step_size,step_to_mm_checking, homing_error_button,log_queue,x_invalid_flag, y_invalid_flag,verbose,testingMode,recording,tracking,motors):
    global boundary
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    manager = Manager()
    step_tracking_data = manager.list()

    # Initialize webcam
    cap = cv2.VideoCapture(0)  # Use default webcam (index 0)
    # cap.set(cv2.CAP_PROP_FPS, 30)

    if not cap.isOpened():
        log("Error: Could not open webcam",log_queue)
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
    
    pygame.init()
    text_panel_height = 320
    window_width, window_height = width+500, height+text_panel_height
    window = pygame.display.set_mode((window_width, window_height))
    pygame.display.set_caption("Camera Live View with Flashlight Tracking")
    
    ensure_dir('saved_tracking_videos')
    ensure_dir('saved_tracking_csvs')
    
    acq_thread = threading.Thread(target=imageacq, args=(cap,recording, fps, log_queue))
    acq_thread.start()
    
    tracking_thread = threading.Thread(target=active_tracking_thread, args=(width // 2, height // 2, command_queue, x_pos, y_pos, is_jf_mode,log_queue,x_invalid_flag, y_invalid_flag,verbose,step_tracking_data,recording, tracking, motors, testingMode))
    tracking_thread.start()

    writer_thread = threading.Thread(target=recording_writer_thread, args=(recording,), daemon=True)
    writer_thread.start()
    
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 36)

    last_frame_time = time.time()
    frame_count = 0
    
    crosshair_x = width // 2
    crosshair_y = height // 2
    move_delay = 2  # How many frames to wait between moves
    move_counter = 0  # Frame counter
    
    def recordingHelper(log_queue,step_tracking_data,recording):
        global timestamp, avi_filename
        if not recording.value:
            states.avi_recorder,timestamp,avi_filename = recordingStart(recording,states.chosenAviType,fps,width,height,log_queue,step_tracking_data)
            states.start_time = datetime.now()
        elif recording.value: # deleting
            if states.avi_recorder:
                states.avi_recorder.release()
                states.avi_recorder = None
            if os.path.exists(avi_filename):
                os.remove(avi_filename)
            recording.value = False
            log("$$Recording deleted.$$", log_queue)
            states.start_time = datetime.now()

    def setLarvaeHome(x_pos,y_pos, xy_LHpos,is_jf_mode,changeModeFlag,log_queue):
        if is_jf_mode.value == 0:
            changeModeFlag.value = False
            xy_LHpos[:] = [x_pos.value, y_pos.value]
            log(f"Larvae Home set to ({x_pos.value},{y_pos.value})", log_queue)
        else:
            log("Cannot set or change larvae home in JF mode.", log_queue)


    def borderHelper(is_jf_mode,log_queue):
        global boundary
        states.boundary_making,boundary = boundaryControl(states.boundary_making,boundary,is_jf_mode,log_queue)

    def borderCancelHelper(log_queue):
        global boundary
        states.boundary_making, boundary = boundaryCancel(states.boundary_making, boundary, log_queue)

    def borderLoadHelper():
        global boundary
        nonlocal log_queue
        boundary = load_boundary(is_jf_mode, log_queue)

    def pixelsCalHelper(pixelsCal_flag,width,height,is_jf_mode, log_queue):
        nonlocal crosshair_x, crosshair_y
        crosshair_x,crosshair_y = pixelsCalibration(pixelsCal_flag,crosshair_x,crosshair_y,width,height,is_jf_mode, log_queue)

    changeModeFlag = multiprocessing.Value('b',False)
    xy_LHpos = multiprocessing.Array('i',[-1,-1])

    rolling_log = RollingLog()
    button_x = window.get_width() - 130  # inside terminal panel left margin
    button_y = 5
    button_width = 120
    button_height = 20
    onOffColors = [(50, 50, 100),(0, 150, 255)]
    RecordingColors =  [(50, 50, 100),(255, 80, 80)]
    saverColors = [(50, 50, 100),(80, 200, 80)]
    calColors = [(50, 50, 100),(38, 75, 139),(25, 100, 178),(13, 125, 216),(0, 150, 255)]

    buttons = [
       Button(330, 570, 150, 50, "Start Recording", lambda: recordingHelper(log_queue,step_tracking_data,recording),get_color=lambda: (50, 50, 100),text_dependence=recording,text_if_true="Delete Recording",text_if_false="Start Recording", get_visible=lambda: not recording.value),
       Button(330, 570, 70, 50, "Save Video", 
           lambda: saveHelper(log_queue, timestamp, step_tracking_data, recording),
           get_color=lambda: (80, 200, 80),
           get_visible=lambda: recording.value),
       Button(410, 570, 70, 50, "Delete Video", 
           lambda: recordingHelper(log_queue,step_tracking_data,recording),
           get_color=lambda: (255, 80, 80),
           get_visible=lambda: recording.value),
       
       Button(330, 630, 150, 50, "Turn Tracking On", lambda: trackingHelper(tracking, log_queue), get_color=lambda: onOffColors[tracking.value], text_dependence=tracking,text_if_true="Tracking On",text_if_false="Tracking Off" ),
       Button(330, 690, 150, 50, "Motors on for Tracking", lambda: trackingMotors(motors,log_queue),get_color=lambda: onOffColors[motors.value], text_dependence=motors,text_if_true="Tracking Motors On",text_if_false="Tracking Motors Off"),
       Button(330, 750, 150, 50, "Arrow Manual Control", lambda: keyBindsControl(keybinds_flag,log_queue), get_color=lambda: onOffColors[not keybinds_flag.value], text_dependence=keybinds_flag,text_if_true="Motors Arrow Control On",text_if_false="Motors Arrow Control Off"),
       
       Button(490, 570, 150, 50, "Change Larvae Home", lambda: setLarvaeHome(x_pos,y_pos, xy_LHpos,is_jf_mode,changeModeFlag,log_queue), get_color=None),
       Button(490, 630, 150, 50, "Home with Error Check", lambda: homingStepsWithErrorCheck(homing_error_button, is_jf_mode, command_queue,x_pos,y_pos, xy_LHpos, x_invalid_flag, y_invalid_flag, log_queue),get_color=lambda: onOffColors[homing_error_button.value]),
       Button(490, 690, 150, 50, "Help", lambda: openHelp(log_queue)),       
       Button(490, 750, 150, 50, "Verbose Mode", lambda: verboseHelper(log_queue,command_queue,verbose),get_color=lambda: onOffColors[verbose.value]),

       Button(650, 570, 150, 50, "Make Border", lambda: borderHelper(is_jf_mode, log_queue),get_color=lambda: onOffColors[states.boundary_making], get_visible=lambda: not states.boundary_making),
       Button(650, 570, 70, 50, "Save Border", 
           lambda: borderHelper(is_jf_mode, log_queue),
           get_color=lambda: (80, 200, 80),
           get_visible=lambda: states.boundary_making),
       Button(730, 570, 70, 50, "Delete Border", 
           lambda: borderCancelHelper(log_queue),
           get_color=lambda: (255, 80, 80),
           get_visible=lambda: states.boundary_making),
       
       Button(650, 630, 150, 50, "", lambda: None),
       Button(650, 690, 150, 50, "Show Border", lambda: borderShowHelper(),get_color=lambda: onOffColors[states.show_boundary]),
       Button(650, 750, 150, 50, "Load Border", lambda: borderLoadHelper()),
       
       Button(810, 570, 150, 50, "Steps Calibration", lambda: stepsCalibration(step_size, step_to_mm_checking, x_pos, y_pos,is_jf_mode, log_queue),get_color=lambda: calColors[step_to_mm_checking.value]),
       Button(810, 630, 150, 50, "Pixels Calibration", lambda: pixelsCalHelper(pixelsCal_flag,width,height,is_jf_mode, log_queue),get_color=lambda: calColors[pixelsCal_flag.value]),
       Button(810, 690, 150, 50, "Change Mode", lambda: changeModePopUp(is_jf_mode,x_pos,y_pos,step_size,log_queue, window, font, homing_error_button, command_queue, x_invalid_flag, y_invalid_flag, changeModeFlag,xy_LHpos), get_visible=lambda: not changeModeFlag.value),
       Button(810, 690, 150, 50, "Set Larvae Home", lambda: setLarvaeHome(x_pos,y_pos, xy_LHpos,is_jf_mode,changeModeFlag,log_queue), get_color=lambda: (255, 165, 0), get_visible=lambda: changeModeFlag.value),


       Button(810, 750, 150, 50, "Testing Function", lambda: testingHelper(log_queue,testingMode), get_color=lambda: onOffColors[testingMode.value]),

       Button(button_x, button_y, button_width, button_height,
                        "Clear Term", lambda: clear_log_callback(rolling_log,log_queue),
                        get_color=lambda: (255, 50, 50))  # red button
    ]
    
    scroll_offset = 0
    scroll_speed = 3
    is_dragging_scrollbar = False
    user_scrolled_up = False

    column_start_x = 970
    scrollbar_width = 8
    margin = 10
    column_width = window.get_width() - column_start_x
    max_width = column_width - 2 * margin - scrollbar_width

    with open("ready.txt", "w") as f:
        f.write("ready")

    while states.running:
        window.fill((0, 0, 0))  # Clear full window

        mouse_pos = pygame.mouse.get_pos()
        mouse_pressed = pygame.mouse.get_pressed()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if recording.value:
                    cont = popup_save_recording(window, font, recordingSave, states.avi_recorder, timestamp, step_tracking_data, recording, avi_filename, log_queue)
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

            elif event.type == pygame.MOUSEWHEEL:
                font = pygame.font.SysFont("consolas", 16)
                total_lines = rolling_log.total_lines()
                visible_lines = (window.get_height() - 50) // 18
                max_scroll = max(0, total_lines - visible_lines)

                scroll_offset -= event.y * scroll_speed
                scroll_offset = max(0, min(scroll_offset, max_scroll))
                user_scrolled_up = scroll_offset < max_scroll

            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_x, mouse_y = pygame.mouse.get_pos()
                scrollbar_x = window.get_width() - 8  # Scrollbar left edge
                scrollbar_width = 8
                panel_height = window.get_height()

                font = pygame.font.SysFont("consolas", 16)
                total_lines = rolling_log.total_lines()
                visible_lines = (panel_height - 50) // 18

                if total_lines <= visible_lines:
                    continue
                scrollbar_height = int((visible_lines / total_lines) * panel_height)
                scrollbar_track_height = panel_height - scrollbar_height
                scrollbar_pos = int((scroll_offset / max(1, total_lines - visible_lines)) * scrollbar_track_height)

                scrollbar_rect = pygame.Rect(scrollbar_x, scrollbar_pos, scrollbar_width, scrollbar_height)
                if scrollbar_rect.collidepoint(mouse_x, mouse_y):
                    is_dragging_scrollbar = True
                    drag_start_y = mouse_y
                    drag_start_offset = scroll_offset

            elif event.type == pygame.MOUSEBUTTONUP:
                is_dragging_scrollbar = False

            elif event.type == pygame.MOUSEMOTION and is_dragging_scrollbar:
                mouse_y = pygame.mouse.get_pos()[1]
                delta_y = mouse_y - drag_start_y

                font = pygame.font.SysFont("consolas", 16)
                total_lines = rolling_log.total_lines()
                visible_lines = (window.get_height() - 50) // 18
                max_scroll = max(0, total_lines - visible_lines)

                panel_height = window.get_height()
                scrollbar_height = int((visible_lines / total_lines) * panel_height)
                scrollbar_track_height = panel_height - scrollbar_height

                if scrollbar_track_height > 0:
                    proportion = delta_y / scrollbar_track_height
                    scroll_offset = drag_start_offset + int(proportion * max_scroll)
                    scroll_offset = max(0, min(scroll_offset, max_scroll))
                    user_scrolled_up = scroll_offset < max_scroll

                
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
        
        while not log_queue.empty():
                msg = log_queue.get()
                rolling_log.append(msg)

       # Auto-scroll logic
        font = pygame.font.SysFont("consolas", 16)
        total_lines = rolling_log.total_lines()
        visible_lines = (window.get_height() - 50) // 18  # same as draw_log_terminal
        max_scroll = max(0, total_lines - visible_lines)

        if not user_scrolled_up:
            scroll_offset = max_scroll  # Stick to bottom when new logs come in
        else:
            scroll_offset = min(scroll_offset, max_scroll)  # Clamp
        if scroll_offset >= max_scroll - 1:  # Close enough to bottom
            user_scrolled_up = False
        # Draw the log terminal with current scroll offset
        draw_log_terminal(window, rolling_log, scroll_offset)
    
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
                    pygame.draw.circle(window, (0, 255, 255), (x1,y1), 10)
                    pygame.draw.circle(window, (0, 255, 255), (x2,y2), 10)
                    trackingFoundSomething = True
            except queue.Empty:
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
    

            current_time = datetime.now() - states.start_time  # This is a timedelta object
            elapsed_seconds = int(current_time.total_seconds())
            hours, remainder = divmod(elapsed_seconds, 3600)
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
                f"{'Boundary Visualization: On' if states.show_boundary else 'Boundary Visualization: Off'}\n"
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
        if frame_count == 600: # normally 600 is good speed
            current_time = time.time()
            frames = 600 / (current_time - last_frame_time)
            frame_count = 0
            last_frame_time = current_time
            log(f"FPS: {frames:.1f}",log_queue)
    
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