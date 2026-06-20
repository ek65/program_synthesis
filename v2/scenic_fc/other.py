import json
from nlp_utils import Chat, client
from synth_utils import Demo, Constraint, Condition
from api_utils import API

def type_to_color(type) -> str:
    type = type.lower()
    if type == 'player':
        return
    
class Target(Condition):

    def __init__(self, info, action):
        super().__init__()
        self.action = action
        self.t = action.t

    def construct(self, demos, api):

        constraintAPI = api[API.targetAPI]

        objects = set()
        for d in demos:
            for i in d.scene.objects:
                objects.add(f'{i.type} (ID: {i.id})')
        
        instruction = f"""
        For a moving action we must sample a point in the scene and determine whether it is a valid target destination or not based on a set of conditions. We are trying to construct those conditions.

        You are provided with

        (1) A Finite State Machine (FSM) describing a behavior in the domain of {api[API.domain]} which we are in the process of learning. 
        Tasks are defined within an FSM where each task represents a node with a termination condition (i.e., the condition that marks the task as completed, allowing a state change),
        and edges represent preconditions (i.e., the condition under which the following task is triggered, transitioning from the previous state).

        (2) The ID and description of the MoveTo action of the node/task for which we are trying to learn the condition that the target desintation must satisfy. 

        (3) Image(s) of the scene when such condition is satisfied for visual context and reference.
        (4) A library of APIs to model the physical conditon we are trying to learn.
        (5) A list of the available objects in the phsyical environment.

        Your task is to model condition for the target destination described by (2), using the APIs we provide.
        To do so, you should understand the behavior and context by refering to (1) and (3).
        Then, model the condition with the APIs in (4), with appropiate input parameters utilizing every piece of information available to you including (5) and your domain knowledge in {api[API.domain]}.

        The purpose of the target condition is to determine the "future" destination to move to. 
        Hence, the API(s) you select need to reason about the conditions that need to be satisfied in the future 
        if the coach reaches the target destination. You should only reason about the conditions of the coach. 
        
        Note that APIs return True if the physical constraint is satisfied and False otherwise.
        You may logically compose these to model the condition with logical operators AND, OR, NOT.
        You should only utilize APIs from the provided API library. Do NOT create a new API!
        Use as MINIMUM number of API and logical operators as possible to model the condition.

        To each identified API, assign a unique identification string in a capital letter with a number in the following manner: 'A1', 'A2', and 'A3'.
        If only a single API is used, then do not put any parenthesis and only state 'A1'.
        If more than one API are necessary, then compose them using the allowed logical operators. e.g. '(A1 AND A2) OR NOT(A3)'.

        You need to return your answers as a json in the following format:

        {{
            'logic': str, // composition of constraints with AND, OR, NOT operators, e.g. '(A1 AND A2) OR NOT(A3)' 
            'constraints': [ // a list of constraints, each of whose information is provided as a dictionary
                {{
                    'id': str, // The unique identification string of the API, e.g. 'A1, A2'
                    'api': str, // The name of the API, e.g. 'HasBallPossession'
                    'params': dict // Input parameters to the API. Reference APIs for details on the inputs. 
                }}
            ],
            'reasoning': str // Provide your reasoning for your selection of APIs and their compositions. 
        }}

        NOTE that
        As specified by API documentation, some parameters are required while others are optional. If not specified or strongly infered by do not include optional paramters on your response.
        For instance, if the user did not specify a numerical value for a numerical entry nor suggested a modification to an already learnt parameter, then do NOT include int the response or return None (NO DUMMY VALUES NOR STRINGS), we will learn the numerical value from the demonstration later.
        Also, DO NOT just copy numerical values from different nodes or edges for the parameters.
        When specifying objects as parameters, you must refer to objects' ID from those available in the scene (i.e. listed in (5)).
        """

        edit_instruction = f"""
        This condition was previously synthesized as

        {{
            'logic': {self.logic},
            'constraints': {[c.to_dict() for c in self.constraints]},
            'reasoning': {self.reasoning}
        }}

        Consider carefully whether the parameters require editing or refinement or not given the user specifications including (1), (2) and (3).
        """

        entries = [
            Chat.Entry(role='system', text=instruction),
        ]

        if self.logic:
            entries += [
                Chat.Entry(role='system', text=edit_instruction),
            ]

        entries += [
            Chat.Entry(role='system', text=f'(1) Behavior (FSM):\n\n{self.action.act.to_dict(expanded=False)}'),
            Chat.Entry(role='system', text='(4) Library of APIs:\n\n' + '\n\n'.join([f'[API ID] {i}\n{c.doc()}' for i, c in constraintAPI.items()])),
            Chat.Entry(role='user', text=f'(5) List of objects available in the scene: {", ".join(list(objects))}'),
            Chat.Entry(role='user', text=f'(2) Node ID: {self.action.id}\nDescription of termination condition: {self.action.info}'),
        ]

        for d in demos:
            idx = 1
            if d.id in self.t and isinstance(self.t[d.id], (float, int)):
                entries.append(
                    Chat.Entry(role='user', text=f'(3) Image(s) when the condition in question is satisfied for demonstration {idx}', im=d.video.get_frame_bytes(self.t[d.id]))
                )
                idx += 1

        chat = Chat(client)
        response = json.loads(chat(entries, json=True))

        self.logic = response.get('logic', '')
        self.reasoning = response.get('reasoning', '')

        constraints = [Constraint.from_response(data, api, self) for data in response.get('constraints', [])]

        return self.logic, constraints

    def synth(self, demos: list[Demo] | Demo, api: dict):
        self.logic, self.constraints = self.construct(demos, api)
        for c in self.constraints:
            c.synth(demos, api)

    @classmethod
    def from_dict(cls, data, action, api) -> 'Target':
        info = data.get('info', '')
        logic = data.get('logic', '')
        out = cls(info, action)
        out.logic = logic
        out.constraints = [Constraint.from_dict(data, out, api[API.constraints]) for data in data.get('constraints', [])]
        return out

    def to_dict(self, expanded: bool = False):
        return {
            'info': self.action.info,
            'logic': self.logic,
            'map': list(set([c.id for c in self.constraints])),
            'constraints': [c.to_dict(expanded) for c in self.constraints],
            'reasoning': self.reasoning
        }
    
class PassTarget(Condition):

    def __init__(self, info, action):
        super().__init__()
        self.info = info
        self.action = action
        self.t = action.t
        self.objID = None
        self.through = False
        self.passInfo = ''
        self.logic = None
        self.constraints = []
        self.reasoning = ''

    def construct(self, demos, api, info):

        constraintAPI = api[API.constraints]

        objects = set()
        for d in demos:
            for i in d.scene.objects:
                objects.add(f'{i.type} (ID: {i.id})')
        
        instruction = """
            You are provided with 
            (1) a library of APIs which are helpful for modeling physical constraints, and
            (2) a description of how to perform the through pass.

            Your task is to model the constraint(s) on the target position that the player should 
            pass the ball as described in the description given library of APIs. 

            First, identify the necessary set of APIs to model the described constraint(s).
            It is important to note that the constraint you need to model is solely about where to pass to.

            If there are more than one relevant APIs, you may need to model the constraint by "composing" the APIs with the following operators: AND, OR, NOT, and IF/ELSE.
            To each identified API, assign a unique identification string in capital letters, i.e. 'A', 'B', and 'C'.
            Provide a composition of these APIs, e.g. '(A AND B) OR C' or 'IF A, then B, ELSE C'
            If only a single API is used, then do not put any parenthesis and only state 'A'.

            It is important that the composition of the APIs return a boolean (True/False).
            It should returns True if the constraints described in the given transcription is satisfied; 
            otherwise, it returns False.
            
            Finally, provide the list of the constraints, where each constraint is encoded as a dictionary
            consisting of (1) the unique identification string referencing the API that you used,
            (2) string name of the API, and (3) the input arguments to the API.
            And, provide a reasoning for your composition of constraints -- explain why 
            you composed in such a way. 

            Provide these information as a json in the following format:

            {
                'logic': str, // composition of constraints with AND, OR, NOT, IF/ELSE operators
                'constraints': [
                    {
                        'id': str, // The ID of the constraint to map it to the logical construction
                        'api': str, // The ID of the reference api
                        'params': dict // API-specific parameters. Reference constraint APIs for more info  
                    }
                ],
                'reasoning': str
            }

            You should only utilize APIs from the provided API library. Do NOT create a new API. 
        """

        entries = [
            Chat.Entry(role='system', text=instruction),
            Chat.Entry(role='system', text='-- (1) Constraint APIs --\n\n' + '\n\n'.join([f'[API ID] {i}\n{c.doc()}' for i, c in constraintAPI.items()])),
            Chat.Entry(role='user', text='-- (2) Description of Through Pass --\n\n' + info),
            Chat.Entry(role='user', text=f'Available Objects: {", ".join(list(objects))}')
        ]

        chat = Chat(client)
        response = json.loads(chat(entries, json=True))

        self.logic = response.get('logic', '')
        self.reasoning = response.get('reasoning', '')

        constraints = [Constraint.from_dict(data, api, self) for data in response.get('constraints', [])]

        return self.logic, constraints

    def synth(self, demos: list[Demo] | Demo, api: dict):

        objects = set()
        for d in demos:
            for i in d.scene.objects:
                objects.add(f'{i.type} (ID: {i.id})')

        instruction_prompt = """
            Your are provided with a task description in the context of soccer involving a pass.
            You are tasked with identifying which player to pass to. 

            Your response should be a JSON following the format

            {
                'player': str // The name of the player the coach should pass to. This could be any in the scene.
                'info': str // A detailed description of where to pass to and conditions that must be met by a suitable position to pass to. You may reference other objects in the scene.
        """

        entries = [
            Chat.Entry(role='system', text=instruction_prompt),
            Chat.Entry(role='user', text = "Task description" + self.action.info),
            Chat.Entry(role='user', text=f'Available Objects: {", ".join(list(objects))}')
        ]

        chat = Chat(client)
        response = json.loads(chat(entries, json=True))

        self.objID = response.get('player', None)
        # self.through = response.get('through', False)
        self.passInfo = response.get('info', '')

    @classmethod
    def from_dict(cls, data, action, api) -> 'Target':
        info = data.get('info', '')
        objID = data.get('obj', '')
        through = data.get('through', '')
        out = cls(info, action)
        out.objID = objID
        out.through = through
        return out

    def to_dict(self, expanded: bool = False):
        return {
            'player': self.objID,
            'info': self.info
        }
    
video_info = """
The visual input are a series of top-down keyframes (in chronological order) from a video of the demonstration which you should utilize to reason about the behaviour intended behaviour.
Note that careful frame mapping between nodes/edges and keyframes is very important for accurate behaviour learning (e.g. when we learn how to take an action like shooting the ball, we want to learn from the frame the shot was made so we learn from the most appropiate data).
"""

infer_shot="""
Example 1:
Input: You first want to get pressure of the ball and get a good defensive stance. If the opponent is left footed then push that player to the right. If the player accelerates towards you then attempt to get the ball from them.
Output: {
    'outline': Pressure the opponent with ball posession. If the opponent is left footed force them into the right. If the opponent ever gets to close attempt to get the ball from them.
    'nodes': [
        {
            'id': 0,
            'action': 'MoveTo',
            'info': 'Move close to the opponent with the ball posession while maintaining an appropiate pressure distance.'
            'termination': 'Stop when you are at pressure distance from the opponent with the ball posession.'
            'keyframe': 2 // Frame with the player already at pressure distance from the opponent with ball posession.
        },
        {
            'id': 1,
            'action': 'MoveTo',
            'info': 'Move slightly to the opponent's left side to force them into the right.'
            'termination': 'Stop if the opponent with the ball posession accelerates towards you or is very close to you.'
            'keyframe': 4 // Frame with the player clearly pushing the opponent to one of the sides, different from the just being at pressure distance from them. 
        },
        {
            'id': 2,
            'action': 'GetBallPossession',
            'info': 'Get the ball from the opponent.'
            'termination': 'Stop when you gain the posession of the ball.'
            'keyframe': 9 // Frame where the player just gained the posession of the ball from the opponent.
        }
    ],
    'edges': [
        {
            'id': 3,
            'prev': 0,
            'next': 1,
            'precondition': 'The opponent is left footed.'
            'keyframe': 2 // Frame with the player already at pressure distance from the opponent with ball posession.
        },
        {
            'id': 4,
            'prev': 1,
            'next': 2,
            'precondition': 'The opponent with the ball posession accelerates towards the player or is very close to the player.'
            'keyframe': 8 // Frame where the opponent with ball posession got very close to the player.
        }
    ]
}

Example 2:
Input: First, get pressure of the ball at arm distance from the opponent. If the opponent is right footed, push them into the left. If the player gets too close to you then you attempt to get the ball from them. Remember, if you ever lose the pressure distance or are too far from the opponent, get closer to him.
Output: {
    'outline': Get pressure of the ball. If the opponent is right footed push the opponent to the left. Get the ball from them if they get close or accelerate towards the player. If ever lost pressure distance reposition back to a pressure position.
    'nodes': [
        {
            'id': 0,
            'action': 'MoveTo',
            'info': 'Move close to the opponent with the ball posession while maintaining a distance of ~1.5 meters away from them.'
            'termination': 'Stop when the player is at pressure distance from the opponent with the ball posession.'
            'keyframe': 3 // Frame with the player already at pressure distance from the opponent with ball posession.
        },
        {
            'id': 1,
            'action': 'MoveTo',
            'info': 'Move slighlty to the opponent's right side to force them into the left.'
            'termination': 'Stop if the opponent with the ball posession accelerates towards the player or is very close to the player.'
            'keyframe': 6 // Frame with the player clearly pushing the opponent to one of the sides, different from the just being at pressure distance from them. 
        },
        {
            'id': 2,
            'action': 'GetBallPossession',
            'info': 'Get the ball from the opponent.'
            'termination': 'Stop when the player gains the posession of the ball.'
            'keyframe': 12 // Frame where the player just gained the posession of the ball from the opponent.
        }
    ],
    'edges': [
        {
            'id': 3,
            'prev': 0,
            'next': 1,
            'precondition': 'The opponent is left footed.'
            'keyframe': 2 // Frame with the player already at pressure distance from the opponent with ball posession.
        },
        {
            'id': 4,
            'prev': 1,
            'next': 2,
            'precondition': 'The opponent with the ball posession accelerates towards the player or is very close to player.'
            'keyframe': 8 // Frame where the opponent with ball posession got very close to the player.
        },
        {
            'id': 5,
            'prev': 1,
            'next': 0,
            'precondition': 'If the player lost pressure distance and are too far from the opponent with the ball posession.'
            'keyframe': 19 // Frame where the player gets just far enough right before deciding to reposition themself closer to the opponent with the ball posession.
        }
    ]
}
"""

combine_shot="""
Example:
Input: [
    {
        'id': 'demo_0',
        'outline': Pressure the opponent with ball posession. If the opponent is left footed force them into the right. If the opponent ever gets to close attempt to get the ball from them.
        'nodes': [
            {
                'id': 0,
                'action': 'MoveTo',
                'info': 'Move close to the opponent with the ball posession while maintaining an appropiate pressure distance.'
                'termination': 'Stop when you are at pressure distance from the opponent with the ball posession.'
                't': 2
            },
            {
                'id': 1,
                'action': 'MoveTo',
                'info': 'Move slighlty to the opponent's left side to force them into the right.'
                'termination': 'Stop if the opponent with the ball posession accelerates towards you or is very close to you.'
                't': 4
            },
            {
                'id': 2,
                'action': 'GetBallPossession',
                'info': 'Get the ball from the opponent.'
                'termination': 'Stop when you gain the posession of the ball.'
                't': 9
            }
        ],
        'edges': [
            {
                'id': 3,
                'prev': 0,
                'next': 1,
                'precondition': 'The opponent is left footed.'
                't': 2
            },
            {
                'id': 4,
                'prev': 1,
                'next': 2,
                'precondition': 'The opponent with the ball posession accelerates towards the player or is very close to the player.'
                't': 8
            }
        ]
    },
    {
        'id': 'demo_1',
        'outline': Get pressure of the ball. If the opponent is right footed push the opponent to the left. Get the ball from them if they get close or accelerate towards the player. If ever lost pressure distance reposition back to a pressure position.
        'nodes': [
            {
                'id': 0,
                'action': 'MoveTo',
                'info': 'Move close to the opponent with the ball posession while maintaining a distance of ~1.5 meters away from them.'
                'termination': 'Stop when the player is at pressure distance from the opponent with the ball posession.'
                't': 3
            {
                'id': 1,
                'action': 'MoveTo',
                'info': 'Move slighlty to the opponent's right side to force them into the left.'
                'termination': 'Stop if the opponent with the ball posession accelerates towards the player or is very close to the player.'
                't': 6
            },
            {
                'id': 2,
                'action': 'GetBallPossession',
                'info': 'Get the ball from the opponent.'
                'termination': 'Stop when the player gains the posession of the ball.'
                't': 12
            }
        ],
        'edges': [
            {
                'id': 3,
                'prev': 0,
                'next': 1,
                'precondition': 'The opponent is right footed.'
                't': 3
            },
            {
                'id': 4,
                'prev': 1,
                'next': 2,
                'precondition': 'The opponent with the ball posession accelerates towards the player or is very close to player.'
                't': 8
            },
            {
                'id': 5,
                'prev': 1,
                'next': 0,
                'precondition': 'If the player lost pressure distance and are too far from the opponent with the ball posession.'
                't': 19
            }
        ]
    }
]
Output: {
    {
        'outline': Get pressure of the ball. If the opponent is right footed push the opponent to the left, otherwise, if left footed push the opponen to the right. Get the ball from them if they get close or accelerate towards the player. If the player ever lost pressure distance, then reposition back to a pressure position.
        'nodes': [
            {
                'id': 0,
                'action': 'MoveTo',
                'info': 'Move close to the opponent with the ball posession while maintaining a distance of ~1.5 meters away from them.'
                'termination': 'Stop when the player is at pressure distance from the opponent with the ball posession.'
                't': {
                    'demo_0': 2,
                    'demo_1': 3
                }
            {
                'id': 1,
                'action': 'MoveTo',
                'info': 'Move slighlty to the opponent's right side to force them into the left.'
                'termination': 'Stop if the opponent with the ball posession accelerates towards the player or is very close to the player.'
                't': {
                    'demo_1': 6
                }
            },
            {
                'id': 2,
                'action': 'MoveTo',
                'info': 'Move slighlty to the opponent's left side to force them into the right.'
                'termination': 'Stop if the opponent with the ball posession accelerates towards the player or is very close to the player.'
                't': {
                    'demo_0': 4
                }
            },
            {
                'id': 3,
                'action': 'GetBallPossession',
                'info': 'Get the ball from the opponent.'
                'termination': 'Stop when the player gains the posession of the ball.'
                't': {
                    'demo_0': 9,
                    'demo_1': 12
                }
            }
        ],
        'edges': [
            {
                'id': 4,
                'prev': 0,
                'next': 1,
                'precondition': 'The opponent is left footed.'
                't': {
                    'demo_0': 2
                }
            },
            {
                'id': 5,
                'prev': 0,
                'next': 2,
                'precondition': 'The opponent is right footed.'
                't': {
                    'demo_1': 3
                }
            },
            {
                'id': 6,
                'prev': 1,
                'next': 3,
                'precondition': 'The opponent with the ball posession accelerates towards the player or is very close to player.'
                't': {
                    'demo_0': 8
                }
            },
            {
                'id': 7,
                'prev': 2,
                'next': 3,
                'precondition': 'The opponent with the ball posession accelerates towards the player or is very close to player.'
                't': {
                    'demo_1': 8
                }
            },
            {
                'id': 8,
                'prev': 1,
                'next': 0,
                'precondition': 'If the player lost pressure distance and are too far from the opponent with the ball posession.'
                't': {
                    'demo_1': 19
                }
            },
            {
                'id': 9,
                'prev': 2,
                'next': 0,
                'precondition': 'If the player lost pressure distance and are too far from the opponent with the ball posession.'
                't': {
                    'demo_1': 19
                }
            }
        ]
    }
}
"""