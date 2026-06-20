from scenic.simulators.unity.actions import *
from scenic.simulators.unity.behaviors import *
from scenic.simulators.unity.constraints import *
model scenic.simulators.unity.model
import trimesh
from scenic.core.regions import MeshVolumeRegion
import random
####HEADER ENDS####

A1target_0 = Overlap({'player': 'Coach', 'ball': 'ball', 'goal': 'goal', 'opponent': 'opponent', 'theta': {'avg': 40, 'std': 5}, 'dist': {'avg': 5, 'std': 1}})
A2target_0 = HeightRelation({'obj': 'Coach', 'relation': 'above', 'ref': None, 'height_threshold': {'avg': 4, 'std': 0.5}})
A1haspath_pass = HasPath({'obj1': 'teammate', 'obj2': 'Coach', 'path_width': {'avg': 2, 'std': 0.2}})
A1hasball_Coach = HasBallPossession({'player': 'Coach'})
A1haspath_shot = HasPath({'obj1': 'Coach', 'obj2': 'goal', 'path_width': {'avg': 2, 'std': 0.2}})
A1haspath_pass_to_teammate = HasPath({'obj1': 'Coach', 'obj2': 'teammate', 'path_width': {'avg': 2, 'std': 0.2}})
A1hasball_teammate = HasBallPossession({'player': 'teammate'})

def λ_target0():
    cond = A1target_0 & A2target_0
    return cond.dist(simulation(), ego=True)

def λ_precondition_pass():
    return (A1haspath_pass.bool(simulation()) and A1hasball_teammate.bool(simulation()))

def λ_precondition_Coach_has_ball():
    return A1hasball_Coach.bool(simulation())

def λ_precondition_shot():
    return A1haspath_shot.bool(simulation()) and A1hasball_Coach.bool(simulation())

def λ_precondition_teammate_shot():
    return A1haspath_pass_to_teammate.bool(simulation()) and A1hasball_Coach.bool(simulation())

behavior CoachBehavior():
    do Idle() for 3 seconds
    do Speak("Wait until path is clear for teammate to pass and teammate has ball")
    do Idle() until λ_precondition_pass()
    do Speak("Call for teammate to pass the ball")
    # Request pass and prepare to move to overlap position
    do Pass('Coach')
    # Wait in position to receive the ball
    do StopAndReceiveBall()
    do Speak("Move to overlap position: 40 deg angle, 5m from ball, and move up the field by 4m")
    do MoveTo(λ_target0(), True)
    do Speak("Wait until you have received the ball from teammate")
    do Idle() until λ_precondition_Coach_has_ball()
    if λ_precondition_shot():
        do Speak("Path to goal is clear and you have the ball; shoot at goal")
        do Shoot('goal')
    elif λ_precondition_teammate_shot():
        do Speak("No clear shot to goal, but path to teammate is open; pass to teammate")
        do Pass('teammate')
    else:
        do Speak("No clear path to shoot or pass, hold possession")
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