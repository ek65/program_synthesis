from scenic.simulators.unity.actions import *
from scenic.simulators.unity.behaviors import *
from scenic.simulators.unity.constraints import *
model scenic.simulators.unity.model
import trimesh
from scenic.core.regions import MeshVolumeRegion
import random
####HEADER ENDS####

# **Summary of Feedback:**  
# 1. When moving to create the passing lane, only move to the side (left or right) by 2-4 meters—ignore constraints for "above teammate," "path width," and "6m from opponent."
# 2. The coach does not need to fully "stop and receive" the ball, but can receive while moving.
# 3. For the transition after receiving possession, only check if the defender starts moving toward the coach (not pressure AND teammate running).
#
# **What Was Changed:**  
# - Replaced the MoveTo target constraint to simply move left or right (x-axis) by 2-4 meters from the starting location, rather than the original conjunction of constraints.
# - Removed the explicit StopAndReceiveBall() step; now the coach receives the pass without stopping movement.
# - Simplified the precondition before passing back: only check if the opponent is moving toward the coach, not the previous conjunction (pressure + teammate running toward goal).
# - Updated or added supporting lambda functions accordingly.
#
# ---
#
# # The code with implemented feedback:
#
# # Existing and unchanged APIs/variables for reference:
# # A1target_0, A2target_0, A3target_0, P1precondition_0, etc.
# # Only λ_target0, λ_precondition_2, and the CoachBehavior are changed.

import random

def λ_moveSideTarget():
    # Move left or right from the starting position by 2-4 meters on the x-axis,
    # keep y the same as coach current position (or minimally forward).
    ego_pos = ego.position  # Scenic context provides this global variable
    # Choose randomly to left or right (x-axis)
    direction = random.choice([-1, 1])
    dist = random.uniform(2, 4)
    target_x = ego_pos.x + direction * dist
    # Maintain the same y as the initial y position to "move to the side"
    target_y = ego_pos.y
    # Output as a Scenic Vector
    return Vector(target_x, target_y, 0)

def λ_opponentMovesToCoach():
    # True if the opponent is moving toward coach's position
    return MovingTowards({'obj': 'opponent', 'ref': 'Coach'}).bool(simulation())

def λ_precondition_0():
    return P1precondition_0.bool(simulation())

def λ_precondition_1():
    return P2precondition_0.bool(simulation())

def λ_precondition_3():
    return P5precondition_0.bool(simulation())

behavior CoachBehavior():
    do Idle() for 3 seconds

    # Change: Only move sideways (left/right) by 2-4 meters, ignore original constraints.
    do Speak("Move 2-4 meters left or right from starting point to open passing lane. Call pass.")
    # Use MoveToBehavior (which accepts a Vector) rather than MoveTo which expects a grid or string.
    do MoveToBehavior(λ_moveSideTarget(), distance=0.5)

    do Speak("Wait until teammate passes toward me.")
    do Idle() until λ_precondition_0()

    # Change: Remove explicit stop, receive pass while moving ("on the move")
    do Speak("Receive the pass on the move.")
    # No need to stop, just wait for ball possession.
    # If still want to model action, could "do Idle()" for a very short time or skip.
    # Omit StopAndReceiveBall()

    do Speak("Wait until I have ball possession.")
    do Idle() until λ_precondition_1()

    # Change: Now only check if the opponent is moving toward the coach (not pressure + teammate running)
    do Speak("Wait until defender starts moving toward me.")
    do Idle() until λ_opponentMovesToCoach()

    do Speak("Pass back to teammate into space.")
    do Pass(teammate)

    do Speak("Wait until teammate controls the ball.")
    do Idle() until λ_precondition_3()

    do Idle()

####Environment Behavior START####
# Parameters for variance
coach_start_dist = Range(5, 6)  # initial distance from teammate
opponent_dist = Range(4, 6)         # distance behind coach

# Behaviors
behavior TeammatePass():
    # Double checking gotBall to ensure the pass is triggered correctly
    # since MoveToBallAndGetPossession() might get interrupted
    gotBall = False
    try:
        do Idle() for 1.0 seconds  # Give coach time to start 
        do MoveToBallAndGetPossession()
        print("got ball")
        gotBall = True
        do Idle()
    interrupt when ego.triggerPass and self.gameObject.ballPossession and gotBall:
        ego.triggerPass = False
        print("trigger pass")
        do Idle() for 1.0 seconds
        do Pass(ego.xMark)
        # Idle after the pass happens
        do Idle() for 1.0 seconds
        
        # move forward to opposite side of field
        # Determine which side coach and opponent are on
        coach_x = ego.position.x
        opponent_x = opponent.position.x
        
        # Calculate target position on opposite side
        # X-axis ranges from -10 to +10, with 0 at center
        # If coach and opponent are on positive side, go to negative side
        # If coach and opponent are on negative side, go to positive side
        if coach_x > 0 and opponent_x > 0:
            # Both on positive side (right), go to negative side (left)
            target_x = -6.0
        elif coach_x < 0 and opponent_x < 0:
            # Both on negative side (left), go to positive side (right)
            target_x = 6.0
        else:
            # Mixed positions, go to the side with more space
            # If coach is on left (negative), go right (positive)
            # If coach is on right (positive), go left (negative)
            target_x = 6.0 if coach_x < 0 else -6.0
        
        # Move forward to the target position (toward goal, so positive Y)
        target_position = Vector(target_x, ego.position.y, 0)
        do MoveToBehavior(target_position, distance=0.5)
        do Idle() for 1.0 seconds

        do Idle() until self.gameObject.ballPossession
        do Shoot(goal)
        do Idle() for 1.0 seconds
        do Shoot(goal)

    do Idle()

behavior OpponentFollowCoach():

    do Idle() until ego.gameObject.ballPossession
    
    # Set opponent speed
    do SetPlayerSpeed(4.0)
    
    while True:
        # Follow coach only until coach receives the ball
        do MoveToBehavior(ego.position, distance=4)
            
    





# Place teammate (AI) at origin
teammate = new Player at (0, 0, 0), with name "teammate", with team "blue", with behavior TeammatePass()

# Place coach (human) in front of teammate
ego = new Coach ahead of teammate by coach_start_dist, 
    with name "Coach", 
    with team "blue", 
    with behavior CoachBehavior(),
    with xMark Vector(0, 0, 0),  # Set initial xMark position
    with triggerPass False  # Initialize triggerPass to False

# Place opponent ahead of coach (closer to goal than coach)
opponent = new Player ahead of ego by opponent_dist, facing toward ego, with name "opponent", with team "red", with behavior OpponentFollowCoach()

# Ball at teammate's feet
ball = new Ball ahead of teammate by 0.5

goal = new Goal at (0, 17, 0)

terminate when (ego.gameObject.stopButton)