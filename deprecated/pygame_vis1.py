import pygame #type: ignore
import os
import sys
import threading

# Function to check for terminal input
def input_listener():
    global running, user_input
    while running:
        # Get input from the terminal
        user_input = input("Enter something: ")
        if user_input == "exit":
            running = False

# Initialize Pygame
pygame.init()

# Get the display's dimensions
screen_info = pygame.display.Info()
screen_width = screen_info.current_w
screen_height = screen_info.current_h

# Set the window size to half of the screen width, and height slightly smaller than the full height
window_width = screen_width // 2
window_height = screen_height - 80  # Leave space for window controls

# Set the window position to the left side of the screen
os.environ['SDL_VIDEO_WINDOW_POS'] = "0,30"
window = pygame.display.set_mode((window_width, window_height))

# Set the window title
pygame.display.set_caption("Pygame Input Display")

# Set up font for rendering text
font = pygame.font.Font(None, 36)  # Default font, size 36

# Initial state
user_input = ""
running = True

# Start the input listener in a separate thread
input_thread = threading.Thread(target=input_listener)
input_thread.start()

# Main loop for Pygame window
while running:
    # Handle events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Fill the window with a color (optional)
    window.fill((0, 128, 255))  # Fill with a blue color

    # Display the user input at the bottom of the window
    if user_input:
        text_surface = font.render(user_input, True, (255, 255, 255))  # Render text in white
        window.blit(text_surface, (10, window_height - 50))  # Position text near the bottom

    # Update the window
    pygame.display.flip()

# Quit Pygame
pygame.quit()
sys.exit()