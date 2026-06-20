from enum import Enum

class API(Enum):
    domain = 'domain'
    actions = 'actions'
    constraints = 'constraints'
    color_map = 'color_map'
    video_info = 'video_info'
    default_obj = 'default_obj'
    infer_shot = 'infer_shot'
    combine_shot = 'combine_shot'
    targetAPI = 'targetAPI'

    def __eq__(self, value):
        return self.value == value.value
    
    def __hash__(self):
        return hash(self.value)

class ActionAPI:

    def __init__(self, action):
        self.action = action

    def synth(self, demos, api):
        raise NotImplementedError
    
    def to_dict(self, expanded: bool = False):
        raise NotImplementedError
    
    @classmethod
    def from_dict(cls, data, action, api) -> 'ActionAPI':
        return cls(action)
    
    @classmethod
    def ref(cls) -> str:
        return 'unknown'
    
class ConstraintAPI:
    
    def __init__(self, constraint):
        self.constraint = constraint
        self.t = constraint.condition.t

    def synth(self, demos, api):
        # print(self)
        raise NotImplementedError(f"Synth not implemented for this constraint API: {self.constraint.condition.info}")
    
    @classmethod
    def from_dict(cls, args, constraint) -> 'ConstraintAPI':
        return cls(constraint)
    
    def to_dict(self, expanded: bool = False):
        raise NotImplementedError
    
    @classmethod
    def ref(cls) -> str:
        return 'unknown'
    
    @classmethod
    def doc(cls) -> str:
        raise NotImplementedError