import PySpin #type: ignore
import sys
import numpy as np # type: ignore
import matplotlib.pyplot as plt # type: ignore
import cv2 # type: ignore
import time
import pygame #type: ignore
import subprocess
import threading
import subprocess
import os


class AviType:
    """'Enum' to select AVI video type to be created and saved"""
    UNCOMPRESSED = 0
    MJPG = 1
    H264 = 2

chosenAviType = AviType.UNCOMPRESSED  # change me!
chosenAviType = AviType.MJPG  # change me!
NUM_IMAGES = 300  # number of images to use in AVI file
name = 'TESTBINNING2'
running = True

shared_image_list = []
shared_image_display_list = [] #list matches the shared image list in length, if it's a 0 it hasn't been displayed yet if it's a 1 it has been displayed on screen
image_acq_done = False

def pyspin_image_to_pygame(image_ptr):
    # Get the width and height of the image
    width = image_ptr.GetWidth()
    height = image_ptr.GetHeight()
    
    # Get the image data as a NumPy array
    image_data = np.array(image_ptr.GetData(), dtype=np.uint8)
    
    # Reshape the data into a 2D or 3D array depending on the color format (assuming 8-bit grayscale or RGB)
    if image_ptr.GetNumChannels() == 1:
        image_data = image_data.reshape((height, width))  # Grayscale image
    else:
        image_data = image_data.reshape((height, width, 3))  # RGB image
    # START HERE NEXT TIME TO FIX THIS THIS DOESN"T WORK NEED TO CONVERT IMAGE IN BETTER WAY
    # Create a Pygame Surface from the buffer
    return pygame.image.frombuffer(image_data.tobytes(), (width, height), "RGB")

def input_listener():
    global running, user_input
    while running:
        user_input = input("Enter something: ")
        if user_input == "exit":
            running = False

def imageacq(cam, nodemap, processor):
    global image_acq_done
    cam.BeginAcquisition()
    for i in range(NUM_IMAGES):
        try:
            image_result = cam.GetNextImage(1000) # need to experiment with - the value here is the number of milliseconds it waits for the next image
            if image_result.IsIncomplete():
                print('Image incomplete with image status %d...' % image_result.GetImageStatus())
            else:
                width = image_result.GetWidth()
                height = image_result.GetHeight()
                # print('Grabbed Image %d, width = %d, height = %d' % (i, width, height))
                shared_image_list.append(processor.Convert(image_result, PySpin.PixelFormat_Mono8))
                shared_image_display_list.append(0)
                # print('image ', i, ' added')
                image_result.Release()
        except PySpin.SpinnakerException as ex:
            print('Error: %s' % ex)
            result = False
    image_acq_done = True
    cam.EndAcquisition()

def imageadder(nodemap, nodemap_tldevice):
    global image_acq_done
    node_acquisition_framerate = PySpin.CFloatPtr(nodemap.GetNode('AcquisitionFrameRate'))
    framerate_to_set = node_acquisition_framerate.GetValue()
    print("frame rate in video set to: ", framerate_to_set)

    avi_recorder = PySpin.SpinVideo()
    ### ASSUMING FOR NOW Avi type is Uncompressed - review SaveToAvi.py for other options' code
    
    if chosenAviType == AviType.MJPG:
        avi_filename = 'SaveToAvi-MJPG-%s' % name

        option = PySpin.MJPGOption()
        option.frameRate = framerate_to_set
        option.quality = 75
    
    if chosenAviType == AviType.UNCOMPRESSED:
        avi_filename = 'SaveToAvi-Uncompressed-%s' % name
        option = PySpin.AVIOption()
        option.frameRate = framerate_to_set

    if chosenAviType == AviType.H264:
        avi_filename = 'SaveToAvi-H264-%s' % name
        option = PySpin.H264Option()
        option.frameRate = framerate_to_set
        option.bitrate = 1000000

    while not image_acq_done or shared_image_list:
        if len(shared_image_list) > 0:
            option.height = shared_image_list[0].GetHeight()
            option.width = shared_image_list[0].GetWidth()
            avi_recorder.Open(avi_filename, option)
            break
        time.sleep(0.01) # adjust if needed

    while not image_acq_done or shared_image_list:
        if len(shared_image_list) > 0:
            im = shared_image_list.pop(0)
            _ = shared_image_display_list.pop(0)
            avi_recorder.Append(im)
            # print('image added to video')
        time.sleep(0.001) # adjust as needed - don't want to spam check

    avi_recorder.Close()
    print('video saved and done at: ' , avi_filename)
    

def main():
    global running
    result = True
    
    # initialize camera
    system = PySpin.System.GetInstance()
    cam_list = system.GetCameras()
    num_cameras = cam_list.GetSize()
    if num_cameras != 1:
        cam_list.Clear()
        system.ReleaseInstance()
        print("Incorrect number of cameras (not 1)")
        return False
    cam = cam_list[0]
    nodemap_tldevice = cam.GetTLDeviceNodeMap()
    cam.Init()
    nodemap = cam.GetNodeMap()
    # setting binning to 2x2 so image will be 1024x1024 (can turn this off for 2048 x 2048 images but then data will be massive)
    cam.BinningVertical.SetValue(2)

    node_acquisition_mode = PySpin.CEnumerationPtr(nodemap.GetNode('AcquisitionMode'))
    if not PySpin.IsReadable(node_acquisition_mode) or not PySpin.IsWritable(node_acquisition_mode):
        print('Unable to set acquisition mode to continuous (enum retrieval). Aborting...')
        return False
    node_acquisition_mode_continuous = node_acquisition_mode.GetEntryByName('Continuous')
    if not PySpin.IsReadable(node_acquisition_mode_continuous):
        print('Unable to set acquisition mode to continuous (entry retrieval). Aborting...')
        return False
    acquisition_mode_continuous = node_acquisition_mode_continuous.GetValue()
    node_acquisition_mode.SetIntValue(acquisition_mode_continuous)
    print('Acquisition mode set to continuous...')

    # print( cam.BinningHorizontal.GetAccessMode())
    
    # for n in nodemap.GetNodeNames():
    #     node = nodemap.GetNode(n)
    #     print(n, 'and type: ', node.GetPrincipalInterfaceType())


    

    processor = PySpin.ImageProcessor()
    processor.SetColorProcessing(PySpin.SPINNAKER_COLOR_PROCESSING_ALGORITHM_HQ_LINEAR)

    node_acquisition_framerate = PySpin.CFloatPtr(nodemap.GetNode('AcquisitionFrameRate'))
    fr = node_acquisition_framerate.GetValue()
    print("Framerate is: ", fr)

    # SETUP PYGAME
    pygame.init()
    screen_info = pygame.display.Info()
    screen_width = screen_info.current_w
    screen_height = screen_info.current_h
    # Set the window size to half of the screen width, and height slightly smaller than the full height
    window_width = screen_width // 2
    window_height = screen_height - 80  # Leave space for window controls
    # Set the window position to the left side of the screen, slightly lower
    os.environ['SDL_VIDEO_WINDOW_POS'] = "0,30"
    window = pygame.display.set_mode((window_width, window_height))
    # Set the window title
    pygame.display.set_caption("Pygame Input Display")
    # Set up font for rendering text
    font = pygame.font.Font(None, 36)  # Default font, size 36
    
    # initial state
    user_input = ""
    new_image = False

    # create 3 threads - 1 receiving images, 1 saving images
    imageacquistion = threading.Thread(target=imageacq, args=(cam, nodemap,processor))
    imageaddtovid = threading.Thread(target=imageadder, args=(nodemap,nodemap_tldevice))
    input_thread = threading.Thread(target=input_listener)

    # start 3 threads
    imageacquistion.start()
    imageaddtovid.start()
    input_thread.start()

    # MAIN LOOP
    while running:
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # Fill the window with a color (optional)
        window.fill((0, 128, 255))  # Fill with a blue color

        # Blit the PySpin image to the top-left corner of the Pygame window
        if len(shared_image_list) > 0 and shared_image_display_list[-1] == 0:
            # need some way to only have to blit / update this once? flags for each one?
            py_image = pyspin_image_to_pygame(shared_image_list[-1])
            shared_image_display_list[-1] == 1
            new_image = True
             
        if new_image:
            window.blit(py_image, (0, 0))

        # Display the user input at the bottom of the window
        if user_input:
            text_surface = font.render(user_input, True, (255, 255, 255))  # Render text in white
            window.blit(text_surface, (10, window_height - 50))  # Position text near the bottom

        # Update the window
        pygame.display.flip()
    
    
    imageacquistion.join()
    imageaddtovid.join()
    


    # clean_up
    cam.DeInit()
    pygame.quit()
    cam_list.Clear()
    system.ReleaseInstance()
    print("done")
    return result

if __name__=='__main__':
    if main():
        sys.exit(0)
    else:
        sys.exit(1)