import numpy as np
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
import cv2 #type: ignore
import time
import io
import sys
import queue
import os
from ultralytics import YOLO # type: ignore
import multiprocessing
import threading

# Constants
DEAD_ZONE = 20  # Minimum movement threshold to ignore small movements
MOVE_MULTIPLIER = 0.91  # Factor to adjust sensitivity of movements

MODEL_PATH_JF = r"C:\Users\JellyTracker\Downloads\best (1).pt" # jf good model
MODEL_PATH_LARVAE = r"C:\Users\JellyTracker\Desktop\TrainingPipeline\Foundational_Training\train_m_Larvae_seg\weights\best.pt" # larvae testing model

IMG_SIZE = 1024  # Set the image size for inference
CONF_THRESHOLD = 0.25  # Confidence threshold
IOU_THRESHOLD = 0.7  # IoU threshold for NMS
HALF_PRECISION = True  # Enable FP16 inference if supported

# Load the trained YOLO model
modelJF = YOLO(MODEL_PATH_JF)
modelLarvae = YOLO(MODEL_PATH_LARVAE)

is_jf_mode = multiprocessing.Value('i', 0)

def detect_jellyfish(frame, is_jf_mode):
    # Check if the frame is valid
    if frame is None:
        return (None,None), (None, None, None, None)
    
    # Ensure the frame is a NumPy array
    if not isinstance(frame, np.ndarray):
        return (None,None), (None, None, None, None)

    # Resize frame for faster processing
    try:
        frame_resized = cv2.resize(frame, (IMG_SIZE, IMG_SIZE))
    except cv2.error as e:
        return (None,None), (None, None, None, None)
    
    if is_jf_mode.value == 0: # larvae tracking
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

    # Perform object detection using the YOLO model
    if is_jf_mode.value == 1:
        results = modelJF.predict(frame_resized,imgsz=IMG_SIZE,conf=CONF_THRESHOLD,iou=IOU_THRESHOLD,half=HALF_PRECISION, device='cuda:0', verbose=False)
    else:
        results = modelLarvae.predict(frame_for_inference,imgsz=IMG_SIZE,conf=CONF_THRESHOLD,iou=IOU_THRESHOLD,half=HALF_PRECISION, device='cuda:0', verbose=False)
    
    original_height, original_width = frame.shape[:2]
    # Find the box with the highest confidence
    highest_conf_box = None
    for result in results:
        for box in result.boxes:
            confidence = float(box.conf.item())
            if highest_conf_box is None or confidence > highest_conf_box['confidence']:
                x1 = int(box.xyxy[0][0] * original_width / IMG_SIZE)
                y1 = int(box.xyxy[0][1] * original_height / IMG_SIZE)
                x2 = int(box.xyxy[0][2] * original_width / IMG_SIZE)
                y2 = int(box.xyxy[0][3] * original_height / IMG_SIZE)
                
                highest_conf_box = {
                    'x1': x1,
                    'y1': y1,
                    'x2': x2,
                    'y2': y2,
                    'class_id': int(box.cls.item()),
                    'confidence': confidence
                }

    # If a highest-confidence box was found, calculate the center coordinates
    if highest_conf_box:
        x1, y1, x2, y2 = highest_conf_box['x1'], highest_conf_box['y1'], highest_conf_box['x2'], highest_conf_box['y2']
        center_x = (x1 + x2) // 2
        center_y = (y1 + y2) // 2
        return (center_x, center_y),(x1,x2,y1,y2)

    # No jellyfish detected
    return (None,None), (None, None, None, None)


if __name__ == "__main__":
    # adjust
    video_path = r"C:\Users\JellyTracker\Desktop\JellyFishTrackingPC-main\saved_tracking_videos\JellyTracking_20250722_163900.mp4"
    cap = cv2.VideoCapture(video_path)

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_time = 1 / fps

    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))


    # Use a multiprocessing.Value for mode, e.g. larvae mode = 0
    is_jf_mode = multiprocessing.Value('i', 0)  # Set as needed (0 = larvae, 1 = jf)

    stored_detections = []
    detection_times = []

    print("Running detection on all frames...")

    frame_idx = 0
    start_detection_time = time.time()

    while frame_idx < total_frames:
        ret, frame = cap.read()
        if not ret:
            break

        detect_start = time.time()
        (cx, cy), (x1, x2, y1, y2) = detect_jellyfish(frame, is_jf_mode)
        detect_duration = time.time() - detect_start

        detection_times.append(detect_duration)

        if cx is not None:
            stored_detections.append((cx, cy, x1, y1, x2, y2))
        else:
            stored_detections.append(None)

        if frame_idx % (total_frames // 10) == 0:
            print(f"Progress: {int(frame_idx / total_frames * 100)}%")

        frame_idx += 1

    cap.release()
    print("Progress: 100%")
    cv2.namedWindow("Larvae Detection", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Larvae Detection", frame_width, frame_height + 60)
    detection_duration = time.time() - start_detection_time

    detected_frames = sum(1 for d in stored_detections if d is not None)

    print("\n==== Detection Summary ====")
    print(f"Frames processed: {frame_idx}")
    print(f"Detections found: {detected_frames} ({(detected_frames / frame_idx) * 100:.2f}%)")
    print(f"No detections: {frame_idx - detected_frames} ({((frame_idx - detected_frames) / frame_idx) * 100:.2f}%)")
    print(f"Average detection FPS: {frame_idx / detection_duration:.2f}")

    # ---------- Playback GUI ----------
    cap = cv2.VideoCapture(video_path)
    cv2.namedWindow('Larvae Detection Review', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Larvae Detection Review', frame_width, frame_height + 80)

    paused = False
    current_frame_idx = 0

    def on_trackbar(val):
        global current_frame_idx
        current_frame_idx = val
        cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame_idx)

    cv2.createTrackbar('Frame', 'Larvae Detection Review', 0, total_frames - 1, on_trackbar)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        detection = stored_detections[current_frame_idx]
        if detection:
            cx, cy, x1, y1, x2, y2 = detection
            cv2.circle(frame, (cx, cy), 5, (0, 255, 0), -1)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
        else:
            cv2.putText(frame, "No Detection", (30, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        cv2.imshow('Larvae Detection Review', frame)
        cv2.setTrackbarPos('Frame', 'Larvae Detection Review', current_frame_idx)

        current_frame_idx += 1
        if current_frame_idx >= total_frames:
            break

        # 60 FPS ≈ 1000 ms / 60 = ~16 ms per frame
        key = cv2.waitKey(16) & 0xFF

        if key == ord('q'):
            break
        # Check if window closed
        if cv2.getWindowProperty('Larvae Detection Review', cv2.WND_PROP_VISIBLE) < 1:
            break

    cap.release()
    cv2.destroyAllWindows()
            