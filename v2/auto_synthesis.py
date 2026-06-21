import os
import re
import sys
import time
import glob
import shutil
import tiktoken
from vanilla_scenic_with_syntax_check import generate_combined_program_from_demos
from unity_utils import UnityTranslator
from scenic_fc.api import api

"""
Auto-synthesis script for generating Scenic programs from demonstrations.

USAGE:
    python v2/auto_synthesis.py <pilot_or_participant_name>
    
    Examples:
        python v2/auto_synthesis.py pilot0
        python v2/auto_synthesis.py pilot13
        python v2/auto_synthesis.py participant0
        python v2/auto_synthesis.py participant12

REQUIREMENTS:
    - Must specify a pilot or participant name as a command line argument
    - Auto-processing all pilots is disabled for safety
    - Pilot/participant directory must exist in _NARRATED_DEMOS/
"""
# Hardcoded constants
TACTICAL_MR_DIR = os.environ.get("TACTICAL_MR_DIR", "/path/to/TacticalMR")
DATA_BASE_PATH = os.environ.get("DATA_BASE_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"))
EXAMPLE_DEMOS_NAME = "daniel-give-and-go"
DEFAULT_DATA_FOLDER = "_NARRATED_DEMOS"  # Default directory to process
UNITY_SYNTHESIZED_PROGRAM_DIR = os.path.join(TACTICAL_MR_DIR, "Scenic-main/examples/unity/_SYNTHESIZED_PROGRAM")
OPENAI_MODEL = "gpt-5"

max_tokens = {
    'gpt-5': 400_000,
    'gpt-5-mini': 272_000,
    'gpt-5-nano': 400_000,
    'gpt-4.1': 1_047_576,
    'gpt-4o': 128_000
}

# Token estimation for sample rate calculation (not for reporting)
tokens_per_frame = 765

def get_num_tokens_for_str(x):
    enc = tiktoken.get_encoding("o200k_base")
    return len(enc.encode(x))

def estimate_total_tokens_for_demos(demos, example_demos, system_text, api_text, doc_text, ex_script, tokens_per_frame=634):
    """
    Estimate the total number of tokens that will be used in the LLM call.
    This is used only for sample rate calculation, not for reporting.
    
    Args:
        demos: List of demonstration objects
        example_demos: List of example demonstration objects
        system_text: System instruction text
        api_text: API documentation text
        doc_text: Documentation text
        ex_script: Example script text
        tokens_per_frame: Estimated tokens per image frame
    
    Returns:
        Dictionary with token estimates broken down by component
    """
    token_estimates = {
        'system_instruction': get_num_tokens_for_str(system_text),
        'documentation': get_num_tokens_for_str(doc_text),
        'api_docs': get_num_tokens_for_str(api_text),
        'example_script': get_num_tokens_for_str(ex_script),
        'demo_transcripts': 0,
        'demo_frames': 0,
        'example_transcripts': 0,
        'example_frames': 0,
        'total': 0
    }
    
    # Count demo transcripts and frames
    for demo in demos:
        token_estimates['demo_transcripts'] += get_num_tokens_for_str(demo.language)
        token_estimates['demo_frames'] += len(demo.video.frame_dir) * tokens_per_frame
    
    # Count example demo transcripts and frames
    if example_demos:
        if not isinstance(example_demos, list):
            example_demos = [example_demos]
        
        for demo in example_demos:
            token_estimates['example_transcripts'] += get_num_tokens_for_str(demo.language)
            token_estimates['example_frames'] += len(demo.video.frame_dir) * tokens_per_frame
    
    # Calculate total
    token_estimates['total'] = sum(token_estimates.values()) - token_estimates['total']  # Exclude the total itself
    
    return token_estimates

def calculate_optimal_sample_rate_on_tokens(data_path, max_tokens, tokens_per_frame):
    return calculate_optimal_sample_rate(data_path, max_frames=(max_tokens // tokens_per_frame))

# NOTE: Could optimize resolution to maximize number of frames?
def calculate_optimal_sample_rate(data_path, max_frames=100):
    """
    Calculate optimal sample rate to stay under max_frames for all videos.
    Handles mixed FPS videos by finding a sample rate that works for all.
    
    Args:
        data_path: Path to demonstration directory
        max_frames: Maximum frames to allow per video
    
    Returns:
        Optimal sample rate (float) that works for all videos
    """
    if not os.path.exists(data_path):
        print(f"Warning: Data path does not exist: {data_path}")
        return 1.5  # Default fallback
    
    video_files = glob.glob(os.path.join(data_path, "**/*.mp4"), recursive=True)
    if not video_files:
        print(f"Warning: No video files found in {data_path}")
        return 1.5  # Default fallback
    
    video_info = []
    
    # Collect information about all videos
    for video_file in video_files:
        try:
            import cv2
            cap = cv2.VideoCapture(video_file)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            cap.release()
            
            if frame_count > 0 and fps > 0:
                video_info.append({
                    'file': os.path.basename(video_file),
                    'frames': frame_count,
                    'fps': fps,
                    'duration': frame_count / fps
                })
                print(f"Video: {os.path.basename(video_file)} - {frame_count} frames, {fps:.1f} FPS")
        except Exception as e:
            print(f"Warning: Could not read video {video_file}: {e}")
    
    if not video_info:
        print("Warning: Could not read any videos. Using default sample rate of 1.5")
        return 1.5
    
    # Find the sample rate that works for all videos
    # For each video: frames_saved = ceil(total_frames / (fps * sample_rate))
    # We want: frames_saved <= max_frames for ALL videos
    # So: sample_rate >= max(total_frames / (fps * max_frames)) across all videos
    
    required_sample_rates = []
    for video in video_info:
        # Calculate minimum sample rate needed for this video
        min_sample_rate = video['frames'] / (video['fps'] * max_frames)
        required_sample_rates.append(min_sample_rate)
        print(f"  {video['file']}: needs sample_rate >= {min_sample_rate:.3f}")
    
    # Take the maximum required sample rate to ensure all videos stay under max_frames
    optimal_sample_rate = max(required_sample_rates)
    
    print(f"Debug calculation:")
    print(f"  Required sample rates for each video: {[f'{r:.3f}' for r in required_sample_rates]}")
    print(f"  Maximum required sample rate: {optimal_sample_rate:.3f}")
    
    # Add 0.5 to ensure we stay under the limit with some margin
    # 1.5 is the fastest that we will sample at
    optimal_sample_rate = max(1.5, optimal_sample_rate + 0.5)
    print(f"  After adding 0.5 and ensuring min 1.0: {optimal_sample_rate}")
    
    # Round up to the nearest 0.5 for cleaner sample rates
    optimal_sample_rate = round(optimal_sample_rate * 2) / 2
    print(f"  After rounding to nearest 0.5: {optimal_sample_rate}")
    
    # Verify the calculation works for all videos
    print(f"\nVerification for target max frames: {max_frames}")
    for video in video_info:
        frames_saved = int((video['frames'] / (video['fps'] * optimal_sample_rate)) + 0.99)  # Ceiling
        print(f"  {video['file']}: {video['frames']} frames → {frames_saved} frames (sample_rate={optimal_sample_rate})")
    
    return optimal_sample_rate



# Example script (hardcoded)
EX_SCRIPT = """
### Modeling Physical Conditions using APIs from the provided API library

# We call the conditions modeling the destination position of the coach as "target" APIs, and name these APIs with the prefix "target_" as shown below. 
A1target_0 = DistanceTo({'from': 'opponent', 'to': 'Coach', 'min': {'avg': 6.399477695297064, 'std': 0.8416729364595561}, 'max': None, 'operator': 'greater_than'})
A2target_0 = HorizontalRelation({'obj': 'Coach', 'ref': 'opponent', 'relation': 'left', 'horizontal_threshold': {'avg': 4.0, 'std': 1.0}})
A1target_2 = DistanceTo({'from': 'Coach', 'to': 'opponent', 'min': {'avg': 6.172259899611368, 'std': 0.0}, 'max': None, 'operator': 'greater_than'})
A2target_5 = DistanceTo({'from': 'Coach', 'to': 'goal', 'min': None, 'max': {'avg': 11.941602839093648, 'std': 0.01539784416917822}, 'operator': 'less_than'})

# We call the conditions modeling the preconditions of the coach as "precondition" APIs, and name these APIs with the prefix "precondition_" as shown below. 
A1precondition_0 = MakePass({'player': 'teammate'})
A1precondition_1 = Pressure({'player1': 'opponent', 'player2': 'Coach'})
A1precondition_3 = Pressure({'player1': 'opponent', 'player2': 'Coach'})
A1precondition_4 = MovingTowards({'obj': 'Teammate', 'ref': 'goal'})

def λ_target0():
    # the target APIs can be "composed" using conjunction (&), disjunction (|), or negation (~) operators.
    cond = A1target_0 & A2target_0
    # you should always return .dist() over either composed or singular target condition in the following format
    return cond.dist(simulation(), ego=True)

def λ_target2():
    return A1target_2.dist(simulation(), ego=True)

def λ_target5():
    return A2target_5.dist(simulation(), ego = True)

def λ_precondition_0():
    # for preconditions and termination conditions, you can also compose them using conjunction (&), disjunction (|), or negation (~) operators in the same way as target APIs.
    # you should always return .bool() over either composed or singular precondition in the following format
    return A1precondition_0.bool(simulation())

def λ_precondition3():
    # here is an example of calling a negation
    cond = ~ A1precondition_3
    return cond.bool(simulation())

def λ_precondition_1():
    return A1precondition_1.bool(simulation())

def λ_precondition_4():
    return A1precondition_4.bool(simulation())

behavior CoachBehavior(): 
    # You need to always start the coach behavior with the followin line, idling for 3 seconds.
    do Idle() for 3 seconds
    # The following structure defines a finite state machine (FSM), where each node is defined as "do <action> until <condition>"
    # and each transition edge is defined as "do Idle() until <condition>". For each node or edge, you need to preceed it with a speak line to explain what to do as below. 
    # Here we start with an action node. Also, when explaining any action nodes or transition edges, you should explain the numerical detail. 
    # Only report the average value (if defined) in the condition up the nearest integer. No need to report the standard deviation. 
    do Speak("you should move away from opponent by more than 6 meters by moving to the left, and recieve the ball from teammate")
    do MoveTo(λ_target0(), True)

    # Following the action node above, we have two transition edges branching out. 
    do Speak("wait to see if the opponent decides to pressure you or not")
    do Idle() until True # when branching occurs, always add this statement as a formality. 
    
    # Here we have a conditional branching. whenever we have conditional branching like this use if/elif/else conditions
    if λ_precondition_1(): # explain the precondition in the speak line below.
        # within each conditional branch, always first explain the condition that is just satisfied and then explain the action (node) that is about to be taken.
        do Speak("In this case, the opponent is pressuring you.")
        do Speak("So, move more than 6 meters away from opponent")
        do MoveTo(λ_target2(), False)

        # explain the transition edge below
        do Speak("wait until teammate moves towards goal")
        do Idle() until λ_precondition_4()

        # explain the action node below
        do Speak("pass the ball to teammate")
        do Pass(teammate)
    else:
        # again, for each conditional branch, explain the condition that is just satisfied and then explain the action (node) that is about to be taken.
        do Speak("The opponent is not pressuring you.")
        do Speak("Hence, move close to goal, within 12 meters")
        do MoveTo(λ_target5())

        # in case when there is no condition for transition edge, then you can just omit Speak() and do Idle() until ... line and move straight to the action node below.
        do Speak("then take a shot towards the goal")
        do Shoot(goal)
    
    # the coach behavior must always end with an idle state as below. 
    do Idle()

"""

def detect_user_study_program_name(data_path):
    """
    Detect the user study program name based on the data path.
    Looks for 'check', 'overlap', or 'distribute' in the path.
    """
    path_lower = data_path.lower()
    
    if 'check' in path_lower:
        return 'check'
    elif 'overlap' in path_lower:
        return 'overlap'
    elif 'distribute' in path_lower:
        return 'distribute'
    else:
        # Default to 'check' if no specific pattern is found
        print("Warning: No specific user study program name detected in path. Defaulting to 'check'")
        return 'check'

def detect_pilot_name(data_path):
    """
    Detect the pilot name from the data path.
    Looks for patterns like 'pilot1', 'pilot2', 'participant1', 'participant2', etc.
    """
    # Extract the base name of the data directory
    data_dir_name = os.path.basename(data_path)
    
    # Look for pilot pattern in the directory name
    pilot_match = re.search(r'pilot(\d+)', data_dir_name, re.IGNORECASE)
    if pilot_match:
        pilot_num = pilot_match.group(1)
        return f"pilot{pilot_num}"
    
    # Look for participant pattern in the directory name
    participant_match = re.search(r'participant(\d+)', data_dir_name, re.IGNORECASE)
    if participant_match:
        participant_num = participant_match.group(1)
        return f"participant{participant_num}"
    
    # If no pilot pattern found, try to extract a meaningful name
    # Remove common suffixes and use the base name
    name = data_dir_name.replace('-check', '').replace('-overlap', '').replace('-distribute', '')
    if name:
        return name
    
    # Default fallback
    print("Warning: No pilot/participant name pattern detected. Using default 'pilot_default'")
    return 'pilot_default'

def find_pilot_folder(pilot_name):
    """
    Find the pilot folder within _NARRATED_DEMOS.
    
    Args:
        pilot_name: The pilot/participant name (e.g., "pilot0", "pilot13", "participant0", "participant13")
    
    Returns:
        The pilot folder path (e.g., "pilot0", "participant0") or None if not found
    """
    narrated_demos_path = os.path.join(DATA_BASE_PATH, DEFAULT_DATA_FOLDER)
    
    if not os.path.exists(narrated_demos_path):
        print(f"Error: Narrated demos directory does not exist: {narrated_demos_path}")
        return None
    
    # Look for the pilot/participant folder
    pilot_folder_path = os.path.join(narrated_demos_path, pilot_name)
    if os.path.exists(pilot_folder_path) and os.path.isdir(pilot_folder_path):
        print(f"Found pilot/participant folder: {pilot_name}")
        return pilot_name
    
    print(f"Error: Pilot/participant folder '{pilot_name}' does not exist in {DEFAULT_DATA_FOLDER}/")
    print(f"Available folders: {[d for d in os.listdir(narrated_demos_path) if os.path.isdir(os.path.join(narrated_demos_path, d))]}")
    return None

def find_pilot_directories():
    """
    Find all pilot and participant directories within the _NARRATED_DEMOS folder.
    
    Returns:
        List of pilot/participant directory names (e.g., ['pilot0', 'pilot13', 'participant0', 'participant5'])
    """
    narrated_demos_path = os.path.join(DATA_BASE_PATH, DEFAULT_DATA_FOLDER)
    
    if not os.path.exists(narrated_demos_path):
        print(f"Error: Narrated demos directory does not exist: {narrated_demos_path}")
        return []
    
    pilot_dirs = []
    for item in os.listdir(narrated_demos_path):
        item_path = os.path.join(narrated_demos_path, item)
        if os.path.isdir(item_path) and (item.startswith("pilot") or item.startswith("participant")):
            pilot_dirs.append(item)
            print(f"Found pilot/participant directory: {item}")
    
    return pilot_dirs

def copy_to_unity_repo(generated_files, pilot_name):
    """
    Copy generated Scenic files to the Unity project repo.
    Always copies the latest file as 'synthesized_program.scenic'.
    
    Args:
        generated_files: Dictionary with paths to generated files
        pilot_name: The pilot name for organizing files
    """
    # Skip the Unity copy when TacticalMR isn't available (standalone runs).
    if not os.path.isdir(TACTICAL_MR_DIR):
        print(f"Note: TACTICAL_MR_DIR ('{TACTICAL_MR_DIR}') not found — skipping copy to "
              f"the Unity project. Set TACTICAL_MR_DIR to enable Unity integration.")
        return

    # Ensure Unity directory exists
    os.makedirs(UNITY_SYNTHESIZED_PROGRAM_DIR, exist_ok=True)

    print(f"Copying latest file to Unity repo: {UNITY_SYNTHESIZED_PROGRAM_DIR}")
    
    # Find the latest generated file (prefer OpenAI over Gemini)
    latest_file = None
    if 'openai' in generated_files and generated_files['openai']:
        latest_file = generated_files['openai']
    elif 'gemini' in generated_files and generated_files['gemini']:
        latest_file = generated_files['gemini']
    elif 'both' in generated_files and generated_files['both']:
        latest_file = generated_files['both']
    
    if latest_file and os.path.exists(latest_file):
        # Always copy as 'synthesized_program.scenic'
        unity_file_path = os.path.join(UNITY_SYNTHESIZED_PROGRAM_DIR, "synthesized_program.scenic")
        
        try:
            shutil.copy2(latest_file, unity_file_path)
            print(f"✓ Copied latest file as 'synthesized_program.scenic' to Unity repo")
        except Exception as e:
            print(f"✗ Failed to copy file: {e}")
    else:
        print("Warning: No valid files found to copy to Unity repo")

def auto_synthesize(pilot_name, use_both=False, enable_syntax_check=True):
    """
    Automatically synthesize Scenic programs from demonstrations.
    
    Args:
        pilot_name: The pilot/participant name (e.g., "pilot0", "pilot13", "participant0", "participant13")
        use_both: Whether to generate both OpenAI and Gemini versions
        enable_syntax_check: Whether to enable syntax checking
    
    Returns:
        Dictionary with paths to generated files
    """
    print(f"Auto-synthesizing for pilot/participant: {pilot_name}")
    
    # Find the pilot folder within _NARRATED_DEMOS
    pilot_folder = find_pilot_folder(pilot_name)
    if not pilot_folder:
        print(f"Could not find pilot/participant folder for {pilot_name}")
        return None
    
    # Look for the actual data folder within the pilot folder (e.g., overlap-pilot0, check-participant12)
    pilot_data_path = os.path.join(DATA_BASE_PATH, DEFAULT_DATA_FOLDER, pilot_folder)
    if not os.path.exists(pilot_data_path):
        print(f"Error: Pilot/participant data directory does not exist: {pilot_data_path}")
        return None
    
    # Find the data subfolder (e.g., overlap-pilot0, check-participant12)
    data_subfolders = []
    for item in os.listdir(pilot_data_path):
        item_path = os.path.join(pilot_data_path, item)
        if os.path.isdir(item_path) and not item.startswith("fsm") and not item.startswith("feedback"):
            # Check if directory contains video files (indicating it's the data directory)
            video_files = glob.glob(os.path.join(item_path, "**/*.mp4"), recursive=True)
            if video_files:
                data_subfolders.append(item)
    
    if not data_subfolders:
        print(f"Error: No data subfolder found in {pilot_data_path}")
        return None
    
    # Use the first data subfolder found
    data_subfolder = data_subfolders[0]
    data_path = os.path.join(DEFAULT_DATA_FOLDER, pilot_folder, data_subfolder)
    print(f"Using data folder: {data_path}")
    
    # Detect parameters from the data subfolder name
    user_study_program_name = detect_user_study_program_name(data_subfolder)
    detected_pilot_name = detect_pilot_name(data_subfolder)
    
    print(f"Detected user study program name: {user_study_program_name}")
    print(f"Detected pilot/participant name: {detected_pilot_name}")
    
    # Calculate optimal sample rate to stay under token limits
    full_data_path = os.path.join(DATA_BASE_PATH, data_path)
    print(f"Full data path: {full_data_path}")
    
    # Use token estimation to determine optimal sample rate (// 2 for safety margin)
    optimal_sample_rate = calculate_optimal_sample_rate_on_tokens(full_data_path, max_tokens=(max_tokens[OPENAI_MODEL] // 2), tokens_per_frame=tokens_per_frame)
    print(f"Using optimal sample rate: {optimal_sample_rate} (calculated from token limits)")
    
    # Load demonstrations
    print("Loading demonstrations...")
    demos = UnityTranslator.get_from(full_data_path, sample_rate=optimal_sample_rate)
    
    # Load example demonstrations
    # example_dir = os.path.join(DATA_BASE_PATH, EXAMPLE_DEMOS_NAME)
    # example_demos = UnityTranslator.get_from(example_dir, sample_rate=optimal_sample_rate)
    
    # Ensure output directory exists
    output_dir = os.path.join(DATA_BASE_PATH, "_SYNTHESIZED_PROGRAM", detected_pilot_name)
    os.makedirs(output_dir, exist_ok=True)
    print(f"Ensured output directory exists: {output_dir}")
    
    # TODO: Token precomputation only possible if we know the token length of the prompt beforehand.
    # Demos are initalized within the synthesis function below after we initalized the demos (sampled frames)
    # so it's in reverse order. Logic must be moved inside the function (or prompt should be moved outside function). 

    # Generate programs
    results = generate_combined_program_from_demos(
        demos=demos,
        example_demos=None, # Removing narrated demo examples
        ex_script=EX_SCRIPT,
        api=api,
        output_dir=output_dir,
        tactical_mr_dir=TACTICAL_MR_DIR,
        use_both=use_both,
        openai_model=OPENAI_MODEL,
        enable_syntax_check=enable_syntax_check,
        user_study_program_name=user_study_program_name,
        pilot_name=detected_pilot_name
    )
    
    print(f"Auto-synthesis complete. Generated files: {results}")
    
    # Display timing information if available
    if 'timing_info' in results:
        print("\n" + "="*50)
        print("TIMING SUMMARY")
        print("="*50)
        
        for model, times in results['timing_info'].items():
            print(f"{model.upper()}:")
            print(f"  Initial synthesis: {times['synthesis_time']:.2f} seconds")
            print(f"  Syntax checking:   {times['syntax_check_time']:.2f} seconds")
            print(f"  Total:             {times['total_time']:.2f} seconds")
            print()
        
        # Calculate total across all models
        total_synthesis = sum(times.get('synthesis_time', 0) for times in results['timing_info'].values())
        total_syntax = sum(times.get('syntax_check_time', 0) for times in results['timing_info'].values())
        total_generation = total_synthesis + total_syntax
        
        print(f"TOTAL ACROSS ALL MODELS:")
        print(f"  Synthesis:      {total_synthesis:.2f} seconds")
        print(f"  Syntax check:   {total_syntax:.2f} seconds")
        print(f"  Generation:     {total_generation:.2f} seconds")
        print("="*50)
    
    # Display token usage information if available
    if 'token_usage' in results:
        print("\n" + "="*50)
        print("TOKEN USAGE SUMMARY")
        print("="*50)
        
        for model, usage in results['token_usage'].items():
            print(f"{model.upper()}:")
            print(f"  Prompt tokens: {usage['prompt_tokens']:,}")
            print(f"  Completion tokens: {usage['completion_tokens']:,}")
            print(f"  Total tokens: {usage['total_tokens']:,}")
            print()
        
        total_tokens = sum(usage.get('total_tokens', 0) for usage in results['token_usage'].values())
        print(f"TOTAL TOKENS ACROSS ALL MODELS: {total_tokens:,}")
        print("="*50)
    
    # Copy generated files to Unity project repo
    if results:
        print("Copying generated files to Unity project repo...")
        copy_to_unity_repo(results, detected_pilot_name)
    
    return results

def process_all_pilots():
    """
    Process all pilot directories found in the _NARRATED_DEMOS folder.
    """
    print("=" * 60)
    print("AUTO-SYNTHESIS: Processing all pilot directories")
    print("=" * 60)
    
    # Find all pilot directories
    pilot_dirs = find_pilot_directories()
    
    if not pilot_dirs:
        print(f"\nNo pilot directories found in {DEFAULT_DATA_FOLDER}/")
        print("Please ensure you have directories like 'pilot0-overlap', 'pilot13-check' etc.")
        print(f"Expected path: {os.path.join(DATA_BASE_PATH, DEFAULT_DATA_FOLDER)}")
        return
    
    print(f"\nFound {len(pilot_dirs)} pilot directory(ies) to process:")
    for i, pilot_dir in enumerate(pilot_dirs, 1):
        print(f"  {i}. {pilot_dir}")
    
    print(f"\nProcessing each pilot directory...")
    
    # Process each pilot directory
    for i, pilot_dir in enumerate(pilot_dirs, 1):
        print(f"\n{'='*40}")
        print(f"Processing {i}/{len(pilot_dirs)}: {pilot_dir}")
        print(f"{'='*40}")
        
        try:
            # The directory name is already the pilot name (e.g., "pilot0")
            pilot_name = pilot_dir
            
            # Run auto synthesis
            results = auto_synthesize(pilot_name)
            if results:
                print(f"✓ Successfully processed {pilot_dir}")
                print(f"  Generated files: {results}")
            else:
                print(f"✗ Failed to process {pilot_dir}")
            
        except Exception as e:
            print(f"✗ Error processing {pilot_dir}: {e}")
            print("Continuing with next pilot directory...")
    
    print(f"\n{'='*60}")
    print("Auto-synthesis complete for all pilot directories!")
    print(f"{'='*60}")

def main():
    """Main function that processes pilot directories."""
    import sys
    
    # Check if command line arguments were provided
    if len(sys.argv) > 1:
        # Process specific pilot/participant
        pilot_name = sys.argv[1]
        print(f"Processing specific pilot/participant: {pilot_name}")
        
        # Run auto synthesis for specific pilot/participant
        start_time = time.time()
        results = auto_synthesize(pilot_name)
        elapsed_seconds = time.time() - start_time
        
        if results:
            print("Synthesis completed successfully!")
            
            # Calculate generation time vs. total time
            generation_time = 0
            if 'timing_info' in results:
                generation_time = sum(times.get('total_time', 0) for times in results['timing_info'].values())
            
            setup_time = elapsed_seconds - generation_time
            
            print(f"\n=== Overall Process Timing ===")
            if generation_time > 0:
                print(f"Generation (synthesis + syntax): {generation_time:.2f} seconds")
                print(f"Setup and overhead:              {setup_time:.2f} seconds")
            print(f"Total execution time:            {elapsed_seconds:.2f} seconds")
        else:
            print("Synthesis failed!")
            sys.exit(1)
    else:
        # No pilot specified - show usage and exit
        print("=" * 60)
        print("ERROR: No pilot/participant name specified!")
        print("=" * 60)
        print("Usage: python v2/auto_synthesis.py <pilot_name>")
        print("")
        print("Examples:")
        print("  python v2/auto_synthesis.py pilot0")
        print("  python v2/auto_synthesis.py pilot13")
        print("  python v2/auto_synthesis.py participant0")
        print("  python v2/auto_synthesis.py participant12")
        print("")
        print("Available pilot/participant directories:")
        pilot_dirs = find_pilot_directories()
        if pilot_dirs:
            for pilot_dir in pilot_dirs:
                print(f"  - {pilot_dir}")
        else:
            print("  No pilot/participant directories found")
        print("")
        print("For safety reasons, auto-processing all pilots is disabled.")
        print("Please specify a specific pilot/participant name to process.")
        print("=" * 60)
        sys.exit(1)

if __name__ == "__main__":
    main() 