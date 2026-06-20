from scenic.simulators.unity.actions import *
from scenic.simulators.unity.behaviors import *
from scenic.simulators.unity.constraints import *
model scenic.simulators.unity.model
import trimesh
from scenic.core.regions import MeshVolumeRegion
import random
####HEADER ENDS####

A1target_overlap = Overlap({
    'player': 'Coach',
    'ball': 'ball',
    'goal': 'goal',
    'opponent': 'opponent',
    'theta': {'avg': 40, 'std': 5},         # Updated to 40 degree angle
    'dist': {'avg': 5, 'std': 0.5}          # Updated to 5 meters from ball
})
A1target_upfield = HeightRelation({
    'obj': 'Coach',
    'relation': 'above',
    'ref': None,                            # Relative to starting position (move up 4m)
    'height_threshold': {'avg': 4, 'std': 0.5}
})

A1target_receive1 = DistanceTo({
    'from': 'Coach',
    'to': 'ball',
    'min': None,
    'max': {'avg': 1.5, 'std': 0.3},
    'operator': 'less_than'
})
A1target_receive2 = DistanceTo({
    'from': 'Coach',
    'to': 'ball',
    'min': None,
    'max': {'avg': 1.5, 'std': 0.3},
    'operator': 'less_than'
})
A1target_receive3 = DistanceTo({
    'from': 'Coach',
    'to': 'ball',
    'min': None,
    'max': {'avg': 1.5, 'std': 0.3},
    'operator': 'less_than'
})
A1HasBall_Coach = HasBallPossession({'player': 'Coach'})
A2HasBall_teammate = HasBallPossession({'player': 'teammate'})
A1Pass_Coach = MakePass({'player': 'Coach'})
A2Pass_teammate = MakePass({'player': 'teammate'})
A1Path_Coach_goal = HasPath({'obj1': 'Coach', 'obj2': 'goal', 'path_width': {'avg': 2, 'std': 0.3}})
A2Path_teammate_goal = HasPath({'obj1': 'teammate', 'obj2': 'goal', 'path_width': {'avg': 2, 'std': 0.3}})

def λ_target_overlap():
    # Overlap at 40 degree angle, 5 meters from ball
    return A1target_overlap.dist(simulation(), ego=True)

def λ_target_upfield():
    # Move up the field by ~4 meters
    return A1target_upfield.dist(simulation(), ego=True)

def λ_target_receive1():
    return A1target_receive1.dist(simulation(), ego=True)

def λ_target_receive2():
    return A1target_receive2.dist(simulation(), ego=True)

def λ_target_receive3():
    return A1target_receive3.dist(simulation(), ego=True)

def λ_termination_overlap():
    # Terminate when Coach is close to the overlap destination but not based on overlap achieved
    return A1target_receive1.bool(simulation())

def λ_termination_receive_pass():
    # Terminate when Coach is close to the ball on pass-in but not dependent on possession
    return A1target_receive2.bool(simulation())

def λ_termination_receive_pass2():
    # Terminate when Coach is close to the ball again after pass
    return A1target_receive3.bool(simulation())

def λ_precondition_has_possession():
    # Precondition: Coach has the ball possession
    return A1HasBall_Coach.bool(simulation())

def λ_precondition_teammate_has_ball():
    # Precondition: Teammate has the ball
    return A2HasBall_teammate.bool(simulation())

def λ_precondition_makepass_teammate():
    # Precondition: Teammate made a pass
    return A2Pass_teammate.bool(simulation())

def λ_precondition_makepass_Coach():
    # Precondition: Coach made a pass
    return A1Pass_Coach.bool(simulation())

def λ_precondition_HasPath_Coach_goal():
    # Precondition: Coach has path to goal (for shooting)
    return A1Path_Coach_goal.bool(simulation())

def λ_precondition_HasPath_teammate_goal():
    # Precondition: teammate has path to goal (for shooting)
    return A2Path_teammate_goal.bool(simulation())

behavior CoachBehavior():
    do Idle() for 3 seconds
    do Speak("Move to overlap position: 40-degree angle, 5 meters from ball, and move 4 meters up the field.")
    do MoveTo(λ_target_overlap() * λ_target_upfield(), True)  # Combined as valid numpy op
    do Speak("Wait until close enough to receive the pass (within 1.5 meters).")
    do Idle() until λ_target_receive1()
    do Speak("Stop and receive the ball from teammate's pass.")
    do StopAndReceiveBall()
    do Speak("Now you have possession, so immediately pass back to your teammate.")
    do Idle() until λ_precondition_has_possession()
    do Pass(teammate)
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