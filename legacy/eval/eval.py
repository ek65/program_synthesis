class Eval:

    def __init__(self, scenes):
        self.scenes = scenes
        self.timeline = []
        self.states = []
        self.expected = []

    def sub(self, state):
        if isinstance(state, list):
            self.states += state
        else:
            self.states += [state]

    def verify(self, expected):
        if isinstance(expected, list):
            self.expected += expected
        else:
            self.expected += [expected]

    def run(self) -> float:
        
        self.timeline = []
        for idx, demo in self.scenes.items():
            objects = {obj.id: obj for obj in demo.objects}
            max_t = len(demo.objects[0]._position)
            for t in range(max_t):
                for i in self.states:
                    if i.check(demo, objects, t):
                        if not i.active:
                            i.active = True
                            self.timeline += [(i, True)]
                    elif i.active:
                        i.active = False
                        self.timeline += [(i, False)]
        
        if len(self.expected) == 0:
            return 0

        verified = [1 if exp.check(self.timeline) else 0 for exp in self.expected]
        print(verified)
        score = sum(verified) / len(self.expected)

        print(f'Score: {sum(verified)}/{len(self.expected)}')
        return score