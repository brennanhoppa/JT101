CONSTANTS = {
    "LeadScrewMm": 8,
    "JellyStepSizeManual": 75,  # was 95, testing
    "LarvaeStepSizeManual": 35,
    "JFStepPerRev": 2000, # set on motor controllers
    "LStepPerRev": 12800, # set on motor controllers
    "JFmaxes": (213300, 212550), # FIX THIS MAX
    "JFPixelsPerMm": 39.5, # for the jellyfish zoom on microscope, measured by calibration function
    "LPixelsPerMm": 437, # 
    "LarvaeHome": (2700,80625), # this is in JF step sizes
    "XmaxLarvae": 1331155,
    "YmaxLarvae": 418670,
}

# Compute Lmaxes from JFmaxes
step_ratio = CONSTANTS["LStepPerRev"] / CONSTANTS["JFStepPerRev"]
CONSTANTS["Lmaxes"] = tuple(int(x * step_ratio) for x in CONSTANTS["JFmaxes"])
CONSTANTS["JFStepsPerMm"] = CONSTANTS["JFStepPerRev"] / CONSTANTS["LeadScrewMm"]  # default b/c 2000 steps per rev, 8mm lead on the screw, also note step_angle = 0.18 deg
CONSTANTS["LStepsPerMm"] = CONSTANTS["LStepPerRev"] / CONSTANTS["LeadScrewMm"]  # default b/c 12800 steps per rev, 8mm lead on the screw, also note step_angle = 0.028125 deg

class AviType:
    UNCOMPRESSED = 0
    MJPG = 1
    H264 = 2