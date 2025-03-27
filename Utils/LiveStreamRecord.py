import sys
import numpy as np
import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame # type: ignore
import threading
import queue
from datetime import datetime
import time
from Utils.JellyTrackingFunctions import detect_jellyfish,calculate_movement, calculate_delta_Pixels, steps_to_mm, pixels_to_mm
from Utils.ManualMotorInput import move
from Utils.Boundaries import save_boundaries, boundary_to_mm_from_steps
import PySpin # type: ignore
import cv2 #type: ignore

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
show_boundary = False

# Tracking settings
TRACKING_INTERVAL = 1 / 50  # 50Hz tracking rate

# Queue for inter-thread communication
image_queue = queue.Queue(maxsize=5)
tracking_result_queue = queue.Queue(maxsize=5)

# Step tracking
# cumulative_steps = {'x': 0, 'y': 0}
step_tracking_data = []

class AviType:
    UNCOMPRESSED = 0
    MJPG = 1
    H264 = 2

chosenAviType = AviType.MJPG

def run_live_stream_record(x_pos,y_pos,command_queue,homing_flag):
    if main(x_pos,y_pos,command_queue,homing_flag):
        sys.exit(0)
    else:
        sys.exit(1)

def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def pyspin_image_to_pygame(image_ptr):
    width = image_ptr.GetWidth()
    height = image_ptr.GetHeight()
    image_data = image_ptr.GetNDArray()
    
    if image_ptr.GetPixelFormat() == PySpin.PixelFormat_Mono8:
        image_data = np.stack((image_data,) * 3, axis=-1)
    
    image_data = np.ascontiguousarray(image_data.astype(np.uint8))
    return pygame.image.frombuffer(image_data.tobytes(), (width, height), "RGB")

# def send_movement_command(step_x, step_y, command_queue):
    
    
#     if step_x != 0:
#         x_direction = 'L' if step_x > 0 else 'R'
#         command_queue.put(f"{x_direction}{abs(step_x)}\n")
#     if step_y != 0:
#         y_direction = 'U' if step_y > 0 else 'D'
#         command_queue.put(f"{y_direction}{abs(step_y)}\n")



# def track_cumulative_steps(step_x, step_y):
#     global cumulative_steps, step_tracking_data, recording
#     if recording:
#         # Note: step_x is positive for 'L' and negative for 'R'
#         cumulative_steps['x'] += step_x
#         cumulative_steps['y'] += step_y
#         timestamp = time.time()
#         step_tracking_data.append((cumulative_steps['x'], cumulative_steps['y'], timestamp))

def save_tracking_data(filename):
    global step_tracking_data
    with open(filename, 'w') as f:
        f.write("x,y,t\n")
        for x, y, t in step_tracking_data:
            f.write(f"{x},{y},{t}\n")
    print(f"Tracking data saved to {filename}")

def imageacq(cam, processor):
    global running, shared_image, recording, avi_recorder
    cam.BeginAcquisition()
    while running:
        try:
            image_result = cam.GetNextImage(1000)
            if not image_result.IsIncomplete():
                processed_image = processor.Convert(image_result, PySpin.PixelFormat_Mono8)
                frame = processed_image.GetNDArray()  # Convert to a valid NumPy array
                
                # Ensure the frame is a 3-channel RGB image
                if frame.ndim == 2:  # Grayscale image
                    frame = np.stack((frame,) * 3, axis=-1)
                
                shared_image = processed_image
                
                if recording and avi_recorder is not None:
                    avi_recorder.Append(processed_image)
                
                # Ensure the frame is a valid NumPy array before putting it in the queue
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
            image_result.Release()
        except PySpin.SpinnakerException as ex:
            print(f'Error in image acquisition: {ex}')
    cam.EndAcquisition()


def active_tracking_thread(center_x, center_y, command_queue, x_pos, y_pos):
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
                    # detect_light = False # normal setting to track jf
                    detect_light = True # testing mode - returns x,y of brightest spot in frame

                    # Use YOLO to detect jellyfish position
                    flashlight_pos = detect_jellyfish(image, detect_light)
                    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-2] 
                    if flashlight_pos:
                        # Calculate deltas
                        dx, dy = calculate_delta_Pixels(flashlight_pos, center_x, center_y)
                        # print(dx,dy)
                        if recording:
                            # x_pos + dx thing and y !!!!!!!!!!!!!!
                            # mm position of jf in the global coords
                            x,y = steps_to_mm(x_pos.value,y_pos.value)
                            x -= dx # matching to the inverting of the x axis with the camera
                            y += dy # same as above
                            step_tracking_data.append((x, y, timestamp))                        
                        if motors:
                            step_x, step_y = calculate_movement(dx,dy)
                            # Send movement command
                            x_pos, y_pos = move(x_pos, y_pos, int(-1*round(step_x*1.3,0)), int(round(step_y*1.3,0)), command_queue)
                            
                        # Communicate tracking results for display
                        tracking_result_queue.put(flashlight_pos, block=False)
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



def main(x_pos,y_pos,command_queue,homing_flag):
    global running, shared_image, recording, tracking, motors, boundary_making, boundary,show_boundary, avi_recorder, step_tracking_data, cumulative_steps
    
    # commands
    print('Press "a" to turn on/off tracking')
    print('Press "m" to turn on/off the motor movement while tracking')
    print('Press "b" to start making a boundary (and "b" again to save it)')
    print('Press "x" to stop making the boundary and discard it')
    print('Press "r" to start recording')
    print('Press "s" to save the recording')
    print('Press "v" to visualize the currently loaded boundary')

    system = PySpin.System.GetInstance()
    cam_list = system.GetCameras()
    if cam_list.GetSize() != 1:
        print("Incorrect number of cameras (not 1)")
        return False
    cam = cam_list[0]
    cam.Init()
    
    nodemap = cam.GetNodeMap()
    cam.BinningVertical.SetValue(2)
    cam.AcquisitionMode.SetValue(PySpin.AcquisitionMode_Continuous)
    
    processor = PySpin.ImageProcessor()
    processor.SetColorProcessing(PySpin.SPINNAKER_COLOR_PROCESSING_ALGORITHM_HQ_LINEAR)
    
    pygame.init()
    window_width, window_height = 1024, 1024
    window = pygame.display.set_mode((window_width, window_height))
    pygame.display.set_caption("Camera Live View with Flashlight Tracking")
    
    ensure_dir('saved_tracking_videos')
    
    acq_thread = threading.Thread(target=imageacq, args=(cam, processor))
    acq_thread.start()
    
    tracking_thread = threading.Thread(target=active_tracking_thread, args=(window_width // 2, window_height // 2, command_queue, x_pos, y_pos))
    tracking_thread.start()
    
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 36)
    
    last_frame_time = time.time()
    frame_count = 0
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r and not recording:
                    recording = True
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    avi_filename = f'saved_tracking_videos/JellyTracking_{timestamp}'
                    
                    node_acquisition_framerate = PySpin.CFloatPtr(nodemap.GetNode('AcquisitionFrameRate'))
                    framerate_to_set = node_acquisition_framerate.GetValue()
                    if chosenAviType == AviType.MJPG:
                        avi_filename += '.avi'
                        option = PySpin.MJPGOption()
                        option.frameRate = framerate_to_set
                        option.quality = 75
                    elif chosenAviType == AviType.UNCOMPRESSED:
                        avi_filename += '.avi'
                        option = PySpin.AVIOption()
                        option.frameRate = framerate_to_set
                    elif chosenAviType == AviType.H264:
                        avi_filename += '.mp4'
                        option = PySpin.H264Option()
                        option.frameRate = framerate_to_set
                        option.bitrate = 1000000
                    
                    if shared_image:
                        option.height = shared_image.GetHeight()
                        option.width = shared_image.GetWidth()
                    
                    avi_recorder = PySpin.SpinVideo()
                    avi_recorder.Open(avi_filename, option)
                    print(f"Recording started: {avi_filename}")
                    
                    # Reset step tracking data
                    step_tracking_data = []
                    # cumulative_steps = {'x': 0, 'y': 0}
                    
                elif event.key == pygame.K_s and recording:
                    recording = False
                    if avi_recorder:
                        avi_recorder.Close()
                        avi_recorder = None
                    print("Recording stopped and saved")
                    
                    # Save tracking data
                    tracking_filename = f'saved_tracking_csvs/JellyTracking_{timestamp}_tracking.csv'
                    save_tracking_data(tracking_filename)
                    
                elif event.key == pygame.K_a:
                    tracking = not tracking # switches tracking on / off
                elif event.key == pygame.K_m:
                    motors = not motors # turn the motors on / off for tracking
                elif event.key == pygame.K_b: # boundary making process
                    if boundary_making:
                        print('Boundary Making Mode turned Off.')
                        file_start = "C:\\Users\\JellyTracker\\Desktop\\JellyFishTrackingPC-main\\saved_boundaries_mm\\"
                        filename = file_start + "new_bounds.csv"
                        print(f'Boundary saved at: {filename}')
                        save_boundaries(filename,boundary_to_mm_from_steps(boundary))
                        boundary_making = False
                    else:
                        print('Boundary Making Mode turned On. Move to record boundary. Finish and save by pressing b again. Press x to cancel/start over.')
                        boundary_making = True
                        boundary = []
                elif event.key == pygame.K_x:
                    if boundary_making:
                        boundary_making = False
                        boundary = [] # reset boundary
                        print('Boundary making turned off, and reset, with nothing saved.')
                    else: # do nothing
                        pass
                elif event.key == pygame.K_v:
                    show_boundary = not show_boundary
            
        if boundary_making:
            boundary.append((x_pos.value,y_pos.value))

        if shared_image is not None:
            py_image = pyspin_image_to_pygame(shared_image)
            py_image_mirror = pygame.transform.flip(py_image, True, False) # mirrored to have live stream make more
            window.blit(py_image, (0, 0))   
            
            # Draw crosshair at the center of the screen
            center_x = window_width // 2
            center_y = window_height // 2
            line_length = 20  # Length of each line segment
            line_color = (255, 0, 0)  # Red color
            line_thickness = 2
            
            # Draw horizontal line
            pygame.draw.line(window, line_color, 
                            (center_x - line_length, center_y),
                            (center_x + line_length, center_y),
                            line_thickness)
            
            # Draw vertical line
            pygame.draw.line(window, line_color,
                            (center_x, center_y - line_length),
                            (center_x, center_y + line_length),
                            line_thickness)
            
            try:
                flashlight_pos = tracking_result_queue.get_nowait()
                if flashlight_pos:
                    pygame.draw.circle(window, (0, 255, 0), flashlight_pos, 10)
            except queue.Empty:
                pass

            # for x, y, t in step_tracking_data:
            # f.write(f"{x},{y},{t}\n")

            current_time = datetime.now().strftime("%H:%M:%S") 
            status_text = (
                    f"{'Recording' if recording else 'Not Recording'} | "
                    f"{'Tracking' if tracking else 'Not Tracking'}\n"
                    f"{'Motors on with Tracking' if motors else 'Motors off with Tracking'}\n"
                    f"Time: {current_time}"
                )

            lines = status_text.split('\n')
            y_offset = 10
            for line in lines:
                line_surface = font.render(line, True, (255, 0, 0) if recording else (0, 255, 0))
                window.blit(line_surface, (10, y_offset))
                y_offset += font.get_linesize()  # Move to next line
            
            # if recording and tracking:
            #     steps_text = f"Steps: X={cumulative_steps['x']}, Y={cumulative_steps['y']}"
            #     steps_surface = font.render(steps_text, True, (255, 255, 0))
            #     window.blit(steps_surface, (10, 50))
            
            pygame.display.flip()
        
        clock.tick(60)  # Keep at 60 FPS for smooth display
        
        frame_count += 1
        if frame_count == 600:
            current_time = time.time()
            fps = 600 / (current_time - last_frame_time)
            print(f"FPS: {fps:.2f}")
            frame_count = 0
            last_frame_time = current_time
    
    if recording and avi_recorder:
        avi_recorder.Close()
    acq_thread.join()
    tracking_thread.join()
    cam.DeInit()
    pygame.quit()
    cam_list.Clear()
    system.ReleaseInstance()
    print("Done")
    return True