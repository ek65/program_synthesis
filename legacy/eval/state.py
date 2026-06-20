class State:

    def __init__(self, label):
        self.id = ''
        self.label = label
        self.active = False

    def check(self, scene, objects, t) -> bool:
        return False

    def __repr__(self) -> str:
        return self.label

class HasBallPosession(State):

    def __init__(self, object):
        super().__init__(f'{object.id} has ball posession')
        self.id = f'HasBallPosession:{object.id}'
        self.object = object

    def check(self, scene, objects, t) -> bool:
        return objects[self.object.id]._ballPossession[t]
    
class PlayerAheadOfOpponents(State):

    def __init__(self, object):
        super().__init__(f'{object.id} is ahead of opponents')
        self.id = f'PlayerAheadOfOpponents:{object.id}'
        self.object = object

    def check(self, scene, objects, t) -> bool:
        opponents = [objects['opponent_A'], objects['opponent_B'], objects['opponent_C'], objects['opponent_D']]
        for opponent in opponents:
            if objects[self.object.id]._position[t].y < opponent._position[t].y:
                return False
        return True
    
class MovedToBox(State):

    def __init__(self, object, x_bounds, y_bounds):
        super().__init__(f'{object.id} moved to bounds within {x_bounds, y_bounds}')
        self.id = f'MovedToBox:{object.id}{x_bounds[0]}{x_bounds[1]},{y_bounds[0]}{y_bounds[1]}'
        self.object = object
        self.min_x, self.max_x = min(x_bounds), max(x_bounds)
        self.min_y, self.max_y = min(y_bounds), max(y_bounds)

    def check(self, scene, objects, t) -> bool:
        location = objects[self.object.id]._position[t]
        if location.x < self.max_x and location.x > self.min_x:
            if location.y < self.max_y and location.y > self.min_y:
                return True
        return False