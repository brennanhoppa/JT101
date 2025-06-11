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
from Utils.log import log
import textwrap

NUM_IMAGES = 300
name = 'TESTBINNING2'
running = True
recording = False
tracking = False
motors = False
boundary_making = False
shared_image = None
avi_recorder = None
verbose = False

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

def run_live_stream_record(x_pos,y_pos,command_queue,homing_flag,keybinds_flag,pixelsCal_flag,is_jf_mode, terminate_event, running_flag,step_size,step_to_mm_checking,homing_button,homing_error_button,log_queue):
    if main(x_pos,y_pos,command_queue,homing_flag,keybinds_flag,pixelsCal_flag,is_jf_mode, terminate_event, running_flag, step_size,step_to_mm_checking,homing_button,homing_error_button,log_queue):
        sys.exit(0)
    else:
        sys.exit(1)

def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

class RollingLog:
    def __init__(self, max_lines=300, font=None, max_width=None):
        self.lines = []
        self.max_lines = max_lines
        self.font = font or pygame.font.SysFont("consolas", 16)
        self.max_width = max_width or 462 # default width

    def append(self, line):
        self.lines.append(line)
        while len(self.lines) > self.max_lines:
            self.lines.pop(0)

    def get_visible_lines(self, start_index, num_lines):
        return self.lines[start_index:start_index + num_lines]

    def total_lines(self):
        count = 0
        for line in self.lines:
            i = 0
            while i < len(line):
                j = i + 1
                while j <= len(line):
                    slice = line[i:j]
                    width = self.font.render(slice, True, (0, 0, 0)).get_width()
                    if width > self.max_width:
                        break
                    j += 1
                count += 1
                i = j - 1
        return count

    def clear(self):
        self.lines.clear()

    def update_width(self, new_width):
        self.max_width = new_width

def draw_log_terminal(surface, rolling_log, scroll_offset=0, margin=10, top=50,
                      line_height=18, bg_color=(0, 0, 0, 180), text_color=(255, 255, 255),
                      font_size=16, scrollbar_width=8):

    font = pygame.font.SysFont("consolas", font_size)
    screen_width = surface.get_width()
    screen_height = surface.get_height()
    column_start_x = 970
    column_width = screen_width - column_start_x
    panel_height = screen_height - top

    # Draw translucent background
    panel_surface = pygame.Surface((column_width, panel_height), pygame.SRCALPHA)
    panel_surface.fill(bg_color)
    surface.blit(panel_surface, (column_start_x, 0))
    
    separator_rect = pygame.Rect(column_start_x, 0, 2, screen_height)
    pygame.draw.rect(surface, (150, 150, 150), separator_rect)
    horiz_bar = pygame.Rect(column_start_x, 35, screen_width-column_width, 2)
    pygame.draw.rect(surface, (150,150,150), horiz_bar)

    label_surf = font.render("Terminal", True, (255, 255, 255))
    surface.blit(label_surf, (column_start_x + margin, 10))

    x = column_start_x + margin
    y = top

    # Calculate how many lines fit in the panel
    visible_lines_count = panel_height // line_height
    total_lines = rolling_log.total_lines()

    # Clamp scroll_offset
    max_scroll = max(0, total_lines - visible_lines_count)
    scroll_offset = max(0, min(scroll_offset, max_scroll))

    # Get visible lines
    lines = rolling_log.get_visible_lines(scroll_offset, visible_lines_count)

    for line in lines:
        i = 0
        while i < len(line):
            max_width = column_width - 2 * margin - scrollbar_width
            j = i + 1
            while j <= len(line):
                slice = line[i:j]
                width = font.render(slice, True, text_color).get_width()
                if width > max_width:
                    # Render up to character before it exceeds
                    if j == i + 1:
                        # Even one character doesn't fit (very narrow terminal)
                        slice = line[i:j]
                    else:
                        slice = line[i:j-1]
                        j -= 1
                    break
                j += 1

            text_surf = font.render(slice, True, text_color)
            surface.blit(text_surf, (x, y))
            y += line_height
            i = j


    # Draw the scrollbar
    if total_lines > visible_lines_count:
        # Scrollbar track starts at y = 35 (the horiz_bar position) and ends at bottom
        scrollbar_track_top = 35
        scrollbar_track_bottom = screen_height
        scrollbar_track_height = scrollbar_track_bottom - scrollbar_track_top

        scrollbar_height = int((visible_lines_count / total_lines) * scrollbar_track_height)
        max_scroll_offset = total_lines - visible_lines_count

        if max_scroll_offset > 0:
            scrollbar_pos = int((scroll_offset / max_scroll_offset) * (scrollbar_track_height - scrollbar_height))
        else:
            scrollbar_pos = 0  # no scrolling needed

        scrollbar_rect = pygame.Rect(
            screen_width - scrollbar_width,
            scrollbar_track_top + scrollbar_pos,
            scrollbar_width,
            scrollbar_height
        )
        pygame.draw.rect(surface, (180, 180, 180), scrollbar_rect)


def webcam_image_to_pygame(frame):
    # Convert BGR to RGB for pygame
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    # Convert to contiguous array
    rgb_frame = np.ascontiguousarray(rgb_frame.astype(np.uint8))
    # Create pygame surface
    return pygame.surfarray.make_surface(rgb_frame.swapaxes(0, 1))

def load_boundary(is_jf_mode, log_queue):
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(title="Select a File", filetypes=[("CSV files", "*.csv"), ("All Files", "*.*")])
    if file_path:  # If a file was selected
        log(f"Selected file: {file_path}",log_queue)
        try:
            boundary_mm = load_boundaries(file_path)
            return boundary_to_steps(boundary_mm,is_jf_mode)
        except:
            log('Incorrect file loaded',log_queue)
    else:
        log("No file selected.",log_queue)
        return []

def imageacq(cam,log_queue):
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
                    log("Warning: Frame conversion failed; not a valid NumPy array.",log_queue)
            else:
                log("Failed to capture frame from webcam",log_queue)
        except Exception as ex:
            log(f'Error in image acquisition: {ex}',log_queue)
    
    # Clean up video writer if it exists
    if avi_recorder is not None:
        avi_recorder.release()


def active_tracking_thread(center_x, center_y, command_queue, x_pos, y_pos, is_jf_mode,log_queue):
    global running, tracking, motors, recording, step_tracking_data,verbose
    last_tracking_time = time.time()
    
    while running:
        if tracking:
            try:
                current_time = time.time()
                if current_time - last_tracking_time >= TRACKING_INTERVAL:
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
                log("Warning: Frame queue is empty; skipping tracking update.",log_queue)
            except Exception as e:
                pass
                # log(f"Error in tracking thread: {e}",log_queue)
        time.sleep(0.001)  # Sleep briefly to prevent excessive CPU usage

def main(x_pos,y_pos,command_queue,homing_flag,keybinds_flag,pixelsCal_flag,is_jf_mode, terminate_event, running_flag, step_size,step_to_mm_checking,homing_button,homing_error_button,log_queue):
    global running, shared_image, chosenAviType, recording, tracking, motors, boundary_making, boundary, show_boundary, avi_recorder, step_tracking_data, start_time, verbose
      
    # Initialize webcam
    cap = cv2.VideoCapture(0)  # Use default webcam (index 0)
    if not cap.isOpened():
        log("Error: Could not open webcam",log_queue)
        return False
    
    # Get camera properties
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = 60 # change if camera settings change
    
    pygame.init()
    text_panel_height = 320
    window_width, window_height = width+500, height+text_panel_height
    window = pygame.display.set_mode((window_width, window_height))
    pygame.display.set_caption("Camera Live View with Flashlight Tracking")
    
    ensure_dir('saved_tracking_videos')
    ensure_dir('saved_tracking_csvs')
    
    acq_thread = threading.Thread(target=imageacq, args=(cap,log_queue))
    acq_thread.start()
    
    tracking_thread = threading.Thread(target=active_tracking_thread, args=(width // 2, height // 2, command_queue, x_pos, y_pos, is_jf_mode,log_queue))
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

    def recordingHelper(log_queue):
        global recording, avi_recorder, step_tracking_data, timestamp, start_time,avi_filename
        if not recording:
            recording,avi_recorder,step_tracking_data,timestamp,avi_filename = recordingStart(recording,chosenAviType,fps,width,height,log_queue)
            start_time = datetime.now()

    def saveHelper(log_queue):
        global recording, start_time
        if recording:
            recording = recordingSave(recording,avi_recorder,timestamp,step_tracking_data,log_queue)
            start_time = datetime.now() 
    
    def trackingHelper():
        global tracking
        tracking = not tracking

    def trackingMotors():
        global motors
        motors = not motors
    
    def borderHelper(is_jf_mode,log_queue):
        global boundary, boundary_making
        boundary_making,boundary = boundaryControl(boundary_making,boundary,is_jf_mode,log_queue)

    def borderCancelHelper(log_queue):
        global boundary, boundary_making
        boundary_making, boundary = boundaryCancel(boundary_making, boundary, log_queue)

    def borderShowHelper():
        global show_boundary
        show_boundary = not show_boundary

    def borderLoadHelper():
        global boundary
        nonlocal log_queue
        boundary = load_boundary(is_jf_mode, log_queue)

    def pixelsCalHelper(pixelsCal_flag,width,height,is_jf_mode, log_queue):
        nonlocal crosshair_x, crosshair_y
        crosshair_x,crosshair_y = pixelsCalibration(pixelsCal_flag,crosshair_x,crosshair_y,width,height,is_jf_mode, log_queue)

    def verboseHelper():
        global verbose
        verbose = not verbose

    def openHelp():
        os.startfile("C:\\Users\\JellyTracker\\Desktop\\HelpDoc.pdf")

    rolling_log = RollingLog()
    def clear_log_callback(rolling_log):
        rolling_log.clear()
        log("New Terminal:",log_queue)
    button_x = window.get_width() - 130  # inside terminal panel left margin
    button_y = 5
    button_width = 120
    button_height = 20

    onOffColors = [(50, 50, 100),(0, 150, 255)]
    calColors = [(50, 50, 100),(38, 75, 139),(25, 100, 178),(13, 125, 216),(0, 150, 255)]
    buttons = [
       Button(330, 570, 150, 50, "Home", lambda: homing_set(homing_button), get_color=lambda: onOffColors[homing_button.value]),
       Button(330, 630, 150, 50, "Home w EC", lambda: homing_set_with_error(homing_error_button),get_color=lambda: onOffColors[homing_error_button.value]),
       Button(330, 690, 150, 50, "Steps Cal", lambda: stepsCalibration(step_size, step_to_mm_checking, x_pos, y_pos,is_jf_mode, log_queue),get_color=lambda: calColors[step_to_mm_checking.value]),
       Button(330, 750, 150, 50, "Change Mode", lambda: change_mode(is_jf_mode,x_pos,y_pos,step_size,log_queue)),
       Button(490, 570, 150, 50, "Keybinds", lambda: keyBindsControl(keybinds_flag,log_queue)),
       Button(490, 630, 150, 50, "Record", lambda: recordingHelper(log_queue),get_color=lambda: onOffColors[recording]),
       Button(490, 690, 150, 50, "Save Video", lambda: saveHelper(log_queue)),
       Button(490, 750, 150, 50, "Tracking", lambda: trackingHelper(), get_color=lambda: onOffColors[tracking]),
       Button(650, 570, 150, 50, "Motors4Track", lambda: trackingMotors(),get_color=lambda: onOffColors[motors]),
       Button(650, 630, 150, 50, "Make Border", lambda: borderHelper(is_jf_mode, log_queue),get_color=lambda: onOffColors[boundary_making]),
       Button(650, 690, 150, 50, "Cancel Border", lambda: borderCancelHelper(log_queue)),
       Button(650, 750, 150, 50, "Show Border", lambda: borderShowHelper(),get_color=lambda: onOffColors[show_boundary]),
       Button(810, 570, 150, 50, "Load Border", lambda: borderLoadHelper()),
       Button(810, 630, 150, 50, "Pixels Cal", lambda: pixelsCalHelper(pixelsCal_flag,width,height,is_jf_mode, log_queue),get_color=lambda: calColors[pixelsCal_flag.value]),
       Button(810, 690, 150, 50, "TrackVerbose", lambda: verboseHelper(),get_color=lambda: onOffColors[verbose]),
       Button(810, 750, 150, 50, "Help", lambda: openHelp()),       
       Button(button_x, button_y, button_width, button_height,
                        "Clear Term", lambda: clear_log_callback(rolling_log),
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

    while running:
        window.fill((0, 0, 0))  # Clear full window

        mouse_pos = pygame.mouse.get_pos()
        mouse_pressed = pygame.mouse.get_pressed()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if recording:
                    cont, recording = popup_save_recording(window, font, recordingSave, avi_recorder, timestamp, step_tracking_data, recording, avi_filename, log_queue)
                    if not cont:
                        running = False
                        terminate_event.set()
                        running_flag.value = False
                else:
                    running = False
                    terminate_event.set()
                    running_flag.value = False
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
                    trackingFoundSomething = True
            except queue.Empty:
                trackingFoundSomething = False

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
            if recording:
                pygame.draw.circle(window, (255, 0, 0), (width-20,20), 8)

            # Determine status values
            if tracking:
                if trackingFoundSomething:
                    tracking_status = "Tracking On | Status: [OK]"
                else:
                    tracking_status = "Tracking On | Status: [FAIL]" 
            else:
                tracking_status = "Tracking Off"

            status_text = (
                f"{'● Recording' if recording else 'Not Recording'}\n"
                f"Duration: {hours:02}:{minutes:02}:{seconds:02}\n"
                f"{tracking_status}\n"
                f" \n"
                f"{'Tracking Motors: On' if motors else 'Tracking Motors: Off'}\n"
                f"{'Boundary Visualization: On' if show_boundary else 'Boundary Visualization: Off'}\n"
                f"Mode: {mode_string(is_jf_mode)}"
            )

            lines = status_text.split('\n')
            y_offset = 570

            for line in lines:
                if ("Recording" in line) or ("Duration" in line):
                    color = (255, 80, 80) if recording else (173, 216, 230)  # red if recording else light blue
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
        
        clock.tick(60)  # Keep at 60 FPS for smooth display
        
        frame_count += 1
        if frame_count == 600: # normally 600 is good speed
            current_time = time.time()
            frames = 600 / (current_time - last_frame_time)
            frame_count = 0
            last_frame_time = current_time
            log(f"FPS: {frames:.1f}",log_queue)
    
    if recording and avi_recorder:
        avi_recorder.release()
        avi_recorder = None
    
    acq_thread.join()
    tracking_thread.join()
    cap.release()
    pygame.quit()
    print("Done")
    return True