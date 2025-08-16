from Utils.CONSTANTS import CONSTANTS
import os

vertical = os.path.exists(r"C:\Users\weiss\Desktop\JT101\Utils\vertical.txt")


def move(x_pos, y_pos, x_direction, y_direction, command_queue, is_jf_mode, log_queue,x_invalid_flag, y_invalid_flag):       
    # Calculate new positions
    new_x = x_pos.value + x_direction
    new_y = y_pos.value + y_direction
    
    if is_jf_mode.value == 1: # jf mode, use limit switches
        x_valid = True
        if x_invalid_flag.value == 1 and x_direction < 0:
            x_valid = False
        elif x_invalid_flag.value == 2 and x_direction > 0:
            x_valid = False
        y_valid = True
        if y_invalid_flag.value == 1 and y_direction < 0:
            y_valid = False
        elif y_invalid_flag.value == 2 and y_direction > 0:
            y_valid = False
    
    # # ignore these for now in case limit switches mess up
    else: # larvae mode, use hard coded maxes 
        x_valid, y_valid = True, True
    #     x_valid = 0 <= new_x <= CONSTANTS['XmaxLarvae']
    #     y_valid = 0 <= new_y <= CONSTANTS['YmaxLarvae']
    # x_valid, y_valid = True, True

    # Update positions and send movement commands
    if x_valid and x_direction != 0 and not vertical:
        x_pos.value = new_x
        command_queue.put(f'{"R" if x_direction > 0 else "L"}{abs(x_direction)}\n')
    if y_valid and y_direction != 0:
        y_pos.value = new_y
        command_queue.put(f'{"U" if y_direction > 0 else "D"}{abs(y_direction)}\n')
    
    return x_pos, y_pos

def autoMove(x_pos,y_pos,goal,command_queue, is_jf_mode, log_queue, x_invalid_flag, y_invalid_flag):
    goal_x, goal_y = goal

    # Compute how much to move in each direction
    x_direction = goal_x - x_pos.value
    y_direction = goal_y - y_pos.value

    move(
        x_pos, 
        y_pos, 
        x_direction, 
        y_direction, 
        command_queue, 
        is_jf_mode, 
        log_queue,
        x_invalid_flag, 
        y_invalid_flag
    )

