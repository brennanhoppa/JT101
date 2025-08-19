# live stream util funcs
import os
import pygame # type: ignore
import cv2 #type: ignore
import numpy as np #type: ignore

def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def webcam_image_to_pygame(frame):
    # Convert BGR to RGB for pygame
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    # Convert to contiguous array
    rgb_frame = np.ascontiguousarray(rgb_frame.astype(np.uint8))
    # Create pygame surface
    return pygame.surfarray.make_surface(rgb_frame.swapaxes(0, 1))

def clear_terminal():
    os.system('cls')   
    print('New Terminal')
