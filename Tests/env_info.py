import sys
import traceback
import torch #type: ignore
import ultralytics #type: ignore
import numpy as np
import cv2
from ultralytics import YOLO #type: ignore

print("===== ENVIRONMENT INFO =====")

# Python
print("Python version:", sys.version)

# PyTorch
print("Torch version:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())
print("CUDA version:", torch.version.cuda)
print("cuDNN version:", torch.backends.cudnn.version())

# GPU info
if torch.cuda.is_available():
    print("GPU device name:", torch.cuda.get_device_name(0))
    print("Allocated memory (MB):", torch.cuda.memory_allocated(0)/1024**2)
    print("Cached memory (MB):", torch.cuda.memory_reserved(0)/1024**2)

# Ultralytics / YOLO
print("Ultralytics YOLO version:", ultralytics.__version__)

# Example: load your YOLO model to inspect architecture
MODEL_PATH_JF = r"C:\Users\JellyTracker\Desktop\JellyFishTrackingPC-main\Models\jf_best.pt"  # adjust path as needed
try:
    model = YOLO(MODEL_PATH_JF)
    print("Model loaded from:", MODEL_PATH_JF)
    print("Model classes:", model.model.names)
    print("Number of classes:", model.model.nc)
    print("Model YAML/architecture info:", model.model.yaml)
except Exception as e:
    print("Error loading model:", e)
    traceback.print_exc()

# NumPy and OpenCV
print("NumPy version:", np.__version__)
print("OpenCV version:", cv2.__version__)

print("===== END OF ENVIRONMENT INFO =====")
