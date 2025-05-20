import cv2
import time
from ultralytics import YOLO
import threading
import traceback

# Load the trained model
# model_path = r"C:\Users\JellyTracker\Downloads\best (1).pt"
model_path = r"C:\Users\JellyTracker\Desktop\TrainingPipeline\Foundational_Training\train_m_Larvae_seg\weights\best.pt"
model = YOLO(model_path)

# Open video file
# video_path = r"C:\Users\JellyTracker\Desktop\JellyFishTrackingPC-main\saved_tracking_videos\JellyTracking_20250430_112937.mp4"
video_path = r"C:\Users\JellyTracker\Desktop\JellyFishTrackingPC-main\saved_tracking_videos\JellyTracking_20250512_121113.mp4"

# YOLO Inference parameters
img_size = 1024  # Set the image size for inference
initial_conf_threshold = 0.25  # Initial Confidence threshold
iou_threshold = 0.7  # IoU threshold for NMS
half_precision = True  # Enable FP16 inference

# Global flag for main loop to know a seek was *initiated* by trackbar
g_seek_initiated_by_user = False
# Global variable for dynamic confidence threshold
g_current_conf_threshold = initial_conf_threshold


class VideoCaptureThread:
    def __init__(self, video_source):
        self.cap = cv2.VideoCapture(video_source)
        self.stopped = True
        self.grabbed = False
        self.frame = None
        self.current_frame_no = -1 # 0-based index of the current frame

        if not self.cap.isOpened():
            print(f"Error: Could not open video source {video_source}")
            return

        self.grabbed, self.frame = self.cap.read()
        if not self.grabbed or self.frame is None:
            print("Failed to read the first frame from video source.")
            self.cap.release() # Release if first frame fails
            return
        
        self.current_frame_no = 0 # First frame (index 0) successfully read
        self.stopped = False
        
        self.lock = threading.Lock()  # Protects frame, grabbed, stopped, current_frame_no, cap operations, seek_request_frame
        self.seek_request_frame = -1  # Target frame for seeking

        self.thread = threading.Thread(target=self.update, daemon=True)
        self.thread.start()

    def update(self):
        while True:
            with self.lock:
                if self.stopped:
                    break

                perform_seek = False
                target_f = -1
                if self.seek_request_frame != -1:
                    perform_seek = True
                    target_f = self.seek_request_frame
                    self.seek_request_frame = -1

                if perform_seek:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, target_f)
                    self.grabbed, self.frame = self.cap.read()
                    if self.grabbed and self.frame is not None:
                        self.current_frame_no = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1
                        if self.current_frame_no < 0 and target_f == 0: 
                            self.current_frame_no = 0
                    else:
                        self.grabbed = False 
                        self.frame = None 
                else:
                    if self.grabbed: 
                        self.grabbed, frame_temp = self.cap.read()
                        if self.grabbed and frame_temp is not None:
                            self.frame = frame_temp
                            self.current_frame_no = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1
                        else:
                            self.grabbed = False 
                            self.frame = None
            time.sleep(0.001) 

    def read(self):
        with self.lock:
            if not self.grabbed or self.frame is None:
                return None, self.current_frame_no 
            frame_copy = self.frame.copy()
            return frame_copy, self.current_frame_no

    def request_seek(self, frame_no):
        with self.lock:
            self.seek_request_frame = frame_no

    def stop(self):
        with self.lock:
            self.stopped = True

    def release(self):
        self.stop() 
        if self.thread.is_alive():
            self.thread.join(timeout=1.0) 
        
        if self.cap.isOpened():
            self.cap.release()

# --- Main script execution starts here ---

_temp_cap = cv2.VideoCapture(video_path)
if not _temp_cap.isOpened():
    print("Error: Could not open video to get metadata.")
    exit()
total_frames_video = int(_temp_cap.get(cv2.CAP_PROP_FRAME_COUNT))
fps_video = _temp_cap.get(cv2.CAP_PROP_FPS)
_temp_cap.release()

if total_frames_video == 0:
    print("Error: Video has 0 frames or metadata could not be read.")
    exit()

target_fps = 20
frame_skip = max(1, int(fps_video / target_fps)) if fps_video > 0 and target_fps > 0 else 1

cv2.namedWindow('YOLOv8 Real-time Detection', cv2.WINDOW_NORMAL)

threaded_cap = VideoCaptureThread(video_path)
if threaded_cap.stopped: 
    print("Error: VideoCaptureThread failed to start. Exiting.")
    cv2.destroyAllWindows()
    exit()

def on_frame_trackbar(val):
    global g_seek_initiated_by_user
    threaded_cap.request_seek(val)
    g_seek_initiated_by_user = True

def on_confidence_trackbar(val):
    global g_current_conf_threshold
    g_current_conf_threshold = val / 100.0

cv2.createTrackbar('Frame', 'YOLOv8 Real-time Detection', 0, max(0, total_frames_video - 1), on_frame_trackbar)
initial_conf_trackbar_val = int(g_current_conf_threshold * 100)
cv2.createTrackbar('Confidence', 'YOLOv8 Real-time Detection', initial_conf_trackbar_val, 100, on_confidence_trackbar)

frames_processed_in_loop = 0
actual_fps_display = 0
paused = False

while True:
    try:
        loop_start_time = time.time()

        if g_seek_initiated_by_user:
            frames_processed_in_loop = 0 
            g_seek_initiated_by_user = False 
            paused = False 

        if paused:
            key_paused = cv2.waitKey(30) & 0xFF
            if key_paused == ord('q'):
                break 
            if key_paused == ord(' '): 
                paused = False
                print("Resumed")
            if paused: 
                continue

        frame, current_frame_idx_from_thread = threaded_cap.read()

        if frame is None:
            time.sleep(0.05) 
            if threaded_cap.stopped and (current_frame_idx_from_thread >= total_frames_video - 2 or current_frame_idx_from_thread == -1):
                print("Main loop: End of video reached or thread stopped.")
                break
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            continue 

        original_height, original_width = frame.shape[:2]
        # Resize the frame for YOLO input
        frame_resized = cv2.resize(frame, (img_size, img_size)) 
        
        frame_for_inference = frame_resized # By default, use the resized frame

        if frames_processed_in_loop % frame_skip == 0:
            
            # --- Apply Histogram Equalization to frame_resized before inference ---
            # 1. Convert to YCrCb colorspace
            ycbcr_frame = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2YCrCb)
            # 2. Split channels
            y_channel, cr_channel, cb_channel = cv2.split(ycbcr_frame)
            # 3. Apply histogram equalization to the Y (luminance) channel
            y_channel_eq = cv2.equalizeHist(y_channel)
            # 4. Merge the equalized Y channel back with the original Cr and Cb channels
            equalized_ycbcr_frame = cv2.merge((y_channel_eq, cr_channel, cb_channel))
            # 5. Convert back to BGR color_space for YOLO model
            frame_for_inference = cv2.cvtColor(equalized_ycbcr_frame, cv2.COLOR_YCrCb2BGR)
            # --- End of Histogram Equalization ---

            results = model.predict(
                frame_for_inference, # Use the histogram-equalized frame
                imgsz=img_size,
                conf=g_current_conf_threshold, 
                iou=iou_threshold,
                half=half_precision,
                verbose=False 
            )

            highest_conf_box = None
            if results: 
                for result in results: 
                    if result.boxes: 
                        for box in result.boxes: 
                            confidence = float(box.conf.item()) 

                            if highest_conf_box is None or confidence > highest_conf_box['confidence']:
                                x1_norm, y1_norm, x2_norm, y2_norm = box.xyxyn[0].tolist()
                                
                                x1 = int(x1_norm * original_width)
                                y1 = int(y1_norm * original_height)
                                x2 = int(x2_norm * original_width)
                                y2 = int(y2_norm * original_height)
                                
                                class_id_val = int(box.cls.item())
                                
                                highest_conf_box = {
                                    'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
                                    'class_id': class_id_val,
                                    'confidence': confidence
                                }
            
            if highest_conf_box:
                x1, y1, x2, y2 = highest_conf_box['x1'], highest_conf_box['y1'], highest_conf_box['x2'], highest_conf_box['y2']
                class_id, confidence_val = highest_conf_box['class_id'], highest_conf_box['confidence']
                label = f'{model.names[class_id]}: {confidence_val:.2f}' 
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        frames_processed_in_loop += 1

        loop_end_time = time.time()
        elapsed_time = loop_end_time - loop_start_time
        if elapsed_time > 0:
            actual_fps_display = 1 / elapsed_time
        
        fps_text = f'Proc. FPS: {actual_fps_display:.2f}'
        cv2.putText(frame, fps_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        conf_display_text = f'Conf: {g_current_conf_threshold:.2f}' 
        cv2.putText(frame, conf_display_text, (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        frame_info_text = f'Frame: {current_frame_idx_from_thread} / {max(0, total_frames_video-1)}'
        cv2.putText(frame, frame_info_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        # Display the original frame (with detections drawn on it)
        # If you want to see the effect of histogram equalization for display, 
        # you could imshow(frame_for_inference) in a separate window or instead of 'frame'.
        # For now, detections are drawn on 'frame' which is not equalized.
        cv2.imshow('YOLOv8 Real-time Detection', frame)


        if current_frame_idx_from_thread >= 0 and current_frame_idx_from_thread < total_frames_video:
            cv2.setTrackbarPos('Frame', 'YOLOv8 Real-time Detection', current_frame_idx_from_thread)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord(' '): 
            paused = not paused
            if paused:
                print("Paused")
            else:
                print("Resumed")

    except Exception as e:
        print(f"Error in main loop: {e}")
        traceback.print_exc()
        break

print("Exiting program...")
threaded_cap.release()
cv2.destroyAllWindows()
print("Resources released.")