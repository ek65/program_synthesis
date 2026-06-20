class Expectation:

    def __init__(self):
        pass

    def check(self, timeline) -> bool:
        return False
    
class DidHappen(Expectation):

    def __init__(self, states, consecutive=False):
        super().__init__()
        self.states = []
        self.consecutive = consecutive
        if isinstance(states, list):
            for s in states:
                if isinstance(s, tuple):
                    self.states += [s]
                else:
                    self.states += [(s, True)]
        else:
            if isinstance(states, tuple):
                self.states += [states]
            else:
                self.states += [(states, True)]

    def check(self, timeline) -> bool:

        # expected = [i for i in self.states]
        # for state in timeline:
        #     if self.compare(state, expected[0]):
        #         expected.pop(0)
        #         if len(expected) == 0:
        #             return True
        # return False

        if self.consecutive:
            for i in range(len(timeline) - len(self.states) + 1):
                if self.compare(timeline[i:i+len(self.states)], self.states):
                    return True
            return False
    
        else:
            i, j = 0, 0

            while i < len(timeline) and j < len(self.states):
                if self.compare(timeline[i], self.states[j]):
                    j += 1
                i += 1

            return j == len(self.states)

    
    def compare(self, a, b) -> bool:
        if isinstance(a, list) and isinstance(b, list):
            for ai, bi in zip(a, b):
                if ai[0].id != bi[0].id or ai[1] != bi[1]:
                    return False
            return True
        else:
            return a[0].id == b[0].id and a[1] == b[1]
    
class Eventually(Expectation):

    def __init__(self, before, after):
        super().__init__()
        self.before = []
        self.after = []
        self._add(before, self.before)
        self._add(after, self.after)
    
    def _add(self, states, expected):
        if isinstance(states, list):
            for s in states:
                if isinstance(s, tuple):
                    expected += [s]
                else:
                    expected += [(s, True)]
        else:
            if isinstance(states, tuple):
                expected += [states]
            else:
                expected += [(states, True)]

    def check(self, timeline) -> bool:
        last = len(timeline)

        for i in range(len(timeline) - len(self.before) + 1):
            if self.compare(timeline[i:i+len(self.before)], self.before):
                last = i + len(self.before)

        for i in range(last, len(timeline) - len(self.after) + 1):
            if self.compare(timeline[i:i+len(self.after)], self.after):
                return True
        return False
    
    def compare(self, a, b) -> bool:
        for ai, bi in zip(a, b):
            if ai[0].id != bi[0].id or ai[1] != bi[1] :
                return False
        return True