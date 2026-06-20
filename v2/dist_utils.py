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
    
    @classmethod
    def from_dict(self, data) -> 'Normal':
        return Normal(
            avg=float(data.get('avg', 2)),
            std=float(data.get('std', 1))
        )

    def to_dict(self, expanded: bool = False):
        return {
            'avg': self.avg,
            'std': self.std
        }