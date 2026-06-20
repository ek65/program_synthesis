from object import Object
from vector import Vector

class Ball(Object):

    @classmethod
    def from_dict(cls, data: dict) -> 'Ball':

        obj = super().from_dict(data)
        obj.type = 'ball'

        return obj