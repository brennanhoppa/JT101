import sys
import numpy as np
import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame # type: ignore
import threading
import queue
from datetime import datetime
import time
from Utils.JellyTrackingFunctions import detect_jellyfish,calculate_movement, calculate_delta_Pixels, mm_to_pixels, pixels_to_mm, mm_to_steps, steps_to_mm, mode_string
from Utils.ManualMotorInput import move
from Utils.Boundaries import save_boundaries, boundary_to_steps, boundary_to_mm_from_steps, boundary_to_pixels_from_steps, load_boundaries
# import PySpin # type: ignore
import cv2 #type: ignore
import tkinter as tk
from tkinter import filedialog
from Utils.ButtonPresses import recordingStart, AviType, recordingSave, boundaryControl, boundaryCancel,pixelsCalibration, keyBindsControl, change_mode, homingSteps, homingStepsWithErrorCheck, stepsCalibration
from Utils.CONTROLS import CONTROLS
from Utils.CALIBRATIONPIECE_MM import CALIBRATIONPIECE_MM
from Utils.Button import Button
from Utils.savePopUp import popup_save_recording

NUM_IMAGES = 300
name = 'TESTBINNING2'
running = True
recording = False
tracking = False
motors = False
boundary_making = False
shared_image = None
avi_recorder = None

boundary = []
# or write filename to load in a boundary
# e.g.
# boundary_filename = "C:\\Users\\JellyTracker\\Desktop\\JellyFishTrackingPC-main\\saved_boundaries_mm\\new_bounds.csv"
# boundary_mm = load_boundaries(boundary_filename)
# boundary = boundary_to_steps(boundary_mm)

show_boundary = False

# Tracking settings
TRACKING_INTERVAL = 1 / 50  # 50Hz tracking rate

# Queue for inter-thread communication
image_queue = queue.Queue(maxsize=5)
tracking_result_queue = queue.Queue(maxsize=5)

# Step tracking
# cumulative_steps = {'x': 0, 'y': 0}
step_tracking_data = []

chosenAviType = AviType.H264
start_time = datetime.now()
avi_filename = ""

def run_live_stream_record(x_pos,y_pos,command_queue,homing_flag,keybinds_flag,pixelsCal_flag,is_jf_mode, terminate_event, running_flag,step_size,step_to_mm_checking,homing_button,homing_error_button):
    if main(x_pos,y_pos,command_queue,homing_flag,keybinds_flag,pixelsCal_flag,is_jf_mode, terminate_event, running_flag, step_size,step_to_mm_checking,homing_button,homing_error_button):
        sys.exit(0)
    else:
        sys.exit(1)

def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def webcam_image_to_pygame(frame):
    # Convert BGR to RGB for pygame
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    # Convert to contiguous array
    rgb_frame = np.ascontiguousarray(rgb_frame.astype(np.uint8))
    # Create pygame surface
    return pygame.surfarray.make_surface(rgb_frame.swapaxes(0, 1))

def load_boundary(is_jf_mode):
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(title="Select a File", filetypes=[("CSV files", "*.csv"), ("All Files", "*.*")])
    if file_path:  # If a file was selected
        print(f"Selected file: {file_path}")
        try:
            boundary_mm = load_boundaries(file_path)
            return boundary_to_steps(boundary_mm,is_jf_mode)
        except:
            print('Incorrect file loaded')
    else:
        print("No file selected.")
        return []

def imageacq(cam):
    global running, shared_image, recording, avi_recorder
    
    while running:
        try:
            ret, frame = cam.read()
            if ret:
                # Convert for display
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Save frame for display
                shared_image = frame

                # Put in queue for tracking
                if isinstance(frame, np.ndarray):
                    try:
                        image_queue.put(frame, block=False)
                    except queue.Full:
                        try:
                            image_queue.get_nowait()  # Remove the oldest frame if queue is full
                            image_queue.put(frame, block=False)
                        except queue.Empty:
                            pass
                else:
                    print("Warning: Frame conversion failed; not a valid NumPy array.")
            else:
                print("Failed to capture frame from webcam")
        except Exception as ex:
            print(f'Error in image acquisition: {ex}')
    
    # Clean up video writer if it exists
    if avi_recorder is not None:
        avi_recorder.release()


def active_tracking_thread(center_x, center_y, command_queue, x_pos, y_pos, is_jf_mode):
    global running, tracking, motors, recording, step_tracking_data
    last_tracking_time = time.time()
    
    while running:
        if tracking:
            try:
                current_time = time.time()
                if current_time - last_tracking_time >= TRACKING_INTERVAL:
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
                    flashlight_pos, (x1,x2,y1,y2) = detect_jellyfish(image, detect_light, is_jf_mode)
                    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-2] 
                    if flashlight_pos:
                        # Calculate deltas
                        dx, dy = calculate_delta_Pixels(flashlight_pos, center_x, center_y)
                        # print(dx,dy)
                        if recording:
                            # x_pos + dx thing and y !!!!!!!!!!!!!!
                            # mm position of jf in the global coords
                            x = steps_to_mm(x_pos.value, is_jf_mode)
                            y = steps_to_mm(y_pos.value, is_jf_mode)
                            x -= dx # matching to the inverting of the x axis with the camera
                            y += dy # same as above
                            step_tracking_data.append((x, y, timestamp))                        
                        if motors:
                            step_x, step_y = calculate_movement(dx,dy,is_jf_mode)
                            # Send movement command
                            x_pos, y_pos = move(x_pos, y_pos, int(-1*round(step_x*1.3,0)), int(round(step_y*1.3,0)), command_queue,is_jf_mode)
                            
                        # Communicate tracking results for display
                        tracking_result_queue.put((flashlight_pos,(x1,x2,y1,y2)), block=False)
                    elif recording:    
                        step_tracking_data.append((None, None, timestamp))

                    # Update tracking timestamp
                    last_tracking_time = current_time
            except queue.Empty:
                # Handle case where no frame is available
                print("Warning: Frame queue is empty; skipping tracking update.")
            except Exception as e:
                print(f"Error in tracking thread: {e}")
        time.sleep(0.001)  # Sleep briefly to prevent excessive CPU usage

def main(x_pos,y_pos,command_queue,homing_flag,keybinds_flag,pixelsCal_flag,is_jf_mode, terminate_event, running_flag, step_size,step_to_mm_checking,homing_button,homing_error_button):
    global running, shared_image, chosenAviType, recording, tracking, motors, boundary_making, boundary, show_boundary, avi_recorder, step_tracking_data, start_time
      
    # Initialize webcam
    cap = cv2.VideoCapture(0)  # Use default webcam (index 0)
    if not cap.isOpened():
        print("Error: Could not open webcam")
        return False
    
    # Get camera properties
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = 60 # change if camera settings change
    
    pygame.init()
    text_panel_height = 320
    window_width, window_height = width+100, height+text_panel_height
    window = pygame.display.set_mode((window_width, window_height))
    pygame.display.set_caption("Camera Live View with Flashlight Tracking")
    
    ensure_dir('saved_tracking_videos')
    ensure_dir('saved_tracking_csvs')
    
    acq_thread = threading.Thread(target=imageacq, args=(cap,))
    acq_thread.start()
    
    tracking_thread = threading.Thread(target=active_tracking_thread, args=(width // 2, height // 2, command_queue, x_pos, y_pos, is_jf_mode))
    tracking_thread.start()
    
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 36)

    last_frame_time = time.time()
    frame_count = 0
    
    crosshair_x = width // 2
    crosshair_y = height // 2
    move_delay = 2  # How many frames to wait between moves
    move_counter = 0  # Frame counter

    video_writer = None
    
    def homing_set(homing_button):
        homing_button.value = 1
    
    def homing_set_with_error(homing_error_button):
        homing_error_button.value = 1

    def recordingHelper():
        global recording, avi_recorder, step_tracking_data, timestamp, start_time,avi_filename
        if not recording:
            recording,avi_recorder,step_tracking_data,timestamp,avi_filename = recordingStart(recording,chosenAviType,fps,width,height)
            start_time = datetime.now()

    def saveHelper():
        global recording, start_time
        if recording:
            recording = recordingSave(recording,avi_recorder,timestamp,step_tracking_data)
            start_time = datetime.now() 
    
    def trackingHelper():
        global tracking
        tracking = not tracking

    def trackingMotors():
        global motors
        motors = not motors
    
    def borderHelper(is_jf_mode):
        global boundary, boundary_making
        boundary_making,boundary = boundaryControl(boundary_making,boundary,is_jf_mode)

    def borderCancelHelper():
        global boundary, boundary_making
        boundary_making, boundary = boundaryCancel(boundary_making, boundary)

    def borderShowHelper():
        global show_boundary
        show_boundary = not show_boundary

    def borderLoadHelper():
        global boundary
        boundary = load_boundary(is_jf_mode)

    def pixelsCalHelper(pixelsCal_flag,width,height,is_jf_mode):
        nonlocal crosshair_x, crosshair_y
        crosshair_x,crosshair_y = pixelsCalibration(pixelsCal_flag,crosshair_x,crosshair_y,width,height,is_jf_mode)

    def openHelp():
        os.startfile("C:\\Users\\JellyTracker\\Desktop\\HelpDoc.pdf")

    buttons = [
       Button(370, 570, 150, 50, "Home", lambda: homing_set(homing_button)),
       Button(370, 630, 150, 50, "Home w EC", lambda: homing_set_with_error(homing_error_button)),
       Button(370, 690, 150, 50, "Steps Cal", lambda: stepsCalibration(step_size, step_to_mm_checking, x_pos, y_pos,is_jf_mode)),
       Button(370, 750, 150, 50, "Change Mode", lambda: change_mode(is_jf_mode,x_pos,y_pos,step_size)),
       Button(530, 570, 150, 50, "Keybinds", lambda: keyBindsControl(keybinds_flag)),
       Button(530, 630, 150, 50, "Record", lambda: recordingHelper()),
       Button(530, 690, 150, 50, "Save Video", lambda: saveHelper()),
       Button(530, 750, 150, 50, "Tracking", lambda: trackingHelper()),
       Button(690, 570, 150, 50, "Tracking Motors", lambda: trackingMotors()),
       Button(690, 630, 150, 50, "Make Border", lambda: borderHelper(is_jf_mode)),
       Button(690, 690, 150, 50, "Cancel Border", lambda: borderCancelHelper()),
       Button(690, 750, 150, 50, "Show Border", lambda: borderShowHelper()),
       Button(850, 570, 150, 50, "Load Border", lambda: borderLoadHelper()),
       Button(850, 630, 150, 50, "Pixels Cal", lambda: pixelsCalHelper(pixelsCal_flag,width,height,is_jf_mode)),
       Button(850, 690, 150, 50, "Help", lambda: openHelp()),       
    ]  

    while running:
        window.fill((0, 0, 0))  # Clear full window
        mouse_pos = pygame.mouse.get_pos()
        mouse_pressed = pygame.mouse.get_pressed()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if recording:
                    cont, recording = popup_save_recording(window, font, recordingSave, avi_recorder, timestamp, step_tracking_data, recording, avi_filename)
                    if not cont:
                        running = False
                        terminate_event.set()
                        running_flag.value = False
                else:
                    running = False
                    terminate_event.set()
                    running_flag.value = False
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
        
        # BUTTON LOGIC
        for button in buttons:
            button.handle_event(event, mouse_pos, mouse_pressed)
            button.draw(window)

        if boundary_making:
            boundary.append((x_pos.value,y_pos.value))
        if shared_image is not None:
            # Handle recording
            if recording and avi_recorder is not None:
                avi_recorder.write(shared_image)

            # Convert webcam image for pygame display
            rgb_frame = cv2.cvtColor(shared_image, cv2.COLOR_BGR2RGB)
            height, width, channels = rgb_frame.shape
            # print("Number of Channels:", channels)
            py_image = pygame.surfarray.make_surface(rgb_frame.swapaxes(0, 1))
            # py_image = pygame.transform.scale(py_image, (window_width, window_height))
            py_image_mirror = pygame.transform.flip(py_image, True, False) # mirrored to have live stream make more
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

            except queue.Empty:
                pass

            if show_boundary: 
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
    

            current_time = datetime.now() - start_time  # This is a timedelta object
            elapsed_seconds = int(current_time.total_seconds())
            hours, remainder = divmod(elapsed_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            status_text = (
                    f"{'Recording' if recording else 'Not Recording'} | "
                    f"{'Tracking' if tracking else 'Not Tracking'}\n"
                    f"{'Motors on with Tracking' if motors else 'Motors off with Tracking'}\n"
                    f"{'Boundary Visualization: On' if show_boundary else 'Boundary Visualization: Off'}\n"
                    f"Duration: {hours:02}:{minutes:02}:{seconds:02}\n"
                    f"Mode: {mode_string(is_jf_mode)}"
                )

            lines = status_text.split('\n')
            y_offset = 570
            for line in lines:
                line_surface = font.render(line, True, (255, 0, 0) if recording else (0, 255, 0))
                window.blit(line_surface, (10, y_offset))
                y_offset += font.get_linesize()  # Move to next line
            
            pygame.display.flip()
        
        clock.tick(60)  # Keep at 60 FPS for smooth display
        
        frame_count += 1
        if frame_count == 600:
            current_time = time.time()
            frames = 600 / (current_time - last_frame_time)
            print(f"FPS: {frames:.2f}")
            frame_count = 0
            last_frame_time = current_time
    
    if recording and avi_recorder:
        avi_recorder.release()
        avi_recorder = None
    
    acq_thread.join()
    tracking_thread.join()
    cap.release()
    pygame.quit()
    print("Done")
    return True