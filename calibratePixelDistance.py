import cv2
import math

# Global variables
points = []

def select_points(event, x, y, flags, param):
    """
    Mouse callback function to select points on the image.
    """
    global points
    if event == cv2.EVENT_LBUTTONDOWN:
        points.append((x, y))
        cv2.circle(frame_copy, (x, y), 5, (0, 0, 255), -1)  # Draw a red dot
        cv2.imshow("Select Points", frame_copy)
        
        # If two points are selected, calculate and display the distance
        if len(points) == 2:
            x1, y1 = points[0]
            x2, y2 = points[1]
            distance = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            print(f"Pixel Distance: {distance:.2f} pixels")
            cv2.line(frame_copy, points[0], points[1], (255, 0, 0), 2)  # Draw a blue line
            cv2.imshow("Select Points", frame_copy)

def main():
    global frame_copy
    
    # Hardcoded video path with proper formatting
    video_path = r"C:\Users\JellyTracker\Desktop\JellyFishTrackingPC-main\saved_tracking_videos\JellyTracking_20241202_235038.avi-0000.avi"
    
    try:
        # Open the video file
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            print(f"Error: Could not open video file at {video_path}")
            print("Please check if the file exists and the path is correct.")
            return
        
        # Read the first frame
        ret, frame = cap.read()
        if not ret:
            print("Error: Could not read the first frame.")
            return
        
        # Make a copy of the frame to display points and lines
        frame_copy = frame.copy()
        
        # Display the frame
        cv2.imshow("Select Points", frame_copy)
        cv2.setMouseCallback("Select Points", select_points)
        
        # Wait for user to press 'q' to quit
        print("Click two points on the frame. Press 'q' to quit.")
        while True:
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        cap.release()
        cv2.destroyAllWindows()
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        print("Please check if the video file exists and the path is correct.")

if __name__ == "__main__":
    main()