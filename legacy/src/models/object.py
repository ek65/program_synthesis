from vector import Vector

class Object:

    def __init__(self, id, type, position=Vector(0, 0), label='', color=''):

        self.id = id

        if label:
            self.label = label
        else:
            self.label = id

        self.type = type

        self.position = position
        self._position = []

        self.velocity = Vector()
        self._velocity = []

        # self.orientation = ?
        # self._orientation = []

        self.color = color

    def at(self, position: Vector) -> 'Object':
        self.position = position
        # self.initial_position = position
        return self
    
    def set_time(self, t=0.0, step=0.2):

        if t is None:
            t = 0.0

        idx = int(t // step)

        if idx < len(self._position):
            self.position = self._position[idx]

        if idx < len(self._velocity):
            self.velocity = self._velocity[idx]
    
    @classmethod
    def from_dict(cls, data, objectsAPI=None):

        if objectsAPI:
            type = data.get('type', '').lower()
            if type in objectsAPI:
                return objectsAPI[type].from_dict(data)
        
        obj = cls(id=data['id'], type='unknown')
        obj._position = [Vector.from_dict(i) for i in data.get('position', [])]
        obj._velocity = [Vector.from_dict(i) for i in data.get('velocity', [])]
        obj._orientation = [i for i in data.get('orientation', []) if isinstance(i, float)]
        obj.position = obj._position[-1]
        return obj
    
    def extend(self, obj):
        self._position += obj._position
        self._velocity += obj._velocity