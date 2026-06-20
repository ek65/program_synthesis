import re
import json
from translator import *
from nlp_utils import Chat
import os
import json
import requests
import sys
import openai
from apiKey import OPENAI_API_KEY
from openai import OpenAI
from nlp_utils import Chat
from scenic_fc.api import api
from nlp_utils import *
from synth_utils import * 

# File to store cached documentation
CACHE_FILE = "doc_cache.json"
client = OpenAI(api_key=OPENAI_API_KEY)

class InZone:
    """
    Represents a constraint that checks if an entity is in a certain zone.

    Attributes:
        args (dict): A dictionary of parameters, e.g. {"zone": "C1"}.
                     The 'zone' key might represent a named or numbered area on a field.
 
    """
    def __init__(self, args):
        # Store the arguments for future evaluation.
        self.args = args

class HasAngle:
    """
    Represents a constraint that checks if an entity has a certain angular relationship to a reference.

    Attributes:
        args (dict): A dictionary of parameters, e.g. {"ref": "player", "r": 1.5}.
                     The 'ref' key indicates the reference entity.
                     The 'r' key indicates the angle in radians or degrees.
    """
    def __init__(self, args):
        self.args = args

class IsVisible:
    """
    Represents a constraint that checks if a target entity is visible from some vantage point.

    Attributes:
        args (dict): A dictionary of parameters, e.g. {"target": "teammate"}.

    """
    def __init__(self, args):
        self.args = args

class DistanceLessThan:
    """
    Represents a constraint checking if the distance between two entities is less than a given value.

    Attributes:
        args (dict): A dictionary of parameters, e.g. {"target": "goal", "distance": 3.0}.

    """
    def __init__(self, args):
        self.args = args

class DistanceGreaterThan:
    """
    Represents a constraint checking if the distance between two entities is greater than a given value.

    Attributes:
        args (dict): A dictionary of parameters, e.g. {"target": "player", "distance": 1.5}.

    """
    def __init__(self, args):
        self.args = args

def parse_node(node, program):
    ### Processing Nodes
    node_id = node["action"]  # e.g. "moveTo", "Idle", "passTo", etc.
    
    until = node.get("termination", "")
    until_func_name = "λ_termination" + node['id']

    target = node.get("target", "")
    target_func_name = "λ_target" + node['id']

    if until:
        logic_expr = until['logic']
        program['termination'].append(f"def {until_func_name}(scene, sample):")
        if logic_expr == "":
            program['termination'].append("    return True\n")
        else:
            logic = synthesize_conditionals(logic_expr)
            logical_list = until['map']
            for element in logical_list:
                logic = logic.replace(element, element + f"termination_{node['id']}.bool(simulation())")
            program['termination'].append(f"    return {logic}\n")
            # program['termination'].append(f"    return cond\n")

    statement = None

    # We generate lines differently based on the node "id".
    if node_id.lower() == "moveto":
        # e.g. do moveTo(λ_dest) until λ_termination
        # if dest and always and until:
        #     statement = f"    do {action_id}({dest}, {always}) until {until}"
        assert target != ""
        if target and until:
            statement = f"{' ' * program['space']}do {node_id}({target_func_name}()) until {until_func_name}(simulation(), None)"
            program['target'].append(f"def {target_func_name}():")
            logic_expr = target['logic']
            logic = synthesize_conditionals(logic_expr)

            if logic == 'None' or logic == '':
                assert "target is None"

            logical_list = target['map']
            for element in logical_list:
                logic = logic.replace(element, element + f"target_{node['id']}.dist(simulation(), ego=True)")
            
            program['target'].append(f"    return {logic}\n")
            # program['target'].append(f"    return cond.dist(simulation(), ego=True)\n")

        elif target and not until:
            statement = f"{' ' * program['space']}do MoveAs({target_func_name}())"
        else:
            raise NotImplementedError("moveTo() invoked but no argument given")

    elif node_id.lower() == "wait":
        if until:
            statement = f"{' ' * program['space']}do Idle() until {until_func_name}(simulation(), None)"
        else:
            print("Wait invoked but no termination condition given")
            pass
            # raise NotImplementedError("Wait invoked but no termination condition given")

    elif node_id.lower() == "pass":
        # e.g. do passTo(teammate)
        target = node['target']['player'].lower()
        if target:
            statement = f"{' ' * program['space']}do Pass({target})"
        else:
            raise NotImplementedError("passTo() invoked but no target given")
        
    elif node_id == "GetBallPossession":
        statement = f"{' ' * program['space']}do GetBallPossession(ball)"

    elif node_id == "Shoot":
        statement = f"{' ' * program['space']}do Shoot(goal)"
    else:
        # If we don't recognize the node id, default to "do <node_id>()"
        # statement = f"    do {node_id}()"
        raise NotImplementedError(f"{node_id} Not Handled")

    assert statement is not None
    return statement

def find_nextNode(data, edge):
    nodes = data['nodes']
    next_nodeID = edge['next']
    for node in nodes:
        if node['id'] == next_nodeID:
            return node
    assert False, f"No Node with ID: {next_nodeID} found"

def construct_coach_behavior(node, data, program):
    """
    Constructs a text-based "behavior" script from a given JSON specification.

    This function:
      - Iterates over the 'actions' in the provided JSON.
      - Inspects the 'id' and various argument fields (like 'dest', 'precondition', etc.).
      - Builds a line of code (e.g., 'do moveTo(...) until ...').
      - Concatenates these lines into a multi-line string that defines a coach behavior.

    :param action_json: dict
        A dictionary with a structure like:
        {
          "actions": [
            {
              "id": <string>,
              "args": { ... },
              "constraints": { ... }
            },
            ...
          ]
        }

    :return: str
        A multi-line string representing a behavior script, for example:

        behavior coachBehavior():
            scene = simulation()
            do Idle() until λ_precondition
            do moveTo(λ_dest) until λ_termination
            ...

    Example Usage:
        example_actions = {...}
        script = construct_coach_behavior(example_actions)
        print(script)
    """

    # function_lines = [
    #     "behavior coachBehavior():",
    #     "    scene = simulation()"
    # ]

    # nodes = action_json['nodes']
    # edges = action_json['edges']
    # sorted_nodes = sorted(nodes, key=lambda d: d.get("id"), reverse=False)
    if program == {}:
        program['termination'] = []
        program['target'] = []
        program['precondition'] = []
        program['behavior'] = ['behavior CoachBehavior():', '    do Idle() for 1 seconds']
        program['space'] = 4 # 4 spaces

    statement = parse_node(node, program)
    program['behavior'].append(statement)

    ### Processing Edges        
    outgoing_edges = [e for e in data['edges'] if str(e['prev']) == str(node['id'])]
    # preconditions = ""
    lambda_precondition_name = "λ_precondition"
    lambda_precondition_construct  = ""

    for i, edge in enumerate(outgoing_edges):
        lambda_precondition_name += f"_{edge['id']}"
        logic_expr = edge['condition']['logic']
        logic = synthesize_conditionals(logic_expr)

        if logic == 'None' or logic == '' or logic is None:
            print(f"Edge {edge['id']} has no logic expression")
            program['precondition'].append(f"def λ_precondition" + {edge['id']} + "(scene, sample):")
            program['precondition'].append(f"    return True\n")
            continue

        logical_list = edge['condition']['map']
        for element in logical_list:
            logic = logic.replace(element, element + f"precondition_{edge['id']}.bool(simulation())")

        # print(f"EDGE: {edge}")
        # print(f"EDGE ID: {edge['id']}")
        program['precondition'].append(f"def λ_precondition{edge['id']}(scene, sample):")
        program['precondition'].append(f"    return {logic}\n")
        # program['precondition'].append(f"    return cond.bool(simulation())\n")

        if lambda_precondition_construct == "":
            lambda_precondition_construct = f"λ_precondition{edge['id']}(simulation(), sample)"
        else:
            lambda_precondition_construct += f" or λ_precondition{edge['id']}(simulation(), sample)"

    if len(outgoing_edges) >= 1:
        program['precondition'].append(f"def {lambda_precondition_name}(scene, sample):")
        program['precondition'].append(f"    return {lambda_precondition_construct}\n")
    
    if len(outgoing_edges) >= 1:
        program['behavior'].append(f"{' ' * program['space']}do Idle() until {lambda_precondition_name}(simulation(), None)")

    for i, edge in enumerate(outgoing_edges):
        if len(outgoing_edges) == 1:
            next_node = find_nextNode(data, edge)
            program = construct_coach_behavior(next_node, data, program)
        elif len(outgoing_edges) > 1:
            if i == 0:
                program['behavior'].append(f"{' ' * program['space']}if λ_precondition{edge['id']}(simulation(), None):")
                program['space'] += 4
                next_node = find_nextNode(data, edge)
                program = construct_coach_behavior(next_node, data, program)
                program['space'] -= 4
            elif 0 < i and i < len(outgoing_edges)-1:
                program['behavior'].append(f"{' ' * program['space']}if λ_precondition{edge['id']}(simulation(), None):")
                program['space'] += 4
                next_node = find_nextNode(data, edge)
                program = construct_coach_behavior(next_node, data, program)
                program['space'] -= 4
            else:
                program['behavior'].append(f"{' ' * program['space']}else:")
                program['space'] += 4
                next_node = find_nextNode(data, edge)
                program = construct_coach_behavior(next_node, data, program)
                program['space'] -= 4
    return program

    # if len(outgoing_edges) > 0:
    #     e = outgoing_edges[0]
    #     if e['condition']['logic'] == 'None':
    #         continue
    #     precondition_func_name = 'λ_precondition'+e['id']
    #     statement = f"    do Idle() until {precondition_func_name}(scene, sample)"
    #     program.append(statement)
    # else:
    #     pass

        # if len(outgoing_edges) == 1:
        #     precondition_func_name = 'λ_precondition'+e['id']
        #     statement = f"    do Idle() until {precondition_func_name}(scene, sample)"
        #     program.append(statement)
        # else:
        #     precondition_func_name = 'λ_precondition'+action['id']
        #     statement = f"    do Idle() until {precondition_func_name}(scene, sample)"
        #     program.append(statement)
        #     edge_count = len(outgoing_edges)
        #     for e in outgoing_edges:
        #         precondition_func_name = 'λ_precondition'+e['id']
        #         statement = f"    if {precondition_func_name}(scene, sample)"

        #         program.append(statement)

    # Combine all lines into one multi-line string for easy viewing/execution.
    # return "\n".join(program)


def synthesize_conditionals(expression):
    """
    Converts a custom logical expression (with IF-THEN-ELSE, AND, OR) 
    into a Pythonic expression that can be interpreted by Python logic.

    The transformations done here:
      1. "IF X THEN Y ELSE Z" -> "(Y if X else Z)"
      2. "AND" -> "and"
      3. "OR" -> "or"

    :param expression: str
        A string containing a logical expression with uppercase AND/OR 
        and optional IF..THEN..ELSE syntax.
        e.g., "IF A THEN B ELSE (C AND D)".

    :return: str
        A string where the syntax has been converted to valid Python expression format.
        e.g., "(B if A else (C and D))".

    Example Usage:
        original_expr = "IF A THEN B ELSE (C AND D)"
        pythonic_expr = synthesize_conditionals(original_expr)
        # pythonic_expr would become "(B if A else (C and D))"
    """
    # 0)
    if not isinstance(expression, str) or not expression.strip():
        return ""  # return empty string or handle as needed

    # 1) Convert IF..THEN..ELSE to Python conditional expression
    expression = re.sub(
        r'\bIF\s+(.*?)\s+THEN\s+(.*?)\s+ELSE\s+(.*?)\b',
        r'(\2 if \1 else \3)',
        expression
    )

    # 2) Convert uppercase AND/OR to Pythonic and/or
    expression = expression.replace("AND", "and").replace("OR", "or").replace("NOT", "not")
    return expression


def get_args(action):
    """
    Retrieves and formats the 'args' for a given constraint in an action into lines of Python code.

    Each constraint dictionary typically has:
        "args": {
          "A": {
            "type": "InZone",
            "args": { "zone": "C1" }
          },
          "B": {
            "type": "HasAngle",
            "args": { "ref": "player", "r": 1.5 }
          }
        }

    We turn that into lines like:
        A = InZone({'zone': 'C1'})
        B = HasAngle({'ref': 'player', 'r': 1.5})

    :param action: dict
        One action item from the JSON. Contains "constraints" which might hold "args" sub-dictionaries.
    :param constraint_name: str
        The key for the specific constraint, e.g. "λ_precondition", "λ_dest", etc.

    :return: str
        A multi-line string of Python code that instantiates the relevant constraint classes.

    Example Usage:
        action = { ... }
        lines_of_code = get_args(action, "λ_precondition")
        print(lines_of_code)  # e.g. "A = InZone({'zone': 'C1'})\nB = HasAngle({...})"
    """
    # Dive into the action's constraints, then the named constraint, then the 'args' block
    keys = []
    if "termination" in action.keys():
        keys.append("termination")
    if "condition" in action.keys():
        keys.append("condition")
    if "target" in action.keys():
        keys.append("target")

    # args = action.get("constraints", {}).get(constraint_name, {}).get("args", {})
    formatted_args = []

    # Each key in 'args' is typically "A", "B", "C", etc.; each value is a dict with "type" and "args".
    for k in keys:
        if 'constraints' not in action[k].keys():
            continue
        constraints = action[k]['constraints']
        for c in constraints:
            arg_name = c['id']
            if k == "termination":
                arg_name += "termination"
            elif k == "condition":
                arg_name += "precondition"
            else:
                arg_name += "target"
            arg_type = c["constraint"]  # e.g. "InZone"
            # Build the dictionary portion used to instantiate the class, e.g. {'zone': 'C1'}
            arg_values = ", ".join([f"'{k}': {repr(v)}" for k, v in c["args"].items()])
            # Construct a single line of code, e.g. "A = InZone({'zone': 'C1'})"
            formatted_args.append(f"{arg_name}_{str(action['id'])} = {arg_type}({{{arg_values}}})")

    return "\n".join(formatted_args)


def create_constraint_definitions(example):
    """
    Creates a block of Python code defining constraints for the action at position 'action_index'.

    This function:
      1. Looks up the action in 'example["actions"]' by index.
      2. Finds all constraint names in action["constraints"].
      3. For each constraint name, calls 'get_args()' to generate lines of code like:
         A = InZone({...})
         B = HasAngle({...})
      4. Joins them into a single string (one definition after another).

    :param action_index: int
        Index of the action in the 'example["actions"]' list.
    :param example: dict
        The main JSON-like dictionary containing 'actions' and each action's constraints.

    :return: str
        Multi-line string of code defining each constraint for the given action.

    Example Usage:
        example_data = { ... }
        index = 0  # first action
        definitions_code = create_constraint_definitions(index, example_data)
        print(definitions_code)
        # Might print:
        #   A = InZone({'zone': 'C1'})
        #   B = HasAngle({'ref': 'player', 'r': 1.5})
    """
    nodes = example['nodes']
    edges = example['edges']
    nodes.extend(edges)
    definitions = []            
    
    for element in nodes:
        # Iterate over all constraints keys in this action, e.g. λ_precondition, λ_dest, λ_termination
        
        constraint_def = get_args(element)
        # print(f"constraint_def: {constraint_def}")
        if constraint_def:
            definitions.append(constraint_def)

    return "\n".join(definitions)


def create_lambda_dest(action):
    """
    Builds a function definition (as a string) for the λ_dest constraint logic.

    Steps:
      1. Retrieve the constraint info under action["constraints"]["λ_dest"].
      2. Extract the 'logical' expression, e.g. "IF A THEN B ELSE (C AND D)".
      3. Use 'synthesize_conditionals' to convert that to Pythonic form, e.g. "(B if A else (C and D))".
      4. Replace placeholders 'A', 'B', 'C', etc., with the function calls 'A(scene, sample)', etc.
      5. Return a string that looks like:
         def λ_dest(scene, sample):
             return (B(scene, sample) if A(scene, sample) else ...)

    :param action: dict
        A single action from the JSON that might contain "constraints" with a "λ_dest" key.

    :return: str
        The full Python function definition as text, or a stub if no logical expression was provided.

    Example Usage:
        action = {
          "constraints": {
            "λ_dest": {
              "logical": "IF A THEN B ELSE (C AND D)",
              "constraints": ["A","B","C","D"]
            }
          }
        }
        code = create_lambda_dest(action)
        print(code)
        #   def λ_dest(scene, sample):
        #       return (B(scene, sample) if A(scene, sample) else (C(scene, sample) and D(scene, sample)))
    """
    target = action['target']
    lambda_def = f"def λ_dest{action['id']}(scene, sample):\n"
    logical_expr = target["logic"]
    constraints = target['constraints']

    if not logical_expr:
        # If there's no expression, return a simple function that returns None
        return lambda_def + "    return None  # No logical expression provided\n"

    # Convert the expression to Python format (IF->if, THEN->, ELSE->, AND->and, OR->or)
    logical_expr = synthesize_conditionals(logical_expr)

    # For each constraint name (e.g. "A", "B", "C"), replace it with A(scene, sample)
    for c in constraints:
        logical_name = c['id']
        constraint_name = c['constraint']
        verify_call = f"{logical_name+action['id']}(simulation(), sample)"
        logical_expr = logical_expr.replace(logical_name, verify_call)

    # Insert the final expression into the function body
    lambda_def += f"    return {logical_expr}\n"
    return lambda_def


def create_lambda_termination(action):
    """
    Builds a function definition (as a string) for the λ_termination constraint logic.

    Similar to 'create_lambda_dest', but reads from "λ_termination".

    :param action: dict
        A single action from the JSON that might contain "constraints" with a "λ_termination" key.

    :return: str
        The full Python function definition as text.

    Example Usage:
        action = {
          "constraints": {
            "λ_termination": {
              "logical": "(E AND F) OR (G AND H)",
              "constraints": ["E","F","G","H"]
            }
          }
        }
        code = create_lambda_termination(action)
        print(code)
        #   def λ_termination(scene, sample):
        #       return (E(scene, sample) and F(scene, sample)) or (G(scene, sample) and H(scene, sample))
    """
    termination = action['termination']
    lambda_def = f"def λ_termination{action['id']}(scene, sample):\n"
    logical_expr = termination['logic']

    if not logical_expr:
        return lambda_def + "    return None  # No logical expression provided\n"

    logical_expr = synthesize_conditionals(logical_expr)

    for c in termination["constraints"]:
        logical_name = c['id']
        constraint_name = c['constraint']
        verify_call = f"{logical_name+action['id']}(simulation(), sample)"
        logical_expr = logical_expr.replace(logical_name, verify_call)

    lambda_def += f"    return {logical_expr}\n"
    return lambda_def


def create_lambda_precondition(action):
    """
    Builds a function definition (as a string) for the λ_precondition constraint logic.

    Similar to 'create_lambda_dest' and 'create_lambda_termination', but reads from "λ_precondition".

    :param action: dict
        A single action from the JSON that might contain "constraints" with a "λ_precondition" key.

    :return: str
        The full Python function definition as text.

    Example Usage:
        action = {
          "constraints": {
            "λ_precondition": {
              "logical": "A AND B",
              "constraints": ["A", "B"]
            }
          }
        }
        code = create_lambda_precondition(action)
        print(code)
        #   def λ_precondition(scene, sample):
        #       return A(scene, sample) and B(scene, sample)
    """
    condition = action['condition']
    lambda_def = f"def λ_precondition{action['id']}(scene, sample):\n"
    logical_expr = condition['logic']

    if not logical_expr:
        return lambda_def + "    return None  # No logical expression provided\n"

    logical_expr = synthesize_conditionals(logical_expr)

    for c in condition['constraints']:
        logical_name = c['id']
        constraint_name = c['constraint']
        verify_call = f"{logical_name + str(action['id'])}(simulation(), sample)"
        logical_expr = logical_expr.replace(logical_name, verify_call)

    lambda_def += f"    return {logical_expr}\n"
    return lambda_def


def generate_all_constraints_and_lambdas(example):
    """
    Given a JSON-like dictionary 'example' with a list of actions, this function:

      1. Iterates through each action (by index).
      2. Prints a block of Python code that defines the constraints (via 'create_constraint_definitions').
      3. Prints out the generated Python function for λ_precondition (if any).
      4. Prints out the generated Python function for λ_dest (if any).
      5. Prints out the generated Python function for λ_termination (if any).

    This is mostly a "debug" or demonstration function to show the user
    which constraints are being defined and how the lambda-based logic is constructed.

    :param example: dict
        A dictionary that includes "actions", each with potential "constraints",
        e.g.:
        {
          "actions": [
            {
              "id": "moveTo",
              "constraints": {
                "λ_dest": { "logical": "IF A THEN B ELSE (C AND D)", ... },
                ...
              },
              ...
            }
            ...
          ]
        }

    :return: None
        (Prints output directly.)

    Example Usage:
        my_data = {...}
        generate_all_constraints_and_lambdas(my_data)
    """
    nodes = example["nodes"]
    edges = example['edges']

    program = []

    for action in nodes:
        # print(f"### Constraints and Lambda Functions for Action {i + 1}: {action['id']}")
        # print(f"action: {action}")

        # # Step 1: Print the constraint definitions for the current action
        # constraint_definitions = create_constraint_definitions(i, example)
        # if constraint_definitions:
        #     print(constraint_definitions)
        # else:
        #     print("No Constraint Definitions.")

        # if 'target' in action.keys():
        #     # Generate and print λ_dest function definition
        #     if 'constraints' in action['target'].keys():
        #         lambda_dest_code = create_lambda_dest(action)
        #         program.append(lambda_dest_code)

        if 'termination' in action.keys():
            if 'logic' in action['termination'].keys():
                # Generate and print λ_termination function definition
                lambda_termination_code = create_lambda_termination(action)
                program.append(lambda_termination_code)

    for edge in edges:
        if edge['condition']['logic'] != 'None':
            # Generate and print λ_precondition function definition
            lambda_precondition_code = create_lambda_precondition(edge)
            program.append(lambda_precondition_code)

    return "\n".join(program)



def load_cache():
    """Load cached documentation from a JSON file."""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_cache(cache):
    """Save the cache dictionary to a JSON file."""
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)

def fetch_documentation(url, cache):
    """
    Fetch documentation content from a URL.
    If available in the cache, use that instead.
    """
    if url in cache:
        print("Using cached documentation.")
        return cache[url]
    else:
        print("Fetching documentation from URL.")
        response = requests.get(url)
        if response.status_code == 200:
            cache[url] = response.text
            save_cache(cache)
            return response.text
        else:
            raise Exception(f"Failed to fetch URL content. Status code: {response.status_code}")

def ask_question_using_cache(doc_text, question, json = False):
    """
    Ask ChatGPT a question using the cached documentation.
    The cached documentation (or an excerpt of it) is sent along with the question.
    """
    # Truncate if necessary to avoid token limits
    doc_excerpt = doc_text
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant that uses provided documentation as a reference."},
        {"role": "user", "content": f"Here is the cached documentation:\n\n{doc_excerpt}"},
        {"role": "user", "content": question}
    ]
    
    chat = client.chat.completions.create(
            model="o4-mini",
            messages=messages,
            response_format={'type': 'json_object' if json else 'text'}
        )
    return chat.choices[0].message.content

def load_python_file_as_string(file_path: str) -> str:
    """
    Load the contents of a Python file as a string.

    Args:
        file_path (str): The path to the Python file.

    Returns:
        str: The contents of the file as a string.
    """
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()

def prepend_text_to_file(existing_file_path, new_file_path, text_to_prepend):
    """
    Prepend a given string to the beginning of a file.
    
    Parameters:
        file_path (str): The path to the file.
        text_to_prepend (str): The text to add at the beginning of the file.
    """
    # Read the original contents of the file
    with open(existing_file_path, 'r', encoding='utf-8') as file:
        original_content = file.read()
    
    # Write the new text followed by the original content
    with open(new_file_path, 'w', encoding='utf-8') as file:
        file.write(text_to_prepend + "\n" + original_content)

def translate(file_name, dir, tactical_mr_dir):
    # user_name = "user1"
    # OUT_DIR = 'exports/user_study'
    # file_name = f"{OUT_DIR}/{user_name}-first-synthesized-program"+'.json'

    with open(file_name, 'r') as json_file:
        data = json.load(json_file)

    output = construct_coach_behavior(data['nodes'][0], data, program={})

    program = "\n".join(output['behavior']) + '\n'
    program += create_constraint_definitions(data) + '\n'
    program += "\n".join(output['target']) + '\n'
    program += "\n".join(output['termination']) + '\n'
    program += "\n".join(output['precondition']) + '\n'
    # program += generate_all_constraints_and_lambdas(data)
    # print(program)

    remainder = create_constraint_definitions(data) + '\n'
    remainder += "\n".join(output['target']) + '\n'
    remainder += "\n".join(output['termination']) + '\n'
    remainder += "\n".join(output['precondition']) + '\n'
    # remainder += generate_all_constraints_and_lambdas(data)


    system_instruction = """
        You are an expert Scenic code generator.
        You are provided with 
        (1) a documentation on Scenic programming language,
        (2) a Scenic program,
        (3) a library of APIs modeling Scenic behaviors, and
        (4) a library of APIs modeling physical constraints

        Your task is to explain the Scenic program by inserting a succinct description (within 20 words) of each line of code within
        the defined "behavior CoachBehavior():" block. To do so, you need to understand the annotations of all the APIs and the program first.
        
        Then, for each line of description, please provide it in the following format:
        do Speak("description of a line of code below"). For example, suppose a given Scenic program is:
        
        behavior CoachBehavior():
            do MoveTo(λ_target0) until λ_termination0(simulation(), None)
            do Idle() until λ_precondition_0(simulation(), None)

        A1termination_0 = MakePass({'player': 'teammate'})
        A1target_0 = HorizontalRelation({'obj': 'Coach', 'ref': None, 'relation': 'left', 'horizontal_threshold': {'avg': 5, 'std': 0.0}})
        A2target_0 = HorizontalRelation({'obj': 'Coach', 'ref': None, 'relation': 'right', 'horizontal_threshold': {'avg': 5, 'std': 0.0}})
        A1precondition_0 = MakePass({'player': 'teammate'})
        A2precondition_0 = HasBallPossession({'player': 'Coach'})
        
        def λ_target0(scene, sample):
            return A1target_0(simulation(), sample) or A2target_0(simulation(), sample)
        
        def λ_termination0(scene, sample):
            return A1termination_0(simulation(), None)

        def λ_precondition0(scene, sample):
            return (A1precondition_0(simulation(), sample) and A2precondition_0(simulation(), sample))

        def λ_precondition_0(scene, sample):
            return λ_precondition0(simulation(), sample)

        For this program, you should output a Scenic program of the following form:
        
        behavior CoachBehavior():
            do Speak("move to either left or right by more than 5 meters until teammate passes to you")
            do MoveTo(λ_target0()) until λ_termination0(simulation(), None)
            do Speak("wait until teammate passes and you have ball possession")
            do Idle() until λ_precondition_0(simulation(), None)

        Note that you should keep the given program intact and only insert explanation of each line of code in the behavior function. 
        Provide the explanation above each line. The explanation should also include some information about the parameters of constraints.
        Note that, in the example, I mentioned that "move to either left or right by more than 5 meters"
        Provide enough details within 20 words such that non-programmers can understand what is going on by listening to your description
        which will be verbalized through SpeakAction. Your explanation is supposed to be read back to a soccer coach who knows nothing about 
        coding. Do not use high level language. Use the language as annotated in the APIs but in a way that soccer coaches can understand.
        round up any numbers you report in the explanation to the nearest integer. 

        Respond ONLY with raw Scenic code. DO NOT use markdown or any comments.


    """

    # URL for the documentation (example: the README for the 'requests' library)
    doc_url = "https://docs.scenic-lang.org/en/latest/tutorials/dynamics.html"

    # Load existing cache (or initialize an empty cache)
    cache = load_cache()

    # Fetch the documentation using the cache mechanism
    documentation = fetch_documentation(doc_url, cache)

    action_library = load_python_file_as_string(dir + '/baseline/baseline_behavior.scenic')
    constraint_library = load_python_file_as_string(dir + '/baseline/baseline_api.py')

    entries = [
        Chat.Entry(role='system', text=system_instruction),
        Chat.Entry(role='user', text= "documentation of Scenic programming language: " + documentation),
        Chat.Entry(role='user', text= "a library of Scenic behaviors: " + action_library),
        Chat.Entry(role='user', text= "a library of constraints APIs: " + constraint_library),
        Chat.Entry(role='user', text= "a Scenic program: " + program)
    ]

    chat = Chat(client, model='o4-mini')
    output = chat(entries, json=False)

    header = ["from scenic.simulators.unity.actions import *", "from scenic.simulators.unity.behaviors import *", "from scenic.simulators.unity.constraints import *", 
          "model scenic.simulators.unity.model", "import trimesh", "from scenic.core.regions import MeshVolumeRegion", "import random"]

    full_program = "\n".join(header)+'\n'+ output+'\n'+remainder
    existing_file_path = tactical_mr_dir + '/Scenic-main/examples/unity/user-study-program-check.scenic'
    new_file_path = tactical_mr_dir + '/Scenic-main/examples/unity/user-synthesized-program.scenic'
    prepend_text_to_file(existing_file_path, new_file_path, full_program)
    print("PROGRAM TRANSLATION COMPLETED")
    return full_program

def main():
    """
    Example driver function to demonstrate usage of the translator.
    You can rename or remove this if you prefer to manage these calls elsewhere.
    """
    example = {
        "actions": [
            {
                "id": "Idle",
                "args": {
                    "precondition": "λ_precondition"
                },
                "constraints": {
                    "λ_precondition": {
                        "logical": "A AND B",
                        "constraints": ["A", "B"],
                        "args": {
                            "A": {
                                "type": "InZone",
                                "args": {
                                    "zone":  "C1"
                                }
                            },
                            "B": {
                                "type": "HasAngle",
                                "args": {
                                    "ref": "player",
                                    "r": 1.5
                                }
                            }
                        }
                    }
                }
            },
            {
                "id": "moveTo",
                "args": {
                    "dest": "λ_dest",
                    "until": "λ_termination"
                },
                "constraints": {
                    "λ_dest": {
                        "logical": "IF A THEN B ELSE (C AND D)",
                        "constraints": ["A", "B", "C", "D"],
                        "args": {
                            "A": {
                                "type": "IsVisible",
                                "args": {
                                    "target": "goal"
                                }
                            },
                            "B": {
                                "type": "DistanceLessThan",
                                "args": {
                                    "target": "goal",
                                    "distance": 3.0
                                }
                            },
                            "C": {
                                "type": "InZone",
                                "args": {
                                    "zone": "C3"
                                }
                            },
                            "D": {
                                "type": "HasAngle",
                                "args": {
                                    "ref": "opponent",
                                    "r": 2.0
                                }
                            }
                        }
                    },
                    "λ_termination": {
                        "logical": "(E AND F) OR (G AND H)",
                        "constraints": ["E", "F", "G", "H"],
                        "args": {
                            "E": {
                                "type": "InZone",
                                "args": {
                                    "zone": "C4"
                                }
                            },
                            "F": {
                                "type": "IsVisible",
                                "args": {
                                    "target": "teammate"
                                }
                            },
                            "G": {
                                "type": "DistanceGreaterThan",
                                "args": {
                                    "target": "player",
                                    "distance": 1.5
                                }
                            },
                            "H": {
                                "type": "HasAngle",
                                "args": {
                                    "ref": "goal",
                                    "r": 3.5
                                }
                            }
                        }
                    }
                }
            },
            {
                "id": "Idle",
                "args": {
                    "precondition": "λ_precondition"
                },
                "constraints": {
                    "λ_precondition2": {
                        "logical": "C AND D",
                        "constraints": ["C", "D"],
                        "args": {
                            "C": {
                                "type": "InZone",
                                "args": {
                                    "zone": "C5"
                                }
                            },
                            "D": {
                                "type": "DistanceLessThan",
                                "args": {
                                    "target": "goal",
                                    "distance": 2.0
                                }
                            }
                        }
                    }
                }
            },
            {
                "id": "passTo",
                "args": {
                    "target": "teammate"
                },
                "constraints": {
                    "λ_dest": {
                        "logical": "A AND B",
                        "constraints": ["A", "B"],
                        "args": {
                            "A": {
                                "type": "IsVisible",
                                "args": {
                                    "target": "teammate"
                                }
                            },
                            "B": {
                                "type": "DistanceLessThan",
                                "args": {
                                    "target": "teammate",
                                    "distance": 4.0
                                }
                            }
                        }
                    }
                }
            }
        ]
    }

    behavior_code = construct_coach_behavior(example['nodes'][0], example, program={})
    print(behavior_code)

    generate_all_constraints_and_lambdas(example)


# if __name__ == "__main__":
#     main()

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python translator.py <input_json_path> <project_root_dir> <tactical_mr_dir>")
        sys.exit(1)

    file_path = sys.argv[1]         # path to the synthesized JSON file
    root_dir = sys.argv[2]          # path to your project root directory (e.g., where `baseline/` is)
    tactical_mr_dir = sys.argv[3]   # path to your Unity Scenic project directory

    # Call the translation process
    result = translate(file_path, root_dir, tactical_mr_dir)
    print(result)
