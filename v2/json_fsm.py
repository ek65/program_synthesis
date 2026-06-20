from nlp_utils import Chat, client
import json
import os
from vanilla_scenic import load_python_file_as_string

import json
import re

def save_fsm_response(response, output_path):
    try:
        match = re.search(r'\{[\s\S]*\}', response)
        if not match:
            raise ValueError("No JSON object found in response.")
        json_str = match.group(0)
        fsm_data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON from LLM response:\n{e}\n\nRaw response:\n{response}")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(fsm_data, f, indent=2)

def scenic_to_fsm_json_with_llm(code: str, output_path: str, model: str = "gpt-5-mini") -> str:
    code = load_python_file_as_string(code)
    example_scenic_code = '''
behavior CoachBehavior():
    do Idle() for 3 seconds
    do Speak(
        "I'm getting into position to receive the ball from my teammate and assess the opponent's pressure."
    )
    do MoveTo(λ_target_initial())
    do Speak("I will recieve ball from my teammate.")
    do StopAndReceiveBall()
    do Speak(
        "Now that I have the ball, I will check the defender's position to decide my next move."
    )
    if C1_close_opponent.bool(simulation(), None):
        do Speak("The opponent is too close!)
        do Speak("I'll fake one way, create space, and then take a shot.")
        do MoveTo(λ_target0())
        do Speak("I've created enough space. Now I'll shoot.")
        do Shoot(goal)
    elif C2_medium_opponent.bool(simulation(), None):
        do Speak("The opponent is at a medium distance.")
        do Speak("The safest play is a pass back to my teammate.")
        do Pass(teammate)
    else:
        do Speak("The opponent is far away, giving me lots of space")
        do Speak("Attack the goal.")
        do MoveTo(λ_target3())
        do Speak("I'm in a good position to score now.")
        do Shoot(goal)
    do Idle()


C1_close_opponent = DistanceTo({
    'from': 'Coach',
    'to': 'opponent',
    'min': None,
    'max': {'avg': 2.0, 'std': 0.5},
    'operator': 'less_than'
})

C2_medium_opponent = DistanceTo({
    'from': 'Coach',
    'to': 'opponent',
    'min': {'avg': 2.0, 'std': 0.5},
    'max': {'avg': 5.0, 'std': 0.5},
    'operator': 'within'
})

A_initial_pos = AtAngle({
    'player': 'Coach',
    'ball': 'ball',
    'left': {
        'theta': {'avg': 65.0, 'std': 5.0},
        'dist': {'avg': 6.7, 'std': 0.5}
    },
    'right': {
        'theta': {'avg': 65.0, 'std': 5.0},
        'dist': {'avg': 6.7, 'std': 0.5}
    }
})

A1_target0 = DistanceTo({
    'from': 'Coach',
    'to': 'opponent',
    'min': {'avg': 3.5, 'std': 0.5},
    'operator': 'greater_than'
})

A2_target0 = DistanceTo({
    'from': 'Coach',
    'to': 'goal',
    'min': None,
    'max': {'avg': 10.0, 'std': 1.0},
    'operator': 'less_than'
})

C1_precondition1 = HasPath({
    'obj1': 'Coach',
    'obj2': 'goal',
    'path_width': {'avg': 2.5, 'std': 0.5}
})

C1_precondition2 = HasPath({
    'obj1': 'Coach',
    'obj2': 'teammate',
    'path_width': {'avg': 2.5, 'std': 0.5}
})

A1_target3 = DistanceTo({
    'from': 'Coach',
    'to': 'goal',
    'min': None,
    'max': {'avg': 8.0, 'std': 1.0},
    'operator': 'less_than'
})

C1_precondition4 = HasPath({
    'obj1': 'Coach',
    'obj2': 'goal',
    'path_width': {'avg': 2.5, 'std': 0.5}
})

def λ_target_initial():
    return A_initial_pos.dist(simulation(), ego=True)

def λ_termination_initial(past_position, current_position):
    return False

def λ_target0():
    cond = A1_target0 and A2_target0
    return cond.dist(simulation(), ego=True)

def λ_termination0(past_position, current_position):
    return False

def λ_precondition1(scene, sample):
    return C1_precondition1.bool(scene, sample)

def λ_termination1(past_position, current_position):
    return False

def λ_precondition2(scene, sample):
    return C1_precondition2.bool(scene, sample)

def λ_termination2(past_position, current_position):
    return False

def λ_target3():
    return A1_target3.dist(simulation(), ego=True)

def λ_termination3(past_position, current_position):
    return False

def λ_precondition4(scene, sample):
    return C1_precondition4.bool(scene, sample)

def λ_termination4(past_position, current_position):
    return False
'''

    example_fsm_json = '''
{
  "states": [
    {
      "id": 1,
      "name": "MoveTo(λ_target_initial())",
      "description": "I'm getting into position to receive the ball from my teammate and assess the opponent's pressure."
    },
    {
      "id": 2,
      "name": "StopAndReceiveBall()",
      "description": "I will recieve ball from my teammate."
    },
    {
      "id": 3,
      "name": "MoveTo(λ_target0())",
      "description": "I'll fake one way, create space, and then take a shot."
    },
    {
      "id": 4,
      "name": "Shoot(goal)",
      "description": "Now I'll shoot."
    },
    {
      "id": 5,
      "name": "Pass(teammate)",
      "description": "The safest play is a pass back to my teammate."
    },
    {
      "id": 6,
      "name": "MoveTo(λ_target3())",
      "description": "Attack the goal."
    },
    {
      "id": 7,
      "name": "Shoot(goal)",
      "description": "I'm in a good position to score now."
    }
  ],
  "transitions": [
    {
      "id": 1001,
      "from": 0,
      "to": 1,
      "condition": "after 3 seconds",
      "description": "Initial Transition"
    },
    {
      "id": 1002,
      "from": 1,
      "to": 2,
      "condition": true,
      "description": "true"
    },
    {
      "id": 1003,
      "from": 2,
      "to": 3,
      "condition": "C1_close_opponent.bool(simulation(), None)",
      "description": " The opponent is too close!"
    },
    {
      "id": 1004,
      "from": 3,
      "to": 4,
      "condition": true,
      "description": "true"
    },
    {
      "id": 1005,
      "from": 2,
      "to": 5,
      "condition": "C2_medium_opponent.bool(simulation(), None)",
      "description": "The opponent is at a medium distance."
    },
    {
      "id": 1006,
      "from": 2,
      "to": 6,
      "condition": "else",
      "description": "The opponent is far away, giving me lots of space."
    },
    {
      "id": 1007,
      "from": 6,
      "to": 7,
      "condition": true,
      "description": "true"
    }
  ]
}
'''

    FSM_EXTRACTION_PROMPT = """
You are an expert Scenic code interpreter. Your task is to extract a Finite State Machine (FSM) from a Scenic behavior definition.

Follow these strict rules:

1. States:
   - Every 'do <Action>()' (excluding 'do Speak(...)' and 'do Idle()') defines a state.
   - Each state must have a unique integer 'id'** starting from 1.
   - Include a 'name' field with the full action (e.g., 'MoveTo(λ_target0())').
   - Attach the text of the 'do Speak("...")' that's directly before the state as a "description".
   
2. Transitions:
   - Transitions occur between states, either:
     - Explicitly, when there is a 'do Idle()' or 'do Idle() until <condition>' → use the idle timing/condition as the '"condition"' field.
     - Implicitly, when there is no 'do Idle()' → use '"condition": true'.
   - Each transition must have a unique **integer 'id'** starting from 1001.
   - 'from' and 'to' must reference the 'id' of the source and destination states, not their names.
   - If the transition is implicit, use '"description": true'.
   - Attach the text of the 'do Speak("...")' that's directly before the transition as a "description" for explicit transitions unless condition is true, in this case use '"description": true'.
3. Conditional Branches ('if' / 'elif' / 'else')**:
   - These are not states.
   - Use them to define transitions with 'condition' set to the condition in the branch.
     - Use '"condition": "else"' for 'else' blocks.
   - The first action inside each conditional block is the target 'to' state of the transition.
   - The first 'do Speak(...)' line inside the branch describes the transition.
   - The second 'do Speak(...)' line inside the branch describes the action to take in the branch.

4. Initial State:
   - Assume a virtual '"Idle"' start state with ID '0'.
   - The first real state is connected via a transition from '"from": 0'.
   - The transition from 0 has "'description': Initial Transition", 
   unless there are no single real first state, e.i branching from the initial state, in which case the transitions from 0 has "f'description': {description of the transition to the branch}"

5. Output Format:
Return a single JSON object with the following structure:

'''json
{
  "states": [
    {"id": 1, "name": "ActionName()", "description": "..."},
    ...
  ],
  "transitions": [
    {"id": 1001, "from": 0, "to": 1, "condition": "after 3 seconds", "description": "..."},
    ...
  ]
}

6. Only look at CoachBehavior block, it is marked with:
'####HEADER ENDS####' and ####Environment Behavior START####

"""
    chat = Chat(client, model=model)
    messages = [
    Chat.Entry(role="system", text=FSM_EXTRACTION_PROMPT),  
    Chat.Entry(role="system", text="This is example code:"),
    Chat.Entry(role="user", text=example_scenic_code.strip()),

    Chat.Entry(role="system", text="This is FSM extracted from that example code:"),
    Chat.Entry(role="user", text=example_fsm_json.strip()),

    Chat.Entry(role="system", text="Now extract the FSM from the following Scenic code:"),
    Chat.Entry(role="user", text=code.strip())  
]
    response = chat(messages).strip()
    
    
    response = response.strip()
    if response.startswith("'''"):
        response = response.strip("'''").strip("json").strip()

    save_fsm_response(response, output_path)

    return response
