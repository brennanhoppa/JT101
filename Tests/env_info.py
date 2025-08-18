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


import platform
import psutil  # type: ignore
import cpuinfo # type: ignore
import GPUtil # type: ignore

def get_system_info():
    info = {}

    # OS info
    info['OS'] = f"{platform.system()} {platform.release()} ({platform.version()})"

    # CPU info
    cpu = cpuinfo.get_cpu_info()
    info['CPU'] = {
        'Brand': cpu.get('brand_raw', 'Unknown'),
        'Arch': cpu.get('arch', 'Unknown'),
        'Cores (logical)': psutil.cpu_count(logical=True),
        'Cores (physical)': psutil.cpu_count(logical=False),
        'Frequency (MHz)': psutil.cpu_freq().max if psutil.cpu_freq() else 'Unknown'
    }

    # RAM info
    ram_gb = round(psutil.virtual_memory().total / (1024 ** 3), 2)
    info['RAM'] = f"{ram_gb} GB"

    # GPU info
    gpus = GPUtil.getGPUs()
    gpu_list = []
    for gpu in gpus:
        gpu_list.append({
            'Name': gpu.name,
            'ID': gpu.id,
            'Driver': gpu.driver,
            'VRAM (GB)': round(gpu.memoryTotal / 1024, 2),
            'GPU Load (%)': gpu.load * 100,
            'Temperature (C)': gpu.temperature
        })
    info['GPUs'] = gpu_list if gpu_list else 'No GPU detected'

    return info

if __name__ == "__main__":
    system_info = get_system_info()
    for key, value in system_info.items():
        print(f"{key}: {value}")
