import google.generativeai as genai
from apiKey import GEMINI_API_KEY
genai.configure(api_key=GEMINI_API_KEY)

import json
from nlp_utils_gemini import Chat, Video, get_im
from synth_utils_gemini import Demo, Act
from api_utils import ActionAPI, ConstraintAPI, API
from tqdm import tqdm

class Inference_Gemini:

    @classmethod
    def act_from(
        cls,
        demos: list[Demo] | Demo,
        api: dict[API: any],
        model: str = "gemini-2.5-flash-preview-05-20"
    ):
        if not isinstance(demos, list):
            demos = [demos]

        actions = ", ".join([f"'{a}'" for a in api[API.actions].keys()])

        objects = set()
        for d in demos:
            for i in d.scene.objects:
                objects.add(f"{i.type} (ID: {i.id})")

        inference_instructions = f"""
        You are a helpful code assistant with domain knowledge in {api[API.domain]}.
        You are provided with:
        (1) A video (i.e., bytes) of an instructor in the domain of {api[API.domain]}, teaching how to solve a particular task, and
        (2) A transcript of the video, which includes the instructor's narration and the actions performed in the video.

        Your task is to model the task performed by the {api[API.default_obj]} in the video as a finite state machine (FSM).
        Ignore behaviors of other objects or agents in the scene; focus solely on the instructor's actions.

        In the FSM:
        - Each **node** represents a sub-task, described by:
            • the action type (from the provided action list),
            • a **description** of the task,
            • a **termination condition** (only if explicitly mentioned in the transcript),
            • a **keyframe**, which is **the exact frame where the task is visually completed**. For example, if the action is "move to the goal", the keyframe should be when the instructor **reaches** the goal (i.e., stops moving after arrival), not when movement begins.
        - Each **edge** represents a **transition** from one task to another and includes:
            • the IDs of the two nodes it connects,
            • a **precondition** for the transition (only if explicitly stated),
            • a **keyframe**, which is the frame where the precondition is **satisfied** and the next action visually begins.

        IMPORTANT:
        - Do NOT write pronouns. Use explicit object references, even if it leads to some redundancy.
        - Available objects in the scene: {", ".join(list(objects))}.
        - Use only the provided action types: [{", ".join(api[API.actions].keys())}]. Do NOT invent new actions.
        - Leave termination conditions and preconditions as an empty string unless explicitly stated in the transcript. Do not invent or infer them.
        - If a fact is both a termination condition and a transition precondition, include it only in the **termination**.
        - When writing the `info` field in each node, be descriptive and specific. Avoid overlap with the termination condition.
        - Pay special attention to keyframes. For actions like **move**, choose the frame where the movement **ends** (i.e., the destination is reached), not when it starts. For manipulations, it’s when the goal of the manipulation is achieved (e.g., "object is placed", "switch is flipped").
        - The demonstration includes pauses where the instructor explains the next step. These **pause frames are useful for keyframes of transitions** — i.e., they often mark when the next action begins. However, action node keyframes must **mark completion**, not explanation or initiation.

        Your output must be a valid JSON of the following structure:

        {{
            "outline": str,               // Detailed description of the behavior
            "nodes": [
                {{
                    "id": int,           // Unique identifier for the task node
                    "action": str,       // One of [{", ".join(api[API.actions].keys())}]
                    "info": str,         // Description of the action
                    "termination": str,  // If applicable, when the task should terminate prematurely
                    "keyframe": int      // Frame when the action is completed (i.e., constraint is met)
                }}
            ],
            "edges": [
                {{
                    "id": int,             // Unique identifier for the transition
                    "prev": int,           // ID of the source node
                    "next": int,           // ID of the destination node
                    "precondition": str,   // If applicable, precondition for the transition
                    "keyframe": int        // Frame when the condition is satisfied (i.e., next action begins)
                }}
            ]
        }}

        NOTE:
        - Good keyframe selection is CRITICAL for effective learning.
        - This instruction will run on multiple demonstrations of the same behavior, so focus on capturing faithful structure in each instance.
        - If the transcript includes or implies quantities (e.g., distances, durations), reflect them in node/edge descriptions as appropriate.

        Reference examples: {api[API.infer_shot]}
        """.strip()

        result = []

        for d in tqdm(demos, desc="Running Gemini inference"):
            entries = [
                Chat.Entry(role='user', text=inference_instructions + (f'\n\n{api[API.video_info]}' if d.video else '')),
                Chat.Entry(role='user', text="Transcription: " + d.language)
            ]
            # if d.video:
            #     # Include all video frames
            #     entries += [
            #         Chat.Entry(role='user', text=f'Video Frame Index: {idx}', im=get_im(im_dir))
            #         for idx, im_dir in enumerate(d.video.frame_dir)
            #     ]
            if d.video_bytes: 
                entries.append(
                Chat.Entry(
                    role='user',
                    text="Video of the instructor performing the task.",
                    file=("video.mp4", d.video_bytes)  # Gemini gets filename + byte content
                )
                )

                # Highlight pause frames specifically
                # if hasattr(d, 'pause_times') and d.pause_times:
                #     pause_frames_info = "Pause frames (instructor explaining next action):\n"
                #     for pause_time in d.pause_times:
                #         frame_idx = d.video.time_to_frame_index(pause_time)
                #         if frame_idx < len(d.video.frame_dir):
                #             pause_frames_info += f"- Frame {frame_idx} (timestamp: {pause_time:.2f}s)\n"
                #     entries.append(Chat.Entry(role='user', text=pause_frames_info))
                if hasattr(d, 'pause_times') and d.pause_times:
                    pause_info = "Pause timestamps (instructor explaining next action):\n"
                    for pause_time in d.pause_times:
                        pause_info += f"- Timestamp: {pause_time:.2f}s\n"
                    entries.append(Chat.Entry(role='user', text=pause_info))

            chat = Chat(model=model)
            response = chat(entries, as_json=True)
            # print(response_text)

            # Remove any ```json or ``` code fences
            # cleaned = response_text.replace("```json", "").replace("```", "").strip()
            # response = json.loads(cleaned)

            # Post-process keyframes
            # if hasattr(d, 'pause_times') and d.pause_times:
            #     for node in response.get('nodes', []):
            #         if 'keyframe' in node:
            #             closest_pause_frame = None
            #             min_dist = float('inf')
            #             for pause_time in d.pause_times:
            #                 pause_frame = d.video.time_to_frame_index(pause_time)
            #                 dist = abs(pause_frame - node['keyframe'])
            #                 if dist < min_dist:
            #                     min_dist = dist
            #                     closest_pause_frame = pause_frame
            #             if min_dist <= 2:
            #                 node['keyframe'] = closest_pause_frame

            result.append(Act.from_dict(response, api, id=d.id, demos=demos, language=d.language))

        print('Inference done.')
        return result

    @classmethod
    def combine(cls, acts: list[Act], api: dict[API: any], model: str = 'gemini-2.5-flash-preview-05-20'):
        actions = ", ".join([f"'{a}'" for a in api[API.actions].keys()])

        combine_instructions = f"""
        The user inputs a list of finite state machines (FSMs) that model sub-behaviours of an intended behaviour.
        You're tasked with reasoning about the finite state machines in the context of {api[API.domain]} and the sub-behaviours outlines to build a final finite state machine (FSM) that combines those from the input.

        Each FSM includes the transcript it was synthesized from. You should consider the multiple transcripts to consider the differences and similarities between FSM to reflect accurately the behaviour the user intended throughout the multiple demonstrations, perhaps demanding branching if two different transcript cover different sub-cases within the behaviour.

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

        entries = [Chat.Entry(role='user', text=combine_instructions)]
        entries += [Chat.Entry(role='user', text=json.dumps(a.to_dict(expanded=False))) for a in acts]

        chat = Chat(model=model)
        response = chat(entries, as_json=True)

        # cleaned = response_text.replace("```json", "").replace("```", "").strip()
        # response = json.loads(cleaned)

        result = Act.from_dict(response, api)
        print('Editing done.')
        return result

    @classmethod
    def fill(cls, act: Act, api: dict[API: any], model: str = 'gemini-2.5-flash-preview-05-20'):
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
            Chat.Entry(role='user', text=system_instruction),
            Chat.Entry(role='user', text="(1) The behaviour FSM to fill out: \n" + json.dumps(act.to_dict(expanded=False))),
        ]

        chat = Chat(model=model)
        response = chat(entries, as_json=True)

        # cleaned = response_text.replace("```json", "").replace("```", "").strip()
        # response = json.loads(cleaned)

        result = Act.from_dict(response, api)
        print('Editing done.')
        return result

    @classmethod
    def outline(cls, act: Act, api: dict[API: any], model: str = 'gemini-2.5-flash-preview-05-20'):
        system_instruction = f"""
        You are provided with
        (1) A finite state machine (FSM) encoding a planner which solves a particular physical task in the domain of {api[API.domain]}. 

        Tasks are defined within an FSM where each task represents a node with a termination condition (i.e., the condition that marks the task as completed, allowing a state change),
        and edges represent preconditions (i.e., the condition under which the following task is triggered, transitioning from the previous state).

        The FSM may have been edited so it could be that the outline is outdated and doesn't fully reflect the updated FSM.
        Your task is to consider whether the outline fully reflect the behavior described by the FSM, if it doesn't then rewrite the outline to describe better the behaviour, otherwise, return the same outline as the original.

        Your response must be a valid JSON in the following format:

        {{
            "outline": str     // Detailed description of the behaviour
        }}
        """

        entries = [
            Chat.Entry(role='user', text=system_instruction),
            Chat.Entry(role='user', text="(1) The behaviour FSM to fill out: \n" + json.dumps(act.to_dict(expanded=False))),
        ]

        chat = Chat(model=model)
        response = chat(entries, as_json=True)

        # cleaned = response_text.replace("```json", "").replace("```", "").strip()
        # response = json.loads(cleaned)
        return response.get('outline', None)