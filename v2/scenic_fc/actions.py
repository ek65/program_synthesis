from api_utils import ActionAPI
from scenic_fc.other import Target, PassTarget
from nlp_utils import *
import json

# MARK: MoveTo
class MoveTo(ActionAPI):
    def __init__(self, action):
        super().__init__(action)
        self.target = Target(action.info, action)

    @classmethod
    def doc(cls) -> str:
        return """
        This MoveTo API defines an action to move to a particular destination.
        Rather than taking a specific location to move to, it takes a constraint API or 
        a conjunction or disjunction of constraint APIs that define the destination.
        The second input to move to specifies if the agent who has the ball should pass it to the destination of MoveTo action or not.
        This should be set to True if the coach agent calls for a pass from the teammate with the ball.
        Input Args:
            - param: this can be either of two object types:
                1. (Constraint API or Conjunction/Disjunction of Constraint APIs).dist(): This is a constraint API with its .dist() which returns a 2d numpy array.
                2. str: the instantiated Unity object of the player or object
            - doPass: this is a boolean value that will inform the agent who has the ball, to pass to the destination of this MoveTo() action.

        example usage:
        # Type 1: (Constraint API or Conjunction/Disjunction of Constraint APIs).dist()
        '
        A1target_5 = DistanceTo({'from': 'Coach', 'to': 'goal', 'min': None, 'max': {'avg': 5.025909493366715, 'std': 0.015410097852564864}, 'operator': 'less_than'})
        A2target_5 = CloseTo({'obj': 'Coach', 'ref': 'ball', 'max': {'avg': 11.941602839093648, 'std': 0.01539784416917822}})
        def λ_target5():
            cond = A1target_5 and A2target_5
            return cond.dist(simulation(), ego = True)
        do MoveTo(λ_target5(), True)
        '

        # Type 2: str
        'do MoveTo('teammate', False)'
        """

    @classmethod
    def from_dict(cls, data, action, api) -> 'Pass':
        out = cls(action)
        out.target = Target.from_dict(data.get('target', {}), action, api)
        return out

    def to_dict(self, expanded: bool = False):
        return {
            'target': self.target.to_dict()
        }
    

# MARK: Pass
class Pass(ActionAPI):
    def __init__(self, action):
        super().__init__(action)
        self.target = PassTarget(action.info, action)
    
    @classmethod
    def doc(cls) -> str:
        return """
        This Pass() API passes a ball to another player.
        Input Args:
            - target (str): The name of the player to pass to. 
        example usage: 'do Pass(teammate)'
        """

    @classmethod
    def from_dict(cls, data, action, api) -> 'Pass':
        out = cls(action)
        out.target = PassTarget.from_dict(data.get('target', {}), action, api)
        return out

    def to_dict(self, expanded: bool = False):
        return {
            'target': self.target.to_dict(expanded)
        }
    

# MARK: Shoot
class Shoot(ActionAPI):
    """
    This Shoot() API executes shooting a ball to the goal.
    """

    def __init__(self, action):
        super().__init__(action)

    @classmethod
    def doc(cls) -> str:
        return """
        This Shoot API executes shooting a ball to the goal.
        Input Args:
            - goal (str): the name of the goal to shoot to.
        example usage: 
        'do Shoot(goal)'
        """

    def to_dict(self, expanded: bool = False):
        return {} # GetBall does not take any input
    
# MARK: Idle
class Idle(ActionAPI):
    """
    This Idle() API defines an action for a player to stop and wait. 
    'do Idle() until precondition' is used to define a precondition for a player to wait until a certain condition is met, such as receiving the ball from another player or waiting for a specific event to occur.
    """
    def __init__(self, action):
        super().__init__(action)

    @classmethod
    def doc(cls) -> str:
        return "This Idle() API defines an action for a player to stop and wait. It has no input argument. \
                'do Idle() until precondition' is used to define a precondition for a player to wait \
                until a certain condition is met, such as receiving the ball from another player or \
                waiting for a specific event to occur."

    def to_dict(self, expanded: bool = False):
        return {

        }

# MARK: MoveToBallAndGetPossession
class MoveToBallAndGetPossession(ActionAPI):
    """
    This MoveToBallAndGetPossession() API defines an action to proactively move to the ball and get possession of the ball. 
    """

    def __init__(self, action):
        super().__init__(action)

    @classmethod
    def doc(self) -> str:
        return "This MoveToBallAndGetPossession() API defines an action to proactively move to the ball and get possession of the ball. \
                It has no input argument. \
                example usage: 'do MoveToBallAndGetPossession()'" 

    def to_dict(self, expanded: bool = False):
        return {} # GetBallPossession does not take any input
    

# MARK: StopAndReceiveBall
class StopAndReceiveBall(ActionAPI):
    """
    This StopAndReceiveBall() API defines an action to stop and wait until it receives the ball from a teammate.
    """
    def __init__(self, action):
        super().__init__(action)

    @classmethod
    def doc(cls) -> str:
        return "This StopAndReceiveBall() API defines an action to stop and wait until it receives the ball from a teammate. \
                It has no input argument. \
                example usage: 'do StopAndReceiveBall()'"
    
    def to_dict(self, expanded: bool = False):
        return {} # ReceiveBall does not take any input
    
    
actionAPI = {
    'MoveTo': MoveTo,
    'Pass': Pass,
    'Idle': Idle,
    'MoveToBallAndGetPossession': MoveToBallAndGetPossession,
    'Shoot': Shoot,
    'StopAndReceiveBall': StopAndReceiveBall
}