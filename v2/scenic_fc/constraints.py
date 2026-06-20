from api_utils import ConstraintAPI
import numpy as np
from dist_utils import Normal
from nlp_utils import Chat, client
import json

class ConstraintAPIDef(ConstraintAPI):
    
    def __init__(self, constraint):
        self.constraint = constraint
        self.t = constraint.condition.t


    @classmethod
    def doc(cls):
        """
        Class ConstraintAPI():
            '''
            The definition of ConstraintAPI abstract class which is inherited by all the Constraint APIs.
            This class provides a common interface and shared functionality for all constraint APIs.
            However, this API must not be used when generating Scenic program. 
            This is merely provided for a reference.
            '''

            def dist(self, scene, ego=False):
                '''
                Gridtizes the soccer field into 2D array of grid cells.
                Then, it computes the probability of the constraint being satisfied at each grid cell.
                Returns a 2D numpy array of probabilities [0,1].

                Input Args:
                    - scene: always 'scene = simulation()' in the Scenic program. This contains all the information of the 
                             state of the world including the positions and orientations of all players and objects.
                    - ego: if True, the constraint is computed with respect to the ego player.
                '''
                pass
                
            def bool(self, scene):
                '''
                Returns a boolean (True/False) indicating whether the constraint is satisfied in the given scene.
                Input Args:
                    - scene: always 'scene = simulation()' in the Scenic program. This contains all the information of the 
                             state of the world including the positions and orientations of all players and objects.
                '''
                pass
                
            '''
            Extra Notes: Two constraints can be composed using the '&' or '|' operators. Moreover, you can negate a constraint using '~' operator.
            For example:
            composite_cond = constraint1 & constraint2
            composite_composite_cond = composite_cond | constraint3
            negated_composite_composite_cond = ~ composite_composite_cond
            return negated_composite_composite_cond.dist(self, scene, ego=False)
            '''
        
        """

# MARK: HasBallPossession
class HasBallPossession(ConstraintAPI):
    def __init__(self, constraint):
        super().__init__(constraint)
        # Required parameter: the name of a soccer player.
        self.player = constraint.args.get('player', None)

    @classmethod
    def ref(cls) -> str:
        return 'HasBallPossession'

    @classmethod
    def doc(cls):
        return """
        Class HasBallPossession(ConstraintAPI):
            def __init__(self, args):
                '''
                
                Required Parameter:
                - args (dict): A dictionary with the following key-value pair:
                    - 'player' (str): The variable name of a soccer player instantiated in the scene. 
                    Reference the given names of instantiated objects and players in the scene and select one from it. 
                '''
                pass
            def bool(self, scene):
                '''
                Returns a boolean (True/False) indicating whether the specified soccer player has ball possession.
                Input Args:
                    - scene: always 'scene = simulation()' in the Scenic program. This contains all the information of the 
                             state of the world including the positions and orientations of all players and objects.
                '''
                pass
            '''
            Extra Notes: Although HasBallPossession has .dist() method, you should not use it in the Scenic program.
            Instead, you should use .bool() method to check if the constraint is satisfied.
            '''
        """

    def synth(self, demos, api):
        pass
    
    def to_dict(self, expanded: bool = False):
        return {
            'id': self.constraint.id,
            'constraint': self.ref(),
            'args': {
                'player': self.player
            }
        }

# MARK: MovingTowards
class MovingTowards(ConstraintAPI):
    def __init__(self, constraint):
        super().__init__(constraint)
        # objID is the object that should be moving toward the reference
        self.objID = constraint.args.get('obj', None)
        self.refID = constraint.args.get('ref', None)

    @classmethod
    def ref(cls) -> str:
        return 'MovingTowards'

    @classmethod
    def doc(cls):
        return """
        Class MovingTowards(ConstraintAPI):
            def __init__(self, args):
                '''
                This API checks whether a player (obj) is moving towards a different player (ref).
                It returns True if obj is moving towards ref; otherwise, it returns False.

                Input Arguments:
                - args (dict): A dictionary with the following key-value pairs:
                    - 'obj' (str): The name of the moving player.
                    - 'ref' (str): The name of the target player.
                    Reference the given names of instantiated objects and players in the scene and select players from it. 
                '''
            pass

            def bool(self, scene):
                '''
                Returns a boolean (True/False) indicating whether the specified player is moving towards the target player.
                Input Args:
                    - scene: always 'scene = simulation()' in the Scenic program. This contains all the information of the 
                             state of the world including the positions and orientations of all players and objects.
                '''
            pass
            '''
            Extra Notes: Although MovingTowards has .dist() method, you should not use it in the Scenic program.
            Instead, you should use .bool() method to check if the constraint is satisfied.
            '''
        """

    def synth(self, demos, api):
        pass

    def to_dict(self, expanded: bool = False):
        return {
            'id': self.constraint.id,
            'constraint': self.ref(),
            'args': {
                'obj': self.objID,
                'ref': self.refID
            }
        }

# MARK: MakePass
class MakePass(ConstraintAPI):
    def __init__(self, constraint):
        super().__init__(constraint)
        self.player = constraint.args.get('player', None)

    @classmethod
    def ref(cls) -> str:
        return 'MakePass'

    @classmethod
    def doc(cls):
        return """
        Class MakePass(ConstraintAPI):
            def __init__(self, args):
                '''
                This API checks if a player executes a pass.

                Input Arguments:
                - args (dict): A dictionary with the following key-value pairs:
                    - 'player' (str): The name of the player (Unity Object) executing the pass.
                Reference the given names of instantiated objects and players in the scene and select a player from it. 
                '''
            pass
            def bool(self, scene):
                '''
                Returns a boolean (True/False) indicating whether the specified player has executed a pass.
                Input Args:
                    - scene: always 'scene = simulation()' in the Scenic program. This contains all the information of the 
                             state of the world including the positions and orientations of all players and objects.
                '''
            pass
            '''
            Extra Notes: Although MakePass has .dist() method, you should not use it in the Scenic program.
            Instead, you should use .bool() method to check if the constraint is satisfied.
        """

    def synth(self, demos, api):
        pass
    
    def to_dict(self, expanded: bool = False):
        return {
            'id': self.constraint.id,
            'constraint': self.ref(),
            'args': {
                'player': self.player
            }
        }

# MARK: Pressure
class Pressure(ConstraintAPI):
    def __init__(self, constraint):
        super().__init__(constraint)
        # Required parameter: the name of a soccer player.
        self.player1 = constraint.args.get('player1', None)
        self.player2 = constraint.args.get('player2', None)

    @classmethod
    def ref(cls) -> str:
        return 'Pressure'

    @classmethod
    def doc(cls):
        return """
        Class Pressure(ConstraintAPI):
            def __init__(self, args):
                '''
                This API checks if a player is pressuring another player.
                It returns True if player1 is chasing after player2, or being close to player2.

                Required Parameter:
                - args (dict): A dictionary with the following key-value pairs:
                    - 'player1' (str): The name of a soccer player (Unity Object) chasing after player2.
                    - 'player2' (str): The name of a soccer player (Unity Object) being chased after.
                    Reference the given names of instantiated objects and players in the scene and select one from it. 
                '''
            pass
            def bool(self, scene):
                '''
                Returns a boolean (True/False) indicating if player1 is pressuring player2.
                Input Args:
                    - scene: always 'scene = simulation()' in the Scenic program. This contains all the information of the 
                             state of the world including the positions and orientations of all players and objects.
                '''
            pass
            '''
            Extra Notes: Although Pressure has .dist() method, you should not use it in the Scenic program.
            Instead, you should use .bool() method to check if the constraint is satisfied.
            '''
        """

    def synth(self, demos, api):
        pass
    
    def to_dict(self, expanded: bool = False):
        return {
            'id': self.constraint.id,
            'constraint': self.ref(),
            'args': {
                'player1': self.player1,
                'player2': self.player2
            }
        }

    
# MARK: HasPathToPass
class HasPath(ConstraintAPI):

    def __init__(self, constraint):
        super().__init__(constraint)
        self.passerID = constraint.args.get('obj1', None)
        self.receiverID = constraint.args.get('obj2', None)
        self.radius = constraint.args.get('path_width', 1)

    @classmethod
    def ref(cls) -> str:
        return 'HasPath'

    @classmethod
    def doc(cls):
        return """
        Class HasPath(ConstraintAPI):
            def __init__(self, args):
                '''
                The API checks if there exists an unobstructed path between the two players, i.e. 'obj1' and 'obj2', 
                to check if there is a path or angle to pass or shoot the ball. 

                The width of the path is measured by the 'path_width' input.
                The path_width refers to the minimum distance of any opponent to the straight line that connects the 'obj1'
                and the 'obj2'. In other words, path_width checks how close is any opponent to the path in between the two players.

                The path_width is modeled as a Gaussian distribution, with the average width and standard deviation in meters.
                You need to infer the average width and standard deviation from the narrated demonstrations.
                If not specified in the narration, then refer to the videos of the demonstrations to infer the height threshold.

                args:
                - args (dict): A dictionary with the following key-value pairs:
                    - 'obj1' (str): The name player or object that intends to pass the ball. Reference the given names of instantiated objects and players in the scene and select one from it. 
                    - 'obj2' (str): The name player or object intented to receive the ball.  Reference the given names of instantiated objects and players in the scene and select one from it. 
                    - 'path_width' (dictionary): The path width is modeled as a Gaussian distribution. The dictionary with the following key-value pairs:
                        - 'avg' (float): The average width of the path in meters. Unless the user specifies the path width, then use the average width of 1 meter by default.
                        - 'std' (float): The standard deviation of the path width in meters.
                '''
                pass
            def bool(self, scene):
                '''
                Returns a boolean (True/False) indicating if there is an unobstructed path between the two players.
                Input Args:
                    - scene: always 'scene = simulation()' in the Scenic program. This contains all the information of the 
                             state of the world including the positions and orientations of all players and objects.
                '''
                pass

            def dist(self, scene, ego=False):
                '''
                Returns:
                    - numpy.ndarray: A 2D grid (rows x cols) where each cell contains a probability
                    value between epsilon and 1.0, representing the likelihood that position
                    is safe for passing between the two specified objects.
                '''
                pass
        """

    def synth(self, demos, api):
        demos = {d.id: d for d in demos}
        radii = []
        for demoID, t in self.t.items():
            demo = demos.get(demoID, None)
            if demo:
                # print("Passer ID:", self.passerID)
                # print("Receiver ID:", self.receiverID)
                
                passer_list = demo.scene[self.passerID]
                receiver_list = demo.scene[self.receiverID]
                if not passer_list or not receiver_list:
                    print(f"Skipping demo {demoID}: Missing passer or receiver object")
                    continue
                if not isinstance(t, int):
                    if isinstance(t, float):
                        t = demo.video.frame_to_traj_index(t)
                    else:
                        print(f"HasPathToPass) t is NOT number: {t}")
                        continue
                passer = passer_list[0]
                receiver = receiver_list[0]
                
                try:
                    start = passer.location[t]
                    end = receiver.location[t]
                except IndexError as e:
                    print(f"IndexError for passer or receiver in demo {demoID}: {e}")
                    continue

                min_d = 2
                for obj in [i for i in demo.scene.objects if i.type.lower() == 'opponent']:
                    try:
                        point = obj.location[t]
                    except IndexError as e:
                        print(f"IndexError for opponent object {obj.id} in demo {demoID}: {e}")
                        continue
                    d = self.distance_to_line(start, end, point)
                    min_d = min(min_d, d)
                radii.append(min_d)
        
        if radii:
            if self.radius is None:
                self.radius = Normal.fromList(radii)
            elif isinstance(self.radius, dict):
                self.radius = Normal.from_dict(self.radius)
            elif not isinstance(self.radius, Normal):
                self.radius = Normal(avg=self.radius, std=0.0)
        else:
            print("Warning: No valid radii computed from demos for HasPathToPass constraint.")


    def distance_to_line(self, start, end, point):

        start = np.array([start.x, start.y])
        end = np.array([end.x, end.y])
        point = np.array([point.x, point.y])

        line_vec, obj_vec = end - start, point - start
        line_len = np.dot(line_vec, line_vec)

        if line_len == 0:
            return np.linalg.norm(point - start)
        
        t = np.dot(obj_vec, line_vec) / line_len
        t = max(0, min(1, t))
        
        closest_point = start + t * line_vec
        distance = np.linalg.norm(point - closest_point)
        
        return distance
    
    def to_dict(self, expanded: bool = False):
        return {
            'id': self.constraint.id,
            'constraint': self.ref(),
            'args': {
                'obj1': self.passerID,
                'obj2': self.receiverID,
                'path_width': self.radius.to_dict() if self.radius and isinstance(self.radius, Normal) else self.radius
            }
        }
    
# MARK: DistanceTo

class DistanceTo(ConstraintAPI):
    def __init__(self, constraint):
        super().__init__(constraint)

        # Required parameters
        self.fromID = constraint.args.get('from', None)
        self.toID = constraint.args.get('to', None)
        print('distance from', self.fromID, 'to', self.toID)
        self.operator = constraint.args.get('operator', None)

        # Optional parameters (if not provided, they default to None)
        self.min = constraint.args.get('min', None)
        self.max = constraint.args.get('max', None)

    @classmethod
    def ref(cls) -> str:
        return 'DistanceTo'

    @classmethod
    def doc(cls):
        return """
            Class DistanceTo(ConstraintAPI):
                def __init__(self, args):
                    '''
                    Checks a constraint related to the distance between a player/object and a reference object on the field.

                    From narrated demonstrations, you need to infer the distance thresholds, which are 'min' and 'max'.
                    The 'min' and 'max' are modeled as Gaussian distributions, with the average and standard deviation in meters.

                    You need to also infer what type of distance comparison is to be performed.
                    For this you need to infer the 'operator'.

                    Required Parameters:
                    - args (dict): A dictionary with the following key-value pairs:
                        - 'to' (str): The name of the object to measure distance to. Reference the given names of instantiated objects and players in the scene and select one from it. 
                                      Do *NOT* use specific coordinates. Use the name of the object instead.
                        - 'from' (str): The name of the object to check distance from. Reference the given names of instantiated objects and players in the scene and select one from it. 
                                      Do *NOT* use specific coordinates. Use the name of the object instead.
                        - 'min' (dict): Minimum distance threshold. A dictionary with the following key-value pairs:
                            - 'avg' (float): Average minimum distance in meters.
                            - 'std' (float): Standard deviation for minimum distance in meters.
                        - 'max' (dict): A dictionary with the following key-value pairs:
                            - 'avg' (float): Average maximum distance in meters.
                            - 'std' (float): Standard deviation for maximum distance in meters.
                        - 'operator' (str): The type of distance comparison to perform. 
                            - 'within': Check if the distance is between min and max.
                            - 'less_than': Check if the distance is less than the max threshold.
                            - 'greater_than': Check if the distance is greater than the min threshold.
                    '''
                    pass
            def dist(self, scene, ego=False):
                '''
                Gridtizes the soccer field into 2D array of grid cells.
                Then, it computes the probability of the distance constraint being satisfied at each grid cell.
                Returns a 2D numpy array of probabilities [0,1].

                Input Args:
                    - scene: always 'scene = simulation()' in the Scenic program. This contains all the information of the 
                             state of the world including the positions and orientations of all players and objects.
                    - ego: if True, the constraint is computed with respect to the ego player.
                '''
                pass
            def bool(self, scene):
                '''
                Returns a boolean (True/False) indicating whether the distance constraint is satisfied in the given scene.
                Input Args:
                    - scene: always 'scene = simulation()' in the Scenic program. This contains all the information of the 
                             state of the world including the positions and orientations of all players and objects.
                '''
                pass
        """

    def synth(self, demos, api):
        demos = {d.id: d for d in demos}
        distances = []
        
        for demoID, t in self.t.items():
            demo = demos.get(demoID, None)
            if not demo:
                continue

            fromList = demo.scene[self.fromID]
            toList = demo.scene[self.toID]
            
            if not fromList or not toList:
                print(f"Skipping demo {demoID}: Missing from or to object")
                continue

            fromObj = fromList[0]
            toObj = toList[0]

            if not isinstance(t, int):
                if isinstance(t, float):
                    t = demo.video.frame_to_traj_index(t)
                else:
                    print(f"DistanceTo) t is NOT number: {t}")
                    continue

            try:
                start = fromObj.location[t]
                end = toObj.location[t]
            except IndexError as e:
                print(f"IndexError for objects in demo {demoID}: {e}")
                continue
            
            # Compute Euclidean distance:
            # d = sqrt((x2 - x1)^2 + (y2 - y1)^2)
            d = np.sqrt((start.x - end.x)**2 + (start.y - end.y)**2)
            distances.append(d)

        if distances:
            if self.operator == 'within':
                # Process min threshold
                if self.min is None:
                    self.min = Normal.fromList([d * 0.9 for d in distances])
                elif isinstance(self.min, dict):
                    self.min = Normal.from_dict(self.min)
                elif not isinstance(self.min, Normal):
                    self.min = Normal(avg=self.min, std=0.0)
                        
                # Process max threshold
                if self.max is None:
                    self.max = Normal.fromList([d * 1.1 for d in distances])
                elif isinstance(self.max, dict):
                    self.max = Normal.from_dict(self.max)
                elif not isinstance(self.max, Normal):
                    self.max = Normal(avg=self.max, std=0.0)
            elif self.operator == 'less_than':
                if self.max is None:
                    self.max = Normal.fromList([d * 1.1 for d in distances])
                elif isinstance(self.max, dict):
                    self.max = Normal.from_dict(self.max)
                elif not isinstance(self.max, Normal):
                    self.max = Normal(avg=self.max, std=0.0)
            elif self.operator == 'greater_than':
                if self.min is None:
                    self.min = Normal.fromList([d * 0.9 for d in distances])
                elif isinstance(self.min, dict):
                    self.min = Normal.from_dict(self.min)
                elif not isinstance(self.min, Normal):
                    self.min = Normal(avg=self.min, std=0.0)
        else:
            print("Warning: No valid distances were computed from the provided demos.")

        # Final safety check (in case of any unconverted values)
        if self.min is not None and not isinstance(self.min, Normal):
            if isinstance(self.min, dict):
                self.min = Normal.from_dict(self.min)
            else:
                self.min = Normal(avg=self.min, std=0.0)
        if self.max is not None and not isinstance(self.max, Normal):
            if isinstance(self.max, dict):
                self.max = Normal.from_dict(self.max)
            else:
                self.max = Normal(avg=self.max, std=0.0)

    
    def to_dict(self, expanded: bool = False):
        return {
            'id': self.constraint.id,
            'constraint': self.ref(),
            'args': {
                'from': self.fromID,
                'to': self.toID,
                'min': (
                    self.min if isinstance(self.min, dict)
                    else self.min.to_dict() if self.min is not None
                    else None
                ),
                'max': self.max.to_dict() if self.max and isinstance(self.max, Normal) else self.max,
                'operator': self.operator
            }
        }
    
# MARK: HeightRelation
class HeightRelation(ConstraintAPI):
    def __init__(self, constraint):
        super().__init__(constraint)
        # Required parameter: the ID of the player to evaluate.
        self.objID = constraint.args.get('obj', None)
        # Optional parameter: the ID of the reference object; if None, absolute y is used.
        self.refID = constraint.args.get('ref', None)
        # Required parameter: relation: a string value ("below" or "above").
        self.relation = constraint.args.get('relation', None)
        # Optional parameter: the learned threshold; if not provided, it will be computed.
        self.height_threshold = constraint.args.get('height_threshold', None)

    @classmethod
    def ref(cls) -> str:
        return 'HeightRelation'

    @classmethod
    def doc(cls):
        return """
        Class HeightRelation(ConstraintAPI):
            def __init__(self, args):
                '''
                Given an object and and a reference object, this API checks whether the object's vertical (y-axis) position is either below or above of a reference object's.
                Thus, this API is useful for modeling narration such as "the player should move up above the opponent" or "the player should stay below the teammate".
                This API may be composed with HorizontalRelation API to model more complex relations such as "position yourself next to the opponent", which would
                require a conjunction of Height Relation and Horizontal Relation. 

                Depending of the context of the narrated demonstrations, the reference object may be not exist.
                Such situation can occur if the narration describes that the object is to move below or above with respect to where it currently is, 
                e.g. "the player should move up the pitch, i.e. soccer field" or "the player should be down the field"
                In such a case, reference object should be None.
                
                From narrated demonstrations, you need to infer what type of relation is to be compared:
                    - relation = "below" if the object's y-axis position needs to be below the reference object's y-axis position, or with respect to itself in case reference object is None.
                    - relation = "above" relation, if the object's y-axis position needs to be above the reference object's y-axis position, or with respect to itself in case reference object is None.
                
                From narrated demonstrations, you need to also infer the "height_threshold" which is the threshold for the difference in the y-axis position of the object and the reference object.
                The height_threshold is modeled as a Gaussian distribution. You need to infer its mean and standard deviation from the narrated demonstrations.
                If not specified in the narration, then refer to the videos of the demonstrations to infer the height threshold.
                
                Required Parameters:
                - args (dict): A dictionary with the following key-value pairs:
                    - 'obj' (str): The name of the instantiated player object. Reference the given names of instantiated objects and players in the scene and select one from it.      
                                   Do *NOT* use specific coordinates. Use the name of the object instead.
                    - 'relation' (str): A string ("below" or "above") indicating the desired relationship.
                    - 'ref' (str or None): The name of the reference object. Reference the given names of instantiated objects and players in the scene and select one from it. 
                                   Do *NOT* use specific coordinates. Use the name of the object instead.
                    - 'height_threshold' (dict): This threshold is modeled as Gaussian distribution. A dictionary with the following key-value pairs:
                        - 'avg' (float): Average height threshold in meters.
                        - 'std' (float): Standard deviation for the height threshold in meters.
                '''
            pass
            def dist(self, scene, ego=False):
                '''
                Gridtizes the soccer field into 2D array of grid cells.
                Then, it computes the probability of the distance constraint being satisfied at each grid cell.
                Returns a 2D numpy array of probabilities [0,1]. Values of the array are 0 if the constraint is not satisfied, 1 if the constraint is satisfied.

                Input Args:
                    - scene: always 'scene = simulation()' in the Scenic program. This contains all the information of the 
                             state of the world including the positions and orientations of all players and objects.
                    - ego: if True, the constraint is computed with respect to the ego player.
                '''
                pass
            def bool(self, scene):
                '''
                Returns a boolean (True/False) indicating whether the height relation constraint is satisfied in the given scene.
                Input Args:
                    - scene: always 'scene = simulation()' in the Scenic program. This contains all the information of the 
                             state of the world including the positions and orientations of all players and objects.
                '''
                pass
        """

    def synth(self, demos, api):
        demos_dict = {d.id: d for d in demos}
        heights = []  # Collect either relative differences or absolute y values.
        
        # Normalize IDs for case-insensitive matching.
        obj_id = self.objID.lower() if self.objID else None
        ref_id = self.refID.lower() if self.refID else None

        for demoID, t in self.t.items():
            demo = demos_dict.get(demoID, None)
            if demo is None:
                continue

            # Match object by lowercased ID.
            player_obj = next((obj for obj in demo.scene.objects if obj.id.lower() == obj_id), None)
            if player_obj is None:
                continue

            if not isinstance(t, int):
                if isinstance(t, float):
                    t = demo.video.frame_to_traj_index(t)
                else:
                    print(f"HeightRelation) t is NOT number: {t}")
                    continue

            try:
                player_y = player_obj.location[t].y
            except IndexError as e:
                print(f"IndexError for player {self.objID} in demo {demoID}: {e}")
                continue

            if ref_id:
                ref_obj = next((obj for obj in demo.scene.objects if obj.id.lower() == ref_id), None)
                if ref_obj is None:
                    print(f"Demo {demoID} skipped: reference object {self.refID} not found.")
                    continue
                try:
                    ref_y = ref_obj.location[t].y
                except IndexError as e:
                    print(f"IndexError for reference {self.refID} in demo {demoID}: {e}")
                    continue
                # Compute the relative height difference.
                heights.append(player_y - ref_y)
            else:
                # Use the absolute y coordinate.
                heights.append(player_y)
        
        # If a threshold was already provided, convert it to Normal if needed.

        if self.height_threshold is not None:
            if isinstance(self.height_threshold, dict):
                self.height_threshold = Normal.from_dict(self.height_threshold)
            elif not isinstance(self.height_threshold, Normal):
                self.height_threshold = Normal(avg=self.height_threshold, std=0.0)
        else:
            if heights:
                if self.relation == 'below':
                    # Compute the threshold as the mean of the heights.
                    self.height_threshold = Normal.fromList([h for h in heights if h < 0])
                else:
                    # Compute the threshold as the mean of the heights.
                    self.height_threshold = Normal.fromList([h for h in heights if h > 0])
            else:
                print("Warning: No valid height measurements were computed from the demos.")
                self.height_threshold = Normal.fromList(heights)


    def to_dict(self, expanded: bool = False):

        return {
            'id': self.constraint.id,
            'constraint': self.ref(),
            'args': {
                'obj': self.objID,
                'ref': self.refID,
                'relation': self.relation,
                'height_threshold': self.height_threshold.to_dict() if self.height_threshold and isinstance(self.height_threshold, Normal) else self.height_threshold
            }
        }
    
# MARK: OrientedTo

class OrientedTo(ConstraintAPI):
    def __init__(self, constraint):
        super().__init__(constraint)
        # The ID of the object we wish to evaluate.
        self.objID = constraint.args.get('obj', None)
        # The reference object whose orientation is used.
        self.refID = constraint.args.get('ref', None)
        # Side: expected to be either "left" or "right"
        self.side = constraint.args.get('side', None)
        # Optional thresholds (in radians) to be learned if not provided.
        self.min = constraint.args.get('min', None)
        self.max = constraint.args.get('max', None)
        # Operator for comparison: 'within' (default), 'less_than', or 'greater_than'
        self.operator = constraint.args.get('operator', 'within')

    @classmethod
    def ref(cls) -> str:
        return 'OrientedTo'

    @classmethod
    def doc(cls):
        return """
        def OrientedTo(args):
            '''
            Checks whether a given object (obj) is to the right or to the left of a reference object's
            line of view. This is determined by computing the signed angle between the reference object's 
            orientation vector and the vector from the reference to obj.
            
            A positive signed angle indicates that obj is to the left of ref's orientation, while a negative 
            signed angle indicates that obj is to the right.
            
            The operator parameter specifies the comparison type:
                - 'within': Checks if the absolute angle lies between min and max.
                - 'less_than': Checks if the absolute angle is less than max.
                - 'greater_than': Checks if the absolute angle is greater than min.
            
            Required Parameters:
            - args (dict): A dictionary with the following key-value pairs:
                - 'obj' (str): The ID of the object to evaluate.
                - 'ref' (str): The ID of the reference object whose orientation is used.
                - 'side' (str): The desired side ("left" or "right") relative to the reference.
                - 'min' (dict): A dictionary with the following key-value pairs:
                    - 'avg' (float): Average of minimum distance.
                    - 'std' (float): Standard deviation of minimum distance.
                - 'max' (dict): A dictionary with the following key-value pairs:
                    - 'avg' (float): Average of maximum distance.
                    - 'std' (float): Standard deviation of maximum distance.
                - 'operator' (str): Type of comparison (default "within").
            '''
            pass
        """

    def synth(self, demos, api):
        import numpy as np
        demos_dict = {d.id: d for d in demos}
        angles = []  # To collect observed angles on the desired side.
        
        for demoID, t in self.t.items():
            demo = demos_dict.get(demoID, None)
            if demo is None:
                continue

            # Retrieve the objects from the demo scene.
            obj = next((o for o in demo.scene.objects if o.id == self.objID), None)
            ref = next((o for o in demo.scene.objects if o.id == self.refID), None)
            if obj is None or ref is None:
                print(f"Skipping demo {demoID}: Missing obj ({self.objID}) or ref ({self.refID}).")
                continue

            try:
                # Get positions at time t.
                obj_pos = obj.location[t]
                ref_pos = ref.location[t]
                # Compute vector from reference to obj.
                v = np.array([obj_pos.x - ref_pos.x, obj_pos.y - ref_pos.y])
            except IndexError as e:
                print(f"IndexError in demo {demoID} while accessing locations: {e}")
                continue

            try:
                # Get the reference's orientation at time t.
                ref_orientation = ref[t].orientation
            except IndexError as e:
                print(f"IndexError in demo {demoID} while accessing orientation: {e}")
                continue

            u = np.array([ref_orientation.x, ref_orientation.y])
            # Compute the signed angle using arctan2(cross, dot)
            dot = np.dot(u, v)
            cross = u[0]*v[1] - u[1]*v[0]
            angle = np.arctan2(cross, dot)  # angle in radians

            # Adjust angle to reflect the specified side.
            if self.side == 'left':
                if angle < 0:
                    continue  # Skip if not on the left.
            elif self.side == 'right':
                if angle > 0:
                    continue  # Skip if not on the right.
                angle = -angle  # Convert to positive for consistency.
            else:
                print(f"Unknown side '{self.side}' specified; skipping demo {demoID}.")
                continue

            # At this point, angle is a positive number representing the deviation on the desired side.
            angles.append(angle)

        if angles:
            if self.operator == 'within':
                if self.min is None:
                    self.min = Normal.fromList([a * 0.9 for a in angles])
                elif not isinstance(self.min, Normal):
                    self.min = Normal(avg=self.min, std=0.0)
                if self.max is None:
                    self.max = Normal.fromList([a * 1.1 for a in angles])
                elif not isinstance(self.max, Normal):
                    self.max = Normal(avg=self.max, std=0.0)
            elif self.operator == 'less_than':
                if self.max is None:
                    self.max = Normal.fromList([a * 1.1 for a in angles])
                elif not isinstance(self.max, Normal):
                    self.max = Normal(avg=self.max, std=0.0)
            elif self.operator == 'greater_than':
                if self.min is None:
                    self.min = Normal.fromList([a * 0.9 for a in angles])
                elif not isinstance(self.min, Normal):
                    self.min = Normal(avg=self.min, std=0.0)
        else:
            print("Warning: No valid angle observations computed from demos.")

    def to_dict(self, expanded: bool = False):
        return {
            'id': self.constraint.id,
            'constraint': self.ref(),
            'args': {
                'obj': self.objID,
                'ref': self.refID,
                'side': self.side,
                'min': self.min.to_dict() if self.min and isinstance(self.min, Normal) else self.min,
                'max': self.max.to_dict() if self.max and isinstance(self.max, Normal) else self.max,
                'operator': self.operator
            }
        }
    
# MARK: HorizontalRelation

class HorizontalRelation(ConstraintAPI):
    def __init__(self, constraint):
        super().__init__(constraint)
        # Required parameter: the ID of the player to evaluate.
        self.objID = constraint.args.get('obj', None)
        # Optional parameter: the ID of the reference object; if None, the absolute x is used.
        self.refID = constraint.args.get('ref', None)
        # Required parameter: relation: a string ("left" or "right") indicating the desired horizontal positioning.
        self.relation = constraint.args.get('relation', None)
        # Optional parameter: the learned threshold. If not provided, it will be learned.
        self.x_threshold = constraint.args.get('horizontal_threshold', None)

    @classmethod
    def ref(cls) -> str:
        return 'HorizontalRelation'

    @classmethod
    def doc(cls):
        return 
    """
        Class HorizontalRelation(ConstraintAPI):
            def __init__(self, args):
                '''
                Given an object and and a reference object, this API checks whether the object's horizontal (X-axis) position is either to the left or right of a reference object's.
                
                Thus, this API is useful for modeling narration such as "the player should move to the right side of the opponent" or "the player should be on the left side of the teammate".
                This API may be composed with HeightRelation API to model more complex relations such as "position yourself right next to the opponent", which would
                require a conjunction of Height Relation and Horizontal Relation. 
                
                Depending of the context of the narrated demonstrations, the reference object may be not exist.
                Such situation can occur if the narration describes that the object is to move to the left or right with respect to where it currently is, 
                e.g. "the player should move to the left of the pitch, i.e. soccer field" or "the player should be to the side of the field".
                In such a case, reference object should be None.
                
                From narrated demonstrations, you need to infer what type of relation is to be compared:
                    - relation = "left" if the object's x-axis position needs to be to the left of the reference object's x-axis position, or with respect to itself in case reference object is None.
                    - relation = "right" relation, if the object's x-axis position needs to be to the right of the reference object's x-axis position, or with respect to itself in case reference object is None.

                From narrated demonstrations, you need to also infer the "horizontal_threshold" which is the threshold for the difference in the x-axis position of the object and the reference object.
                The horizontal_threshold is modeled as a Gaussian distribution. You need to infer its mean and standard deviation from the narrated demonstrations.
                If not specified in the narration, then refer to the videos of the demonstrations to infer the horizontal threshold.

                Required Parameters:
                - args (dict): A dictionary with the following key-value pairs:
                    - 'obj' (str): The name of the instantiated player object. Reference the given names of instantiated objects and players in the scene and select one from it.
                                    Do *NOT* use specific coordinates. Use the name of the object instead.
                    - 'relation' (str): A string ("left" or "right") indicating the desired relationship.
                    - 'ref' (str or None): The name of the reference object. Reference the given names of instantiated objects and players in the scene and select one from it.
                                            Do *NOT* use specific coordinates. Use the name of the object instead.
                    - 'horizontal_threshold' (dict): This threshold is modeled as Gaussian distribution. A dictionary with the following key-value pairs:
                        - 'avg' (float): Average horizontal threshold in meters.
                        - 'std' (float): Standard deviation for the horizontal threshold in meters.
                '''
            pass
            def dist(self, scene, ego=False):
                '''
                Gridtizes the soccer field into 2D array of grid cells.
                Then, it computes the probability of the horizontal relation constraint being satisfied at each grid cell.
                Returns a 2D numpy array of probabilities [0,1]. Values of the array are 0 if the constraint is not satisfied, 1 if the constraint is satisfied.

                Input Args:
                    - scene: always 'scene = simulation()' in the Scenic program. This contains all the information of the 
                             state of the world including the positions and orientations of all players and objects.
                    - ego: if True, the constraint is computed with respect to the ego player.
                '''
                pass
            def bool(self, scene):
                '''
                Returns a boolean (True/False) indicating whether the horizontal relation constraint is satisfied in the given scene.
                Input Args:
                    - scene: always 'scene = simulation()' in the Scenic program. This contains all the information of the 
                             state of the world including the positions and orientations of all players and objects.
                '''
                pass
        """

    def synth(self, demos, api):
        demos_dict = {d.id: d for d in demos}
        x_values = []  # Collect horizontal differences or absolute x values.
        
        for demoID, t in self.t.items():
            demo = demos_dict.get(demoID, None)
            if demo is None:
                continue

            # Retrieve the player object from the demo scene.
            player_obj = next((obj for obj in demo.scene.objects if obj.id == self.objID), None)
            if player_obj is None:
                continue

            if not isinstance(t, int):
                if isinstance(t, float):
                    t = demo.video.frame_to_traj_index(t)
                else:
                    print(f"HorizontalRelation: t is not a number: {t}")
                    continue

            try:
                player_x = player_obj.location[t].x
            except IndexError as e:
                print(f"IndexError for player {self.objID} in demo {demoID}: {e}")
                continue

            # If a reference is provided, compute the horizontal difference.
            if self.refID:
                ref_obj = next((obj for obj in demo.scene.objects if obj.id == self.refID), None)
                if ref_obj is None:
                    print(f"Demo {demoID} skipped: reference object {self.refID} not found.")
                    continue
                try:
                    ref_x = ref_obj.location[t].x
                except IndexError as e:
                    print(f"IndexError for reference {self.refID} in demo {demoID}: {e}")
                    continue
                x_values.append(player_x - ref_x)
            else:
                # Use the absolute x coordinate of the player.
                x_values.append(player_x)
        
        if x_values:
            if self.x_threshold is None:
                if self.relation == 'left':
                    self.x_threshold = Normal.fromList([x for x in x_values if x < 0])
                else:
                    self.x_threshold = Normal.fromList([x for x in x_values if x > 0])
            elif isinstance(self.x_threshold, dict):
                self.x_threshold = Normal.from_dict(self.x_threshold)
            elif not isinstance(self.x_threshold, Normal):
                self.x_threshold = Normal(avg=self.x_threshold, std=0.0)
        else:
            print("Warning: No valid horizontal measurements were computed from the demos.")
            self.x_threshold = Normal.fromList(x_values)


    def to_dict(self, expanded: bool = False):
        return {
            'id': self.constraint.id,
            'constraint': self.ref(),
            'args': {
                'obj': self.objID,
                'ref': self.refID,
                'relation': self.relation,
                'horizontal_threshold': self.x_threshold.to_dict() if self.x_threshold and isinstance(self.x_threshold, Normal) else self.x_threshold
            }
        }

# MARK: CloseTo

class CloseTo(ConstraintAPI):
    def __init__(self, constraint):
        super().__init__(constraint)
        # Required parameter: the object that should be close (e.g. the player)
        self.objID = constraint.args.get('obj', None)
        # Required parameter: the reference object (e.g. the ball)
        self.refID = constraint.args.get('ref', None)
        # Optional parameter: maximum distance threshold. If not provided, it will be learned.
        self.max_dist = constraint.args.get('max', None)

    @classmethod
    def ref(cls) -> str:
        return 'CloseTo'

    @classmethod
    def doc(cls):
        return """
        def CloseTo(args):
            '''
            Checks whether the specified object (obj) is very close to the reference object (ref).
            This is typically used in scenarios such as determining if a player is moving towards the ball.
            
            The distance between obj and ref is measured using the Euclidean distance between their positions.
            If a maximum distance threshold (max) is provided, it is used as-is (after conversion to a Normal distribution).
            Otherwise, it is learned from demonstration data.
            
            Required Parameters:
            - args (dict): A dictionary with the following key-value pairs:
                - 'obj' (str): The ID of the object that should be close.
                - 'ref' (str): The ID of the reference object (e.g. the ball).
                - 'max' (dict): A dictionary with the following key-value pairs:
                    - 'avg' (float): The average maximum allowable distance.
                    - 'std' (float): The standard deviation allowed for the distance.
    
            '''
            pass
        """

    def synth(self, demos, api):
        demos_dict = {d.id: d for d in demos}
        distances = []
        
        for demoID, t in self.t.items():
            demo = demos_dict.get(demoID, None)
            if demo is None:
                continue

            obj_list = demo.scene[self.objID]
            ref_list = demo.scene[self.refID]
            if not obj_list or not ref_list:
                print(f"Skipping demo {demoID}: Missing object {self.objID} or reference {self.refID}")
                continue

            obj_instance = obj_list[0]
            ref_instance = ref_list[0]

            if not isinstance(t, int):
                if isinstance(t, float):
                    t = demo.video.frame_to_traj_index(t)
                else:
                    print(f"CloseTo) t is NOT number: {t}")
                    continue
            
            try:
                obj_pos = obj_instance.location[t]
                ref_pos = ref_instance.location[t]
            except IndexError as e:
                print(f"IndexError in demo {demoID}: {e}")
                continue

            # Compute Euclidean distance.
            d = np.sqrt((obj_pos.x - ref_pos.x)**2 + (obj_pos.y - ref_pos.y)**2)
            distances.append(d)
        
        if distances:
            if self.max_dist is None:
                # Learn a maximum distance threshold with a slight margin (10% larger than observed).
                self.max_dist = Normal.fromList([d * 1.1 for d in distances])
            elif isinstance(self.max_dist, dict):
                # Convert dict representation to a Normal instance.
                self.max_dist = Normal.from_dict(self.max_dist)
            elif not isinstance(self.max_dist, Normal):
                # Convert a provided float threshold into a Normal distribution.
                self.max_dist = Normal(avg=self.max_dist, std=0.0)
        else:
            print("Warning: No valid distances computed from demos for CloseTo constraint.")

    def to_dict(self, expanded: bool = False):
        return {
            'id': self.constraint.id,
            'constraint': self.ref(),
            'args': {
                'obj': self.objID,
                'ref': self.refID,
                'max': self.max_dist.to_dict() if self.max_dist and isinstance(self.max_dist, Normal) else self.max_dist
            }
        }
    
# MARK: AtAngle

class AtAngle(ConstraintAPI):
    def __init__(self, constraint):
        super().__init__(constraint)
        # Required parameters
        self.playerID = constraint.args.get('player', None)
        self.ballID = constraint.args.get('ball', None)
        
        # Optional parameters for learned thresholds
        self.left_args = constraint.args.get('left', None)
        self.right_args = constraint.args.get('right', None)

    @classmethod
    def ref(cls) -> str:
        return 'AtAngle'

    @classmethod
    def doc(cls):
        return """
        Class AtAngle(ConstraintAPI):
            def __init__(self, args):
                '''
                This API checks whether a player's destination position is at a specific angle and distance with respect to the ball's position.
                AtAngle() computes the player's destination position that is "at angle" between the player's current location and the position of the ball.
                This angle is created by the two vectors between the vector connecting the player's position to the ball's position, and the other vector connecting the player's destination position to the ball position.

                Computes the angle between two vectors:
                1. Vector from player's current position to ball position
                2. Vector from player's destination position to ball position
                
                From narrated demonstrations, you need to infer which direction the player needs to be at angle with respect to the ball in both left and right sides with respect to the player's current position.
                You should also infer the thresholds for the angle ('theta') and distance ('dist') on both sides.
                The angle and distance thresholds are modeled as Gaussian distributions, with mean and standard deviation.
                The range of the angle is [0, 180) degrees.
                The distance is the Euclidean distance between the player's destination position and the ball position in meters.
                If these information is not specified in the narration, then refer to the videos of the demonstrations to infer the horizontal threshold.

                
                Required Parameters:
                    - args (dict): A dictionary with the following key-value pairs:
                        - 'player' (str): The name of the player object. Do *NOT* use specific coordinates. Use the name of the object instead.
                        - 'ball' (str): The name of the ball object. Do *NOT* use specific coordinates. Use the name of the object instead.
                        - 'left' (dict, optional): A dictionary defining thresholds for the left side. Contains:
                            - 'theta' (dict): Angular threshold with:
                                - 'avg' (float): Average angle in degrees.
                                - 'std' (float): Standard deviation.
                            - 'dist' (dict): Distance threshold with:
                                - 'avg' (float): Average distance.
                                - 'std' (float): Standard deviation.
                        - 'right' (dict, optional): Same structure as 'left', but for the right side.
                '''
            pass
            def dist(self, scene, ego=False):
                '''
                Gridtizes the soccer field into 2D array of grid cells.
                Then, it computes the probability of the angle constraint being satisfied at each grid cell.
                Returns a 2D numpy array of probabilities [0,1].
                '''
                pass
            def bool(self, scene):
                '''
                Returns a boolean (True/False) indicating whether the angle constraint is satisfied in the given scene.
                Input Args:
                    - scene: always 'scene = simulation()' in the Scenic program. This contains all the information of the 
                             state of the world including the positions and orientations of all players and objects.
                '''
                pass
        """
    def to_dict(self, expanded: bool = False):
        return {
            'id': self.constraint.id,
            'constraint': self.ref(),
            'args': {
                'player': self.playerID,
                'ball': self.ballID,
                'left': self.left_args,
                'right': self.right_args
            }
        }

# MARK: Overlap

class Overlap(ConstraintAPI):
    def __init__(self, constraint):
        super().__init__(constraint)
        # Required parameters
        self.playerID = constraint.args.get('player', None)
        self.ballID = constraint.args.get('ball', None)
        self.goalID = constraint.args.get('goal', None)
        self.opponentID = constraint.args.get('opponent', None)
        
        # Optional parameters for learned thresholds
        self.theta = constraint.args.get('theta', None)
        self.dist = constraint.args.get('dist', None)

    @classmethod
    def ref(cls) -> str:
        return 'Overlap'

    @classmethod
    def doc(cls):
        return """
        Class Overlap(ConstraintAPI):
            def __init__(self, args):
                '''
                This API is used to model player's destination position to overlap a teammate with a ball in soccer. 
                The API computes the player's destination position based on the player's current position, ball (assumed to always be with a teammate), opponent (defender), and goal. 
                
                The area to reach in order to overlap the teammate with the ball is defined by two vectors:
                1. One vector connects the ball's position to the goal.
                2. The other vector connects the ball's position to the player's destination position.

                The following logic is baked into this overlap API:
                - The opponent closest to the ball is identified.
                - If the opponent is to the left of the vector connecting the ball to the goal, then the player should move to the left of this vector in order to attract the opponent and create space for the teammate.
                - If the opponent is to the right of the vector connecting the ball to the goal, then the player should move to the right of this vector in order to attract the opponent and create space for the teammate.
                
                From the narrated demonstrations, you need to infer the angle and distance thresholds for the overlap.
                Based on the destination that the coach reached in order to overlap the teammate with the ball, you need to infer the angle and the distance thresholds. 
                The angle is represented as a Normal distribution with mean and standard deviation in degrees.
                The range of angle is [0, 180) degrees.
                The distance is the Euclidean distance between the player's destination position and the ball position in meters.
                
                Required Parameters:
                    - args (dict): A dictionary with the following key-value pairs:
                        - 'player' (str): The name of the player making the overlap. Do *NOT* use specific coordinates. Use the name of the object instead.
                        - 'ball' (str): The name of the ball (assumed to be with a teammate).
                        - 'goal' (str): The name of the goal object.
                        - 'opponent' (str): The name of the opponent (defender) object. Do *NOT* use specific coordinates. Use the name of the object instead.
                        - 'theta' (dict): Angular threshold represented as a Normal distribution:
                            - 'avg' (float): Average angle in degrees.
                            - 'std' (float): Standard deviation of the angle in degrees.
                        - 'dist' (dict): Distance threshold represented as a Normal distribution:
                            - 'avg' (float): Average distance in meters.
                            - 'std' (float): Standard deviation of the distance in meters.
                '''
            pass

            def dist(self, scene, ego=False):
                '''
                Gridtizes the soccer field into 2D array of grid cells.
                Then, it computes the probability of the overlap constraint being satisfied at each grid cell.
                Returns a 2D numpy array of probabilities [0,1].
                '''
                pass
            def bool(self, scene):
                '''
                Returns a boolean (True/False) indicating whether the overlap constraint is satisfied in the given scene.
                Input Args:
                    - scene: always 'scene = simulation()' in the Scenic program. This contains all the information of the 
                             state of the world including the positions and orientations of all players and objects.
                '''
                pass
        """

    def to_dict(self, expanded: bool = False):
        return {
            'id': self.constraint.id,
            'constraint': self.ref(),
            'args': {
                'player': self.playerID,
                'ball': self.ballID,
                'goal': self.goalID,
                'opponent': self.opponentID,
                'theta': self.theta,
                'dist': self.dist
            }
        }


    
constraintAPI = {
    'ConstraintAPI': ConstraintAPIDef,
    'HasBallPossession': HasBallPossession,
    'MovingTowards': MovingTowards,
    'HasPath': HasPath,
    'DistanceTo': DistanceTo,
    'HeightRelation': HeightRelation,
    # 'OrientedTo': OrientedTo,
    'HorizontalRelation': HorizontalRelation,
    'MakePass': MakePass,
    'Pressure': Pressure,
    'AtAngle': AtAngle,
    'Overlap': Overlap
}

targetAPI = {
    # 'InZone': InZone,
    'DistanceTo': DistanceTo,
    'HeightRelation': HeightRelation,
    # 'OrientedTo': OrientedTo,
    'HorizontalRelation': HorizontalRelation
    # 'CloseTo': CloseTo,
}