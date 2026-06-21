import os
import json
import requests
import time
from openai import OpenAI
from tqdm import tqdm
import nlp_utils
import nlp_utils_gemini as gemini_utils
from api_utils import API
from apiKey import OPENAI_API_KEY, GEMINI_API_KEY
from syntax_checker import ScenicSyntaxChecker
from collections.abc import Iterable

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
    output_dir,
    tactical_mr_dir,
    use_gemini: bool = False,
    use_both: bool = False,
    openai_model: str = "gpt-5-mini",
    gemini_model: str = "gemini-2.5-pro",
    enable_syntax_check: bool = True,
    user_study_program_name: str = "check",
    pilot_name: str = "pilot_default",
    include_demos: bool = True,
    include_narrations: bool = True
):
    """
    Generate a combined Scenic program from demos using OpenAI, Gemini, or both.
    Automatically checks and fixes syntax issues in the generated files.

    If use_both=True, calls both OpenAI and Gemini, saving two separate files.
    """
    print("Generating initial Scenic program from demos...")

    # Load documentation and APIs
    doc_url = "https://docs.scenic-lang.org/en/latest/tutorials/dynamics.html"
    cache = load_cache()
    doc_text = fetch_documentation(doc_url, cache)
    constraintAPI = api[API.constraints]
    print(constraintAPI)
    actionAPI = api[API.actions]
    print(actionAPI)

    # Prepare header and paths
    header = "\n".join(HEADER_LINES)
    existing_path = os.path.join(tactical_mr_dir, f"Scenic-main/examples/unity/user-study-program-{user_study_program_name}.scenic")
    if not os.path.exists(existing_path):
        # Fall back to the scene-suffix templates bundled in this repo so synthesis
        # runs standalone, without a local TacticalMR checkout.
        existing_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "scenic_suffix",
            f"user-study-program-{user_study_program_name}.scenic",
        )

    if not isinstance(demos, Iterable):
        demos = [demos]

    # Prepare message content
    actions = ", ".join(f"'{a}'" for a in api[API.actions].keys())
    all_objects = {f"{obj.label}" for demo in demos for obj in demo.scene.objects}
    
    first_clause = {
        (True, True):  f"(1) a set of narration and demonstration pairs from an expert in {api[API.domain]}.\n"
                    "    The narration is provided as a transcript. The demonstrations are provided as a sequence of images.",
        (True, False): f"(1) a set of narrations from an expert in {api[API.domain]}.\n"
                    "    The narration is provided as a transcript. No demonstration is provided.",
        (False, True): f"(1) a set of demonstrations from an expert in {api[API.domain]}.\n"
                    "    The demonstrations are provided as a sequence of images.  No narration is provided."
    }.get((include_narrations, include_demos), "")

    system_instruction = f"""
You are a coding assistant with in depth knowlege of {api[API.domain]}.

You are given:
{first_clause}
(2) a library of APIs for modeling physical actions and constraints,
(3) a documentation on the Scenic programming language syntax and semantics.
(4) an example Scenic program to reference the style and the structure of coding. 

Your task is to model the expert's behavior as in a behavior funcion in Scenic programming language using the provided APIs. 
Note that Scenic is a programming language embedded in Python so it inherits Python syntax and semantics. 
No need to import any packages or statements. Assume that all the provided APIs are imported in the file. 
And, your output will be copied and pasted into the existing Scenic file which already has instantiated objects and players.

Guidelines:
  - Write a Scenic behavior called `behavior CoachBehavior():' along with constraint definitions outside the CoachBehavior() function.
  - The program should be structured in the same format as in the provided example Scenic program. 
  - The program structure represents a finite state machine (FSM):
    For context, the CoachBehavior() code structure should reflects a FSM, where:
        - Nodes are represented as: "do actionAPI until termination_condition" 
        - Edges are represented as: "do Idle() until precondition" (constraintAPI)
        - the termination and pre-conditions are modeled using the provided APIs on modeling constraints 
  - The actionAPIs consist of these actions: [{actions}]. Select from only within this action space. 
  - A 'do Speak("...")' line before each action and precondition (max 20 words) for a soccer coach:
        a) These 'do Speak("...")' have to describe the action or precondtion in plain English in the same style as shown in the example Scenic program. 
        b) We will execute the CoachBehavior() to have your modeled behavior narrate and demonstrate back what it learned. 
           Watching and listening to your code's execution, we will have the expert to give corrective feedback. 
           So, make sure that your speak action contains sufficient information about the code logic but in plain laymen's term such that
           experts without programming background can easily correct the code. 
           When possible you should use action's or precondition's input values that are important. 
  - All necessary constraint class instantiations, these should be instantiated *outside* the 'behavior CoachBehavior():' block
  - All λ_target, λ_termination, and λ_precondition functions, each defined explicitly, these should be instantiated *outside* the 'behavior CoachBehavior():' block
  - These are the names of the instantiated objects and players. Only use these objects' and players' names to reference objects (don't declare new object or player names): {', '.join(sorted(all_objects))}
  - When invoking APIs, make sure to reference objects or players by their names in "string" format as indicated in the API documentation. Do not use the objects directly. 
  - Make sure you abide by the API documentation's input argument types and formats. 
  - The CoachBehavior() function and the constraint definitions should be the only functions and constraints in the file. 
  - Unless otherwise stated that a parameter is optional, all the parameters of the APIs you invoke *must* be filled out in the correct type/format as defined in the API documentation.

IMPORTANT NOTES about code structure:
1) Please always start 'CoachBehavior():' block with do Idle() for 3 seconds, and end the function with do Idle() as shown in the example Scenic program.
2) The λ_termination function must not represent the goal or intended outcome of the action itself.
   For example, if the action is MoveTo(...) and the goal is to obtain a clear passing path, then λ_termination = HasPath(...).bool is invalid—because HasPath is the desired result of moving.
   Instead, termination should be triggered by an intermediate signal or condition indicating when the action should stop (e.g., a change in environment), not the success condition of the action.
2) Each action (except the first one and possibly THE FIRST ACTION AFTER THE FIRST do Speak line) should be preceded by a correct precondition: either 'do Idle() until precondition', or if we have multiple preconditions leading to different actions we should have if/elif/else structure as shown in the example Scenic program.
    a) IMPORTANT: Whenever you define a constraint, make sure it is possible to fulfill — especially constraints involving ball possession at the beginning of the scenario. For this reason, the first action after the first do Speak("...") line does not need a precondition.
    b) In case you create if/else structure, you can use if/elif/else. DO NOT USE else if, that would error!
    c) When using if/elif/else conditions, use 'do Speak("...")' to explain which condition is satisfied first, and then 
    in the immediate next line add another do Speak("...")' to explain the action that is to be taken in the following line as shown in the example Scenic program.

Please output a Scenic behavior function called CoachBehavior() along with constraint defintions that models the expert's behavior as described in the guidelines. 
Also, output the entire file as a string without any annotations, markdowns, backticks, or headers like ```scenic, ```python, ```, etc.
Make sure that I can copy and paste the output into the existing Scenic file and have it runnable.
""".strip()

    # Build message entries for OpenAI
    openai_entries = [
        nlp_utils.Chat.Entry(role='system', text=system_instruction),
        nlp_utils.Chat.Entry(role='user', text="Scenic documentation:\n" + doc_text),
        nlp_utils.Chat.Entry(role='system', text='Library of actionAPIs:\n\n' + '\n\n'.join([f'[API ID] {i}\n{c.doc()}' for i, c in actionAPI.items()])),
        nlp_utils.Chat.Entry(role='system', text='Library of constraintAPIs:\n\n' + '\n\n'.join([f'[API ID] {i}\n{c.doc()}' for i, c in constraintAPI.items()]))
    ]

    if include_narrations:
        openai_entries.extend(
            nlp_utils.Chat.Entry(role='user', text=f"Transcript {demo.id} (these indicies match the indicies of the lists of videos that are given later, e.g. transcript 1 is for video 1):\n{demo.language}")
            for i, demo in enumerate(demos))
    
    if include_demos:
        for demo in demos:
            for idx, frame_path in enumerate(demo.video.frame_dir):
                # print("frame_path: ", frame_path)
                openai_entries.append(
                    nlp_utils.Chat.Entry(role='user', text=f"Video {demo.id} - Frame {idx}", im=get_im(frame_path))
                )

        # NOTE: Indentation of the commented lines below could need refactoring.
        # print("Number of elements: ", len(demo.video.frame_dir))

        # if hasattr(demo, 'pause_times') and demo.pause_times:
        #     pause_frames_info = "Pause frames (instructor explaining next action):\n"
        #     for pause_time in demo.pause_times:
        #         frame_idx = demo.video.time_to_frame_index(pause_time)
        #         if frame_idx < len(demo.video.frame_dir):
        #             pause_frames_info += f"- Frame {frame_idx} (timestamp: {pause_time:.2f}s) for Demo {demo.id}\n"
            
        #     openai_entries.append(nlp_utils.Chat.Entry(role='user', text="Pauses in video:\n"+pause_frames_info))
    
    # if not isinstance(example_demos, list):
    #     example_demos = [example_demos] if example_demos else []

    # openai_entries.extend(
    #     nlp_utils.Chat.Entry(role='user', text=f"Transcript of an example narrated demonstration {demo.id} (these indicies match the indicies of the lists of frames that are given later):\n{demo.language}")
    #     for i, demo in enumerate(example_demos))

    # for demo in example_demos:
    #     for idx, frame_path in enumerate(demo.video.frame_dir):
    #         openai_entries.append(
    #             nlp_utils.Chat.Entry(role='user', text=f"Example Demo {demo.id} - Frame {idx}", im=get_im(frame_path))
    #         )

    #     if hasattr(demo, 'pause_times') and demo.pause_times:
    #         pause_frames_info = "Pause frames (instructor explaining next action):\n"
    #         for pause_time in demo.pause_times:
    #             frame_idx = demo.video.time_to_frame_index(pause_time)
    #             if frame_idx < len(demo.video.frame_dir):
    #                 pause_frames_info += f"- Frame {frame_idx} (timestamp: {pause_time:.2f}s)\n"
            
    #         openai_entries.append(nlp_utils.Chat.Entry(role='user', text="Example Pauses in video:\n"+pause_frames_info))
    openai_entries.append(nlp_utils.Chat.Entry(role='user', text="Example Scenic program:\n" + ex_script))

    # # Build message entries for Gemini
    # gemini_entries = [
    #     gemini_utils.Chat.Entry(role='system', text=system_instruction),
    #     gemini_utils.Chat.Entry(role='user', text="Scenic documentation:\n" + doc_text),
    #     gemini_utils.Chat.Entry(role='system', text='Library of actionAPIs:\n\n' + '\n\n'.join([f'[API ID] {i}\n{c.doc()}' for i, c in actionAPI.items()])),
    #     gemini_utils.Chat.Entry(role='system', text='Library of constraintAPIs:\n\n' + '\n\n'.join([f'[API ID] {i}\n{c.doc()}' for i, c in constraintAPI.items()]))
    # ]

    # gemini_entries.extend(
    #     gemini_utils.Chat.Entry(role='user', text=f"Transcript of narrated demonstration {demo.id} (these indicies match the indicies of the lists of frames (and videos) that are given later):\n{demo.language}")
    #     for i, demo in enumerate(demos))

    # for demo in demos:
    #     for idx, frame_path in enumerate(demo.video.frame_dir):
    #         gemini_entries.append(
    #             gemini_utils.Chat.Entry(role='user', text=f"Demo {demo.id} - Frame {idx}", im=get_im(frame_path))
    #         )
    #     if hasattr(demo, 'pause_times') and demo.pause_times:
    #         pause_frames_info = "Pause frames (instructor explaining next action):\n"
    #         for pause_time in demo.pause_times:
    #             frame_idx = demo.video.time_to_frame_index(pause_time)
    #             if frame_idx < len(demo.video.frame_dir):
    #                 pause_frames_info += f"- Frame {frame_idx} (timestamp: {pause_time:.2f}s) for Demo {demo.id}\n"
            
    #         gemini_entries.append(gemini_utils.Chat.Entry(role='user', text="Pauses in video:\n"+pause_frames_info))

    #     if demo.video_bytes: 
    #             gemini_entries.append(
    #             gemini_utils.Chat.Entry(
    #                 role='user',
    #                 text=f"Video of the instructor performing the task. Demo {demo.id}",
    #                 file=(f"demo{demo.id}.mp4", demo.video_bytes)  # Gemini gets filename + byte content
    #             )
    #             )
    # if not isinstance(example_demos, list):
    #     example_demos = [example_demos] if example_demos else []

    # gemini_entries.extend(
    #     gemini_utils.Chat.Entry(role='user', text=f"Transcript of an example narrated demonstration {demo.id} (these indicies match the indicies of the lists of frames (and videos) that are given later):\n{demo.language}")
    #     for i, demo in enumerate(example_demos))
    
    # for demo in example_demos:
    #     for idx, frame_path in enumerate(demo.video.frame_dir):
    #         gemini_entries.append(
    #             gemini_utils.Chat.Entry(role='user', text=f"Example Demo {demo.id} - Frame {idx}", im=get_im(frame_path))
    #         )
    #     if hasattr(demo, 'pause_times') and demo.pause_times:
    #         pause_frames_info = "Pause frames (instructor explaining next action):\n"
    #         for pause_time in demo.pause_times:
    #             frame_idx = demo.video.time_to_frame_index(pause_time)
    #             if frame_idx < len(demo.video.frame_dir):
    #                 pause_frames_info += f"- Frame {frame_idx} (timestamp: {pause_time:.2f}s)\n"
            
    #         gemini_entries.append(gemini_utils.Chat.Entry(role='user', text="Example Pauses in video:\n"+pause_frames_info))

    #     if demo.video_bytes: 
    #             gemini_entries.append(
    #             gemini_utils.Chat.Entry(
    #                 role='user',
    #                 text=f"Example Video of the instructor performing the task. Example Demo {demo.id}",
    #                 file=(f"example_demo{demo.id}.mp4", demo.video_bytes)  # Gemini gets filename + byte content
    #             )
    #             )
    # gemini_entries.append(gemini_utils.Chat.Entry(role='user', text="Example output script:\n" + ex_script))

    results = {}
    token_usage = {}  # Track token usage for each model
    timing_info = {}  # Track timing for each phase
    
    # Create syntax checker if enabled
    syntax_checker = None
    if enable_syntax_check:
        syntax_checker = ScenicSyntaxChecker(api=api, openai_model="gpt-5-mini", gemini_model=gemini_model)
    
    # OpenAI run
    if not use_gemini or use_both:
        print("Generating OpenAI Scenic program...")
        
        # Start timing for OpenAI synthesis
        openai_synthesis_start = time.time()
        
        chat_openai = nlp_utils.Chat(client, model=openai_model)
        print(f"Synthesizing Initial Scenic program with OpenAI model: {openai_model}")
        result_openai = chat_openai(openai_entries)
        
        # Calculate synthesis time
        openai_synthesis_time = time.time() - openai_synthesis_start
        print(f"OpenAI synthesis completed in {openai_synthesis_time:.2f} seconds")
        
        # Capture token usage
        usage = chat_openai.get_last_token_usage()
        if usage:
            token_usage['openai'] = usage
            print(f"OpenAI Token Usage: {usage['total_tokens']} total tokens (prompt: {usage['prompt_tokens']}, completion: {usage['completion_tokens']})")
        
        full_openai = f"{header}\n\n{result_openai}"
        output_openai = os.path.join(output_dir, f"{user_study_program_name}-{pilot_name}-openai.scenic")
        prepend_text_to_file(existing_path, output_openai, full_openai)
        results['openai'] = output_openai
        
        # Check and fix syntax if enabled
        openai_syntax_time = 0.0
        if syntax_checker and os.path.exists(output_openai):
            print("Checking and fixing syntax for OpenAI output...")
            
            # Start timing for syntax checking
            openai_syntax_start = time.time()
            
            try:
                fixed_content, issues = syntax_checker.check_and_fix_file(output_openai, overwrite=False)
                if issues:
                    print(f"Fixed {len(issues)} syntax issues in OpenAI output")
                else:
                    print("No syntax issues found in OpenAI output")
                
                # Capture syntax checker token usage
                syntax_usage = syntax_checker.get_last_token_usage()
                if syntax_usage:
                    token_usage['openai_syntax_check'] = syntax_usage
                    
            except Exception as e:
                print(f"Error checking syntax for OpenAI output: {e}")
            
            # Calculate syntax checking time
            openai_syntax_time = time.time() - openai_syntax_start
            print(f"OpenAI syntax checking completed in {openai_syntax_time:.2f} seconds")
        
        # Store timing info for OpenAI
        timing_info['openai'] = {
            'synthesis_time': openai_synthesis_time,
            'syntax_check_time': openai_syntax_time,
            'total_time': openai_synthesis_time + openai_syntax_time
        }

    # Gemini run
    # if use_gemini or use_both:
    #     print("Generating Gemini Scenic program...")
    #     chat_gemini = gemini_utils.Chat(model=gemini_model)
    #     result_gemini = chat_gemini(gemini_entries)
        
    #     # Capture token usage
    #     usage = chat_gemini.get_last_token_usage()
    #     if usage:
    #         token_usage['gemini'] = usage
    #         print(f"Gemini Token Usage: {usage['total_tokens']} total tokens (prompt: {usage['prompt_tokens']}, completion: {usage['completion_tokens']})")
        
    #     full_gemini = f"{header}\n\n{result_gemini}"
    #     output_gemini = os.path.join(output_dir, f"{user_study_program_name}-{pilot_name}-gemini.scenic")
    #     prepend_text_to_file(existing_path, output_gemini, full_gemini)
    #     results['gemini'] = output_gemini
        
    #     # Check and fix syntax if enabled
    #     if syntax_checker and os.path.exists(output_gemini):
    #         print("Checking and fixing syntax for Gemini output...")
    #         try:
    #             fixed_content, issues = syntax_checker.check_and_fix_file(output_gemini, overwrite=False)
    #             if issues:
    #                 print(f"Fixed {len(issues)} syntax issues in Gemini output")
    #             else:
    #                 print("No syntax issues found in Gemini output")
    #         except Exception as e:
    #             print(f"Error checking syntax for Gemini output: {e}")

    print(f"Scenic program(s) saved to {results}")
    
    # Add token usage to results
    if token_usage:
        results['token_usage'] = token_usage
        total_tokens = sum(usage.get('total_tokens', 0) for usage in token_usage.values())
        print(f"Total tokens used across all models: {total_tokens}")
    
    # Add timing information to results
    if timing_info:
        results['timing_info'] = timing_info
        
        # Print timing summary
        print(f"\n=== Timing Summary ===")
        for model, times in timing_info.items():
            print(f"{model.upper()} - Synthesis: {times['synthesis_time']:.2f}s, Syntax Check: {times['syntax_check_time']:.2f}s, Total: {times['total_time']:.2f}s")
    
    return results 