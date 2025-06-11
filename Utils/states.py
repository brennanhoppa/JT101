from Utils.ButtonPresses import AviType
from datetime import datetime

running = True
recording = False
tracking = False
motors = False
boundary_making = False
shared_image = None
avi_recorder = None
verbose = False
show_boundary = False
chosenAviType = AviType.H264
start_time = datetime.now()
avi_filename = ""