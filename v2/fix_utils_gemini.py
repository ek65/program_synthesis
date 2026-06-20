import json
from tqdm import tqdm

from nlp_utils import Chat
from nlp_utils import client


class Fix_Gemini:
    """
    Orchestrates the FSM fixing process using human feedback.
      - fsm_json: dict representing the current FSM
      - script: comprehensive script describing every second of the video
      - original_demos: list of original narrated demonstrations (Demo objects)
      - api: dictionary of APIs (optional)
    """
    def __init__(self, fsm_json: dict, script: str, original_demos: list, api: dict, example_fsm: dict):
        self.fsm_json = fsm_json
        self.script = script
        self.original_demos = original_demos
        self.api = api
        self.example_fsm = example_fsm

    def build_prompt(self) -> str:
        """
        Constructs a detailed prompt for ChatGPT to fix the FSM based on a comprehensive script and original demonstrations.
        """
        return f"""
You are a helpful assistant improving a Finite State Machine (FSM) that represents a behavior learned from narrated demonstrations.

You are provided with:
(1) A FSM in JSON format.
(2) A comprehensive natural language script of the behavior (every second described).
(3) The original narrated demonstrations, including video frames, transcripts, and pause timestamps.
(4) A library of APIs describing allowed actions and semantics.
(5) A list of the available objects in the physical environment.

Your task is to:
- Fix the FSM structure based on the corrected behavior script and other inputs.
- DO NOT invent new actions unless strongly implied in the script.
- Fix ONLY the parts of the FSM that you explicitly identify as problematic.
- Do not invent or remove nodes unless the script directly contradicts them.
- Do not add new transitions or change node structure beyond the minimal required fix.
- Maintain all field formats (e.g., 'target', 't', 'termination') as in the original FSM.
- Only return a corrected FSM JSON with changed fields marked or annotated if needed.
- Pay close attention to timing and causality.

First identify in words what is the problem. Then which part of the graph is resonsible and your change. Then return the corrected FSM in JSON format.
""".strip()
    
    

    def run(self):
        chat = Chat(client, model="gpt-4o")

        messages = [
            Chat.Entry("system", "You are a helpful assistant that corrects FSMs based on narrated demonstrations and a comprehensive behavior script."),
            Chat.Entry("user", self.build_prompt()),
            Chat.Entry("user", f"Example FSM (fromat to follow):\n {json.dumps(self.example_fsm, indent=2)}"),
            Chat.Entry("user", f"FSM to fix:\n{json.dumps(self.fsm_json, indent=2)}"),
            Chat.Entry("user", f"Comprehensive script:\n{self.script}")
        ]

        # Add all original demos (transcript + pause timestamps + frames)
        for demo in self.original_demos:
            if demo.language:
                messages.append(Chat.Entry("user", f"Narrated transcript:\n{demo.language}"))
            if hasattr(demo, 'pause_times') and demo.pause_times:
                pause_info = "Pause timestamps (instructor explaining next step):\n"
                for pause_time in demo.pause_times:
                    pause_info += f"- {pause_time:.2f}s\n"
                messages.append(Chat.Entry("user", pause_info))
            if demo.video:
                frame_paths = demo.video.frame_dir  # list of frame image paths
                messages.append(Chat.Entry("user", "Video as a sequence of frame images:", imgs_paths=frame_paths))

        response = chat(messages)
        fixed_fsm = self.extract_fsm(response)
        return fixed_fsm, response

    def extract_fsm(self, text: str) -> dict:
        """
        Attempt to extract corrected FSM JSON from LLM output.
        """
        try:
            start = text.index('{')
            end = text.rindex('}') + 1
            json_str = text[start:end]
            return json.loads(json_str)
        except Exception as e:
            print(" Failed to parse FSM JSON:", e)
            return {}