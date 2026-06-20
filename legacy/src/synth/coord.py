import json
from chat import *
from constraint import Constraint

class Coord:

    def __init__(self, action, scenes):
        self.task = action.task
        self.scenes = scenes
        self.constraints = []
        self.identifiers = []
        self.logic = None

    def construct(self, constraintAPI, prompt=''):
        if not prompt:

            objList = ', '.join([obj.id + '(' + obj.type + ')' for obj in self.scenes[0].objects])
            apiList = '\n'.join([api.doc() for api in constraintAPI.values()])
            format = "{'logic': str, 'constraints': [{'id': str, 'api': str, params: dict}], 'reasoning': str}"
            example = "{'logic': 'A AND B', 'constraints': [{'id': 'A', 'api': 'DistanceTo', params: {'ref': 'player1'} }, {'id': 'B', 'api': 'InZone', params: {'zone': None} }]}"

            prompt = f"""
                You are given a soccer's coach explanation to how the player should position him/herself on the field under a specifc scenario. 
                Your task is to construct a logical expression of constraint with AND/OR/IF operators. Your 
                Choose constraints from the options provided and logically combine them.
                The output should be a json with format {format} where the constraints are a list of constraint objects with id mapping the label in the logical expression to the specific constraint, the api and the params, which is a dictionary with relevant arguments to the constraint that could be inferred from the task description.
                Include a reasoning of why each constraint.
                
                Here's a list of the available constraints:
                    {apiList}

                The scene has the following list of available objects [{objList}].

                For instance, if the task specifies that a player should be at a certain distance from a player labeled 'player1' and in some zone then you would return {example}.
                Note that for InZone, despite having parameters to fill in they were not specified in the task description so they aren't filled out in the response; the only varialbes that should be filled in here are ones that give a concrete values or object reference.
                Also note that the constraints that should be used here are only constraints that relate to the to the position; for example, HasBallPossession would not be an API to be used here.
            """

        entries = [
            ChatEntry(role='system', content=prompt),
            ChatEntry(role='user', content=str(self.task)),
        ]

        output = json.loads(chat(entries, json=True))

        print(output)

        print('reasoning', output['reasoning'])
        logic = output['logic']
        constraints = output['constraints']

        return logic, constraints
    
    def learn(self, constraintAPI, prompt=''):

        _logic, _constraints = self.construct(constraintAPI, prompt)

        self.logic = _logic

        for c in _constraints:

            id = c.get('id', None)
            _api = c.get('api', None)
            params = c.get('params', None)

            if id and _api and params:
                api = constraintAPI.get(_api, Constraint)(params)
                api.learn(self.scenes)
                c['params'] = vars(api)

                self.identifiers += [id]
                self.constraints += [api]

    def toDict(self):
        return {
            'logical': self.logic,
            'identifiers': self.identifiers,
            'args': {i: c.toDict() for i, c in zip(self.identifiers, self.constraints)}
        }