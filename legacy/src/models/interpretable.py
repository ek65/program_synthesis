class Interpretable:

    def __init__(self, language):
        self.language = language

    def __call__(self) -> str:
        return self.language