import numpy as np
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
import cv2 #type: ignore
import time
import io
from ultralytics import YOLO # type: ignore
try:
    from Utils.CONSTANTS import CONSTANTS
    from Utils.log import log
except:
    from CONSTANTS import CONSTANTS
    from log import log

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

def run_yolo_with_output(model, frame_resized, **kwargs):
    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)
    
    # Use the ultralytics logger, not root
    yolo_logger = logging.getLogger('ultralytics')
    yolo_logger.addHandler(handler)
    yolo_logger.setLevel(logging.INFO)

    try:
        results = model.predict(frame_resized, **kwargs)
    finally:
        yolo_logger.removeHandler(handler)

    return results, log_stream.getvalue()

def detect_jellyfish(frame, detect_light, is_jf_mode, log_queue, verbose):
    """
    Uses the YOLO model to detect jellyfish in a given frame.
    
    :param frame: The current frame to analyze
    :return: The coordinates (center_x, center_y) of the detected jellyfish if found, otherwise None
    """
    # Check if the frame is valid
    if frame is None:
        log("Warning: Frame is None, skipping detection.",log_queue)
        return None
    
    # Ensure the frame is a NumPy array
    if not isinstance(frame, np.ndarray):
        log("Warning: Frame is not a valid NumPy array.",log_queue)
        return None

    # Resize frame for faster processing
    try:
        frame_resized = cv2.resize(frame, (IMG_SIZE, IMG_SIZE))
    except cv2.error as e:
        log(f"Error during resize: {e}",log_queue)
        return None

    if detect_light:
        brightness_threshold=200
        gray = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if len(contours) == 0:
            return None  
        largest_contour = None
        max_area = 0
        largest_center = None
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > max_area:
                max_area = area
                largest_contour = contour
        if max_area < brightness_threshold:
            return None  
        M = cv2.moments(largest_contour)
        if M['m00'] == 0:
            return None 
        cx = int(M['m10'] / M['m00'])
        cy = int(M['m01'] / M['m00'])
        return (cx, cy), (0,0,0,0)
    
    if is_jf_mode.value == 0: # larvae tracking
        ### BRAD EDIT THIS ###
        ######FOR LARVAE ONLY#######
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
    if verbose.value == False:
        if is_jf_mode.value == 1:
            results = modelJF.predict(frame_resized,imgsz=IMG_SIZE,conf=CONF_THRESHOLD,iou=IOU_THRESHOLD,half=HALF_PRECISION, device='cuda:0', verbose=False)
        else:
            results = modelLarvae.predict(frame_for_inference,imgsz=IMG_SIZE,conf=CONF_THRESHOLD,iou=IOU_THRESHOLD,half=HALF_PRECISION, device='cuda:0', verbose=False)
    else:
        if is_jf_mode.value == 1:
            results, log_output = run_yolo_with_output(modelJF,frame_resized,imgsz=IMG_SIZE,conf=CONF_THRESHOLD,iou=IOU_THRESHOLD,half=HALF_PRECISION, device='cuda:0', verbose=True)
        else:
            results, log_output = run_yolo_with_output(modelLarvae,frame_resized,imgsz=IMG_SIZE,conf=CONF_THRESHOLD,iou=IOU_THRESHOLD,half=HALF_PRECISION, device='cuda:0', verbose=True)
        log(log_output,log_queue)

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
    return None, (None, None, None, None)

def mode_string(mode):
    if mode.value == 0:
        return "larvae"
    elif mode.value == 1:
        return "jellyfish"
    else:
        return "invalid mode"

def calculate_delta_Pixels(jellyfish_pos, center_x, center_y):
    """
    Calculates the pixel difference in x and y from the center of the frame to the center of the jellyfish box
    """
    jx, jy = jellyfish_pos
    dx = jx - center_x
    dy = center_y - jy  # Invert y-axis to match Cartesian coordinates
    return dx,dy

def calculate_movement(dx,dy,is_jf_mode):
    """
    Calculates the movement needed to center the camera on the jellyfish.
    
    :param jellyfish_pos: Current detected position of the jellyfish (x, y)
    :param center_x: Center x-coordinate of the camera's frame
    :param center_y: Center y-coordinate of the camera's frame
    :return: Tuple of steps (step_x, step_y) needed to center the jellyfish
    """
    
    # Constants for tracking
    if is_jf_mode.value == 1: # means JF mode
        MIN_STEP_SIZE = 10 # 10 for JF
        MAX_STEP_SIZE = 95
    else: # means larvae mode
        MIN_STEP_SIZE = 15 # 5 for larvae
        MAX_STEP_SIZE = 75
    # Calculate step sizes with adjusted sensitivity
    step_x = int(np.clip(dx * MOVE_MULTIPLIER, -MAX_STEP_SIZE, MAX_STEP_SIZE))
    step_y = int(np.clip(dy * MOVE_MULTIPLIER, -MAX_STEP_SIZE, MAX_STEP_SIZE))

    # Ensure a minimum step size for quicker response
    if 0 < abs(step_x) < MIN_STEP_SIZE:
        step_x = MIN_STEP_SIZE if step_x > 0 else -MIN_STEP_SIZE
    if 0 < abs(step_y) < MIN_STEP_SIZE:
        step_y = MIN_STEP_SIZE if step_y > 0 else -MIN_STEP_SIZE

    # Ignore small movements within a dead zone
    if abs(dx) < DEAD_ZONE:
        step_x = 0
    if abs(dy) < DEAD_ZONE:
        step_y = 0
        
    step_x, step_y = int(-1*round(step_x,0)), int(round(step_y,0))
    return step_x, step_y

def steps_to_mm(steps, is_jf_mode):
    if is_jf_mode.value == 1: # jf
        return steps / CONSTANTS["JFStepsPerMm"]
    else: # larvae
        return steps / CONSTANTS["LStepsPerMm"]

def mm_to_steps(mm, is_jf_mode):
    if is_jf_mode.value == 1: # jf
        return mm * CONSTANTS["JFStepsPerMm"]
    else: # larvae
        return mm * CONSTANTS["LStepsPerMm"]

def pixels_to_mm(pixel_distance, is_jf_mode):
    """
    Convert pixel distance to millimeters
    """
    if is_jf_mode.value == 1: # jf
        return pixel_distance / CONSTANTS["JFPixelsPerMm"]
    else: # larvae
        return pixel_distance / CONSTANTS["LPixelsPerMm"]

def mm_to_pixels(mm_distance, is_jf_mode):
    if is_jf_mode.value == 1: # jf
        return mm_distance * CONSTANTS["JFPixelsPerMm"]
    else: # larvae
        return mm_distance * CONSTANTS["LPixelsPerMm"]

def detect_flashlight(image_ptr):
    image_data = image_ptr.GetNDArray()
    threshold = 200
    binary = (image_data > threshold).astype(np.uint8) * 255
    
    # Find connected components
    num_labels, labels = cv2.connectedComponents(binary)
    
    # Find the largest non-background component
    largest_area = 0
    largest_centroid = None
    for i in range(1, num_labels):  # Start from 1 to skip background
        area = np.sum(labels == i)
        if area > largest_area:
            largest_area = area
            y, x = np.where(labels == i)
            largest_centroid = (int(np.mean(x)), int(np.mean(y)))
    
    return largest_centroid

def track_cumulative_steps(step_x, step_y, cumulative_steps, recording):
    if recording:
        # Note: step_x is positive for 'L' and negative for 'R'
        cumulative_steps['x'] += step_x
        cumulative_steps['y'] += step_y
        timestamp = time.time()
        return (cumulative_steps['x'], cumulative_steps['y'], timestamp)
    return None
