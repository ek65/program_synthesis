from object import Object

class Bound(Object):

    @classmethod
    def from_dict(cls, data: dict) -> 'Bound':

        obj = super().from_dict(data)
        obj.type = 'bound'

        return obj
