import json
from nlp_utils import Chat, client
from api_utils import *

class Fix_Gemini_Simple:
    """
    Fixes a Finite State Machine (FSM) using instructor feedback and contextual domain knowledge.

    Args:
        fsm_json (dict): The original FSM to be fixed.
        feedback (str): Instructor feedback after viewing the Unity simulation.
        api (dict): Dictionary with keys:
            - API.domain: domain name (e.g., "soccer")
            - API.default_obj: main actor (e.g., "Coach")
            - API.actions: allowed actions (dict)
            - API.constraints: allowed constraints (dict of Constraint objects with .doc())
    """

    def __init__(self, fsm_json: dict, feedback: str, api:  dict[API: any]):
        self.fsm_json = fsm_json
        self.feedback = feedback
        self.api = api

    def build_prompt(self) -> str:
        actions = ", ".join([f"'{a}'" for a in self.api[API.actions].keys()])
        constraints = "\n\n".join([f"[{i}] {c.doc()}" for i, c in self.api[API.constraints].items()])
        domain = self.api[API.domain]
        actor = self.api[API.default_obj]

        return f"""
You are a helpful assistant tasked with fixing a Finite State Machine (FSM) that was used to generate a Scenic script for Unity.

### Context:
- Domain: {domain}
- Main actor: {actor}
- The FSM defines a behavior for the main actor in the simulation.
- The FSM was used to generate a Scenic program for Unity.
- An instructor watched the simulation and provided feedback on what was incorrect or needs improvement.

### Legal Setup:
- Allowed actions: [{actions}]
- You may only use these actions — do NOT invent new ones.
- Allowed constraint APIs (with parameters): 
{constraints}

These APIs can be used in the `target`, `termination`, or `condition` fields inside the FSM. Each constraint must have:
- a unique ID (e.g., "A1", "A2"),
- a valid API name (must be one from the list),
- correct parameter structure (omit optional params if not specified).

Use logical operators (AND, OR, NOT) if multiple constraints are used. Do not include dummy numerical values or placeholders.

### Your Job:
Given:
1. The original FSM.
2. The instructor's feedback.

Return a corrected FSM that addresses the feedback while:
- Modifying **only** the parts clearly required by the feedback.
- Keeping the FSM structure, field names, and format identical.
- Not inventing or deleting nodes/transitions unless absolutely necessary and justified.
- Not duplicating reasoning already covered by another field.
- Providing reasoning for each constraint you define.

---

### FSM Format (You MUST follow this structure):

Each node:
{{
  "id": "string",
  "action": "string",
  "info": "string",
  "t": {{ "demo_*": int }},
  "synthesized": true,
  "target": {{
    "info": "string",
    "logic": "A1",  // OR (A1 AND A2) etc.
    "map": ["A1"],
    "constraints": [
      {{
        "id": "A1",
        "constraint": "API_Name",
        "args": {{ ... }}
      }}
    ],
    "reasoning": "string"
  }},
  "termination": {{
    "info": "string",
    "logic": "A1",
    "map": ["A1"],
    "constraints": [ ... ],
    "reasoning": "string"
  }}
}}

Each edge:
{{
  "id": int,
  "prev": "string",
  "next": "string",
  "priority": "string",
  "t": int OR {{ "demo_*": int }},
  "synthesized": true,
  "condition": {{
    "info": "string",
    "logic": "A1",
    "map": ["A1"],
    "constraints": [ ... ]
  }}
}}

---

### Output Format:
1. First explain:
   - What the instructor's feedback said.
   - What you changed in the FSM to address it.
2. Then return the corrected FSM JSON only.
""".strip()

    def run(self):
        chat = Chat(client, model="gpt-4o")
        messages = [
            Chat.Entry("system", "You are a helpful assistant that corrects FSMs for Unity simulation based on instructor feedback."),
            Chat.Entry("user", self.build_prompt()),
            Chat.Entry("user", f"Original FSM:\n{json.dumps(self.fsm_json, indent=2)}"),
            Chat.Entry("user", f"Instructor Feedback:\n{self.feedback}")
        ]
        response = chat(messages)
        fixed_fsm = self.extract_fsm(response)
        return fixed_fsm, response

    def extract_fsm(self, text: str) -> dict:
        try:
            start = text.index('{')
            end = text.rindex('}') + 1
            return json.loads(text[start:end])
        except Exception as e:
            print("Failed to parse FSM JSON:", e)
            return {}