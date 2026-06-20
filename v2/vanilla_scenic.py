import os
import json
import requests
from openai import OpenAI
from tqdm import tqdm
import nlp_utils
import nlp_utils_gemini as gemini_utils
from api_utils import API
from apiKey import OPENAI_API_KEY, GEMINI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

HEADER_LINES = [
    "from scenic.simulators.unity.actions import *",
    "from scenic.simulators.unity.behaviors import *",
    "from scenic.simulators.unity.constraints import *",
    "model scenic.simulators.unity.model",
    "import trimesh",
    "from scenic.core.regions import MeshVolumeRegion",
    "import random",
    "####HEADER ENDS####"
]

def get_im(path):
    with open(path, "rb") as im:
        return im.read()

def load_cache(cache_file="doc_cache.json"):
    if os.path.exists(cache_file):
        with open(cache_file, "r") as f:
            return json.load(f)
    return {}

def save_cache(cache, cache_file="doc_cache.json"):
    with open(cache_file, "w") as f:
        json.dump(cache, f)

def fetch_documentation(url, cache):
    if url in cache:
        print("Using cached Scenic documentation")
        return cache[url]
    else:
        print("Fetching Scenic documentation")
        response = requests.get(url)
        if response.status_code == 200:
            cache[url] = response.text
            save_cache(cache)
            return response.text
        else:
            raise Exception(f"Failed to fetch URL content: {response.status_code}")

def load_python_file_as_string(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()

def prepend_text_to_file(existing_file_path, new_file_path, text_to_prepend):
    with open(existing_file_path, 'r', encoding='utf-8') as file:
        original_content = file.read()
    with open(new_file_path, 'w', encoding='utf-8') as file:
        file.write(text_to_prepend + "\n" + original_content)

def generate_combined_program_from_demos(
    demos,
    example_demos,
    ex_script,
    api,
    tactical_mr_dir,
    use_gemini: bool = False,
    use_both: bool = False,
    openai_model: str = "gpt-5-mini",
    gemini_model: str = "gemini-2.5-pro"
):
    """
    Generate a combined Scenic program from demos using OpenAI, Gemini, or both.

    If use_both=True, calls both OpenAI and Gemini, saving two separate files.
    """
    print("Generating complete Scenic program from demos...")

    # Load documentation and APIs
    doc_url = "https://docs.scenic-lang.org/en/latest/tutorials/dynamics.html"
    cache = load_cache()
    doc_text = fetch_documentation(doc_url, cache)
    # behavior_lib = load_python_file_as_string(os.path.join(baseline_dir, "baseline/baseline_behavior.scenic"))
    # constraint_lib = load_python_file_as_string(os.path.join(baseline_dir, "baseline/baseline_api.py"))
    constraintAPI = api[API.constraints]
    print(constraintAPI)
    actionAPI = api[API.actions]
    print(actionAPI)

    # Prepare header and paths
    header = "\n".join(HEADER_LINES)
    # existing_path = os.path.join(tactical_mr_dir, "Scenic-main/examples/unity/robot/factory_demo2_program.scenic") ### factory setting
    #existing_path = os.path.join(tactical_mr_dir, "Scenic-main/examples/unity/user-study-program.scenic")
    existing_path = os.path.join(tactical_mr_dir, "Scenic-main/examples/unity/user-study-program-distribute.scenic")

    # Prepare message content
    actions = ", ".join(f"'{a}'" for a in api[API.actions].keys())
    # print(actions)
    all_objects = {f"{obj.label}" for demo in demos for obj in demo.scene.objects}         ####put this inside the prompt {', '.join(sorted(all_objects))} instead of {all__objects}
    # all__objects = ['goal', 'Coach', 'teammmate', 'opponent', 'ball']
    system_instruction = f"""
You are a coding assistant with in-depth knowledge of the following physical domain: {api[API.domain]}.

You are given a set of narrated demonstrations, i.e. narration accompanied by demonstrations, by an expert coach/instructor in {api[API.domain]} domain. 
In the narrated demonstrations, the coach provides variations of how to solve a particular tactical situation in coordination with surrounding players. 
Your task is to model the coach's behavior in Scenic programming language. Note that Scenic language is embedded in Python, meaning that
it inherits Scenic syntax and semantics.

Your synthesized program will be used in the following way:
Once you model the coach's behavior from narrated demonstrations as a Scenic program, we will execute this program in a simulated environment which will control an avatar of the coach.
We want this coach avatar to teach other human players of physical coordination skills. This means, your synthesized coach behavior should not only demonstrate but also 
narrate the actions and preconditions in a way that is easy to understand for humans.

You are provided with the following information:
(1) the coach's narrated demonstrations consisting of a transcript of narration and a video of an instructor performing the task (both video mp4 file and image frames are provided)),
(2) a library of APIs you can use for modeling actions and physical constraints,
(3) a documentation on the syntax and semantics of Scenic programming language.
(4) an example of Scenic script that models a separate set of example narrated demonstrations. 
This example is provided to you to help you understand the structure of the Scenic program you are going to generate.

In this setting, the surrounding players and their behaviors are prescripted in a Scenic program.
The coach avatar is also instantiated in the same Scenic program as "ego" object.
Your task is to generate a snippet of Scenic program, i.e. the CoachBehavior block.
This behavior block you generate will be concatenated with the existing Scenic program. 
So, do not include any other code in your output.

You should output the following:
(i) A behavior block 'behavior CoachBehavior():' using the actions and constraints APIs provided to you. Do *not* create new actions or constraints.
(ii) Reference the CoachBehavior in the example Scenic script to understand the structure of the Scenic program you are going to generate.
     The structure of the CoachBehavior is as follows:
     - The CoachBehavior starts with `do Idle() for 3 seconds`; so before the first do Speak line we have to have do Idle() for 3 seconds
     - The CoachBehavior ends with do Idle().
     - Each action should be preceded by a precondition for taking the action.
     - Each precondition should be in a form of 'do Idle() until precondition' or 'if/elif/else precondition: action'.
     - Each action and precondition should be preceded by a Speak(...) line except for the first line `do Idle() for 3 seconds` as shown in the example script.
     - The CoachBehavior has a sequence of actions and preconditions with Speak(...) lines in between as shown in the example script.
     - Speak(...) is invoked to explain the action or precondition in plain English first, before executing the action or precondition.
     - In the Speak(...) line, you want to teach human players how to take certain actions or what conditions to check in order to coordinate with other players.
       Thus, the Speak(...) line should be concise and informative, ideally consisting of 2-3 sentences describing:
       a) the rationale for taking an action or checking a precondition (if provided in the coach's narrations; otherwise, do *not* include rationale.)
       b) the action to execute or a set of conditions to check
       c) when describing an action, explain the numerical details of the action (round up the numerical values to nearest integer place).
          please refer to the example script to see how to describe the numerical details of the action.
          e.g. if the action is MoveTo(...), then you should explain the constraint over the destination of the action.
          e.g. if the action is Pass(...), then you should explain who or where to pass the ball to.
       d) when describing a precondition, explain the numerical details of the precondition (round up the numerical values to nearest integer place).
          please refer to the example script to see how to describe the numerical details of the precondition.
          the precondition may consists of conjunction, disjunction, or negation of constraints. In such a case, you should explain them 
          as concisely as possible with numerical details. Furthermore, the precondition may have multiple constraints leading to different actions.
          In such a case, we should have if/elif/else structure as shown in the example script.
       e) Speak(...) lines should describe as if the coach avatar is speaking to human players. The style of the Speak(...) lines should be like a coach 
          explaining the action or precondition as the coach oneself embodying the role of a player that the coach wants to teach. So, the coach should 
          refer to oneself as not 'Coach' but 'you' or 'your' as shown in the example script.
(iii) These are the names of the instantiated objects and players in the existing Scenic program. 
    Only use these objects' and players' names to reference objects (don’t declare new object or player names): {', '.join(sorted(all_objects))}

*IMPORTANT*: The λ_termination function must *not* represent the goal or intended outcome of the action itself because this termination condition is internally checked within the action itself.
Rather, the termination condition should encode a different constraint (if provided in narration; otherwise, do not include a termination condition).
For example, if the action is MoveTo(...) and the goal is to obtain a clear passing path, then λ_termination must not be HasPath(...).bool because HasPath is the desired outcome of the action.

Output only the code in text such that I can directly copy and paste it into the existing Scenic program.
Do not include any header like "```scenic". Your code needs to be executable after being copy-pasted into the existing Scenic program.
""".strip()

    # Build message entries for OpenAI
    openai_entries = [
        nlp_utils.Chat.Entry(role='system', text=system_instruction),
        nlp_utils.Chat.Entry(role='user', text="Scenic programming language documentation:\n" + doc_text),
        nlp_utils.Chat.Entry(role='system', text='Library of APIs for modeling actions:\n\n' + '\n\n'.join([f'[API ID] {i}\n{c.doc()}' for i, c in actionAPI.items()])),
        nlp_utils.Chat.Entry(role='system', text='Library of APIs for modeling physical constraints:\n\n' + '\n\n'.join([f'[API ID] {i}\n{c.doc()}' for i, c in constraintAPI.items()]))
        # nlp_utils.Chat.Entry(role='user', text="Narrated transcripts:\n" + "\n---\n".join(demo.language for demo in demos)),
        # nlp_utils.Chat.Entry(role='user', text="Example Narrated transcripts:\n" + "\n---\n".join(demo.language for demo in example_demos)),
        # nlp_utils.Chat.Entry(role='user', text="Example output script:\n" + ex_script)

    ]

    openai_entries.extend(
        nlp_utils.Chat.Entry(role='user', text=f"Transcript of narrated demonstration {demo.id} (these indicies match the indicies of the lists of frames that are given later):\n{demo.language}")
        for i, demo in enumerate(demos))

    for demo in demos:
        for idx, frame_path in enumerate(demo.video.frame_dir):
            openai_entries.append(
                nlp_utils.Chat.Entry(role='user', text=f"Demo {demo.id} - Frame {idx}", im=get_im(frame_path))
            )

        if hasattr(demo, 'pause_times') and demo.pause_times:
            pause_frames_info = "Pause frames (instructor explaining next action):\n"
            for pause_time in demo.pause_times:
                frame_idx = demo.video.time_to_frame_index(pause_time)
                if frame_idx < len(demo.video.frame_dir):
                    pause_frames_info += f"- Frame {frame_idx} (timestamp: {pause_time:.2f}s) for Demo {demo.id}\n"
            
            openai_entries.append(nlp_utils.Chat.Entry(role='user', text="Pauses in video:\n"+pause_frames_info))
    
    if not isinstance(example_demos, list):
        example_demos = [example_demos] if example_demos else []

    openai_entries.extend(
        nlp_utils.Chat.Entry(role='user', text=f"Transcript of an example narrated demonstration {demo.id} (these indices match the indices of the lists of frames that are given later):\n{demo.language}")
        for i, demo in enumerate(example_demos))

    for demo in example_demos:
        for idx, frame_path in enumerate(demo.video.frame_dir):
            openai_entries.append(
                nlp_utils.Chat.Entry(role='user', text=f"Example Demo {demo.id} - Frame {idx}", im=get_im(frame_path))
            )

        if hasattr(demo, 'pause_times') and demo.pause_times:
            pause_frames_info = "Pause frames (instructor explaining next action):\n"
            for pause_time in demo.pause_times:
                frame_idx = demo.video.time_to_frame_index(pause_time)
                if frame_idx < len(demo.video.frame_dir):
                    pause_frames_info += f"- Frame {frame_idx} (timestamp: {pause_time:.2f}s) for Demo {demo.id}\n"
            
            openai_entries.append(nlp_utils.Chat.Entry(role='user', text="Example Pauses in video:\n"+pause_frames_info))
    openai_entries.append(nlp_utils.Chat.Entry(role='user', text="Example output script:\n" + ex_script))

    # Build message entries for Gemini
    gemini_entries = [
        gemini_utils.Chat.Entry(role='system', text=system_instruction),
        gemini_utils.Chat.Entry(role='user', text="Scenic documentation:\n" + doc_text),
        gemini_utils.Chat.Entry(role='system', text='Library of actionAPIs:\n\n' + '\n\n'.join([f'[API ID] {i}\n{c.doc()}' for i, c in actionAPI.items()])),
        gemini_utils.Chat.Entry(role='system', text='Library of constraintAPIs:\n\n' + '\n\n'.join([f'[API ID] {i}\n{c.doc()}' for i, c in constraintAPI.items()]))
        # gemini_utils.Chat.Entry(role='user', text="Narrated transcripts:\n" + "\n---\n".join(demo.language for demo in demos)),
        # gemini_utils.Chat.Entry(role='user', text="Example Narrated transcripts:\n" + "\n---\n".join(demo.language for demo in example_demos)),
        # gemini_utils.Chat.Entry(role='user', text="Example output script:\n" + ex_script)
    ]

    gemini_entries.extend(
        gemini_utils.Chat.Entry(role='user', text=f"Transcript of narrated demonstration {demo.id} (these indicies match the indicies of the lists of frames (and videos) that are given later):\n{demo.language}")
        for i, demo in enumerate(demos))

    for demo in demos:
        for idx, frame_path in enumerate(demo.video.frame_dir):
            gemini_entries.append(
                gemini_utils.Chat.Entry(role='user', text=f"Demo {demo.id} - Frame {idx}", im=get_im(frame_path))
            )
        if hasattr(demo, 'pause_times') and demo.pause_times:
            pause_frames_info = "Pause frames (instructor explaining next action):\n"
            for pause_time in demo.pause_times:
                frame_idx = demo.video.time_to_frame_index(pause_time)
                if frame_idx < len(demo.video.frame_dir):
                    pause_frames_info += f"- Frame {frame_idx} (timestamp: {pause_time:.2f}s) for Demo {demo.id}\n"
            
            gemini_entries.append(gemini_utils.Chat.Entry(role='user', text="Pauses in video:\n"+pause_frames_info))

        if demo.video_bytes: 
                gemini_entries.append(
                gemini_utils.Chat.Entry(
                    role='user',
                    text=f"Video of the instructor performing the task. Demo {demo.id}",
                    file=(f"demo{demo.id}.mp4", demo.video_bytes)  # Gemini gets filename + byte content
                )
                )
    if not isinstance(example_demos, list):
        example_demos = [example_demos] if example_demos else []

    gemini_entries.extend(
        gemini_utils.Chat.Entry(role='user', text=f"Transcript of an example narrated demonstration {demo.id} (these indicies match the indicies of the lists of frames (and videos) that are given later):\n{demo.language}")
        for i, demo in enumerate(example_demos))
    
    for demo in example_demos:
        for idx, frame_path in enumerate(demo.video.frame_dir):
            gemini_entries.append(
                gemini_utils.Chat.Entry(role='user', text=f"Example Demo {demo.id} - Frame {idx}", im=get_im(frame_path))
            )
        if hasattr(demo, 'pause_times') and demo.pause_times:
            pause_frames_info = "Pause frames (instructor explaining next action):\n"
            for pause_time in demo.pause_times:
                frame_idx = demo.video.time_to_frame_index(pause_time)
                if frame_idx < len(demo.video.frame_dir):
                    pause_frames_info += f"- Frame {frame_idx} (timestamp: {pause_time:.2f}s)\n"
            
            gemini_entries.append(gemini_utils.Chat.Entry(role='user', text="Example Pauses in video:\n"+pause_frames_info))

        if demo.video_bytes: 
                gemini_entries.append(
                gemini_utils.Chat.Entry(
                    role='user',
                    text=f"Example Video of the instructor performing the task. Example Demo {demo.id}",
                    file=(f"example_demo{demo.id}.mp4", demo.video_bytes)  # Gemini gets filename + byte content
                )
                )
    gemini_entries.append(gemini_utils.Chat.Entry(role='user', text="Example output script:\n" + ex_script))

    results = {}
    # OpenAI run
    if not use_gemini or use_both:
        chat_openai = nlp_utils.Chat(client, model=openai_model)
        result_openai = chat_openai(openai_entries)
        full_openai = f"{header}\n\n{result_openai}"
        output_openai = os.path.join(tactical_mr_dir, "Scenic-main/examples/unity/user-synthesized-openai-with-example.scenic")
        prepend_text_to_file(existing_path, output_openai, full_openai)
        results['openai'] = output_openai

    # Gemini run
    if use_gemini or use_both:
        chat_gemini = gemini_utils.Chat(model=gemini_model)
        result_gemini = chat_gemini(gemini_entries)
        full_gemini = f"{header}\n\n{result_gemini}"
        output_gemini = os.path.join(tactical_mr_dir, "Scenic-main/examples/unity/user-synthesized-gemini-with-example.scenic")
        prepend_text_to_file(existing_path, output_gemini, full_gemini)
        results['gemini'] = output_gemini

    print(f"Scenic program(s) saved to {results}")
    return results







