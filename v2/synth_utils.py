import copy
import json
import math
from enum import Enum
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import networkx as nx
from tqdm import tqdm

import ipywidgets as widgets
from IPython.display import display, clear_output

from nlp_utils import Chat, client, Video
from api_utils import ActionAPI, ConstraintAPI, API

class Vector2D:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

    @classmethod
    def from_dict(cls, dict):
        return cls(dict.get('x', 0.0), dict.get('y', 0.0))
    
    def dist(self, other):
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)
    
    def to_dict(self, expanded: bool = False) -> dict:
        return {
            'x': self.x,
            'y': self.y
        }
    
class Object:
    def __init__(self, id: str, type: str = '', label: str = '', color: str = '', fig = 'o', location: list[Vector2D] = [], orientation: list[Vector2D] = []):

        self.id = id
        self.type = type
        self.label = label
        self.color = color
        self.fig = fig
        
        self.dt = 0.02 # TODO: Do not hardcode
        
        self.location = location
        self.orientation = orientation

    def __getitem__(self, key):
        if isinstance(key, int):
            key = float(key)
        if isinstance(key, float):
            out = copy.copy(self)
            out.location = out.location[min(int(key / self.dt), len(out.location) - 1)]
            print(self.id, 'location:', out.location)
            # out.orientation = out.orientation[min(int(key / self.dt), len(out.orientation) - 1)] # TODO: Add orientation
            return out

class Scene:
    def __init__(self, objects: list[Object] = [], dt: float = 0.0):
        self.objects = objects
        self.dt = dt

    def __getitem__(self, key):
        if isinstance(key, str):
            key_lower = key.lower()
            return [obj for obj in self.objects if key_lower in obj.id.lower()]

class Demo: # a single narrated demonstration
    def __init__(self, id: str, scene: Scene, language: str, video: Video | None):
        self.id = id
        self.scene = scene
        self.language = language
        self.video = video
        self.pause_times = []

    @classmethod
    def find_by_id(cls, id, demos): # this is helpful in case not all demos have the timing
        demos = {d.id: d for d in demos}
        return demos.get(id, None)
    
class Condition:
    def __init__(self):
        self.t = None
        self.logic = None
        self.constraints = []
        self.reasoning = ''
        pass

    def synth(self, demos: list[Demo], api: dict):
        raise NotImplemented

class Termination(Condition):
    def __init__(self, info, action):
        super().__init__()
        self.info = info
        self.action = action
        self.t = action.t

    def construct(self, demos, api):

        constraintAPI = api[API.constraints]

        objects = set()
        for d in demos:
            for i in d.scene.objects:
                objects.add(f'{i.type} (ID: {i.id})')
        
        instruction = f"""
        You are provided with

        (1) A Finite State Machine (FSM) describing a behavior in the domain of {api[API.domain]} which we are in the process of learning. 
        Tasks are defined within an FSM where each task represents a node with a termination condition (i.e., the condition that marks the task as completed, allowing a state change),
        and edges represent preconditions (i.e., the condition under which the following task is triggered, transitioning from the previous state).
        (2) The ID and description of the termination condition of the node/task for which we are trying to learn the termination condition.
        (3) Image(s) of the scene when the termination condition is satisfied for visual context and reference.
        (4) A library of APIs to model the physical conditon we are trying to learn.
        (5) A list of the available objects in the phsyical environment.

        Your task is to model the termination condition described by (2), using the APIs we provide.
        To do so, you should understand the behavior and context by refering to (1) and (3).
        Then, model the termination condition with the APIs in (4), with appropiate input parameters utilizing every piece of information available to you including (5) and your domain knowledge in {api[API.domain]}.

        Note that APIs return True if the physical constraint is satisfied and False otherwise.
        You may logically compose these to model the termination condition with logical operators AND, OR, NOT.
        You should only utilize APIs from the provided API library. Do NOT create a new API!
        Use as minimum number of APIs and logical operators as possible to model the termination condition.

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

        # print(self.action.act.to_dict(expanded=False))

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
            Chat.Entry(role='user', text=f'(2) Node ID: {self.action.id}\nDescription of termination condition: {self.info}'),
        ]

        for d in demos:
            idx = 1
            if d.id in self.t and isinstance(self.t[d.id], int):
                entries.append(
                    Chat.Entry(role='user', text=f'(3) Image(s) when the condition in question is satisfied for demonstration {idx}', im=d.video.get_frame_bytes(self.t[d.id])) ### potential issue these are sometime key frames but should be seconds!
                )
                idx += 1

        chat = Chat(client)
        response_text = chat(entries, json=True)
        print("=== Gemini Raw Response Construct ===")
        print(repr(response_text))
        # response = json.loads(chat(entries, json=True))
        cleaned = response_text.replace("```json", "").replace("```", "").strip()
        # Fix np.float64 artifacts
        import re
        cleaned = re.sub(r'"np\.float64\(([\d.]+)\)"', r'\1', cleaned)
        response = json.loads(cleaned)

        # print("Termination Class construct()\n")
        # print(json.dumps(response, indent=4))

        self.logic = response.get('logic', '')
        self.reasoning = response.get('reasoning', '')
        constraints = [Constraint.from_response(data, api, self) for data in response.get('constraints', [])]
        return self.logic, constraints

    def synth(self, demos: list[Demo], api: dict):
        self.logic, self.constraints = self.construct(demos, api)
        for c in self.constraints:
            c.api.synth(demos, api)

    @classmethod
    def from_dict(cls, data, action, api) -> 'Termination':
        info = data.get('info', '')
        logic = data.get('logic', '')
        out = cls(info, action)
        out.logic = logic
        out.constraints = [Constraint.from_dict(data, out, api[API.constraints]) for data in data.get('constraints', [])]
        return out

    def to_dict(self, expanded: bool = False):

        if expanded:
            if self.logic:
                return {
                    'info': self.info,
                    'logic': self.logic,
                    'map': list(set([c.id for c in self.constraints])),
                    'constraints': [c.to_dict(expanded) for c in self.constraints],
                    'reasoning': self.reasoning
                }
            else:
                return {
                    'info': self.info,
                    'logic': '',
                }
        else:
            return {
                'info': self.info
            }

class Precondition(Condition):
    def __init__(self, info, transition):
        super().__init__()
        self.info = info
        self.transition = transition
        self.t = transition.t

    def construct(self, demos, api):

        constraintAPI = api[API.constraints]

        objects = set()
        for d in demos:
            for i in d.scene.objects:
                objects.add(f'{i.type} (ID: {i.id})')
        
        instruction = """
        You are provided with

        (1) A Finite State Machine (FSM) describing a behavior in the domain of {api[API.domain]} which we are in the process of learning. 
        Tasks are defined within an FSM where each task represents a node with a termination condition (i.e., the condition that marks the task as completed, allowing a state change),
        and edges represent preconditions (i.e., the condition under which the following task is triggered, transitioning from the previous state).

        (2) The ID and description of the precondition of the edge/transition for which we are trying to learn the precondition.

        (3) Image(s) of the scene when the precondition is satisfied for visual context and reference.
        (4) A library of APIs to model the physical conditon we are trying to learn.
        (5) A list of the available objects in the phsyical environment.

        Your task is to model the precondition described by (2), using the APIs we provide.
        To do so, you should understand the behavior and context by refering to (1) and (3).
        Then, model the precondition with the APIs in (4), with appropiate input parameters utilizing every piece of information available to you including (5) and your domain knowledge in {api[API.domain]}.

        Note that APIs return True if the physical constraint is satisfied and False otherwise.
        You may logically compose these to model the precondition with logical operators AND, OR, NOT.
        You should only utilize APIs from the provided API library. Do NOT create a new API!
        Use as minimum number of APIs and logical operators as possible to model the precondition.

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
            Chat.Entry(role='system', text=f'(1) Behavior (FSM):\n\n{self.transition.act.to_dict(expanded=False)}'),
            Chat.Entry(role='system', text='(4) Library of APIs:\n\n' + '\n\n'.join([f'[API ID] {i}\n{c.doc()}' for i, c in constraintAPI.items()])),
            Chat.Entry(role='user', text=f'(5) List of objects available in the scene: {", ".join(list(objects))}'),
            Chat.Entry(role='user', text=f'(2) Node ID: {self.transition.id}\nDescription of precondition: {self.info}'),
        ]

        # print(f"Precondition info: {self.info}")
        # print(f"Precondition Timing: {self.t}")

        for d in demos:
            idx = 1
            if d.id in self.t and isinstance(self.t[d.id], int):
                entries.append(
                    Chat.Entry(role='user', text=f'(3) Image(s) when the condition in question is satisfied for demonstration {idx}', im=d.video.get_frame_bytes(self.t[d.id]))
                )
                idx += 1

        chat = Chat(client)
        # response = json.loads(chat(entries, json=True))
        response_text = chat(entries, json=True)
        print("=== Gemini Raw Response ===")
        print(repr(response_text))
        cleaned = response_text.replace("```json", "").replace("```", "").strip()
        # Fix np.float64 artifacts
        import re
        cleaned = re.sub(r'"np\.float64\(([\d.]+)\)"', r'\1', cleaned)
        response = json.loads(cleaned)

        logic = response.get('logic', '')
        constraints = [Constraint.from_response(data, api, self) for data in response.get('constraints', [])]

        return logic, constraints

    def synth(self, demos: list[Demo], api: dict):
        self.logic, self.constraints = self.construct(demos, api)
        for c in self.constraints:
            c.synth(demos, api)
            # print(c.to_dict())

    @classmethod
    def from_dict(cls, data, transition, api) -> 'Termination':
        info = data.get('info', '')
        logic = data.get('logic', '')
        out = cls(info, transition)
        out.logic = logic
        out.constraints = [Constraint.from_dict(data, out, api[API.constraints]) for data in data.get('constraints', [])]
        return out

    def to_dict(self, expanded: bool = False):
        if expanded:
            return {
                'info': self.info,
                'logic': self.logic,
                'map': list(set([c.id for c in self.constraints])),
                'constraints': [c.to_dict(expanded) for c in self.constraints]
            }
        else:
            return {
                'info': self.info
            }

class Interruption(Condition):
    def __init__(self):
        super().__init__()

class Constraint:
    
    def __init__(self, id: str, condition: Condition, constraint: str | ConstraintAPI = None, args: dict = None, constraintAPI: dict = None):
        self.id = id
        self.args = args
        self.condition = condition

        # print(constraint, constraintAPI.keys())
        if isinstance(constraint, ConstraintAPI):
            self.api = constraint
        elif constraintAPI:
            self.api = constraintAPI.get(constraint, ConstraintAPI)(self)
        else:
            self.api = ConstraintAPI(self)

    @classmethod
    def doc(cls):
        raise NotImplementedError
    
    def synth(self, demos: list[Demo], api: dict):
        if self.api:
            print(self.api.ref(), self.args)
            self.api.synth(demos, api)
        else:
            raise NotImplementedError
    
    @classmethod
    def from_dict(cls, data, condition, constraintAPI: dict = None) -> 'Constraint':

        id = data.get('id', '')
        args = data.get('args', {})
        out = cls(id, condition, args=args)

        constraint = data.get('constraint', '')
        if constraint and constraintAPI:
            _api = constraintAPI.get(constraint, ConstraintAPI)
            out.api = _api.from_dict(args, out)
        else:
            out.args = args

        return out
    
    def to_dict(self, expanded: bool = False):
        try:
            return self.api.to_dict(expanded)
        except NotImplementedError:
            return {
                'id': self.id,
                'constraint': self.api.ref(),
                'args': self.args
            }
    
    @classmethod
    def from_response(cls, data: dict, api: dict, condition: Condition) -> 'Constraint':

        constraintAPI = api.get(API.constraints)

        id = data.get('id', None)
        constraint = data.get('api', None)
        args = data.get('params', None)

        return cls(
            id=id,
            constraint=constraint,
            args=args,
            constraintAPI=constraintAPI,
            condition=condition
        )

class Action:
    def __init__(self, id: int, action: str | ActionAPI, info: str, termination: str | Termination, t: dict[str: int] | int, api: dict = None, act = None, synthesized=False):

        self.id = id
        self.info = info
        self.t = t if isinstance(t, dict) else {'': t}

        if isinstance(termination, Termination):
            self.termination = termination
        if isinstance(termination, dict):
            self.termination = Termination.from_dict(termination, self, api)
        else:
            # print(f"Action -- Creating Termination: {termination}")
            self.termination = Termination(termination, self)

        actionAPI = api[API.actions]
        if isinstance(action, ActionAPI):
            self.api = action
        elif actionAPI:
            self.api = actionAPI.get(action, ActionAPI)(self)
        else:
            self.api = ActionAPI(self)

        # self.original = copy.deepcopy(self)
        self.act = act
        self.synthesized = synthesized

    def __repr__(self):
        return f'[{self.api.ref()}] {self.info}'
    
    def synth(self, demos: list[Demo], api: dict):
        try:
            self.api.synth(demos, api)
            # self.termination.synth(demos, api)
        except NotImplementedError:
            self.termination.synth(demos, api)
        self.synthesized = True

    def to_dict(self, expanded: bool = False) -> dict:
        t_out = self.t if len(self.t.keys()) > 1 else self.t.get('', self.t)
        out = {
            'id': str(self.id),
            'action': self.api.ref(),
            'info': self.info,
            't': t_out,
            'synthesized': self.synthesized
        }
        if expanded:
            out.update({
                'termination': self.termination.to_dict(expanded)
            })
        else:
            out.update({
                'termination': self.termination.info
            })
        try:
            api_dict = self.api.to_dict(expanded)
            api_dict.update(out)
            return api_dict
        except NotImplementedError:
            return out

    @classmethod
    def ref(cls) -> str:
        return 'unknown'

    @classmethod
    def from_dict(cls, data: dict, api: dict = None, demos: list[Demo] | Demo = [], act = None):

        if not isinstance(demos, list):
            demos = [demos]

        id = data.get('id', None)
        action = data.get('action', None)

        info = data.get('info', '')

        termination = data.get('termination', '')
        synthesized = data.get('synthesized', False)

        if 'keyframe' in data:
            keyframe = data['keyframe']
            t = keyframe if isinstance(keyframe, int) else -1
        else:
            t = data.get('t', -1)

        out = cls(id, action, info, termination, t, api, act, synthesized)

        actionsAPI = api[API.actions]
        if action and actionsAPI:
            _api = actionsAPI.get(action, ActionAPI)
            out.api = _api.from_dict(data, out, api)

        return out
    
    def show(self, demos):
        demos_dict = {d.id: d for d in demos}
        num_images = len(self.t)
        
        fig, axes = plt.subplots(1, num_images, figsize=(4 * num_images, 4))

        if num_images == 1:
            axes = [axes]

        for ax, (demoID, t) in zip(axes, self.t.items()):
            demo = demos_dict[demoID]
            ax.imshow(demo.scene.video[t])
            ax.set_title(str(demoID) + 't')
            ax.axis('off')

        plt.tight_layout()
        plt.show()
    
class Transition:
    def __init__(self, id: int, prev: int, next: int, precondition: str | Precondition, t: dict[str: int] | int, api: dict = None, act = None, synthesized=False):
        
        self.id = id
        self.prev = prev
        self.next = next

        self.t = t if isinstance(t, dict) else {'': t}

        if isinstance(precondition, Precondition):
            self.precondition = precondition
        elif isinstance(precondition, dict):
            self.precondition = Precondition.from_dict(precondition, self, api)
        else:
            self.precondition = Precondition(precondition, self)

        self.act = act
        self.synthesized = synthesized

    def synth(self, demos: list[Demo], api: dict):
        self.precondition.synth(demos, api)
        self.synthesized = True

    def to_dict(self, expanded: bool = False):
        t_out = self.t if len(self.t.keys()) > 1 else self.t.get('', self.t)
        out = {
            'id': self.id,
            'prev': str(self.prev),
            'next': str(self.next),
            'priority': 'precondition',
            't': t_out,
            'synthesized': self.synthesized
        }
        if expanded:
            out.update({
                'condition': self.precondition.to_dict(expanded),
            })
        else:
            out.update({
                'condition': self.precondition.info
            })
        return out

    @classmethod
    def from_dict(cls, data: dict, api: dict = None, demos: list[Demo] | Demo = [], act = None):

        if not isinstance(demos, list):
            demos = [demos]

        id = data.get('id', None)
        prev = data.get('prev', None)
        next = data.get('next', None)

        precondition = data.get('condition', data.get('precondition', ''))
        synthesized = data.get('synthesized', False)

        # demo = demos[0] if isinstance(demos, list) else demos
        # timing = data.get('t', {})
        # for demoID, t in timing.items():
        #     t = demo.video.time_to_frame_index(t)
        #     timing[demoID] = t

        if 'keyframe' in data:
            keyframe = data['keyframe']
            t = keyframe if isinstance(keyframe, int) else -1
        else:
            t = data.get('t', -1)

        return cls(id, prev, next, precondition, t, api, act, synthesized)

class Act:
    def __init__(self, outline: str = '', id: str | None = None, language: str | None = None):
        self.id = id
        self.outline = outline
        self.nodes = []
        self.edges = []
        self.language = language

    def add_node(self, action: Action):
        self.nodes.append(action)

    def add_edge(self, trans: Transition):
        self.edges.append(trans)

    @classmethod
    def from_dict(cls, data, api: dict = {}, demos: list[Demo] | Demo = [], id: str | None = None, language: str | None = None):
        if not isinstance(demos, list):
            demos = [demos]
        result = cls(outline=data.get('outline', ''), id=id, language=language)
        for n in data.get('nodes', []):
            result.add_node(Action.from_dict(n, api, demos=demos, act=result))
        for e in data.get('edges', []):
            result.add_edge(Transition.from_dict(e, api, demos=demos, act=result))
        return result
    
    def to_dict(self, id: str = None, expanded: bool = False) -> dict:
        out = {
            'outline': self.outline,
            'nodes': [n.to_dict(expanded) for n in self.nodes],
            'edges': [e.to_dict(expanded) for e in self.edges]
        }
        if id:
            out.update({'id': id})
        elif self.id:
            out.update({'id': self.id})
        if self.language:
            out.update({'transcript': self.language})
        return out
    
    def show(self):
        G = nx.DiGraph()

        for n in self.nodes:
            G.add_node(n.id, label=f'[{n.api.ref()}]\n{n.info}')

        for e in self.edges:
            G.add_edge(e.prev, e.next, label=e.precondition.info)

        pos = nx.spring_layout(G)
        labels = nx.get_node_attributes(G, "label")

        plt.figure(figsize=(10, 6))
        nx.draw(G, pos, with_labels=True, labels=labels, node_color="skyblue", edge_color="black", node_size=2000, font_size=10)
        edge_labels = nx.get_edge_attributes(G, "label")
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=8)
        plt.title("Infered Behaviour")
        plt.show()

class Synth:
    def __init__(self, act: Act, demos: list[Demo] | Demo, api: dict):
        self.act = act
        self.demos = demos if isinstance(demos, list) else [demos]
        self.api = api

    def run(self, edit_logger=None):
        all_elements = self.act.nodes + self.act.edges
        if edit_logger and hasattr(edit_logger, 'edited') and len(edit_logger.edited) > 0:
            edit_elements = []
            for elem in all_elements:
                if str(elem.id) in str(edit_logger.edited) or elem.synthesized == False:
                    edit_elements.append(elem)
        else:
            edit_elements = all_elements
        for elem in tqdm(edit_elements, desc="Synthesizing"):
            elem.synth(self.demos, self.api)

        if edit_logger and hasattr(edit_logger, 'edited') and len(edit_logger.edited) > 0:
            edit_logger.edited = []

    def to_dict(self, expanded: bool = False) -> dict:
        return {
            'nodes': [n.to_dict(expanded) for n in self.act.nodes],
            'edges': [e.to_dict(expanded) for e in self.act.edges]
        }