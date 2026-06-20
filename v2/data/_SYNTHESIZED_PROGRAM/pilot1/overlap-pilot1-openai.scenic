from scenic.simulators.unity.actions import *
from scenic.simulators.unity.behaviors import *
from scenic.simulators.unity.constraints import *
model scenic.simulators.unity.model
import trimesh
from scenic.core.regions import MeshVolumeRegion
import random
####HEADER ENDS####

A1target_overlap_right = Overlap({
    'player': 'Coach',
    'ball': 'ball',
    'goal': 'goal',
    'opponent': 'opponent',
    'theta': {'avg': 38, 'std': 2},
    'dist': {'avg': 5, 'std': 0.5}
})
A1target_overlap_left = Overlap({
    'player': 'Coach',
    'ball': 'ball',
    'goal': 'goal',
    'opponent': 'opponent',
    'theta': {'avg': 38, 'std': 2},
    'dist': {'avg': 4, 'std': 0.5}
})

A1precondition_receive = MakePass({'player': 'teammate'})
A1precondition_possession = HasBallPossession({'player': 'Coach'})
A1precondition_opponent_close = DistanceTo({
    'from': 'opponent',
    'to': 'Coach',
    'min': None,
    'max': {'avg': 3, 'std': 0.2},
    'operator': 'less_than'
})
A1precondition_pass_clear = HasPath({
    'obj1': 'Coach',
    'obj2': 'teammate',
    'path_width': {'avg': 2, 'std': 0.3}
})
A1precondition_shot_clear = HasPath({
    'obj1': 'Coach',
    'obj2': 'goal',
    'path_width': {'avg': 2, 'std': 0.3}
})

def lambda_target_overlap_right():
    return A1target_overlap_right.dist(simulation(), ego=True)

def lambda_target_overlap_left():
    return A1target_overlap_left.dist(simulation(), ego=True)

def lambda_precondition_receive():
    return A1precondition_receive.bool(simulation())

def lambda_precondition_possession():
    return A1precondition_possession.bool(simulation())

def lambda_precondition_opponent_close():
    return A1precondition_opponent_close.bool(simulation())

def lambda_precondition_pass_clear():
    return A1precondition_pass_clear.bool(simulation())

def lambda_precondition_shot_clear():
    return A1precondition_shot_clear.bool(simulation())

behavior CoachBehavior():
    do Idle() for 3 seconds
    do Speak("Wait for a pass, teammate should have possession before overlap.")
    do Idle() until lambda_precondition_receive()
    do Speak("Create overlap on the right or left with angle 38 deg and distance about 5 or 4 meters so teammate can pass.")
    if lambda_target_overlap_right().max() > lambda_target_overlap_left().max():
        do MoveTo(lambda_target_overlap_right(), True)
    else:
        do MoveTo(lambda_target_overlap_left(), True)
    do Speak("Wait until you receive the pass from teammate, look for MakePass by teammate.")
    do Idle() until lambda_precondition_possession()
    do Speak("You now have possession. Decide to shoot or pass based on opponent distance.")
    if lambda_precondition_opponent_close(): 
        do Speak("Opponent is very close, look for a clear passing path back to teammate, path width 2 meters.")
        do Idle() until lambda_precondition_pass_clear()
        do Speak("Passing the ball back to teammate.")
        do Pass('teammate')
        do Idle()
    else:
        do Speak("Opponent is not too close, check for a clear shot to goal, path width 2 meters.")
        do Idle() until lambda_precondition_shot_clear()
        do Speak("Take the shot towards the goal.")
        do Shoot('goal')
        do Idle()

####Environment Behavior START####

opponent_y_distance = Range(3, 5)
opponent_x_distance = Range(-2, 2)
ego_x_distance = Range(-2, 2)
ego_y_distance = Range(-1, -2)

# Ensure teammate and opponent are on the same side
#require (opponent_x_distance < 0 and ego_x_distance < 0) or (opponent_x_distance >= 0 and ego_x_distance >= 0)

behavior Follow(obj):
    while ego.position.y > 1:
        do MoveToBehavior(obj, distance = 2, status = f"Follow {obj.name}")

behavior TeammateBehavior():
    # Double checking gotBall to ensure the pass is triggered correctly
    # since MoveToBallAndGetPossession() might get interrupted
    do SetPlayerSpeed(6.0)
    gotBall = False
    try:
        do Idle() for 1 seconds
        do MoveToBallAndGetPossession()
        gotBall = True
        do Idle()
    interrupt when ego.triggerPass and self.gameObject.ballPossession and gotBall:
        ego.triggerPass = False
        do Idle() for 1 seconds
        do Pass(ego.xMark)
        
        # After passing to coach, go to opposite side at same height as ego
        do Idle() for 1 seconds
        
        # Calculate target position: height between coach and goal, opposite X side
        ego_x = ego.position.x
        ego_y = ego.position.y
        goal_y = goal.position.y
        
        # Go to opposite side (negative if ego is positive, positive if ego is negative)
        target_x = -ego_x if ego_x > 0 else abs(ego_x)
        target_y = (ego_y + goal_y) / 2  # Height between coach and goal


        
        target_position = Vector(target_x, target_y, 0)
        do MoveToBehavior(target_position)
        
        # Wait to receive ball back from coach
        do Idle() until self.gameObject.ballPossession
        
        # If received ball back, score a goal
        if self.gameObject.ballPossession:
            do Shoot(goal)
    
    do Idle()
    
### Modified opponent behavior: Keep position until ego receives ball, then move to middle of line with variation
behavior DefenderBehavior():
    do Idle() for 1 seconds
    do Idle() until ego.position.y > 1
    
    # Keep position until ego receives the ball
    while not ego.gameObject.ballPossession:
        do Idle() for 0.1 seconds
    
    # Once ego receives ball, move to middle of line between ego and goal
    if ego.gameObject.ballPossession:
        # Calculate middle point between ego and goal
        goal_x = goal.position.x
        goal_y = goal.position.y
        ego_x = ego.position.x
        ego_y = ego.position.y
        
        middle_x = (ego_x + goal_x) / 2
        middle_y = (ego_y + goal_y) / 2
        
        # Add some variation to create opportunities or blocking
        variation = Range(-1, 1)  # Random variation in both directions


        target_x = middle_x + variation
        target_y = middle_y + variation
        
        # Move to the target position
        target_position = Vector(target_x, target_y, 0)
        do MoveToBehavior(target_position)
        
        # Face the ego (coach) once in position
        do LookAt(ego)


    

teammate = new Player at (0, 0, 0),
      with behavior TeammateBehavior(), with name "teammate", with team "blue"

ball = new Ball ahead of teammate by 1

ego = new Coach at (0, ego_y_distance, 0),
    with name "Coach",
    with team "blue",
    with behavior CoachBehavior(),
    with xMark Vector(0, 0, 0),  # Set initial xMark position
    with triggerPass False  # Initialize triggerPass to False

opponent = new Player at (0, Range(4, 6), 0), with name "opponent",
            with behavior DefenderBehavior(), with team "red"

goal = new Goal at (0, 17, 0)

line = new Line at (0, 10, 0)

terminate when (ego.gameObject.stopButton)