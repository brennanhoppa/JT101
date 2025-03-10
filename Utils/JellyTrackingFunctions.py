import numpy as np
import logging

# Constants for tracking
MAX_STEP_SIZE = 95
MIN_STEP_SIZE = 10
DEAD_ZONE = 20  # Minimum movement threshold to ignore small movements
MOVE_MULTIPLIER = 0.7  # Factor to adjust sensitivity of movements

# Logging setup
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

import cv2 #type: ignore
import numpy as np
import time
from ultralytics import YOLO # type: ignore
import threading

# Constants
MODEL_PATH = r"C:\Users\JellyTracker\Desktop\JellyFishTrackingPC-main\best (1).pt"
IMG_SIZE = 1024  # Set the image size for inference
CONF_THRESHOLD = 0.25  # Confidence threshold
IOU_THRESHOLD = 0.7  # IoU threshold for NMS
HALF_PRECISION = True  # Enable FP16 inference if supported

# Load the trained YOLO model
model = YOLO(MODEL_PATH)

def detect_jellyfish(frame):
    """
    Uses the YOLO model to detect jellyfish in a given frame.
    
    :param frame: The current frame to analyze
    :return: The coordinates (center_x, center_y) of the detected jellyfish if found, otherwise None
    """
    # Check if the frame is valid
    if frame is None:
        print("Warning: Frame is None, skipping detection.")
        return None
    
    # Ensure the frame is a NumPy array
    if not isinstance(frame, np.ndarray):
        print("Warning: Frame is not a valid NumPy array.")
        return None

    # Resize frame for faster processing
    try:
        frame_resized = cv2.resize(frame, (IMG_SIZE, IMG_SIZE))
    except cv2.error as e:
        print(f"Error during resize: {e}")
        return None

    # Perform object detection using the YOLO model
    results = model.predict(
        frame_resized,
        imgsz=IMG_SIZE,
        conf=CONF_THRESHOLD,
        iou=IOU_THRESHOLD,
        half=HALF_PRECISION
    )



    # Find the box with the highest confidence
    highest_conf_box = None
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

    # If a highest-confidence box was found, calculate the center coordinates
    if highest_conf_box:
        x1, y1, x2, y2 = highest_conf_box['x1'], highest_conf_box['y1'], highest_conf_box['x2'], highest_conf_box['y2']
        center_x = (x1 + x2) // 2
        center_y = (y1 + y2) // 2
        return (center_x, center_y)

    # No jellyfish detected
    return None


def calculate_movement(jellyfish_pos, center_x, center_y):
    """
    Calculates the movement needed to center the camera on the jellyfish.
    
    :param jellyfish_pos: Current detected position of the jellyfish (x, y)
    :param center_x: Center x-coordinate of the camera's frame
    :param center_y: Center y-coordinate of the camera's frame
    :return: Tuple of steps (step_x, step_y) needed to center the jellyfish
    """
    if not jellyfish_pos:
        return None, None
    
    jx, jy = jellyfish_pos
    dx = jx - center_x
    dy = center_y - jy  # Invert y-axis to match Cartesian coordinates
    
    # Ignore small movements within a dead zone
    if abs(dx) < DEAD_ZONE and abs(dy) < DEAD_ZONE:
        return None, None

    # Calculate step sizes with adjusted sensitivity
    step_x = int(np.clip(dx * MOVE_MULTIPLIER, -MAX_STEP_SIZE, MAX_STEP_SIZE))
    step_y = int(np.clip(dy * MOVE_MULTIPLIER, -MAX_STEP_SIZE, MAX_STEP_SIZE))

    # Ensure a minimum step size for quicker response
    if 0 < abs(step_x) < MIN_STEP_SIZE:
        step_x = MIN_STEP_SIZE if step_x > 0 else -MIN_STEP_SIZE
    if 0 < abs(step_y) < MIN_STEP_SIZE:
        step_y = MIN_STEP_SIZE if step_y > 0 else -MIN_STEP_SIZE

    return step_x, step_y


def steps_to_mm(steps_x, steps_y, step_angle=1.8, lead=8):
    """
    Converts stepper motor steps to millimeters for x and y axes.
    
    Parameters:
    - steps_x (int): Number of steps for the x-axis.
    - steps_y (int): Number of steps for the y-axis.
    - step_angle (float): Step angle of the motor in degrees (default is 1.8°).
    - lead (float): Lead of the lead screw in mm (default is 8 mm).
    
    Returns:
    - (float, float): Distance in mm for x and y axes.
    """
    steps_per_revolution = 360 / step_angle
    mm_per_step = lead / steps_per_revolution
    
    distance_x = steps_x * mm_per_step
    distance_y = steps_y * mm_per_step
    
    return distance_x, distance_y




PIXELS_PER_CM = 154  # Calibration value: 154 pixels = 1 cm
PIXELS_PER_MM = PIXELS_PER_CM / 10  # Convert to pixels per mm (15.4 pixels = 1 mm)

def pixels_to_mm(pixel_distance):
    """
    Convert pixel distance to millimeters
    """
    return pixel_distance / PIXELS_PER_MM



















































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

# def calculate_movement(flashlight_pos, center_x, center_y):
#     if not flashlight_pos:
#         return None, None

#     fx, fy = flashlight_pos
#     dx = fx - center_x
#     dy = center_y - fy  # Invert y-axis to match Cartesian coordinates

#     # Ignore very small movements
#     if abs(dx) < DEAD_ZONE and abs(dy) < DEAD_ZONE:
#         return None, None

#     # Calculate step sizes with adjusted sensitivity
#     step_x = int(np.clip(dx * MOVE_MULTIPLIER, -MAX_STEP_SIZE, MAX_STEP_SIZE))
#     step_y = int(np.clip(dy * MOVE_MULTIPLIER, -MAX_STEP_SIZE, MAX_STEP_SIZE))

#     # Ensure minimum step size for quicker response
#     if 0 < abs(step_x) < MIN_STEP_SIZE:
#         step_x = MIN_STEP_SIZE if step_x > 0 else -MIN_STEP_SIZE
#     if 0 < abs(step_y) < MIN_STEP_SIZE:
#         step_y = MIN_STEP_SIZE if step_y > 0 else -MIN_STEP_SIZE

#     return step_x, step_y

def track_cumulative_steps(step_x, step_y, cumulative_steps, recording):
    if recording:
        # Note: step_x is positive for 'L' and negative for 'R'
        cumulative_steps['x'] += step_x
        cumulative_steps['y'] += step_y
        timestamp = time.time()
        return (cumulative_steps['x'], cumulative_steps['y'], timestamp)
    return None

def save_tracking_data(filename, step_tracking_data):
    with open(filename, 'w') as f:
        f.write("x,y,t\n")
        for x, y, t in step_tracking_data:
            f.write(f"{x},{y},{t}\n")
    print(f"Tracking data saved to {filename}")