import torch
from ultralytics import YOLO

# Load the trained model
model_path = r"C:\Users\JellyTracker\Desktop\JellyFishTrackingPC-main\JellyFishModel.pt"
model = YOLO(model_path)

# Specify the path for the ONNX export
onnx_model_path = r"C:\Users\JellyTracker\Desktop\JellyFishTrackingPC-main\JellyFishModel.onnx"

# Export the model to ONNX format
# Use 'imgsz' for image size (width, height), and specify the export format
model.export(format="onnx", imgsz=(1024, 1024), optimize=True)
