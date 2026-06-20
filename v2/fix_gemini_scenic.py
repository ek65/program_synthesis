import json
from nlp_utils import Chat, client
from api_utils import API
import nlp_utils_gemini as gemini_utils


class Fix_Gemini_Scenic:
    """
    Fixes a Scenic program using instructor feedback and access to Scenic documentation.

    Args:
        scenic_code (str): The original Scenic code to be fixed.
        feedback (str): Instructor feedback on what needs to change.
        scenic_docs_url (str): URL to Scenic language/API documentation.
    """

    def __init__(self, scenic_code: str, feedback: str, scenic_docs_url: str, api, context: str, synth_demo, demos, use_synth_demo: bool = True):
        self.scenic_code = scenic_code
        self.feedback = feedback
        self.scenic_docs_url = scenic_docs_url
        self.api = api
        self.constraintAPI = api[API.constraints]
        self.actionAPI = api[API.actions]
        self.context = context
        self.synth_demo = synth_demo
        self.demos = demos
        self.use_synth_demo = use_synth_demo
        # print(self.constraintAPI)
        # print(self.actionAPI)
# - 'Coach Feedback': A text narration pointing out the issue with the coach behavior.
    def build_prompt(self) -> str:
        return f"""
You are a helpful coding assistant. Your task is to help fix a program written in Scenic probabilistic programming language based on a feedback.
The Scenic is a domain-specific language for modeling and simulating physical scenarios in simulation.

Previously, you modeled (i.e. generated) the CoachBehavior() in the program based on a set of narrated demonstrations (i.e. demonstrations accompanied by narrations) from a coach. 
We provide you the recordings and the transcripts of the narrated demonstrations for reference. This is meant to be used to provide you the context for the coach's feedback. 
However, depending on the feedback, this set of narrated demonstrations may not be useful in such as case please ignore it. 

Here, the coach now provides feedback specifically regarding modeled CoachBehavior of the program, after watching a video of the program's execution in simulation.
In the simulation, you will see different agents including the coach avatar (named as '{self.api[API.default_obj]}') being controlled by the program, e.g. coach avatar is controlled by the CoachBehavior() function.
You will be provided with this video that coach commented on, and the transcript of the coach's feedback along with the narration from the program. 
For context, during simulation, the program provides a narration and demonstration of the coach's behavior. As you will see, the "Speak" action is invoked in the 
CoachBehavior() to narrate. This narration is included in the transcript we provide to you. 

When reading the transcript, you will need to differentiate between the coach's feedback and the narration from the program.
This should be easy because the speak action is acting like a debug print statements that you can reference to debug the program
In particular, by comparing the transcript and the texts within Speak actions in the program, you should be able to identify what's coach's feedback 
and to which line of the program the coach is providing the feedback. 

You are given:
- 'Full Scenic Code' which models a soccer scenario with agents and their behaviors.
- 'Scenic Code Snippet': This is the part of the full Scenic code, which models the coach behavior, and is the part that needs to be fixed based on the coach's feedback.
   You should only modify this code snippet, and leave the rest of the code intact.
- 'Scenic Documentation': This is a documentation regarding Scenic syntax and semantics: {self.scenic_docs_url}
- 'Actions and Constraint APIs': A library of APIs for defining action space and constraints to model coach behavior. Do not create new APIs, only use the ones in this library.
- 'Video and Transcript': This is the video of the simulation run that the coach watched, and the transcript of the narration from the program and the coach's feedback:
    a)IMPORTANT: The transcript contains coach's feedback
- 'Original Narrated Demonstrations': This contains a set of videos and corresponding transcripts of narrated demonstrations from the coach that is previously used to model the CoachBehavior() in the program.
        These transcripts consists only of what the coach said, and videos showing the coach performing the task.
- 'Scenic Program Structure': The CoachBehavior() code represents a finite state machine (FSM)
        - Nodes are represented as: "do actionAPI until termination_condition"
        - Edges are represented as: "do Idle() until precondition" (constraintAPI)
        - the termination and pre-conditions are modeled using the APIs related to constraints 

Your Task:
- Modify only the CoachBehavior() and the lambda functions it uses (with the constraints) to address the instructor's feedback.
- Only change what is needed to resolve the issues raised.
- Preserve the original structure and logic as much as possible.
- Use valid Scenic syntax and semantics — check the documentation if needed.
- Only use valid constraints and actions as specified in APIs
- Do not add unrelated objects or behaviors.
- Provide comments *in the code* explaining what was changed and why.

Output Format:
1. First explain briefly:
   - What the feedback was.
   - What exactly you changed in the Scenic code.
2. Then output only the fixed Scenic code, CoachBehavior() with supporting lambda functions and constraints, as valid Python-style code. Don't rearange code, unless that's the fix. If you keep some parts they should be in the same place.

IMPORTANT NOTES about code structure:
1) Please always start 'CoachBehavior():' block with do Idle() for 3 seconds; so before the first do Speak line we have to have do Idle() for 3 seconds
2) Each action should be preceded by a correct precondition: either 'do Idle() until precondition', or if we have multiple preconditions leading to different actions we should have if/else structure.
3) Anytime the CoachBehavior() ends please finish with a line do Idle(); do Idle() should always be the last action Coach is doing

""".strip()

    def run(self):
        chat = gemini_utils.Chat(model="gemini-2.5-pro")
        messages = [
            gemini_utils.Chat.Entry("system", self.build_prompt()),
            gemini_utils.Chat.Entry("user", f"Snippet of the Scenic program that you need to fix:\n{self.scenic_code}"),
            gemini_utils.Chat.Entry("user", f"Full scenic program provided for context:\n{self.context}"),
            # gemini_utils.Chat.Entry("user", f"Instructor Feedback:\n{self.feedback}"),
            gemini_utils.Chat.Entry(role='system', text='Library of actionAPIs:\n\n' + '\n\n'.join([f'[API ID] {i}\n{c.doc()}' for i, c in self.actionAPI.items()])),
            gemini_utils.Chat.Entry(role='system', text='Library of constraintAPIs:\n\n' + '\n\n'.join([f'[API ID] {i}\n{c.doc()}' for i, c in self.constraintAPI.items()]))
            # gemini_utils.Chat.Entry(role='user', text="Transcripts from the original narrated demonstrations:\n" + "\n---\n".join(demo.language for demo in self.demos)),
            # gemini_utils.Chat.Entry(role='user', text="Transcript(s) from the video(s) that the coach provided feedback for:\n" + "\n---\n".join(self.synth_demo.language)),
        ]

        messages.extend(
        gemini_utils.Chat.Entry(role='user', text=f"Transcript from original narrated demonstration {i+1} (these indicies match the indicies of the vidoes that are given later):\n{demo.language}")
        for i, demo in enumerate(self.demos))
        i = 0
        for demo in self.demos:
            if demo.video_bytes: 
                messages.append(
                gemini_utils.Chat.Entry(
                    role='user',
                    text=f"Original video of the instructor performing the task. Original Narrated Demonstration {i+1}.",
                    file=(f"original_video_{i+1}.mp4", demo.video_bytes)  # Gemini gets filename + byte content
                )
                )
                i += 1
        if self.use_synth_demo:
            synth_demos = getattr(self, 'synth_demo', [])
            if not isinstance(synth_demos, list):
                synth_demos = [synth_demos] if synth_demos else []

            for i, demo in enumerate(synth_demos):
                messages.append(
                    gemini_utils.Chat.Entry(
                        role='user',
                        text=(
                            f"Transcript(s) from synthesized narrated demonstration {i+1}, THIS CONTAINS FEEDBACK you want to implement in code "
                            f"(these indices match the indices of the synthesized videos that are given later):\n{demo.language}"
                        )
                    )
                )
            i = 0
            for demo in synth_demos:
                if demo.video_bytes: 
                    messages.append(
                    gemini_utils.Chat.Entry(
                        role='user',
                        text=f"Synthesized video on which the feedback is based on {i+1}.",
                        file=(f"synth_video{i+1}.mp4", self.synth_demo.video_bytes)  # Gemini gets filename + byte content
                    )
                    )
                    i += 1

        # for entry in messages:
        #     print(f"Role: {entry.role}")
        #     print(f"Text:\n{entry.text}")
        #     print("=" * 40)

        response = chat(messages)
        fixed_code = self.extract_code(response)
        return fixed_code, response

    def extract_code(self, text: str) -> str:
        """Extract Scenic code block from model response."""
        try:
            # Find first triple backtick block for code
            start = text.index("```")
            end = text.index("```", start + 3)
            return text[start+3:end].strip()
        except ValueError:
            return text.strip()