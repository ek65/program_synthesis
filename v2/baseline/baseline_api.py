import numpy as np

def findObj(id, objects):
    if isinstance(id, str):
        key_lower = id.lower()
        return [obj for obj in objects if key_lower in obj.name.lower()]

def isEgo(id, scene):
    return id.lower() == scene.egoObject.name.lower()
    
# MARK: Constraints
class Constraint:
    def __init__(self, args):
        self.args = args

    def __call__(self, sample, scene):
        pass

# MARK: HasBallPossession 
class HasBallPossession(Constraint):

    def __init__(self, args):
        """
        Input Argument:
            - player (str): the name of a soccer player. 
        """
        self.playerID = args.get('player', None)

    def __call__(self, scene, sample):
        '''
            The API returns a boolean (True/False) on whether the given soccer player (i.e. self.playerID) has ball possession.
            It returns True if the player has ball possession; otherwise, False.
        '''
        pass
    
# MARK: InZone

FIELD_WIDTH, FIELD_HEIGHT = 20, 34
NUM_ZONES_X, NUM_ZONES_Y = 4, 5
ZONE_WIDTH = FIELD_WIDTH / NUM_ZONES_X
ZONE_HEIGHT = FIELD_HEIGHT / NUM_ZONES_Y

class InZone(Constraint):

    def __init__(self, args={}):
        """
        Input Arguments:
            - player (str): The name of the player that must be in such zone. By default this is the coach, otherwise specify the name of the object in the scene.  
            - zone (str): The zone that the player should be in. The zone is a string in the format 'AX' where 'A' is a letter denoting the column and 'X' is an integer denoting the row of the zone. 
        """
        self.objID = args.get('obj', None)
        self.zone = args.get('zone', None)

    def __call__(self, scene, sample):
        """
        '''
            The constraint checks if a particular player (i.e. self.objID) is in a defined zone (i.e. self.zone) on the soccer field. 
            This constraint may be triggered by specific linguistic hints that are specific to the domain of soccer like 'drop down', or 'move ahead'.
            Given a player and a zone, the API returns True if the player is in the zone; otherwise, returns False.
        """
        pass
        
# MARK: MovingTowards
class MovingTowards(Constraint):

    def __init__(self, args={}):
        """
        Input Arguments:
            - obj (str): The name of the moving player.
            - ref (str): The name of the target player.
        """
        self.objID = args.get('obj', None)
        self.refID = args.get('ref', None)

    def __call__(self, scene, sample):
        """
            This API checks whether a player (i.e. self.objID) is moving towards a different player (i.e. self.refID).
            It returns True if self.objID is moving towards self.refID; otherwise, it returns False.
        """
        pass

# MARK: HasPathToPass

class HasPath(Constraint):

    def __init__(self, args={}):
        """
        Input Arguments:
                - passer (str): The name player object that intends to pass the ball. The name must be that of a player in the scene.
                - receiver (str): The name player object intented to receive the ball.  The name must be that of a player in the scene.
                - path_width (float): The path_width measures the degree of angle to pass. If the line of pass crosses any circle of radius r 
                                    centered at an opponent, the it is not a valid line of pass.
        """
        self.passerID = args.get('passer', None)
        self.receiverID = args.get('receiver', None)
        self.radius = args.get('path_width', None)
        self.radiusAvg = self.radius.get('avg', 0.0)
        self.radiusStd = self.radius.get('std', 1.0)

    def __call__(self, scene, sample):
        """
        The API checks if there exists an unobstructed path between the two input players, i.e. 'passer' and 'receiver',
        to pass a ball. The width of the path is measured by the 'path_width' input.
        The path_width refers to the minimum distance of any opponent to the straight line that connects the 'passer'
        and the 'receiver'. 

        This API returns True if there is no opponent within the path; otherwise, returns False. 
        """
        pass
    
# MARK: CloseTo
class CloseTo(Constraint):
    def __init__(self, args):
        self.obj = args.get('obj', None)
        self.ref = args.get('ref', None)
        self.max = float(args.get('max', None))

    def __call__(self, scene, sample):
        """
        
        """

# MARK: DistanceTo
class DistanceTo(Constraint):
    def __init__(self, args):
        """
        Input Arguments:
            - to_obj (str): The name of the object to measure distance to. Could be teammate, opponent, or any other object on field.
            - from_obj (str): The name of the object to check distance from.
            - min (float): Optional minimum distance threshold. If not specified, set its value to None.
            - max (float): Optional maximum distance threshold. If not specified, set its value to None.
            - operator (str): The type of distance comparison to perform. Options:
                - 'within': Check if distance is between min and max (default)
                - 'less_than': Check if distance is less than max_dist
                - 'greater_than': Check if distance is greater than min_dist
        """
        self.fromID = args.get('from', None)
        self.toID = args.get('to', None)
        self.min = args.get('min', None)
        self.max = args.get('max', None)
        self.operator = args.get('operator', None)

        self.minAvg = self.min.get('avg', None)
        self.maxAvg = self.max.get('avg', None)

    def __call__(self, scene, sample):
        """
        The function checks a constraint (i.e. self.operator) related a distance between a player/object (i.e. self.fromID) and a 
        reference object (i.e. self.toID) on the field, and returns a boolean (True / False).
        """
        
# MARK: HeightRelation
        
class HeightRelation(Constraint):
    def __init__(self, args):
        """
        Input Arguments:
                - obj (str): The ID of the player object to evaluate.
                - ref (str or None): The ID of the reference object. If None, the absolute y is used.
                - relation (str): A string ("behind" or "ahead") indicating the desired relationship.
                - vertical_threshold (dict): A dictionary containing the average and standard deviation of the height threshold in float type.
        """
        self.objID = args.get('obj', None)
        self.refID = args.get('ref', None)
        self.relation = args.get('relation', None)
        self.threshold = args.get('vertical_threshold', None)
        self.threshold_avg = self.threshold.get('avg') if self.threshold else None

    def __call__(self, scene, sample):
        """
        This API checks whether the specified player's (i.e. obj) vertical y-coordinate position is either behind or ahead of a reference (i.e. ref).
            
        If a reference (ref) is provided, the API computes the difference in y-coordinate (player.y - ref.y) and learns a threshold.
        If ref is None, it learns the absolute y position of the player.
        
        At evaluation:
            - For a "above" relation, if ref is provided, the obj's y-coordinate value must be greater than 
                that of the ref and absolute value of the difference between the two values must be greater than the average vertical threshold.
                If ref is None, then the obj's y-coordinate value must be greater than the average vertical threshold.
            - For a "below" relation, if ref is provided, the obj's y-coordinate value must be less than 
                that of the ref and absolute value of the difference between the two values must be greater than the vertical threshold.
                If ref is None, then the obj's y-coordinate value must be less than the vertical threshold.
        """
        if sample and isEgo(self.objID, scene):
            player_y = sample[1]
        else:
            player_objs = findObj(self.objID, scene.objects)
            if not player_objs:
                print(f"Player '{self.objID}' not found in the scene.")
                return False
            player_obj = player_objs[0]
            player_y = player_obj.position.y

        if self.refID:
            ref_objs = findObj(self.refID, scene.objects)
            if not ref_objs:
                print(f"Reference object '{self.refID}' not found in the scene.")
                return False
            ref_obj = ref_objs[0]
            ref_y = ref_obj.position.y
            value = player_y - ref_y
        else:
            value = player_y

        print(player_y, ref_y, value, sample)

        if self.threshold_avg is None:
            print("No height threshold provided for HeightRelation.")
            return False
        
        if self.relation == 'behind':
            return value < self.threshold_avg
        elif self.relation == 'ahead':
            return value > self.threshold_avg
        else:
            print(f"Unknown relation '{self.relation}' in HeightRelation.")
            return False

class HorizontalRelation(Constraint):
    def __init__(self, args):
        """
        Input Arguments:
                - obj (str): The ID of the player object to evaluate.
                - ref (str or None): The ID of the reference object. If None, the absolute x coordinate is used.
                - relation (str): A string ("left" or "right") indicating the desired horizontal relationship.
                - horizontal_threshold (dict): A dictionary containing the average and standard deviation of the x-axis threshold in float type.
        """
        self.objID = args.get('obj', None)
        self.refID = args.get('ref', None)
        self.relation = args.get('relation', None)
        self.horizontal_threshold = args.get('horizontal_threshold', None)
        self.threshold_avg = float(self.threshold.get('avg')) if self.threshold else None

    def __call__(self, scene, sample):
        """
            This API checks whether the specified player's horizontal (x-axis) position is either to the left or 
            to the right of a reference.
            
            If a reference (ref) is provided, the API computes the difference in x-coordinate (player.x - ref.x) and 
            learns a threshold value. If ref is None, it learns the absolute x position of the player.
            
            At evaluation:
                - For a "left" relation, if ref is provided, the obj's x-coordinate value must be less than 
                    that of the ref and absolute value of the difference between the two values must be greater than the horizontal threshold.
                    If ref is None, then the obj's x-coordinate value must be less than the horizontal threshold.
                - For a "right" relation, if ref is provided, the obj's x-coordinate value must be greater than 
                    that of the ref and absolute value of the difference between the two values must be greater than the horizontal threshold.
                    If ref is None, then the obj's x-coordinate value must be greater than the horizontal threshold.
        """
