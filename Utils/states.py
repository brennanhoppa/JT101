from Utils.ButtonPresses import AviType
from datetime import datetime

running = True
boundary_making = False
shared_image = None
avi_recorder = None
show_boundary = False
chosenAviType = AviType.H264
# chosenAviType = AviType.MJPG
start_time = datetime.now()
avi_filename = ""