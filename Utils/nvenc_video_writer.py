import os
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

        # Set the environment so that GPU 1 appears as "cuda:0" to FFmpeg

        command = [
            'ffmpeg',
            # '-loglevel', 'debug',
            '-y',
            '-f', 'rawvideo',
            '-vcodec', 'rawvideo',
            '-pix_fmt', 'bgr24',
            '-s', f'{width}x{height}',
            '-r', str(fps),
            '-i', '-',
            '-c:v', 'h264_nvenc',
            '-gpu', '0', # uses the 3090   
            '-preset', 'llhp',
            '-b:v', self.bitrate,
            '-maxrate', self.bitrate,
            '-bufsize', str(int(int(self.bitrate[:-1]) * 2)) + 'M',
            '-pix_fmt', 'yuv420p',
            self.filename
        ]

        if self.log:
            self.log(f"Starting NVENC FFmpeg recording on GPU 1 (3090).", None)

        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            # stdout=subprocess.DEVNULL,
            # stderr=subprocess.PIPE,
        )

        # time.sleep(0.3)

        # if self.process.poll() is not None:
        #     error_msg = self.process.stderr.read().decode('utf-8', errors='replace')
        #     if self.log:
        #         self.log(f"[FFMPEG] Failed to start: {error_msg.strip()}", None)
        #     raise RuntimeError(f"[FFMPEG ERROR] NVENC failed to start.\n{error_msg}")


    def write(self, frame):
        """Write a single frame (numpy array in BGR)"""
        self.process.stdin.write(frame.tobytes())

    def release(self):
        """Close FFmpeg cleanly."""
        self.process.stdin.close()
        self.process.wait()