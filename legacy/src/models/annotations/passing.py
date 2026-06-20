from annotations.annotation import Annotation
from object import Object
from vector import Vector

class Passing(Annotation):
    def __init__(self, id: str, origin: str, receiver: str | Vector):
        super().__init__(id)
        self.origin = origin
        self.receiver = receiver

    def __str__(self) -> str:
        return f"[The {self.origin} passed the ball to {self.receiver} in the scene.]"
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Annotation':
        receiver = None

        if data['type'].lower() == 'pass':
            receiver = data['to']
        else:
            receiver = Vector.from_dict(data['to'])
                       
        return cls(id=data['id'], origin=data['from'], receiver=receiver)