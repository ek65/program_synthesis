class Constraint:

    def __init__(self, args):
        self.args = args

    @classmethod
    def doc(cls):
        raise Exception('No logic for function doc().')

    def learn(self, scene):
        raise Exception('No logic for function learn().')
    
    def __call__(self, scene):
        raise Exception('No logic for function __call__().')
    
    def toDict(self):
        return {}