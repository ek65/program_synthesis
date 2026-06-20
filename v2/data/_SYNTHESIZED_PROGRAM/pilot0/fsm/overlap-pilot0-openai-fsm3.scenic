from scenic.simulators.unity.actions import *
from scenic.simulators.unity.behaviors import *
from scenic.simulators.unity.constraints import *
model scenic.simulators.unity.model
import trimesh
from scenic.core.regions import MeshVolumeRegion
import random
####HEADER ENDS####

# Constraint instantiations
A1_overlap = Overlap({'player': 'Coach', 'ball': 'ball', 'goal': 'goal', 'opponent': 'opponent', 'theta': {'avg': 33, 'std': 6}, 'dist': {'avg': 5, 'std': 1}})
A1_haspass_teammate_to_coach = MakePass({'player': 'teammate'})
A1_possession_coach = HasBallPossession({'player': 'Coach'})
A1_possession_teammate = HasBallPossession({'player': 'teammate'})
A1_path_coach_goal = HasPath({'obj1': 'Coach', 'obj2': 'goal', 'path_width': {'avg': 2, 'std': 0.5}})
A2_path_teammate_goal = HasPath({'obj1': 'teammate', 'obj2': 'goal', 'path_width': {'avg': 2, 'std': 0.5}})

# Target for Coach overlapping on side and receiving ball
def λ_target_overlap():
    return A1_overlap.dist(simulation(), ego=True)

# Precondition: teammate passes to Coach (Coach is about to get possession)
def λ_precondition_pass_from_teammate():
    return A1_haspass_teammate_to_coach.bool(simulation())

# Precondition: Coach has the ball
def λ_precondition_coach_possession():
    return A1_possession_coach.bool(simulation())

# Precondition: Teammate has the ball
def λ_precondition_teammate_possession():
    return A1_possession_teammate.bool(simulation())

# Termination function: the HasPath from Coach to goal exists (do not use as action termination!)
def λ_precondition_clear_path_shot():
    return A1_path_coach_goal.bool(simulation())

# Termination function: HasPath from Coach to goal does not exist (i.e. blocked)
def λ_precondition_blocked_path_shot():
    cond = ~A1_path_coach_goal
    return cond.bool(simulation())

# Precondition: HasPath from teammate to goal is clear
def λ_precondition_teammate_path_goal():
    return A2_path_teammate_goal.bool(simulation())

behavior CoachBehavior():
    do Idle() for 3 seconds
    do Speak("Move to overlap to the side, about 33 degrees, 5 meters from ball. Move up the field by 4 meters and call for ball from teammate.")
    do MoveTo(λ_target_overlap(), True)
    do Speak("Wait for teammate to pass you the ball before moving again.")
    do Idle() until λ_precondition_pass_from_teammate()
    do Speak("Get ready to receive the ball from teammate.")
    do StopAndReceiveBall()
    # Feedback change: don't wait for extra confirmation of possession after receiving ball.
    do Speak("You have the ball now. Pass it back to your teammate immediately.")
    do Pass("teammate")
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