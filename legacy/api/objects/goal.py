from object import Object
from api.objects.team import Team
from vector import Vector

class Goal(Object):

    @classmethod
    def from_dict(cls, data: dict) -> 'Goal':

        obj = super().from_dict(data)
        obj.type = 'goal'

        return obj