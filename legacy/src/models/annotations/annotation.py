class Annotation:
    def __init__(self, id: str):
        self.id = id

    def text(self) -> str:
        return ""

    def __str__(self) -> str:
        raise Exception("Unknown annotation or undefined 'text' method.")
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Annotation':
        from annotations.ann_registry import REGISTRY
        type = data.get('type', '')
        if type in REGISTRY:
            return REGISTRY[type].from_dict(data)
        obj = cls(id=data['id'])
        return obj