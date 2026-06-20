from object import Object
from vector import Vector

class Player(Object):

    def __init__(self, id, type, team=""):
        super().__init__(id, type)
        self.team = team

    @classmethod
    def from_dict(cls, data):

        obj = super().from_dict(data)
        obj.type = 'player'
        obj._ballPossession = [i for i in data['ballPossession']]

        return obj

# class Player(Object):
#     def __init__(self, id: str, label: str = '', team: str = 'None'):
#         super().__init__(id, label, team)
#         # team.players.append(self)
#         self.footPreference = 'right'
#         self.ballPossession = False
#         self._ballPossession = []
    
# class Coach(Player):
#     def __init__(self, id: str, label: str = '', team: str = 'blue'):
#         super().__init__(id, label, team)
#         # team.players.append(self)
#         self.footPreference = 'right'
#         self.ballPossession = False
#         self._ballPossession = []

#     @classmethod
#     def from_dict(cls, data: dict):
#         team = "blue"
#         obj = cls(id=data['id'], team=team)
#         obj._ballPossession = [i for i in data['ballPossession']]
#         obj._position = [Vector.from_dict(i) for i in data['position']]
#         obj._velocity = [Vector.from_dict(i) for i in data['velocity']]
#         # Gets starting position
#         obj.position = obj._position[0]
#         return obj
    
# class Teammate(Object):
#     def __init__(self, id: str, label: str = '', team: str = 'None'):
#         super().__init__(id, label, team)
#         # team.players.append(self)
#         self.footPreference = 'right'
#         self.ballPossession = False
#         self._ballPossession = []

#     @classmethod
#     def from_dict(cls, data: dict):
#         team = "blue"
#         obj = cls(id=data['id'], team=team)
#         obj._ballPossession = [i for i in data['ballPossession']]
#         obj._position = [Vector.from_dict(i) for i in data['position']]
#         obj._velocity = [Vector.from_dict(i) for i in data['velocity']]
#         # Gets starting position
#         obj.position = obj._position[0]
#         return obj
    
# class Opponent(Object):
#     def __init__(self, id: str, label: str = '', team: str = 'None'):
#         super().__init__(id, label, team)
#         # team.players.append(self)
#         self.footPreference = 'right'
#         self.ballPossession = False
#         self._ballPossession = []

#     @classmethod
#     def from_dict(cls, data: dict):
#         team = "red"
#         obj = cls(id=data['id'], team=team)
#         obj._ballPossession = [i for i in data['ballPossession']]
#         obj._position = [Vector.from_dict(i) for i in data['position']]
#         obj._velocity = [Vector.from_dict(i) for i in data['velocity']]
#         # Gets starting position
#         obj.position = obj._position[0]
#         return obj

# # Target position for coach to move to
# class Target(Object):
#     def __init__(self, label, location=Vector(0, 0)):
#         super().__init__(label, 'target', location)