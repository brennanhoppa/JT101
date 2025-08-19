import os

CONSTANTS = {
    "LeadScrewMm": 8,
    "JellyStepSizeManual": 75,  # was 95, testing
    "LarvaeStepSizeManual": 35,
    "JFStepPerRev": 2000, # set on motor controllers
    "JFmaxes": (213300, 212550), 
    # for the jellyfish zoom on microscope, measured by calibration function. 
    # Default: 39.5 pixels/mm
    # Change value below if needed, keep default value stored above
    "JFPixelsPerMm": 39.5,
    # for the larvae zoom on microscope, measured by calibration function.
    # Default: 437 pixels/mm
    # Change value below if needed, keep default value stored above
    "LPixelsPerMm": 437, 
    "LarvaeHome": (4125,83925), # this is in JF step sizes
    "XmaxLarvae": 1331155,
    "YmaxLarvae": 418670,
}
vertical = os.path.exists(r"C:\Users\weiss\Desktop\JT101\Utils\vertical.txt")
if vertical:
    CONSTANTS["LStepPerRev"] = 6400 # baseline for vertical is 6400 microsteps. Can adjust here if using different value.
else: 
    CONSTANTS["LStepPerRev"] = 12800 # baseline for XY is 12800 microsteps. Can adjust here if using different value. 

# Compute Lmaxes from JFmaxes
step_ratio = CONSTANTS["LStepPerRev"] / CONSTANTS["JFStepPerRev"]
CONSTANTS["Lmaxes"] = tuple(int(x * step_ratio) for x in CONSTANTS["JFmaxes"])
CONSTANTS["JFStepsPerMm"] = CONSTANTS["JFStepPerRev"] / CONSTANTS["LeadScrewMm"]  # default b/c 2000 steps per rev, 8mm lead on the screw, also note step_angle = 0.18 deg
CONSTANTS["LStepsPerMm"] = CONSTANTS["LStepPerRev"] / CONSTANTS["LeadScrewMm"]  # default b/c 12800 steps per rev, 8mm lead on the screw, also note step_angle = 0.028125 deg

class AviType:
    UNCOMPRESSED = 0
    MJPG = 1
    H264 = 2