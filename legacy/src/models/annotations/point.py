from annotations.annotation import Annotation
from vector import Vector
from object import Object

class PointReference(Annotation):
    def __init__(self, id: str, point: Vector):
        super().__init__(id)
        self.point = point

    def __str__(self) -> str:
        return f"[The expert referenced the point at {self.point} in the scene.]"
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Annotation':
        point = Vector.from_dict(data['point'])
        obj = cls(id=data['id'], point=point)
        return obj