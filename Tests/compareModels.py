import numpy as np
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
import cv2
import time
import multiprocessing
from ultralytics import YOLO #type: ignore

# ----------------- Constants -----------------
IMG_SIZE = 1024
CONF_THRESHOLD = 0.25
IOU_THRESHOLD = 0.7
HALF_PRECISION = True

# ----------------- Model Paths -----------------
MODEL_PATH_L1 = r"C:\Users\JellyTracker\Desktop\TrainingPipeline\Foundational_Training\train_m_Larvae_seg\weights\best.pt"
MODEL_PATH_L2 = r"C:\Users\JellyTracker\Desktop\TrainingPipeline\Larvae_additional_training\train_l_Larvae_seg\weights\best.pt"

# ----------------- Load YOLO models -----------------
modelL1 = YOLO(MODEL_PATH_L1)
modelL2 = YOLO(MODEL_PATH_L2)

# ----------------- Detection Function -----------------
def detect_jellyfish(frame, model1=True):
    """
    Uses global models: modelL1 if model1=True, else modelL2
    """
    if frame is None or not isinstance(frame, np.ndarray):
        return (None,None), (None,None,None,None)
    
    try:
        frame_resized = cv2.resize(frame, (IMG_SIZE, IMG_SIZE))
    except cv2.error:
        return (None,None), (None,None,None,None)
    
    # Optional preprocessing for larvae (model2)
    if not model1:
        ycbcr_frame = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2YCrCb)
        y, cr, cb = cv2.split(ycbcr_frame)
        y_eq = cv2.equalizeHist(y)
        frame_resized = cv2.cvtColor(cv2.merge((y_eq, cr, cb)), cv2.COLOR_YCrCb2BGR)

    model = modelL1 if model1 else modelL2
    results = model.predict(
        frame_resized,
        imgsz=IMG_SIZE,
        conf=CONF_THRESHOLD,
        iou=IOU_THRESHOLD,
        half=HALF_PRECISION,
        device='cuda:0',
        verbose=False
    )

    h, w = frame.shape[:2]
    highest_conf_box = None

    for result in results:
        for box in result.boxes:
            conf = float(box.conf.item())
            if highest_conf_box is None or conf > highest_conf_box['confidence']:
                x1 = int(box.xyxy[0][0] * w / IMG_SIZE)
                y1 = int(box.xyxy[0][1] * h / IMG_SIZE)
                x2 = int(box.xyxy[0][2] * w / IMG_SIZE)
                y2 = int(box.xyxy[0][3] * h / IMG_SIZE)
                highest_conf_box = {'x1':x1,'y1':y1,'x2':x2,'y2':y2,'confidence':conf}

    if highest_conf_box:
        x1,y1,x2,y2 = highest_conf_box['x1'], highest_conf_box['y1'], highest_conf_box['x2'], highest_conf_box['y2']
        cx = (x1+x2)//2
        cy = (y1+y2)//2
        return (cx, cy), (x1, x2, y1, y2)
    
    return (None,None), (None,None,None,None)

# ----------------- Video Processing -----------------
def run_detection(video_path, model1=True):
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    stored_detections = []
    detection_times = []

    print(f"Running detection with {'L1' if model1 else 'L2'} on all frames...")

    frame_idx = 0
    start_time = time.time()

    while frame_idx < total_frames:
        ret, frame = cap.read()
        if not ret:
            break

        t0 = time.time()
        (cx, cy), (x1, x2, y1, y2) = detect_jellyfish(frame, model1=model1)
        detection_times.append(time.time() - t0)

        if cx is not None:
            stored_detections.append((cx, cy, x1, y1, x2, y2))
        else:
            stored_detections.append(None)

        if frame_idx % max(1, total_frames//10) == 0:
            print(f"Progress: {int(frame_idx/total_frames*100)}%")

        frame_idx += 1

    cap.release()
    print("Progress: 100%")

    # Summary metrics
    detected_frames = sum(1 for d in stored_detections if d is not None)
    duration = sum(detection_times)
    print(f"\n==== {'L1' if model1 else 'L2'} Detection Summary ====")
    print(f"Frames processed: {frame_idx}")
    print(f"Detections found: {detected_frames} ({detected_frames/frame_idx*100:.2f}%)")
    print(f"No detections: {frame_idx-detected_frames} ({(frame_idx-detected_frames)/frame_idx*100:.2f}%)")
    print(f"Average detection FPS: {frame_idx/duration:.2f}")

    return stored_detections, frame_width, frame_height, total_frames

# ----------------- Playback Side-by-Side -----------------
def playback_side_by_side(video_path, det1, det2, frame_width, frame_height, total_frames):
    cap = cv2.VideoCapture(video_path)
    frame_idx = 0

    cv2.namedWindow("Model Comparison", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Model Comparison", frame_width*2, frame_height)

    while frame_idx < total_frames:
        ret, frame = cap.read()
        if not ret:
            break

        # Copy frames for side-by-side display
        frame1 = frame.copy()
        frame2 = frame.copy()

        # Draw detections
        d1 = det1[frame_idx]
        d2 = det2[frame_idx]

        if d1:
            cx, cy, x1, y1, x2, y2 = d1
            cv2.circle(frame1, (cx, cy), 5, (0,255,0), -1)
            cv2.rectangle(frame1, (x1, y1), (x2, y2), (255,0,0), 2)
            cv2.putText(frame1, "L1", (10,30), cv2.FONT_HERSHEY_SIMPLEX,1,(0,255,255),2)
        else:
            cv2.putText(frame1, "L1: No Detection", (10,30), cv2.FONT_HERSHEY_SIMPLEX,1,(0,0,255),2)

        if d2:
            cx, cy, x1, y1, x2, y2 = d2
            cv2.circle(frame2, (cx, cy), 5, (0,255,0), -1)
            cv2.rectangle(frame2, (x1, y1), (x2, y2), (255,0,0), 2)
            cv2.putText(frame2, "L2", (10,30), cv2.FONT_HERSHEY_SIMPLEX,1,(0,255,255),2)
        else:
            cv2.putText(frame2, "L2: No Detection", (10,30), cv2.FONT_HERSHEY_SIMPLEX,1,(0,0,255),2)

        combined = np.hstack([frame1, frame2])
        cv2.imshow("Model Comparison", combined)
        key = cv2.waitKey(16) & 0xFF
        if key==ord('q') or cv2.getWindowProperty("Model Comparison", cv2.WND_PROP_VISIBLE)<1:
            break

        frame_idx += 1

    cap.release()
    cv2.destroyAllWindows()

# ----------------- Main -----------------
if __name__ == "__main__":
    video_path = r"C:\Users\JellyTracker\Desktop\JellyFishTrackingPC-main\saved_tracking_videos\JellyTracking_20250722_163900.mp4"

    # Run detection for L1
    det_L1, w, h, total_frames = run_detection(video_path, model1=True)
    # Run detection for L2
    det_L2, _, _, _ = run_detection(video_path, model1=False)

    # Playback side by side
    playback_side_by_side(video_path, det_L1, det_L2, w, h, total_frames)
