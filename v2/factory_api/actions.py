from api_utils import ActionAPI
from scenic_fc.other import Target

# MARK: MoveTo

class MoveTo(ActionAPI):
    def __init__(self, action):
        super().__init__(action)
        self.target = Target(action.info, action)
    
    @classmethod
    def doc(cls) -> str:
        return "This MoveTo API defines an action to move to a particular destination"

    def synth(self, demos, api):
        self.target.synth(demos, api)
        self.action.termination.synth(demos, api)

    @classmethod
    def ref(cls) -> str:
        return 'move_to'

    def to_dict(self):
        return {
            'target': self.target.to_dict()
        }

# MARK: PickUp
class PickUp(ActionAPI):
    def __init__(self, action):
        super().__init__(action)

    @classmethod
    def doc(cls) -> str:
        return "This PickUp API defines an action of picking up an object"

    def synth(self, demos, api):
        # no parameters to infer for PickUp
        pass

    @classmethod
    def ref(cls) -> str:
        return 'pick_up'

    def to_dict(self):
        return {}
    
# MARK: Drop

class Drop(ActionAPI):

    def __init__(self, action):
        super().__init__(action)
    
    @classmethod
    def doc(cls) -> str:
        return "This Drop API defines an action of dropping an object"

    def synth(self, demos, api):
        raise NotImplementedError

    @classmethod
    def ref(cls) -> str:
        return 'drop'

    def to_dict(self):
        return {

        }
    
# MARK: Wait
    
class Idle(ActionAPI):

    def __init__(self, action):
        super().__init__(action)

    @classmethod
    def doc(cls) -> str:
        return "This Wait API defines an action to wait. For example, this API can be used when you are waiting to receive a ball from another player, or a certain event to occur. "


    def synth(self, demos, api):
        raise NotImplementedError

    @classmethod
    def ref(cls) -> str:
        return 'wait'

    def to_dict(self):
        return {

        }

# MARK: PutDown
class PutDown(ActionAPI):
    def __init__(self, action):
        super().__init__(action)
        self.position = action.position

    @classmethod
    def doc(cls) -> str:
        return "This PutDown API defines an action of putting down an object"

    def synth(self, demos, api):
        pass

    @classmethod
    def ref(cls) -> str:
        return 'put_down'

    def to_dict(self):
        return {'position': self.position}

# MARK: Packaging (Robot)
class Packaging(ActionAPI):
    def __init__(self, action):
        super().__init__(action)

    @classmethod
    def doc(cls) -> str:
        return "This Packaging API defines an action of packaging an object"

    def synth(self, demos, api):
        pass

    @classmethod
    def ref(cls) -> str:
        return 'packaging'

    def to_dict(self):
        return {}

# MARK: RaiseHand (Robot)
class RaiseHand(ActionAPI):
    def __init__(self, action):
        super().__init__(action)

    @classmethod
    def doc(cls) -> str:
        return "This RaiseHand API defines an action of raising a hand"

    def synth(self, demos, api):
        pass

    @classmethod
    def ref(cls) -> str:
        return 'raise_hand'

    def to_dict(self):
        return {}

actionAPI = {
    'MoveTo': MoveTo,
    'PickUp': PickUp,
    'Drop': Drop,
    'Idle': Idle,
    'PutDown': PutDown,
    'Packaging': Packaging,
    'RaiseHand': RaiseHand,
}