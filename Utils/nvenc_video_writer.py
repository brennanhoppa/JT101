import subprocess
import time

class NvencVideoWriter:
    def __init__(self, filename, width, height, fps=30, bitrate="10M", log=None):
        self.filename = filename
        self.width = width
        self.height = height
        self.fps = fps
        self.bitrate = bitrate
        self.log = log

        command = [
            'ffmpeg',
            '-y',
            '-f', 'rawvideo',
            '-vcodec', 'rawvideo',
            '-pix_fmt', 'bgr24',
            '-s', f'{width}x{height}',
            '-r', str(fps),
            '-i', '-',
            '-gpu', '1', 
            '-c:v', 'h264_nvenc',
            '-preset', 'llhp',              
            '-b:v', self.bitrate,
            '-maxrate', self.bitrate,
            '-bufsize', str(int(int(self.bitrate[:-1]) * 2)) + 'M',
            '-pix_fmt', 'yuv420p',
            self.filename
        ]

        if self.log:
            self.log(f"Starting NVENC FFmpeg recording.", None)

        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            # # Code to help with error with the code below, but doesn't work correctly 100% of the time
            # stdout=subprocess.DEVNULL,  # discard normal output
            # stderr=subprocess.PIPE     # capture errors
        )
        # # Code to attempt to help with command error process, but doesn't work effeciently while getting output.
        # time.sleep(0.2)
        # if self.process.poll() is not None:
        #     error_msg = self.process.stderr.read().decode('utf-8', errors='replace')
        #     if self.log:
        #         self.log(f"FFmpeg failed to start: {error_msg}. Restart program to fix.", None)
        #     raise RuntimeError(f"FFmpeg NVENC failed to start: {error_msg}. Restart VS Code or program to fix.")

    def write(self, frame):
        """Write a single frame (numpy array in BGR)"""
        self.process.stdin.write(frame.tobytes())

    def release(self):
        """Close FFmpeg cleanly."""
        self.process.stdin.close()
        self.process.wait()