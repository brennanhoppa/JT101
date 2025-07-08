from Utils.ManualMotorInput import move

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

