import json
from chat import *

class Task:

    def __init__(self, id, what, how, until, when, sources):

        self.id = id
        self.what = what
        self.how = how
        self.until = until
        self.when = when

        self.sources = sources

    def sourceScenesIn(self, demoMap, timeMap=None):

        if timeMap is None:
            timeMap = {}

        scenes = []
        times = []

        print(self.sources)

        for i in self.sources:

            # TODO: Do parsing properly
            s = demoMap.get(i, None).get('a', None)
            t = timeMap.get(i, 0.0)
            if s:
                scenes += [s]
                times += [t]

        print(scenes, times)
        return scenes, times


    @classmethod
    def fromInterpretable(cls, interpretable, prompt='', firstID=0) -> list['Task']:
        if not prompt:
            prompt = """
                You are an expert in the domain of soccer. You are provided with narrated explanations for multiple demonstrations from coach for the same scenario.
                You are tasked with combining the narrated explanations into a list of subtasks. Your response should be a json with format {'tasks': [{'objective': str, 'control': str, 'termination': str, 'condition': str, 'sources': [str]}]}
                Note that only the tasks that should be carried out by the coach should be included, although these tasks could relate to other players and or objects in the scene.
                Tasks should be in order as they should be performed. Note that for every tasks there is: (1) an objective, the task specification; (2) the control, how to do perform the task; (3) the termination, the conditions under which such task should be interrupted; (4) and a condition, the conditions under which such task gets triggered.
                Note that (2), (3) and (4) could be empty or None if not specified by the coach. If no condition or termination conditions was specified or is implied maybe by domain logic, set to empty or None, the assumption is that task will happen sequentially then. In addition to the task specification provide the (5) source, i.e. the demonstration you got such task from, which could and should be a list if there are multiple sources.
                For instance, if the coach said in the first demonstration 'pass the ball and move towards the goal' and in the second demonstration 'move towards the goal after passing the ball', there should be two tasks, moving and passing the ball, where moving has sources [1, 2] while passing has sources [1, 2]. Single numbers should be strings.
                You should rationale about the narrated explanations and conjoint them smartly with domain knowledge. You are allowed to remove or modify tasks to combine concepts from different demonstrations or ignore them if redundant or if the coach might have made a mistake, or if a task is already being accomplished by another better described one in another demonstration.
            """
        
        tasks = json.loads(chat([
            ChatEntry('system', content=prompt),
            ChatEntry('user', content=interpretable())
        ], json=True)).get('tasks', [])

        id = firstID
        output = []
        for t in tasks:
            what = t.get('objective', '')
            how = t.get('control', '')
            until = t.get('termination', '')
            when = t.get('condition', '')
            sources = t.get('sources', '')

            output += [cls(id, what, how, until, when, sources)]
            id += 1

        return output
    
    def __str__(self):
        return f'Task ID: {self.id}\nObjective (what): {self.what}\nControl (how): {self.how}\nTermination (until): {self.until}\nCondition (when): {self.when}'