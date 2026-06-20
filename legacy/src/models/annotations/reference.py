from annotations.annotation import Annotation
from object import Object


class Reference(Annotation):
    def __init__(self, id: str, obj: Object):
        super().__init__(id)
        self.object = obj

    def __str__(self) -> str:
        return f"[The expert referenced '{self.object}' in the scene.]"
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Annotation':
        obj = cls(id=data['id'], obj=data['obj'])
        return obj