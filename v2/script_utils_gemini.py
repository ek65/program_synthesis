import json
from tqdm import tqdm

from nlp_utils_gemini import Chat
from api_utils import API

class ScriptGenerator:
    def __init__(self, model: str = "gemini-2.5-flash-preview-05-20"):
        self.model = model
        self.chat = Chat(model)

    def build_prompt(self, demo, api):
        actions = ", ".join([f"'{a}'" for a in api[API.actions].keys()])
        objects = set(obj.type for obj in demo.scene.objects)

        prompt = f"""
You are a helpful assistant with expertise in interpreting video demonstrations.

You are provided with:
(1) A video (as bytes) of an instructor performing a task in the domain of {api[API.domain]}.
(2) A transcript of the instructor's narration.
(3) A list of all objects in the scene.
(4) The actions the instructor is allowed to perform.

Your task is to generate a **comprehensive narrated script** that:
- Includes a detailed description of **what happens every second** in the video.
- Aligns closely with the transcript (any spoken content **must appear** in the script). But if you are not sure then don't make up allignment. Once \'TRANScRIPTION PROCESSING\' vsibile no narration ever happens. Any changes of color mean the instructor highlights the spot (might indicate that talks about this character etc.)
- Mentions key actions, spatial relationships, and object interactions.
- Captures visual cues if noticeable (e.g., "instructor points at the goal").
- Quantifies actions when possible (e.g., distances, timing).
- Put at last second +1 whole transcript

Constraints:
- Do NOT invent new events or actions.
- Use only the following available actions: [{actions}].
- Refer to objects by explicit names, not pronouns.
- If unsure, say "unclear in video".

Objects in the environment: {', '.join(objects)}

Return your output as a JSON list where each entry looks like this:
{{
  "second": int,            // The second of the video
  "description": str        // What happens during that second
}}
        """
        return prompt.strip()

    def run(self, demos, api):
        if not isinstance(demos, list):
            demos = [demos]

        results = []
        for d in tqdm(demos, desc="Generating comprehensive scripts"):
            prompt = self.build_prompt(d, api)

            entries = [
                Chat.Entry(role="user", text=prompt),
                Chat.Entry(role="user", text="Transcript: " + d.language)
            ]

            if d.video_bytes:
                entries.append(Chat.Entry(
                    role="user",
                    text="Video of the instructor performing the task.",
                    file=("video.mp4", d.video_bytes)
                ))

            if hasattr(d, 'pause_times') and d.pause_times:
                pause_info = "Pause timestamps (when instructor explains next step):\n"
                for pause_time in d.pause_times:
                    pause_info += f"- Timestamp: {pause_time:.2f}s\n"
                entries.append(Chat.Entry(role='user', text=pause_info))

            response = self.chat(entries, as_json=True)
            results.append(response)

        return results