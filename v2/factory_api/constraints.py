from api_utils import ConstraintAPI
import numpy as np
from dist_utils import Normal
from nlp_utils import Chat, client
import json

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
        def HasBallPossession(player):
            '''
            Returns a boolean (True/False) indicating whether the specified soccer player has ball possession.
            
            Required Parameter:
                - player (str): The name of a soccer player.
            '''
            pass
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


# MARK: InZone

FIELD_WIDTH, FIELD_HEIGHT = 20, 34
NUM_ZONES_X, NUM_ZONES_Y = 4, 5
ZONE_WIDTH = FIELD_WIDTH / NUM_ZONES_X
ZONE_HEIGHT = FIELD_HEIGHT / NUM_ZONES_Y

class InZone(ConstraintAPI):
    def __init__(self, constraint):
        super().__init__(constraint)
        self.zone = constraint.args.get('zone', None) # TODO: Fix initalization to allow sets
        self.objID = constraint.args.get('obj', 'coach')

    @classmethod
    def ref(cls) -> str:
        return 'InZone'

    @classmethod
    def doc(cls):
        return """
        def InZone(player, zone):
            '''
            The constraint checks if a particular player is in a defined zone on the soccer field. 
            This constraint may be triggered by specific linguistic hints that are specific to the domain of soccer like 'drop down', or 'move ahead'.
            Given a player and a zone, the API returns True if the player is in the zone; otherwise, returns False.

            Input Arguments:
                - player (str): The name of the player that must be in such zone. By default this is the coach, otherwise specify the name of the object in the scene.  
                - zone (str): The zone that the player should be in. The zone is a string in the format 'AX' where 'A' is a letter denoting the column and 'X' is an integer denoting the row of the zone. 
            '''
            pass
        """

    def synth(self, demos, api):
        demos = {d.id: d for d in demos}
        self.zone = []
        for demoID, t in self.t.items():
            demo = demos.get(demoID, None)

            if not isinstance(t, int):
                if isinstance(t, float):
                    t = demo.video.frame_to_traj_index(t)
                else:
                    print(f"InZone) t is NOT number: {t}")
                    continue
            if demo:
                for obj in demo.scene[self.objID]:
                    x = obj.location[t]
                    z = self.get_zone(x)
                    self.zone.append(z)

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
    
    def to_dict(self, expanded: bool = False):
        return {
            'id': self.constraint.id,
            'constraint': self.ref(),
            'args': {
                'obj': self.objID,
                'zone': self.zone
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
        def MovingTowards(obj, ref):
            '''
            This API checks whether a player (obj) is moving towards a different player (ref).
            It returns True if obj is moving towards ref; otherwise, it returns False.

            Input Arguments:
                - obj (str): The name of the moving player.
                - ref (str): The name of the target player.
            '''
            pass
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
        def MakePass(player):
            '''
            This API checks if a passer executes a pass. 
            It returns True if the passer executes a pass; otherwise, it returns False.

            Input Arguments:
                - player (str): The name of the player executing the pass.
            '''
            pass
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
        def Pressure(player1, player2):
            '''
            Returns a boolean (True/False) indicating if player1 is pressuring player2. 
            This pressuring is defined as a player1 chasing after player2. 
            
            Required Parameter:
                - player1 (str): The name of a soccer player chasing after another player.
                - player2 (str): The name of a soccer player being chased after.
            '''
            pass
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
        self.radius = constraint.args.get('path_width', None)

    @classmethod
    def ref(cls) -> str:
        return 'HasPath'

    @classmethod
    def doc(cls):
        return """
        def HasPath(obj1, obj2, path_width):
            '''
            The API checks if there exists an unobstructed path between the two objects, i.e. 'obj1' and 'obj2', 
            to check if there is a path or angle to pass or shoot the ball. 

            The width of the path is measured by the 'path_width' input.
            The path_width refers to the minimum distance of any opponent to the straight line that connects the 'obj1'
            and the 'obj2'. 

            This API returns True if there is no opponent within the path to intercept; otherwise, returns False. 

            Params:
                - obj1 (str): The name player or object that intends to pass the ball. The name must be that of a player in the scene.
                - obj2 (str): The name player or object intented to receive the ball.  The name must be that of a player in the scene.
                - path_width (float): The width of the path between the obj1 and obj2. This is the minimum distance of any opponent to the straight line that connects the obj1 and obj2.
            '''
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
            def DistanceTo(to, from, operator, min=None, max=None):
                '''
                Checks a constraint related to the distance between a player/object and a reference object on the field,
                returning a boolean (True/False).

                Required Parameters:
                    - to (str): The name of the object to measure distance to.
                    - from (str): The name of the object to check distance from.
                    - operator (str): The type of distance comparison to perform. Options:
                        - 'within': Check if the distance is between min and max.
                        - 'less_than': Check if the distance is less than the max threshold.
                        - 'greater_than': Check if the distance is greater than the min threshold.

                Optional Parameters:
                    - min (float): Minimum distance threshold. Default is None.
                    - max (float): Maximum distance threshold. Default is None.
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
        def HeightRelation(obj, relation, ref=None, height_threshold=None):
            '''
            This API checks whether the specified player's vertical (y-axis) position is either below or above of a reference.
            In soccer above means closer to the opponent's goal while below means closer to the the player's team goal.
            
            If a reference (ref) is provided, the API computes the difference in y-coordinate (player.y - ref.y) and learns a threshold.
            If ref is None, it learns the absolute y position of the player.
            
            At evaluation:
                - For a "below" relation, the player's value must be less than the learned threshold.
                - For an "above" relation, the player's value must be greater than the learned threshold.
            
            Required Parameters:
                - obj (str): The ID of the player object to evaluate.
                - relation (str): A string ("below" or "above") indicating the desired relationship.
            
            Optional Parameters:
                - ref (str or None): The ID of the reference object. If None, the absolute y coordinate is used.
                - height_threshold (float or Normal, optional): The learned threshold represented as a Normal distribution over heights (or height differences). 
                  If not provided, it will be learned from demo data.
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
        def OrientedTo(obj, ref, side, min=None, max=None, operator='within'):
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
                - obj (str): The ID of the object to evaluate.
                - ref (str): The ID of the reference object whose orientation is used.
                - side (str): The desired side ("left" or "right") relative to the reference.
            
            Optional Parameters:
                - min (float or Normal, optional): Minimum angle threshold (in radians). If not provided, it will be learned.
                - max (float or Normal, optional): Maximum angle threshold (in radians). If not provided, it will be learned.
                - operator (str): Type of comparison (default "within").
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
        return """
        def HorizontalRelation(obj, relation, ref=None, horizontal_threshold=None):
            '''
            Checks whether the specified player's horizontal (x-axis) position is either to the left or 
            to the right of a reference.
            
            If a reference (ref) is provided, the API computes the difference in x-coordinate (player.x - ref.x)
            and learns a threshold value. If ref is None, it learns the absolute x position of the player.
            
            At evaluation:
                - For a "left" relation:
                    - If ref is provided, the player's x-coordinate must be less than that of the ref and 
                      the absolute difference must be greater than the horizontal_threshold.
                    - If ref is None, the player's x-coordinate must be less than the horizontal_threshold.
                - For a "right" relation:
                    - If ref is provided, the player's x-coordinate must be greater than that of the ref and 
                      the absolute difference must be greater than the horizontal_threshold.
                    - If ref is None, the player's x-coordinate must be greater than the horizontal_threshold.
            
            Required Parameters:
                - obj (str): The ID of the player object to evaluate.
                - relation (str): A string ("left" or "right") indicating the desired horizontal relationship.
            
            Optional Parameters:
                - ref (str or None): The ID of the reference object. If None, the absolute x coordinate is used.
                - horizontal_threshold (float or Normal, optional): The learned threshold as a Normal distribution over horizontal differences or positions.
                  If not provided, it will be learned from demonstration data.
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
        def CloseTo(obj, ref, max=None):
            '''
            Checks whether the specified object (obj) is very close to the reference object (ref).
            This is typically used in scenarios such as determining if a player is moving towards the ball.
            
            The distance between obj and ref is measured using the Euclidean distance between their positions.
            If a maximum distance threshold (max) is provided, it is used as-is (after conversion to a Normal distribution).
            Otherwise, it is learned from demonstration data.
            
            Required Parameters:
                - obj (str): The ID of the object that should be close.
                - ref (str): The ID of the reference object (e.g. the ball).
            
            Optional Parameter:
                - max (float or Normal, optional): Maximum distance threshold. Default is None.
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
    
# MARK: HandRaised

class HandRaised(ConstraintAPI):
    def __init__(self, constraint):
        super().__init__(constraint)
        # same key you’ll put in your DSL
        self.objID = constraint.args.get('player', constraint.args.get('obj', None))

    @classmethod
    def ref(cls) -> str:
        return 'HandRaised'

    @classmethod
    def doc(cls) -> str:
        return """
        def HandRaised(player):
            '''
            Returns True if the specified player's current behavior is a hand-raise.
            
            Required Parameter:
              - player (str): the name or id of the object whose hand-raise we’re checking.
            '''
            pass
        """

    def synth(self, demos, api):
        # no parameters to learn — it’s either raised or not
        pass

    def to_dict(self, expanded: bool = False):
        return {
            'id':         self.constraint.id,
            'constraint': self.ref(),
            'args': {
                'player': self.objID
            }
        }

    
constraintAPI = {
    'HasBallPossession': HasBallPossession,
    'InZone': InZone,
    'MovingTowards': MovingTowards,
    'HasPath': HasPath,
    'DistanceTo': DistanceTo,
    'HeightRelation': HeightRelation,
    # 'OrientedTo': OrientedTo,
    'HorizontalRelation': HorizontalRelation,
    'CloseTo': CloseTo,
    'MakePass': MakePass,
    'Pressure': Pressure,
    'HandRaised': HandRaised
}

targetAPI = {
    'InZone': InZone,
    'DistanceTo': DistanceTo,
    'HeightRelation': HeightRelation,
    # 'OrientedTo': OrientedTo,
    'HorizontalRelation': HorizontalRelation,
    'CloseTo': CloseTo,
}