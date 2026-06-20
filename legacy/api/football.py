import json
from chat import *
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches

from object import Object
from vector import Vector
from constraint import Constraint
from action import Action
from api.objects.player import Player

FIELD_WIDTH, FIELD_HEIGHT = 20, 34

NUM_ZONES_X, NUM_ZONES_Y = 4, 5
ZONE_WIDTH = FIELD_WIDTH / NUM_ZONES_X
ZONE_HEIGHT = FIELD_HEIGHT / NUM_ZONES_Y

class Coach(Player):
    def __init__(self, id: str, type: str = 'coach', team: str = 'None'):
        super().__init__(id, type, team)
        self.footPreference = 'right'
        self.ballPossession = False
        self._ballPossession = []

    @classmethod
    def from_dict(cls, data: dict):
        team = "blue"
        obj = cls(id=data['id'], team=team)
        obj._ballPossession = [i for i in data['ballPossession']]
        obj._position = [Vector.from_dict(i) for i in data['position']]
        obj._velocity = [Vector.from_dict(i) for i in data['velocity']]
        # Gets starting position
        obj.position = obj._position[0]
        obj.type = "coach"
        return obj
    
class Teammate(Player):
    def __init__(self, id: str, type: str = 'teammate', team: str = 'None'):
        super().__init__(id, type, team)
        self.footPreference = 'right'
        self.ballPossession = False
        self._ballPossession = []

    @classmethod
    def from_dict(cls, data: dict):
        team = "blue"
        obj = cls(id=data['id'], team=team)
        obj._ballPossession = [i for i in data['ballPossession']]
        obj._position = [Vector.from_dict(i) for i in data['position']]
        obj._velocity = [Vector.from_dict(i) for i in data['velocity']]
        # Gets starting position
        obj.position = obj._position[0]
        obj.type = "teammate"
        return obj
    
class Opponent(Player):
    def __init__(self, id: str, type: str = 'opponent', team: str = 'None'):
        super().__init__(id, type, team)
        self.footPreference = 'right'
        self.ballPossession = False
        self._ballPossession = []

    @classmethod
    def from_dict(cls, data: dict):
        team = "red"
        obj = cls(id=data['id'], team=team)
        obj._ballPossession = [i for i in data['ballPossession']]
        obj._position = [Vector.from_dict(i) for i in data['position']]
        obj._velocity = [Vector.from_dict(i) for i in data['velocity']]
        # Gets starting position
        obj.position = obj._position[0]
        obj.type = "opponent"
        return obj

# Target position for coach to move to
class Target(Object):
    def __init__(self, id: str, type: str = 'target'):
        super().__init__(id, type)

def plotField(scene, zones=False, axis=False):
    fig, ax = plt.subplots()

    # Field bounds
    ax.set_xlim(-FIELD_WIDTH / 2, FIELD_WIDTH / 2)
    ax.set_ylim(-FIELD_HEIGHT / 2, FIELD_HEIGHT / 2)

    ax.set_aspect('equal', 'box')

    # Field decoration

    center_circle = patches.Circle((0, 0), radius=3.75, edgecolor='lightgray', facecolor='none', linewidth=1)
    ax.add_patch(center_circle)

    GOAL_WIDTH = 9.5
    GOAL_HEIGHT = 5.25

    left_goal_area = patches.Rectangle((-GOAL_WIDTH / 2, -FIELD_HEIGHT / 2), GOAL_WIDTH, GOAL_HEIGHT, edgecolor='lightgray', facecolor='none', linewidth=1)
    right_goal_area = patches.Rectangle((-GOAL_WIDTH / 2, FIELD_HEIGHT / 2 - GOAL_HEIGHT), GOAL_WIDTH, GOAL_HEIGHT, edgecolor='lightgray', facecolor='none', linewidth=1)
    ax.add_patch(left_goal_area)
    ax.add_patch(right_goal_area)

    ax.axhline(0, color='lightgray', linestyle='-', linewidth=1)

    # Field zones

    if zones:
        zone_x_labels = ['A', 'B', 'C', 'D', 'E']
        zone_y_labels = ['1', '2', '3', '4', '5', '6', '7', '8']

        # Zone boxes

        for i in range(1, NUM_ZONES_X):
            ax.axvline(-FIELD_WIDTH / 2 + i * ZONE_WIDTH, color='lightgray', linestyle='--')
        for i in range(1, NUM_ZONES_Y):
            ax.axhline(-FIELD_HEIGHT / 2 + i * ZONE_HEIGHT, color='lightgray', linestyle='--')

        # Zone labels

        for i in range(NUM_ZONES_X):
            for j in range(NUM_ZONES_Y):
                zone_label = zone_x_labels[i] + zone_y_labels[j]
                ax.text(-FIELD_WIDTH / 2 + i * ZONE_WIDTH + 1, -FIELD_HEIGHT / 2 + j * ZONE_HEIGHT + 1,
                        zone_label, fontsize=8, ha='left', va='bottom', color='gray')
                
    # Draw objects

    for obj in scene.objects:
        x, y = obj.position.x, obj.position.y
        if obj.type.lower() == 'teammate':
            ax.plot(x, y, 'o', markersize=4, color='tab:blue') # Teammate (blue circle)
        elif obj.type.lower() == 'coach':
            ax.plot(x, y, 'o', markersize=4, color='tab:orange') # Coach (orange circle)
        elif obj.type.lower() == 'opponent':
            ax.plot(x, y, 'o', markersize=4, color='tab:red') # Opponent (red circle)
        elif obj.type.lower() == 'target':
            ax.plot(x, y, 'x', markersize=4, color='tab:orange') # Target (orange cross)

        ax.text(x, y, f' {obj.id.lower()}', fontsize=9, ha='left', va='bottom') # Object label

    if not axis:
        plt.axis('off')

    plt.show()

class InZone(Constraint):
    def __init__(self, args):
        self.zone = args.get('zone', None)
        self.obj = args.get('obj', None)

    @classmethod
    def doc(cls):
        return """
            Constraint: InZone
            The constraint checks if an object is in a specific zone on the field. This constraint may be triggered by specific linguistic hints that are specific to the domain of soccer like 'drop down', or 'move ahead'.
            Params:
                - zone (str): The zone that the object should be in. The zone is a string in the format 'AX' where 'A' is a letter denoting the column and 'X' is an integer denoting the row of the zone. This parameters should not be filled in by the LLM.
                - obj (Object): The player that must be in such zone, by default this is the coach, otherwise specify the id of the object in the scene.  
        """

    def learn(self, scenes):
        """
        Learns the zone the target position should be in based on the target point from the physical demonstration.
        """
        self.zone = []
        for scene in scenes:
            if self.obj is not None:
                print(self.obj)
                print([obj.id for obj in scene.objects])
                target = [obj for obj in scene.objects if obj.id.lower() == self.obj.lower()][0]
            else:
                target = [obj for obj in scene.objects if obj.type == 'target'][0]
            self.zone += [self.get_zone(target.position)]

    def get_zone(self, point):
        """
        Return a string denoting the zone of a point in the field based on its coordinates.
        """

        zone_x = int((point.x + FIELD_WIDTH / 2) // ZONE_WIDTH)
        zone_y = int((point.y + FIELD_HEIGHT / 2) // ZONE_HEIGHT)

        zone_x_labels = ['A', 'B', 'C', 'D', 'E']
        zone_y_labels = ['1', '2', '3', '4', '5', '6', '7', '8']
        
        if 0 <= zone_x < NUM_ZONES_X and 0 <= zone_y < NUM_ZONES_Y:
            zone_label = zone_x_labels[zone_x] + zone_y_labels[zone_y]
            return zone_label
        else:
            return None

    def __call__(self, scene, sample):
        """
        Checks if the zone of the sampled position is the same as the constraint zone learnt durign demonstration.
        """
        if self.obj is not None:
            sample = [obj for obj in scene.objects if obj.id == self.obj][0].position
            return self.get_zone(sample) in self.zone
        else:
            return self.get_zone(sample) in self.zone
    
    def toDict(self):
        return {
            'type': 'InZone',
            'args': {
                'obj': self.obj,
                'zone': self.zone[0]
            }
        }

from dist import *

# NOTE: May need to add another variable of target destination to the constraint, 
# since if this is used as a termination, it might end early
class HasAngleOfPass(Constraint):

    def __init__(self, args):
        self.ref = args.get('ref', None)
        self.radius = args.get('radius', None)

    @classmethod
    def doc(cls):
        return """
            Constraint: HasAngleOfPass
            The constraint checks if there exists an angle of pass between the user-controlled player and the specified teammate.
            Params:
                - ref (Object): The player object to pass the ball to. 
                - radius (float): The radius a player the pass is not intended to could cover the pass and therefore intercept it.
                    If the line of pass crosses any circle of radius r centered at an opponent, the it is not a valid line of pass.
        """

    def learn(self, scenes):
        target_teammate = None
        print(self.ref)

        # TODO: What object from what scene to choose?

        if self.ref is None: # if no teammate just get the first one
            # TODO: find closest teammate or teammate who received a pass in demo.
            target_teammate = [obj for obj in scenes[0].objects if obj.type.lower() == 'teammate'][0]
            self.ref = target_teammate.id
        else: # case where LLM gave us the teammate reference
            target_teammate = [obj for obj in scenes[0].objects if obj.id == self.ref][0]

        radii = []
        for scene in scenes:

            types = {obj.type: obj for obj in scene.objects}
            origin = types.get('target', types.get('coach', None))
            print(origin)
            min_d = float('inf')
            for obj in [obj for obj in scene.objects if obj.type == 'opponent']:
                min_d = min(min_d, self.closest(origin, target_teammate, obj))
            radii += [min_d]

        self.radius = Normal.fromList(radii)

    def closest(self, start, end, obj):

        p1 = np.array([start.position.x, start.position.y])
        p2 = np.array([end.position.x, end.position.y])
        p0 = np.array([obj.position.x, obj.position.y])
        
        line_vec, obj_vec = p2 - p1, p0 - p1
        line_len = np.dot(line_vec, line_vec)

        if line_len == 0:
            return np.linalg.norm(p0 - p1)
        
        t = np.dot(obj_vec, line_vec) / line_len
        t = max(0, min(1, t))
        
        closest_point = p1 + t * line_vec
        distance = np.linalg.norm(p0 - closest_point)
        
        return distance

    def __call__(self, scene, sample):

        for obj in [obj for obj in scene if obj.type.lower() == 'opponent']:
            if self.closest(Object('A', 'coach', sample), self.args['ref'], obj) < self.radius:
                return False

        return True
    
    def toDict(self):
        return {
            'type': 'HasAngleOfPass',
            'args': {
                'ref': self.ref,
                'radius': self.radius.toDict()
            }
        }
    
class HasBallPossession(Constraint):

    def __init__(self, args):
        self.ref = args.get('ref', None)

    @classmethod
    def doc(cls):
        return """
            Constraint: HasBallPossession
            The constraint checks if the given player has ball possession.
            Params:
                - ref (Player): The player object to check if they have ball possession. 
        """

    def learn(self, scenes):
        pass

    def __call__(self, scene, sample):
        return self.ref.ballPossession
    
    def toDict(self):
        return {
            'type': 'HasBallPossession',
            'args': {
                'ref': self.ref
            }
        }
    
class AheadOfLine(Constraint):

    def __init__(self, args):

        lines = {
            'midfield': 0.0
        }

        self.obj = args.get('obj', None)
        self.height = lines.get(args.get('line', None), None)

    @classmethod
    def doc(cls):
        return """
            Constraint: AheadOfLine
            The constraint checks if the player is ahead of some line in the field determined by a learnt or predefined height. Ahead in the context of footbal means closer to the attacking side / the opponent's goal.
            Params:
                - obj (Object): The player that must be ahead of the reference line, by default this is the coach, otherwise specify the id of the object in the scene.
                - height (str): The height of the reference line, if nothing is specified and it is left blank (very likely) the value will be learnt from the demonstration,
                    If the height is specified to be any of the predefined reference height then specify by the corresponding string.

            Available predefined lines: ['midfield']
        """
    
    def learn(self, scenes):

        if self.obj is None:
            ref = [obj for obj in scene.objects if obj.type.lower() == 'coach'][0]
        else:
            ref = {obj.id: obj for obj in scenes[0].objects}[self.obj]

        heighti = []
        for scene in scenes:
            if ref.type == 'coach':
                target = [obj for obj in scene.objects if obj.type.lower() == 'target'][0]
                h = target.position.y
            else:
                h = ref.position.y

            heighti += [h]

        self.height = Normal.fromList(heighti)

    def __call__(self, scene, sample):

        return True
    
    def toDict(self):
        return {
            'type': 'AheadOfLine',
            'args': {
                'obj': self.obj,
                'height': self.height.toDict()
            }
        }
    
class BehindOfLine(Constraint):

    def __init__(self, args):

        lines = {
            'midfield': 0.0
        }

        self.obj = args.get('obj', None)
        self.height = lines.get(args.get('line', None), None)

    @classmethod
    def doc(cls):
        return """
            Constraint: AheadOfLine
            The constraint checks if the player is behind of some line in the field determined by a learnt or predefined height. Behind in the context of footbal means closer to the defendig side / the player's goal.
            Params:
                - obj (Object): The player that must be ahead of the reference line, by default this is the coach, otherwise specify the id of the object in the scene.
                - height (str): The height of the reference line, if nothing is specified and it is left blank (very likely) the value will be learnt from the demonstration,
                    If the height is specified to be any of the predefined reference height then specify by the corresponding string.

            Available predefined lines: ['midfield']
        """
    
    def learn(self, scenes):

        if self.obj is None:
            ref = [obj for obj in scene.objects if obj.type.lower() == 'coach'][0]
        else:
            ref = {obj.id: obj for obj in scenes[0].objects}[self.obj]

        heighti = []
        for scene in scenes:
            if ref.type == 'coach':
                target = [obj for obj in scene.objects if obj.type.lower() == 'target'][0]
                h = target.position.y
            else:
                h = ref.position.y

            heighti += [h]

        self.height = Normal.fromList(heighti)

    def __call__(self, scene, sample):

        return True
    
    def toDict(self):
        return {
            'type': 'AheadOfLine',
            'args': {
                'obj': self.obj,
                'height': self.height.toDict()
            }
        }

class DistanceToObject(Constraint):
    def __init__(self, args):
        self.ref = args.get('ref', None)  # Reference object to measure distance to
        self.obj = args.get('obj', None)  # Object to check distance from (defaults to coach)
        self.min_dist = args.get('min_dist', None)  # Minimum distance threshold
        self.max_dist = args.get('max_dist', None)  # Maximum distance threshold
        self.operator = args.get('operator', 'between')  # Comparison operator: 'between', 'less_than', 'greater_than'

    @classmethod
    def doc(cls):
        return """
            Constraint: DistanceToObject
            The constraint checks the distance between a player/object and a reference object on the field.
            This can be used to maintain specific distances in formations, marking opponents, or creating space.
            
            Params:
                - ref (Object): The reference object to measure distance to. Could be teammate, opponent, or any other object on field.
                - obj (Object): The object to check distance from. By default this is the coach, otherwise specify the id of the object in the scene.
                - min_dist (float): Optional minimum distance threshold. If not specified, will be learned from demonstrations.
                - max_dist (float): Optional maximum distance threshold. If not specified, will be learned from demonstrations.
                - operator (str): The type of distance comparison to perform. Options:
                    - 'between': Check if distance is between min_dist and max_dist (default)
                    - 'less_than': Check if distance is less than max_dist
                    - 'greater_than': Check if distance is greater than min_dist
        """

    def learn(self, scenes):
        """
        Learns the distance thresholds based on demonstrations.
        For 'between' operator, learns both min and max distances.
        For 'less_than' or 'greater_than', learns the respective threshold.
        """
        distances = []
        
        for scene in scenes:
            # Get reference object
            if self.ref is None:
                # Default to first teammate if no reference specified
                ref_obj = [obj for obj in scene.objects if obj.type.lower() == 'teammate'][0]
                self.ref = ref_obj.id
            else:
                print(self.ref)
                print([obj.id for obj in scene.objects])
                ref_obj = [obj for obj in scene.objects if obj.id == self.ref][0]
            
            # Get target object (coach/target position or specified object)
            if self.obj is None:
                target = [obj for obj in scene.objects if obj.type == 'target'][0]
            else:
                print([obj.id for obj in scene.objects], self.obj)
                target = [obj for obj in scene.objects if obj.id == self.obj][0]
            
            # Calculate distance between points
            dist = np.sqrt((ref_obj.position.x - target.position.x)**2 + 
                         (ref_obj.position.y - target.position.y)**2)
            distances.append(dist)
        
        # Learn thresholds based on operator type
        if self.operator == 'between':
            # Learn both min and max distances with some margin
            self.min_dist = Normal.fromList([d * 0.9 for d in distances])  # 90% of observed
            self.max_dist = Normal.fromList([d * 1.1 for d in distances])  # 110% of observed
        elif self.operator == 'less_than':
            # Learn maximum distance threshold
            self.max_dist = Normal.fromList([d * 1.1 for d in distances])
        elif self.operator == 'greater_than':
            # Learn minimum distance threshold
            self.min_dist = Normal.fromList([d * 0.9 for d in distances])

    def calculate_distance(self, pos1, pos2):
        """Helper function to calculate distance between two positions"""
        return np.sqrt((pos1.x - pos2.x)**2 + (pos1.y - pos2.y)**2)

    def __call__(self, scene, sample):
        """
        Checks if the distance between objects satisfies the constraint based on the operator.
        Returns True if the constraint is satisfied, False otherwise.
        """
        # Get reference object
        ref_obj = [obj for obj in scene.objects if obj.id == self.ref][0]
        
        # Get current position to check (either sample point or object position)
        if self.obj is None:
            current_pos = sample  # Direct position for coach/target
        else:
            current_pos = [obj for obj in scene.objects if obj.id == self.obj][0].position
            
        distance = self.calculate_distance(ref_obj.position, current_pos)
        
        # Check distance based on operator
        if self.operator == 'between':
            return (self.min_dist.sample() <= distance <= self.max_dist.sample())
        elif self.operator == 'less_than':
            return distance <= self.max_dist.sample()
        elif self.operator == 'greater_than':
            return distance >= self.min_dist.sample()
        
        return False  # Invalid operator
    
    def toDict(self):
        """Convert constraint to dictionary representation"""
        return {
            'type': 'DistanceToObject',
            'args': {
                'ref': self.ref,
                'obj': self.obj,
                'min_dist': self.min_dist.toDict() if self.min_dist else None,
                'max_dist': self.max_dist.toDict() if self.max_dist else None,
                'operator': self.operator
            }
        }
    
from coord import Coord
    
class MoveTo(Action):

    def __init__(self, id, task):
        super().__init__(id, task)
        self.coord = None

    def learn(self, demoMap, timeMap=None):

        scenes, times = self.task.sourceScenesIn(demoMap, timeMap)

        for s, t in zip(scenes, times):
            s.set_time(t)

        self.coord = Coord(self, scenes)
        self.coord.learn(constraintAPI)

    def toDict(self):
        result = {
            'id': 'MoveTo',
            'args': {
                # 'target': self.coord.toDict()
                "dest": "lambda_dest",
                "until": ""
            },
            "constraints": {
                "lambda_dest": self.coord.toDict()
            }
        }

        # TODO: How do I do lambda termination?
        # if self.task.until: # if there is a termination condition
            # result['args']['until'] = ...
            # result['constraints']['λ_termination'] = ...


        return result

class PassTo(Action):

    def __init__(self, id, task):
        super().__init__(id, task)
        self.obj = None

    def learn(self, demoMap, timeMap=None):

        scenes, times = self.task.sourceScenesIn(demoMap, timeMap)

        scene = scenes[0]
        scene.set_time(times[0])

        objList = ', '.join([obj.id + ' (' + obj.type.lower() + ')' for obj in scene.objects])
        format = "{'obj': str}"
        example = "{'obj': 'midfielder'}"
        
        prompt = f"""
            You are an expert in the domain of soccer. Given a particular task description for a defending scenario,
            your task is to identify the object the player must pass the ball to.
            The scene has the following list of available objects [{objList}].
            The output should be a json with format {format} where the label is the label of the object.
            For instance, if the task specifies or implies that a pass should be done to the object 'midfielder (Teammate)' then you would return {example}.
        """

        output = json.loads(chat([
            ChatEntry('system', prompt),
            ChatEntry('user', str(self.task))
        ], json=True))

        self.obj = output.get('obj', None)
        print(self.obj)

    def toDict(self):
        return {
            'id': 'PassTo',
            'args': {
                'obj': self.obj
            }
        }
    
class Wait(Action):
    def __init__(self, id, task):
        super().__init__(id, task)
        self.constraints = []
        self.identifiers = []
        self.logic = None

    def construct(self, scene, constraintAPI, prompt=''):
        if not prompt:

            objList = ', '.join([obj.id + '(' + obj.type + ')' for obj in scene.objects])
            apiList = '\n'.join([api.doc() for api in constraintAPI.values()])
            format = "{'logic': str, 'constraints': [{'id': str, 'api': str, params: dict}], 'reasoning': str}"
            example = "{'logic': 'A AND B', 'constraints': [{'id': 'A', 'api': 'DistanceTo', params: {'ref': 'player1'} }, {'id': 'B', 'api': 'InZone', params: {'zone': None}, {'id': 'C', 'api': 'HasBallPossession', params: {'ref': 'coach'} }]}"

            prompt = f"""
                You are given a soccer's coach explanation to how the player should act under a specifc scenario. 
                Your task is to construct a logical expression of constraint with AND/OR/IF operators.
                Note that the constraint should satisfy the until condition of a waiting action, i.e. the logical expression consisting of constraints should return true only if the player should be done waiting, that is some trigger denoted by the constraints and the expression.
                Choose constraints from the options provided and logically combine them.
                The output should be a json with format {format} where the constraints are a list of constraint objects with id mapping the label in the logical expression to the specific constraint, the api and the params, which is a dictionary with relevant arguments to the constraint that could be inferred from the task description.
                Include a reasoning of why each constraint.
                
                Here's a list of the available constraints:
                    {apiList}

                The scene has the following list of available objects [{objList}].

                For instance, if the task specifies that a player should be at a certain distance from a player labeled 'player1' and in some zone then you would return {example}. Note that for InZone, despite having parameters to fill in they were not specified in the task description so they aren't filled out in the response; the only varialbes that should be filled in here are ones that give a concrete values or object reference.
            """

        entries = [
            ChatEntry(role='system', content=prompt),
            ChatEntry(role='user', content=str(self.task)),
        ]

        output = json.loads(chat(entries, json=True))

        print(output)

        print('reasoning', output['reasoning'])
        logic = output['logic']
        constraints = output['constraints']

        return logic, constraints

    def learn(self, demoMap, timeMap=None):

        scenes, times = self.task.sourceScenesIn(demoMap, timeMap)

        for s, t in zip(scenes, times):
            s.set_time(t)

        _logic, _constraints = self.construct(scenes[0], constraintAPI)

        self.logic = _logic

        for c in _constraints:

            id = c.get('id', None)
            _api = c.get('api', None)
            params = c.get('params', None)

            if id and _api and params:
                api = constraintAPI.get(_api, Constraint)(params)
                api.learn(scenes)
                c['params'] = vars(api)

                self.identifiers += [id]
                self.constraints += [api]
    
    def toDict(self):
        return {
            'id': 'Idle',
            'args': {
                "precondition": "lambda_precondition"
            },
            "constraints": {
                "lambda_precondition": {
                    "logical": self.logic,
                    "identifiers": self.identifiers,
                    "args": {i: c.toDict() for i, c in zip(self.identifiers, self.constraints)}
                }
            }
        }

actionsAPI = {
    'MoveTo': MoveTo,
    'PassTo': PassTo,
    'Wait': Wait
}

constraintAPI = {
    'InZone': InZone,
    'HasAngleOfPass': HasAngleOfPass,
    'HasBallPossession': HasBallPossession,
    'AheadOfLine': AheadOfLine,
    'BehindOfLine': BehindOfLine,
    'DistanceToObject': DistanceToObject
}

api = {
    'actions': actionsAPI
}