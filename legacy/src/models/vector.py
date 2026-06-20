class Vector:
    def __init__(self, x: float = 0.0, y: float = 0.0) -> None:
        self.x = x
        self.y = y

    def to_dict(self):
        return {
            'x': self.x,
            'y': self.y
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(x=data['x'], y=data['y'])
    
    def __str__(self):
        return f"(x: {self.x}, y: {self.y})"