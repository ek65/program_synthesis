import json
from nlp_utils import *
from synth_utils import * 
from tqdm import tqdm

class Inference:

    @classmethod
    def act_from(cls, demos: list[Demo] | Demo, api: dict[API: any], model: str = 'o3-mini'):
        if not isinstance(demos, list):
            demos = [demos]

        actions = ", ".join([f"'{a}'" for a in api[API.actions].keys()])

        objects = set()
        for d in demos:
            for i in d.scene.objects:
                objects.add(f'{i.type} (ID: {i.id})')

        inference_instructions = f"""
        You are a helpful code assistant with a domain knowledge in {api[API.domain]}.
        You are provided with
        (1) A video (i.e. a sequence of image frames) of an instructor in the domain of {api[API.domain]}, teaching how to solve a particular task, and
        (2) A transcript of the video, which includes the instructor's narration and the actions performed in the video.

        Your task is to model the task performed by the {api[API.default_obj]} in the video as a finite state machine (FSM).
        Do not concern of about the behaviors of other objects or agents in the scene, only focus on the instructor's behavior.
        
        In the FSM, each node represents a sub-task with a description of a task and a termination condition for interrupting the subtask before it is completed,
        and each edge represents a transition from one node to another, consisting of a description of a precondition for the transition to occur. 

        It is important to note that the purpose of the termination condition is to define any condition
        to abruptly end the subtask in the node "before" the described subtask is completed. So, only fill out the termination condition
        if it is explicitly mentioned in the transcript. Otherwise, leave it as an empty string.

        For example, if the transcript states that the "move next to a player to receive a pass," then 
        the description of a node should be "move next to a player to receive a pass" and the termination condition should be an empty string. 
        However, if the transcript states that the "move next to a player to receive a pass while your teammate is under pressure," then
        the description of a node should be "move next to a player to receive a pass" and the termination condition should be "your teammate is NOT under pressure."
        As highlighted in these examples, the termination condition should be a "new" or "irrelevant" information 
        compared to the description of the node. The termination condition should be an empty string in general unless 
        it is explicitly mentioned in the transcript like the example above.

        Likewise, for the precondition, leave it as an empty string if it is not explicitly mentioned in the transcript, and 
        just connect the nodes for a transition. This empty string will be interpreted as being "True."

        Do NOT repeat the same information in the termination condition of a node and its transition's precondition.
        If there is a redundancy, only include the information in the termination condition of the node, and only include new information in the transition's precondition,
        or if there is no new information, leave the precondition as an empty string.

        In your response, DO NOT write pronouns. Instead, directly reference the object you are referring to without being concerned of redundancy.
        Note the set of availabible objects in the scene: {", ".join(list(objects))}.

        Your response must be a valid JSON in the following format:

        {{
            "outline": str               // Detailed description of the behaviour
            "nodes": [
                {{
                    "id": int,           // Unique identifier for the task node
                    "action": str,       // Action type: [{actions}]
                    "info": str,         // Description of the action
                    "termination": str,  // Condition under which the task terminates
                    "keyframe": int      // Keyframe index at which the task ends. Do not include if no visual input from the user.
                }}
            ],
            "edges": [
                {{
                    "id": int,             // Unique identifier for the condition edge
                    "prev": int,           // ID of the previous node
                    "next": int,           // ID of the next node
                    "precondition": str,   // Condition under which the transition occurs
                    "keyframe": int        // Keyframe index at which the condition is satisfied (i.e. when the action next action starts). Do not include if no visual input from the user.
                }}
            ]
        }}

        NOTE the following
        A good selection of keyframes is EXTREMELY important for producing an effective output when learning from the demonstration. Reason about the images, compare them and make sure you pick the most relevant one.
        Note that this instruction will be run multiple times over different demonstrations of a single behaviour, each potentially including different aspects. Later then output FSM for the different demonstrations will be combined into one.
        If the narration specifies or infers quantitative values, incorporate the appropiate node/edge description.
        When writing the nodes try to make the description (info) of an action and its termination not redundant. If the termination is already fully covered by the description of the action you may return an empty string for the termination.

        Do NOT make up new ACTIONS, they should only be picked from the following list of options: [{actions}]

        IMPORTANT: The demonstration contains pauses where the instructor explains the next action they'll perform. The pause frames are crucial keyframes to use for the start of actions. When assigning keyframe values to actions, prefer to use the pause frames as a starting point for the next action, as they typically occur right before an important action is demonstrated.
        
        You should reference the following examples for reference: {api[API.infer_shot]}
        """

        result = []

        for d in tqdm(demos):
        
            entries = [
                Chat.Entry(role='system', text=inference_instructions + (f'\n\n{api[API.video_info]}' if d.video else '')),
                Chat.Entry(role='user', text="Transcription: "+d.language)
            ]
            
            if d.video:
                # Include all video frames
                entries += [Chat.Entry(role='user', text=f'Video Frame Index: {idx}', im=get_im(im_dir)) 
                        for idx, im_dir in enumerate(d.video.frame_dir)]
                
                # Highlight pause frames specifically
                if hasattr(d, 'pause_times') and d.pause_times:
                    pause_frames_info = "Pause frames (instructor explaining next action):\n"
                    for pause_time in d.pause_times:
                        frame_idx = d.video.time_to_frame_index(pause_time)
                        if frame_idx < len(d.video.frame_dir):
                            pause_frames_info += f"- Frame {frame_idx} (timestamp: {pause_time:.2f}s)\n"
                    
                    entries.append(Chat.Entry(role='user', text=pause_frames_info))

            chat = Chat(client, model=model)
            response = json.loads(chat(entries, json=True))
            # print(response)
            
            # Process the response to ensure keyframe values align with pause times when appropriate
            if hasattr(d, 'pause_times') and d.pause_times:
                for node in response.get('nodes', []):
                    if 'keyframe' in node:
                        # Find the closest pause frame to this keyframe
                        closest_pause_frame = None
                        min_dist = float('inf')
                        
                        for pause_time in d.pause_times:
                            pause_frame = d.video.time_to_frame_index(pause_time)
                            dist = abs(pause_frame - node['keyframe'])
                            if dist < min_dist:
                                min_dist = dist
                                closest_pause_frame = pause_frame
                        
                        # If the closest pause frame is very close (within 2 frames), use it instead
                        if min_dist <= 2:
                            node['keyframe'] = closest_pause_frame

            result.append(Act.from_dict(response, api, id=d.id, demos=demos, language=d.language))
        
        print('Inference done.')
        return result
    
    @classmethod
    def combine(cls, acts: list[Act], api: dict[API: any], model: str = 'o3-mini'):

        actions = ", ".join([f"'{a}'" for a in api[API.actions].keys()])
        
        combine_instructions = f"""
        The user inputs a list of finite state machines (FSMs) that model sub-behaviours of an intended behaviour.
        You're tasked with reasoning about the finite state machines in the context of {api[API.domain]} and the sub-behaviours outlines to build a final finite state machine (FSM) that combines those from the input.

        Each FSM includes the transcript it was synthesized from. You should consider the multiple transcripts to consider the differences and similarities between FSM to reflect accurately the behaviour the user intended throughout the multiple demonstrations, perhaps demanding branching if two different transcript cover different sub-cases within the beahviour.

        Tasks are defined within an FSM where each task represents a node with a termination condition (i.e., the condition that marks the task as completed, allowing a state change),
        and edges represent preconditions (i.e., the condition under which the following task is triggered, transitioning from the previous state).

        Your response must be a valid JSON in the following format:

        {{
            "outline": str                        // Detailed description of the behaviour
            "nodes": [
                {{
                    "id": int,                    // Unique identifier for the task node
                    "action": str,                // Action type: [{actions}]
                    "info": str,                  // Description of the action
                    "termination": str,           // Condition under which the task terminates
                    "t": {{str: int}}             // A dictionary mapping sub-behaviour IDs to the time t. If a node was the combination of two nodes in two different sub-behaviors ('act_0' and 'act_1') with defined times (2 and 6 respectively) then the dictionary would be {{'act_0': 2, 'act_1': 6}}. Note that not every node might contain a mapping to every sub-behaviour (e.g. a node is a combination of two nodes in two different sub-behaviours out of three available sub-behaviours). The string keys must not be empty
                }}
            ],
            "edges": [
                {{
                    "id": int,                    // Unique identifier for the condition edge
                    "prev": int,                  // ID of the previous node
                    "next": int,                  // ID of the next node
                    "precondition": str,          // Condition under which the transition occurs
                    "t": {{str: int}}             // A dictionary mapping sub-behaviour IDs to the time t. If an edge was the combination of two edges in two different sub-behaviors ('act_0' and 'act_1') with defined times (2 and 6 respectively) then the dictionary would be {{'act_0': 2, 'act_1': 6}}. Note that not every edge might contain a mapping to every sub-behaviour (e.g. an edge is a combination of two edges in two different sub-behaviours out of three available sub-behaviours). The string keys must not be empty
                }}
            ]
        }}

        Exploit the structure and properties of finite state machines (FSMs) to allow for complex logic through branching and cycles.
        Do not simply merge similar edges into one, but consider their differences and if they lead to actions with different conditions consider branching to maximize the expressivity of the logic through the FSM.
        
        NOTE the following
        There should only be one starting node, i.e. one node with no incoming edges.
        There should be no more than one edge outgoing from one node to another, i.e. no two nodes should be directly connected by 2 or more edges.
        Try to output a well structured and highly interpretable FSM.
        If any node/edge description specifies or infers quantitative values, incorporate the appropiate node/edge description.
        User your domain knowledge on {api[API.domain]} to make a very concise yet effective behaviour that includes all of the intentded instructions in the input FSMs.

        Do NOT make up new ACTIONS, they should only be picked from the following list of options: [{actions}]

        You should reference the following examples for reference
        {api[API.combine_shot]}
        """
            
        entries = [
            Chat.Entry(role='system', text=combine_instructions),
        ] + [Chat.Entry(role='user', text=json.dumps(a.to_dict(expanded=False))) for idx, a in enumerate(acts)]

        chat = Chat(client, model=model)
        response = json.loads(chat(entries, json=True))

        result = Act.from_dict(response, api)
        
        print('Editing done.')
        return result
    
    @classmethod
    def fill(cls, act: Act, api: dict[API: any], model: str = 'o3-mini'):
        actions = ", ".join([f"'{a}'" for a in api[API.actions].keys()])
        
        system_instruction = f"""
        You are provided with
        (1) A finite state machine (FSM) encoding a planner which solves a particular physical task in the domain of {api[API.domain]}. 
        (2) A list of action APIs modeling different physical actions in the domain of {api[API.domain]}.

        Tasks are defined within an FSM where each task represents a node with a termination condition (i.e., the condition that marks the task as completed, allowing a state change),
        and edges represent preconditions (i.e., the condition under which the following task is triggered, transitioning from the previous state).

        You are tasked with filling out the action and termination properties for nodes where these are empty based on the description (info) of the corresponding node
        and its context, i.e. neighbour nodes and transitions as well as the whole behaviour outline.
        Do NOT overwrite any existing information. Only fill out attributes with missing information.

        The FSM's nodes encode physical tasks to solve and edges encode transition between nodes. 

        Your response must be a valid JSON in the following format:

        {{
            "outline": str                        // Detailed description of the behaviour
            "nodes": [
                {{
                    "id": int,                    // Unique identifier for the task node
                    "action": str,                // Action type: [{actions}]
                    "info": str,                  // Description of the task
                    "termination": str,           // Description of the condition under which the task completes 
                    "t": {{str: int}}             // A dictionary mapping sub-behaviour IDs to the time t. If a node was the combination of two nodes in two different sub-behaviors ('act_0' and 'act_1') with defined times (2 and 6 respectively) then the dictionary would be {{'act_0': 2, 'act_1': 6}}. Note that not every node might contain a mapping to every sub-behaviour (e.g. a node is a combination of two nodes in two different sub-behaviours out of three available sub-behaviours). The string keys must not be empty
                }}
            ],
            "edges": [
                {{
                    "id": int,                    // Unique identifier for the condition edge
                    "prev": int,                  // ID of the previous node
                    "next": int,                  // ID of the next node
                    "precondition": str,          // Description of the condition under which the transition occurs
                    "t": {{str: int}}             // A dictionary mapping sub-behaviour IDs to the time t. If an edge was the combination of two edges in two different sub-behaviors ('act_0' and 'act_1') with defined times (2 and 6 respectively) then the dictionary would be {{'act_0': 2, 'act_1': 6}}. Note that not every edge might contain a mapping to every sub-behaviour (e.g. an edge is a combination of two edges in two different sub-behaviours out of three available sub-behaviours). The string keys must not be empty
                }}
            ]
        }}

        Do NOT make up new ACTIONS, they should only be picked from the following list of options (2): [{actions}]
        """

        entries = [
            Chat.Entry(role='system', text=system_instruction),
            Chat.Entry(role='user', text="(1) The behaviour FSM to fill out: \n" + json.dumps(act.to_dict(expanded=False))),
        ]

        chat = Chat(client, model=model)
        response = json.loads(chat(entries, json=True))
        result = Act.from_dict(response, api)
        
        print('Editing done.')
        return result
    
    @classmethod
    def outline(cls, act: Act, api: dict[API: any], model: str = 'o3-mini'):
        system_instruction = f"""
        You are provided with
        (1) A finite state machine (FSM) encoding a planner which solves a particular physical task in the domain of {api[API.domain]}. 

        Tasks are defined within an FSM where each task represents a node with a termination condition (i.e., the condition that marks the task as completed, allowing a state change),
        and edges represent preconditions (i.e., the condition under which the following task is triggered, transitioning from the previous state).

        The FSM may have been edited so it could be that the outline is outdated and doesn't fully reflect the updated FSM.
        Your task is to consider whether the outline fully reflect the behavior decribed by the FSM, if it doesn't then rewrite the outline to describe better the behaviour, otherwise, return the same outline as the original.

        Your response must be a valid JSON in the following format:

        {{
            "outline": str     // Detailed description of the behaviour
        }}
        """

        entries = [
            Chat.Entry(role='system', text=system_instruction),
            Chat.Entry(role='user', text="(1) The behaviour FSM to fill out: \n" + json.dumps(act.to_dict(expanded=False))),
        ]

        chat = Chat(client, model=model)
        response = json.loads(chat(entries, json=True))
        result = response.get('outline', None)
        
        return result