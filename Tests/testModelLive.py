import cv2
import time
from ultralytics import YOLO
import threading
import traceback
import numpy as np

# --- Configuration ---
# Path to the trained YOLO model
# Ensure this path is correct for your system
model_path = r"C:\Users\JellyTracker\Desktop\TrainingPipeline\Foundational_Training\train_m_Larvae_seg\weights\best.pt"

# Path to the video file for processing
# Ensure this path is correct for your system
# video_path = r"C:\Users\JellyTracker\Desktop\JellyFishTrackingPC-main\saved_tracking_videos\JellyTracking_20250512_121113.mp4"
video_path = r"C:\Users\JellyTracker\Desktop\JellyFishTrackingPC-main\saved_tracking_videos\good_larvae_vids_to_label_and_train_on\JellyTracking_20250520_165319.mp4"
# YOLO Inference parameters
IMG_SIZE_INFERENCE = 640  # Image size for YOLOv8 model input (resized frame)
INITIAL_CONF_THRESHOLD = 0.25  # Initial confidence threshold for detections
IOU_THRESHOLD = 0.7  # IoU threshold for Non-Maximum Suppression (NMS)
HALF_PRECISION = True  # Use FP16 for inference if supported (faster)

# Video processing parameters
TARGET_FPS_PROCESSING = 20  # Target FPS for processing frames (skips frames if video FPS is higher)

# --- Global Variables ---
g_seek_initiated_by_user = False
g_current_conf_threshold = INITIAL_CONF_THRESHOLD


# --- VideoCaptureThread Class for threaded video reading ---
class VideoCaptureThread:
    def __init__(self, video_source):
        self.cap = cv2.VideoCapture(video_source)
        self.stopped = True
        self.grabbed = False
        self.frame = None
        self.current_frame_no = -1  # 0-based index of the current frame

        if not self.cap.isOpened():
            print(f"Error: Could not open video source {video_source}")
            return

        self.grabbed, self.frame = self.cap.read()
        if not self.grabbed or self.frame is None:
            print("Failed to read the first frame from video source.")
            if self.cap.isOpened():
                self.cap.release()
            return
        
        self.current_frame_no = 0  # First frame (index 0) successfully read
        self.stopped = False
        
        self.lock = threading.Lock()  # Protects frame, grabbed, stopped, current_frame_no, cap operations, seek_request_frame
        self.seek_request_frame = -1  # Target frame for seeking

        self.thread = threading.Thread(target=self._update_frame, daemon=True)
        self.thread.start()

    def _update_frame(self):
        """Internal method to continuously read frames from the video source."""
        while True:
            with self.lock:
                if self.stopped:
                    break

                perform_seek = False
                target_frame_for_seek = -1
                if self.seek_request_frame != -1:
                    perform_seek = True
                    target_frame_for_seek = self.seek_request_frame
                    self.seek_request_frame = -1  # Reset request

                if perform_seek:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame_for_seek)
                    self.grabbed, self.frame = self.cap.read()
                    if self.grabbed and self.frame is not None:
                        # CAP_PROP_POS_FRAMES can be 1-based for next frame, or 0-based for current
                        # It's safer to explicitly set current_frame_no after a successful seek if needed
                        self.current_frame_no = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES)) -1
                        if self.current_frame_no < 0 and target_frame_for_seek == 0: # Handle seeking to frame 0
                            self.current_frame_no = 0
                    else:
                        self.grabbed = False
                        self.frame = None
                else:
                    # Only read next frame if the previous one was successfully grabbed
                    if self.grabbed: 
                        self.grabbed, frame_temp = self.cap.read()
                        if self.grabbed and frame_temp is not None:
                            self.frame = frame_temp
                            self.current_frame_no = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1
                        else: # End of video or read error
                            self.grabbed = False
                            self.frame = None
            time.sleep(0.001)  # Small sleep to prevent busy-waiting

    def read(self):
        """Reads the current frame from the buffer."""
        with self.lock:
            if not self.grabbed or self.frame is None:
                return None, self.current_frame_no 
            frame_copy = self.frame.copy()
            return frame_copy, self.current_frame_no

    def request_seek(self, frame_no):
        """Requests the thread to seek to a specific frame number."""
        with self.lock:
            self.seek_request_frame = frame_no

    def stop(self):
        """Signals the thread to stop."""
        with self.lock:
            self.stopped = True

    def release(self):
        """Stops the thread and releases video capture resources."""
        self.stop()
        if self.thread.is_alive():
            self.thread.join(timeout=1.0)  # Wait for the thread to finish
        
        if self.cap.isOpened():
            self.cap.release()
        print("VideoCaptureThread released.")

# --- Main Script ---
if __name__ == "__main__":
    # Load the YOLO model
    try:
        model = YOLO(model_path)
        print(f"Successfully loaded YOLO model from: {model_path}")
    except Exception as e:
        print(f"Error loading YOLO model: {e}")
        traceback.print_exc()
        exit()

    # Get video metadata
    _temp_cap = cv2.VideoCapture(video_path)
    if not _temp_cap.isOpened():
        print(f"Error: Could not open video at {video_path} to get metadata.")
        exit()
    total_frames_video = int(_temp_cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps_video = _temp_cap.get(cv2.CAP_PROP_FPS)
    _temp_cap.release()

    if total_frames_video == 0:
        print("Error: Video has 0 frames or metadata could not be read.")
        exit()
    
    print(f"Video Info: Total Frames: {total_frames_video}, FPS: {fps_video:.2f}")

    # Calculate frame skipping for target processing FPS
    frame_skip_interval = max(1, int(fps_video / TARGET_FPS_PROCESSING)) if fps_video > 0 and TARGET_FPS_PROCESSING > 0 else 1
    print(f"Targeting ~{TARGET_FPS_PROCESSING} FPS by processing 1 every {frame_skip_interval} frames.")

    # Initialize VideoCaptureThread
    threaded_cap = VideoCaptureThread(video_path)
    if threaded_cap.stopped: # Check if initialization failed
        print("Error: VideoCaptureThread failed to start. Exiting.")
        cv2.destroyAllWindows()
        exit()

    # Create OpenCV window and trackbars
    WINDOW_NAME = 'YOLOv8 Real-time Larva Detection (Tiled)'
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)

    def on_frame_trackbar_change(val):
        global g_seek_initiated_by_user
        threaded_cap.request_seek(val)
        g_seek_initiated_by_user = True

    def on_confidence_trackbar_change(val):
        global g_current_conf_threshold
        g_current_conf_threshold = val / 100.0

    cv2.createTrackbar('Frame', WINDOW_NAME, 0, max(0, total_frames_video - 1), on_frame_trackbar_change)
    initial_conf_trackbar_val = int(g_current_conf_threshold * 100)
    cv2.createTrackbar('Confidence', WINDOW_NAME, initial_conf_trackbar_val, 100, on_confidence_trackbar_change)

    # Initialize CLAHE (Contrast Limited Adaptive Histogram Equalization)
    # These parameters can be tuned for optimal contrast enhancement.
    clahe_processor = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))

    frames_processed_counter = 0
    display_fps = 0
    is_paused = False

    print("\nStarting main processing loop.")
    print("Press 'q' to quit, ' ' (space) to pause/resume.")
    print("Timings for preprocessing, tracking, and drawing will be printed for each processed frame.\n")

    while True:
        try:
            loop_iteration_start_time = time.time()

            if g_seek_initiated_by_user:
                frames_processed_counter = 0  # Reset counter for frame skipping logic
                g_seek_initiated_by_user = False
                is_paused = False # Resume on seek

            if is_paused:
                key_input_paused = cv2.waitKey(30) & 0xFF
                if key_input_paused == ord('q'):
                    break
                if key_input_paused == ord(' '):
                    is_paused = False
                    print("Resumed")
                if is_paused: # Still paused
                    continue
            
            # Read frame from threaded capture
            current_frame, current_frame_index = threaded_cap.read()

            if current_frame is None:
                # Wait a bit if no frame, check for quit, or break if video ended
                time.sleep(0.01) 
                key_check_no_frame = cv2.waitKey(1) & 0xFF
                if key_check_no_frame == ord('q'):
                    break
                # Check if the thread is stopped and we are near the end or at an invalid frame index
                if threaded_cap.stopped and (current_frame_index >= total_frames_video -2 or current_frame_index == -1):
                    print("Main loop: End of video reached or VideoCaptureThread stopped.")
                    break
                continue # Try reading again

            # --- Frame Processing ---
            frame_processing_start_time = time.time()
            original_height, original_width = current_frame.shape[:2]
            
            # Create a copy of the frame for drawing annotations for display
            annotated_display_frame = current_frame.copy()

            # Draw tile lines on the display frame (visual aid for 2x2 tiling)
            display_tile_width = original_width // 2
            display_tile_height = original_height // 2
            cv2.line(annotated_display_frame, (display_tile_width, 0), (display_tile_width, original_height), (255, 255, 0), 1) # Vertical
            cv2.line(annotated_display_frame, (0, display_tile_height), (original_width, display_tile_height), (255, 255, 0), 1) # Horizontal
            
            total_inference_duration_for_frame = 0
            all_detections_from_tiles = [] # To store detections from all tiles for this frame

            # Process frame only if it's the right one in the skip interval
            if frames_processed_counter % frame_skip_interval == 0:
                # 1. Resize frame for model input
                frame_resized_for_model = cv2.resize(current_frame, (IMG_SIZE_INFERENCE, IMG_SIZE_INFERENCE))

                # 2. Preprocessing: Apply CLAHE for contrast enhancement
                preprocessing_start_time = time.time()
                ycbcr_frame = cv2.cvtColor(frame_resized_for_model, cv2.COLOR_BGR2YCrCb)
                y_channel, cr_channel, cb_channel = cv2.split(ycbcr_frame)
                y_channel_clahe = clahe_processor.apply(y_channel)
                clahe_enhanced_ycbcr_frame = cv2.merge((y_channel_clahe, cr_channel, cb_channel))
                frame_for_inference_tiled = cv2.cvtColor(clahe_enhanced_ycbcr_frame, cv2.COLOR_YCrCb2BGR)
                preprocessing_duration = time.time() - preprocessing_start_time

                # 3. Tiled Inference (2x2 grid on the resized, preprocessed frame)
                tile_width_inf = IMG_SIZE_INFERENCE // 2  # e.g., 640/2 = 320
                tile_height_inf = IMG_SIZE_INFERENCE // 2 # e.g., 640/2 = 320
                
                # Define origins (top-left corner) of the 4 tiles in the resized frame coordinates
                tile_origins_inference = [
                    (0, 0), (tile_width_inf, 0),             # Top-left, Top-right
                    (0, tile_height_inf), (tile_width_inf, tile_height_inf) # Bottom-left, Bottom-right
                ]
                tile_labels = {0: "T1_TL", 1: "T2_TR", 2: "T3_BL", 3: "T4_BR"} # Tile labels for debugging

                for i_tile, (origin_x_inf, origin_y_inf) in enumerate(tile_origins_inference):
                    # Extract the current tile from the (resized, CLAHE-enhanced) frame
                    current_tile_image = frame_for_inference_tiled[
                        origin_y_inf : origin_y_inf + tile_height_inf,
                        origin_x_inf : origin_x_inf + tile_width_inf
                    ].copy() # Use .copy() if subsequent operations might modify it in-place

                    if current_tile_image.size == 0: # Safety check for empty tile
                        print(f"Warning: Tile {i_tile} is empty.")
                        continue
                    
                    tile_inference_start_time = time.time()
                    # Run YOLOv8 tracking on the individual tile
                    # `persist=True` helps ByteTrack maintain track IDs between calls for the same tile context
                    # `tracker="bytetrack.yaml"` specifies the tracking algorithm
                    tile_results_yolo = model.track(
                        source=current_tile_image,
                        imgsz=tile_width_inf, # Model input size should match tile size
                        conf=g_current_conf_threshold,
                        iou=IOU_THRESHOLD,
                        half=HALF_PRECISION,
                        verbose=False, # Set to True for more detailed output from YOLO
                        persist=True, 
                        tracker="bytetrack.yaml" 
                    )
                    total_inference_duration_for_frame += (time.time() - tile_inference_start_time)

                    # Process detections from the current tile
                    if tile_results_yolo and tile_results_yolo[0].boxes is not None and len(tile_results_yolo[0].boxes) > 0:
                        boxes_xyxyn_tile_coords = tile_results_yolo[0].boxes.xyxyn.cpu().numpy() # Normalized (0-1) bbox within tile
                        confidences_tile = tile_results_yolo[0].boxes.conf.cpu().numpy()
                        class_ids_tile = tile_results_yolo[0].boxes.cls.cpu().numpy().astype(int)
                        # Tile-local track IDs (if available and needed for more advanced tracking)
                        # track_ids_tile = None
                        # if tile_results_yolo[0].boxes.id is not None:
                        #    track_ids_tile = tile_results_yolo[0].boxes.id.cpu().numpy().astype(int)

                        for j in range(len(boxes_xyxyn_tile_coords)):
                            # Convert normalized tile coordinates to absolute coordinates in the full resized frame
                            norm_tile_x1, norm_tile_y1, norm_tile_x2, norm_tile_y2 = boxes_xyxyn_tile_coords[j]
                            
                            abs_resized_x1 = (norm_tile_x1 * tile_width_inf) + origin_x_inf
                            abs_resized_y1 = (norm_tile_y1 * tile_height_inf) + origin_y_inf
                            abs_resized_x2 = (norm_tile_x2 * tile_width_inf) + origin_x_inf
                            abs_resized_y2 = (norm_tile_y2 * tile_height_inf) + origin_y_inf

                            # Convert absolute resized frame coordinates to original display frame coordinates
                            display_x1 = int((abs_resized_x1 / IMG_SIZE_INFERENCE) * original_width)
                            display_y1 = int((abs_resized_y1 / IMG_SIZE_INFERENCE) * original_height)
                            display_x2 = int((abs_resized_x2 / IMG_SIZE_INFERENCE) * original_width)
                            display_y2 = int((abs_resized_y2 / IMG_SIZE_INFERENCE) * original_height)
                            
                            all_detections_from_tiles.append({
                                'x1': display_x1, 'y1': display_y1, 'x2': display_x2, 'y2': display_y2,
                                'confidence': confidences_tile[j],
                                'class_id': class_ids_tile[j],
                                'tile_reference': tile_labels.get(i_tile, f"Tile_{i_tile}") # Store which tile it came from
                            })
                
                # --- Select the single "best" larva detection based on highest confidence from all tiles ---
                best_larva_overall = None
                if all_detections_from_tiles:
                    best_larva_overall = max(all_detections_from_tiles, key=lambda det: det['confidence'])

                # 4. Draw the best detection on the annotated_display_frame
                drawing_start_time = time.time()
                if best_larva_overall:
                    det = best_larva_overall
                    x1, y1, x2, y2 = det['x1'], det['y1'], det['x2'], det['y2']
                    conf = det['confidence']
                    cls_id = det['class_id']
                    tile_ref = det['tile_reference']
                    
                    class_name = model.names[cls_id] if cls_id in model.names else f"CLS_{cls_id}"
                    label_text = f'{class_name}: {conf:.2f} ({tile_ref})'
                    
                    cv2.rectangle(annotated_display_frame, (x1, y1), (x2, y2), (0, 255, 0), 2) # Green box
                    cv2.putText(annotated_display_frame, label_text, (x1, y1 - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                drawing_duration = time.time() - drawing_start_time
                
                print(f"Frame {current_frame_index}: Preproc: {preprocessing_duration:.4f}s, Tiles Infer: {total_inference_duration_for_frame:.4f}s, Draw: {drawing_duration:.4f}s")

            # --- End of conditional processing for frame_skip_interval ---
            frames_processed_counter += 1
            
            # Calculate overall display FPS
            loop_iteration_duration = time.time() - loop_iteration_start_time
            if loop_iteration_duration > 0:
                display_fps = 1.0 / loop_iteration_duration
            else:
                display_fps = float('inf') # Avoid division by zero if loop is too fast

            # Display information on the frame
            fps_text_display = f'Display FPS: {display_fps:.2f}'
            cv2.putText(annotated_display_frame, fps_text_display, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2) # Cyan
            cv2.putText(annotated_display_frame, f'Confidence Thresh: {g_current_conf_threshold:.2f}', (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            cv2.putText(annotated_display_frame, f'Frame: {current_frame_index}/{max(0, total_frames_video-1)}', (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            
            # Show the annotated frame
            cv2.imshow(WINDOW_NAME, annotated_display_frame)

            # Update trackbar position
            if current_frame_index >= 0 and current_frame_index < total_frames_video:
                 cv2.setTrackbarPos('Frame', WINDOW_NAME, current_frame_index)

            # Handle key presses
            key_input_main = cv2.waitKey(1) & 0xFF
            if key_input_main == ord('q'):
                print("Quit key pressed. Exiting loop.")
                break
            elif key_input_main == ord(' '): # Spacebar
                is_paused = not is_paused
                if is_paused:
                    print("Paused")
                else:
                    print("Resumed")

        except Exception as e:
            print(f"An error occurred in the main loop: {e}")
            traceback.print_exc()
            break # Exit loop on critical error

    # --- Cleanup ---
    print("Exiting program...")
    threaded_cap.release()
    cv2.destroyAllWindows()
    print("Resources released. Program terminated.")