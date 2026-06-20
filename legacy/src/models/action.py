import json
from chat import *

class Act:

    def __init__(self, actions=[]):
        self.actions = actions

    def do(self, actions):
        if isinstance(actions, list):
            self.actions += actions
        else:
            self.actions += [actions]

    def toDict(self):
        return { 'actions': [a.toDict() for a in self.actions] }

    def export(self):    
        return json.dumps(self.toDict(), indent=4)
    
class Action:

    def __init__(self, id, task):
        self.id = id
        self.task = task

    def learn(self, demoMap, t=None):
        pass

    def toDict(self):
        pass

    @classmethod
    def fromTask(cls, tasks, actionsAPI, prompt=''):

        if not prompt:
            prompt = """
                You are an expert in the domain of soccer. Given a list of tasks descriptions for a training scenario,
                your task is to identify what type of action the tasks involve. This is a step towards learning the intended behavior for such scenario.

                The following are available actions:
                - MoveTo(Vector)
                - PassTo(Teammate)
                - ThroughPass(Vector)
                - Shoot()
                - Wait()

                Later, following the task specifications, sets of constraint to sample valid arguments to the actions will be identified such that the tasks are satisfied.
                Your response should be a list of tasks formatted as a json: {'actions': [{'id': str, task_id: int}]}, where the id is the name of the action, not including the arguments and the task_id is the id of the task that motivated that particular action.

                For instance, if the task specification were to be "
                Task 1 (id: 1): 
                    Objective: Move toward the goal.
                Task 2 (id: 2):
                    Objective: Shoot the ball.
                "
                then you would return {'actions': [{'id': 'MoveTo', task_id: 1}, {'id': 'Shoot', task_id: 2}]}.

                If the task specification was "
                Task 1 (id: 1): 
                    Objective: Go ahead to pass the ball.
                Task 2 (id: 2):
                    Objective: Shoot the ball.
                    Condition: Receives the ball.
                "
                then you would return {'actions': [{'id': 'MoveTo', task_id: 1}, {'id': 'PassTo', task_id: 1}, {'id': 'Wait', task_id: 2}, {'id': 'Shoot', task_id: 2}]}.

                Note that you could choose more than one action per task, but these will be perfomed sequentially and not at the same time, so order matters.
                Note that in the example, passing the ball is not directly specified as a task but it is implied that it should be done inmmediately after moving since that is the goal of the action, which is why passTo is included after moveTo.
                Note that if the action is a Wait(), the task_id should be the id of the next task that should be performed after waiting.
                Also, Wait should be chosen if there's something to wait for after the inmediate previous task was satisfied, meaning that there should be little overlap between a previous task and the following wait function, for isntance, if the rpevious task was to move to somewhere under some condition, the following wait function should not try to wait for that condition since the preivous task already satisfied that condition.
            """

        identification = json.loads(chat([
            ChatEntry('system', prompt),
            ChatEntry('user', '\n'.join(f'Task {i}: ' + str(t) for i, t in enumerate(tasks)))
        ], json=True))

        actions = identification['actions']

        result = []
        for a in actions:

            id = a['id']
            taskID = a['task_id']
            task = {t.id: t for t in tasks}.get(taskID, None)

            if id in actionsAPI:
                result += [actionsAPI[id](id, task)]
            else:
                result += [cls(id, task)]

        return result