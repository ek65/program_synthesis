import numpy as np

class Dist:

    def __init__(self):
        pass

class Normal(Dist):

    def __init__(self, avg, std):
        super().__init__()
        self.avg = avg
        self.std = std

    @classmethod
    def fromList(cls, list) -> 'Normal':
        return cls(np.mean(list), np.std(list))

    def toDict(self):
        return {
            'avg': self.avg,
            'std': self.std
        }


        
    