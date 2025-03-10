import cv2
import time
from ultralytics import YOLO
import threading

# Load the trained model
model_path = r"C:\Users\JellyTracker\Desktop\JellyFishTrackingPC-main\best (1).pt"
model = YOLO(model_path)

# Open video file
video_path = r"C:\Users\JellyTracker\Desktop\JellyFishTrackingPC-main\saved_tracking_videos\TrackingTest1.mp4"
cap = cv2.VideoCapture(video_path)

# Check if the video capture was successful
if not cap.isOpened():
    print("Error: Could not open video.")
    exit()

# Get the total number of frames in the video and the frame rate
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
fps_video = cap.get(cv2.CAP_PROP_FPS)

# Desired processing frame rate (20 FPS)
target_fps = 20
frame_skip = max(1, int(fps_video / target_fps))  # Calculate the number of frames to skip for 20 FPS processing

# Create a named window for displaying the video
cv2.namedWindow('YOLOv8 Real-time Detection', cv2.WINDOW_NORMAL)

# Trackbar callback function to set the video frame position
def on_trackbar(val):
    cap.set(cv2.CAP_PROP_POS_FRAMES, val)

# Create a trackbar for navigating the video
cv2.createTrackbar('Frame', 'YOLOv8 Real-time Detection', 0, total_frames - 1, on_trackbar)

# YOLO Inference parameters
img_size = 1024  # Set the image size for inference
conf_threshold = 0.25  # Confidence threshold
iou_threshold = 0.7  # IoU threshold for NMS
half_precision = True  # Enable FP16 inference

# Initialize variables for FPS calculation and frame control
prev_time = 0
frame_count = 0
actual_fps = 0

# Multi-threaded frame capture
class VideoCaptureThread:
    def __init__(self, video_source):
        self.cap = cv2.VideoCapture(video_source)
        self.grabbed, self.frame = self.cap.read()
        self.stopped = False
        self.lock = threading.Lock()

        # Start the thread to read frames from the video stream
        threading.Thread(target=self.update, daemon=True).start()

    def update(self):
        while not self.stopped:
            if not self.grabbed:
                self.stop()
            else:
                self.grabbed, frame = self.cap.read()
                with self.lock:
                    self.frame = frame

    def read(self):
        with self.lock:
            frame = self.frame.copy()
        return frame

    def stop(self):
        self.stopped = True

    def release(self):
        self.cap.release()

# Start the threaded video capture
threaded_cap = VideoCaptureThread(video_path)

# Loop over frames from the video
while True:
    start_time = time.time()

    # Read the frame from the video
    frame = threaded_cap.read()

    # Break the loop if there are no more frames
    if frame is None:
        break

    # Resize the frame for faster processing if needed
    frame_resized = cv2.resize(frame, (img_size, img_size))

    # Get the current frame index
    current_frame = int(cap.get(cv2.CAP_PROP_POS_FRAMES))

    # Run inference only if it's the correct frame based on frame_skip
    if frame_count % frame_skip == 0:
        # Perform object detection with the specified parameters
        results = model.predict(
            frame_resized,
            imgsz=img_size,  # Set the input size for the model
            conf=conf_threshold,  # Minimum confidence threshold
            iou=iou_threshold,  # IoU threshold for NMS
            half=half_precision  # Use half-precision (FP16) inference
        )

        # Initialize a variable to store the highest-confidence box
        highest_conf_box = None

        # Iterate through results to find the box with the highest confidence
        for result in results:
            for box in result.boxes:
                confidence = float(box.conf.item())
                if highest_conf_box is None or confidence > highest_conf_box['confidence']:
                    highest_conf_box = {
                        'x1': int(box.xyxy[0][0]),
                        'y1': int(box.xyxy[0][1]),
                        'x2': int(box.xyxy[0][2]),
                        'y2': int(box.xyxy[0][3]),
                        'class_id': int(box.cls.item()),
                        'confidence': confidence
                    }

        # If a highest-confidence box was found, draw it
        if highest_conf_box:
            x1, y1, x2, y2 = highest_conf_box['x1'], highest_conf_box['y1'], highest_conf_box['x2'], highest_conf_box['y2']
            class_id, confidence = highest_conf_box['class_id'], highest_conf_box['confidence']
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            label = f'{result.names[class_id]}: {confidence:.2f}'
            cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    # Update frame count
    frame_count += 1

    # Display the actual FPS
    end_time = time.time()
    elapsed_time = end_time - start_time
    if elapsed_time > 0:
        actual_fps = 1 / elapsed_time
    fps_text = f'Actual FPS: {actual_fps:.2f}'
    cv2.putText(frame, fps_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

    # Display the frame with or without bounding boxes
    cv2.imshow('YOLOv8 Real-time Detection', frame)

    # Update the trackbar position
    cv2.setTrackbarPos('Frame', 'YOLOv8 Real-time Detection', current_frame)

    # Break the loop if 'q' is pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Stop video capture and release resources
threaded_cap.stop()
threaded_cap.release()
cv2.destroyAllWindows()
