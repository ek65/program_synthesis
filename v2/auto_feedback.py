import os
import sys
import glob
import shutil
import argparse
import re
import time
import tiktoken
from feedback_with_syntax_check import generate_final_scenic_with_syntax_check
from unity_utils import UnityTranslator
from scenic_fc.api import api

"""
Auto-feedback script for generating feedback Scenic programs from demonstrations.

USAGE:
    python v2/auto_feedback.py <pilot_or_participant_name> --fsm
    python v2/auto_feedback.py <pilot_or_participant_name> --feedback
    
    Examples:
        python v2/auto_feedback.py pilot0
        python v2/auto_feedback.py pilot0 --feedback
        python v2/auto_feedback.py pilot13 --fsm
        python v2/auto_feedback.py participant0 --fsm
        python v2/auto_feedback.py participant12 --feedback

REQUIREMENTS:
    - Must specify a pilot or participant name as a command line argument
    - Must specify either --fsm or --feedback mode
    - Pilot/participant directory must exist in _NARRATED_DEMOS/
    - Must have existing synthesized programs from auto_synthesis.py first
    - Requires TacticalMR output directory with latest demonstrations
"""

# Hardcoded constants
TACTICAL_MR_DIR = os.environ.get("TACTICAL_MR_DIR", "/path/to/TacticalMR")
DATA_BASE_PATH = os.environ.get("DATA_BASE_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"))
DEFAULT_DATA_FOLDER = "_NARRATED_DEMOS"
TACTICAL_MR_OUTPUT = os.environ.get("TACTICAL_MR_OUTPUT", os.path.join(TACTICAL_MR_DIR, "output/participant0/Test"))
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

def get_latest_demonstration():
    """
    Get the latest demonstration from the TacticalMR output directory.
    
    Returns:
        Tuple of (demonstration_path, demonstration_number) or (None, None) if not found
    """
    if not os.path.exists(TACTICAL_MR_OUTPUT):
        print(f"Error: TacticalMR output directory does not exist: {TACTICAL_MR_OUTPUT}")
        return None, None
    
    # Look for demonstration folders
    demo_folders = []
    for item in os.listdir(TACTICAL_MR_OUTPUT):
        item_path = os.path.join(TACTICAL_MR_OUTPUT, item)
        if os.path.isdir(item_path) and item.startswith("demonstration"):
            # Extract demonstration number
            demo_match = re.search(r'demonstration(\d+)', item)
            if demo_match:
                demo_num = int(demo_match.group(1))
                demo_folders.append((item_path, demo_num))
    
    if not demo_folders:
        print("No demonstration folders found in TacticalMR output")
        return None, None
    
    # Sort by demonstration number and get the latest
    demo_folders.sort(key=lambda x: x[1], reverse=True)
    latest_demo_path, latest_demo_num = demo_folders[0]
    
    print(f"Latest demonstration: {os.path.basename(latest_demo_path)} (number: {latest_demo_num})")
    return latest_demo_path, latest_demo_num

def copy_latest_demonstration_to_pilot(pilot_folder, mode):
    """
    Copy the latest demonstration to the pilot's fsm or feedback subdirectory.
    
    Args:
        pilot_folder: The pilot folder name (e.g., "overlap-pilot0")
        mode: Either "fsm" or "feedback"
    
    Returns:
        Path to the copied demonstration directory or None if failed
    """
    # Get the latest demonstration
    latest_demo_path, demo_num = get_latest_demonstration()
    if not latest_demo_path:
        return None
    
    # Construct target path
    target_dir = os.path.join(DATA_BASE_PATH, DEFAULT_DATA_FOLDER, pilot_folder, mode)
    os.makedirs(target_dir, exist_ok=True)
    
    # Create the target demonstration folder name
    target_demo_name = f"demonstration{demo_num}"
    target_demo_path = os.path.join(target_dir, target_demo_name)
    
    # Remove existing demonstration folder if it exists
    if os.path.exists(target_demo_path):
        shutil.rmtree(target_demo_path)
        print(f"Removed existing {target_demo_name} folder")
    
            # Copy the demonstration
    try:
        shutil.copytree(latest_demo_path, target_demo_path)
        print(f"✓ Copied {target_demo_name} to {target_dir}")
        
        # Just remove the .DS_Store file that can cause issues with UnityTranslator
        ds_store_path = os.path.join(target_demo_path, ".DS_Store")
        if os.path.exists(ds_store_path):
            os.remove(ds_store_path)
            print("✓ Removed .DS_Store file")
        
        # Create the proper folder structure
        # We need to find the original data subfolder name (e.g., "overlap-pilot0", "check-participant12")
        pilot_data_path = os.path.join(DATA_BASE_PATH, DEFAULT_DATA_FOLDER, pilot_folder)
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
        
        # Find the next available number for the mode folder
        existing_folders = []
        for item in os.listdir(target_dir):
            if item.startswith(f"{data_subfolder}-{mode}"):
                # Extract the number from folder names like "overlap-pilot0-fsm1"
                number_match = re.search(f"{data_subfolder}-{mode}(\\d+)", item)
                if number_match:
                    existing_folders.append(int(number_match.group(1)))
        
        # Determine the next number
        # FSM and feedback folders should start at 1, not 0
        next_number = 1
        if existing_folders:
            next_number = max(existing_folders) + 1
        
        # Create the proper folder name (e.g., "overlap-pilot0-fsm1")
        new_folder_name = f"{data_subfolder}-{mode}{next_number}"
        new_folder_path = os.path.join(target_dir, new_folder_name)
        
        # Create the new folder and move demonstration inside
        os.makedirs(new_folder_path, exist_ok=True)
        demonstration_path = os.path.join(new_folder_path, f"demonstration{demo_num}")
        shutil.move(target_demo_path, demonstration_path)
        
        print(f"✓ Created {new_folder_name} with demonstration{demo_num} inside")
        
        return new_folder_path
        
    except Exception as e:
        print(f"Error copying demonstration: {e}")
        return None

def get_latest_scenic_file(pilot_dir, mode="scenic"):
    """
    Get the latest scenic file from the specified directory.
    
    Args:
        pilot_dir: Path to the pilot directory
        mode: Either "scenic", "fsm", or "feedback"
    
    Returns:
        Tuple of (file_path, file_number) or (None, None) if no files found
    """
    if mode == "scenic":
        # Look in the main pilot directory for .scenic files
        search_pattern = os.path.join(pilot_dir, "*.scenic")
        files = glob.glob(search_pattern)
    else:
        # Look in the fsm or feedback subdirectory
        subdir = os.path.join(pilot_dir, mode)
        if not os.path.exists(subdir):
            print(f"Warning: {mode} subdirectory does not exist: {subdir}")
            return None, None
        
        search_pattern = os.path.join(subdir, f"*-{mode}*.scenic")
        files = glob.glob(search_pattern)
    
    if not files:
        print(f"No {mode} files found in {pilot_dir}")
        return None, None
    
    # Extract numbers from filenames and find the highest
    file_numbers = []
    for file_path in files:
        filename = os.path.basename(file_path)
        if mode == "scenic":
            # For main scenic files, look for pattern like "overlap-pilot0-openai.scenic"
            if "-openai.scenic" in filename or "-gemini.scenic" in filename:
                file_numbers.append((file_path, 0))  # Main files get number 0
        else:
            # For fsm/feedback files, extract number from pattern like "overlap-pilot0-openai-fsm1.scenic"
            parts = filename.split(f"-{mode}")
            if len(parts) > 1:
                number_part = parts[1].replace(".scenic", "")
                try:
                    number = int(number_part)
                    file_numbers.append((file_path, number))
                except ValueError:
                    continue
    
    if not file_numbers:
        print(f"No valid {mode} files found with proper naming convention")
        return None, None
    
    # Sort by number and return the latest
    file_numbers.sort(key=lambda x: x[1], reverse=True)
    latest_file, latest_number = file_numbers[0]
    
    print(f"Latest {mode} file: {os.path.basename(latest_file)} (number: {latest_number})")
    return latest_file, latest_number

def detect_user_study_program_name(pilot_folder):
    """
    Detect the user study program name based on the pilot folder name.
    Looks for 'check', 'overlap', or 'distribute' in the name.
    """
    name_lower = pilot_folder.lower()
    
    if 'check' in name_lower:
        return 'check'
    elif 'overlap' in name_lower:
        return 'overlap'
    elif 'distribute' in name_lower:
        return 'distribute'
    else:
        # Default to 'check' if no specific pattern is found
        print("Warning: No specific user study program name detected in folder name. Defaulting to 'check'")
        return 'check'

def copy_to_unity_repo(file_path, pilot_name, mode):
    """
    Copy generated Scenic file to the Unity project repo.
    Always copies the file as 'synthesized_program.scenic'.
    
    Args:
        file_path: Path to the generated Scenic file
        pilot_name: The pilot name for organizing files
        mode: Either "fsm" or "feedback" for subdirectory organization
    """
    # Ensure Unity directory exists
    os.makedirs(UNITY_SYNTHESIZED_PROGRAM_DIR, exist_ok=True)
    
    print(f"Copying file to Unity repo: {UNITY_SYNTHESIZED_PROGRAM_DIR}")
    
    if file_path and os.path.exists(file_path):
        # Always copy as 'synthesized_program.scenic'
        unity_file_path = os.path.join(UNITY_SYNTHESIZED_PROGRAM_DIR, "synthesized_program.scenic")
        
        try:
            shutil.copy2(file_path, unity_file_path)
            print(f"✓ Copied file as 'synthesized_program.scenic' to Unity repo")
        except Exception as e:
            print(f"✗ Failed to copy file: {e}")
    else:
        print(f"Warning: File not found: {file_path}")

def detect_pilot_name(pilot_folder):
    """
    Detect the pilot name from the pilot folder name.
    Looks for patterns like 'pilot1', 'pilot2', 'participant1', 'participant2', etc.
    """
    # Look for pilot pattern in the folder name
    pilot_match = re.search(r'pilot(\d+)', pilot_folder, re.IGNORECASE)
    if pilot_match:
        pilot_num = pilot_match.group(1)
        return f"pilot{pilot_num}"
    
    # Look for participant pattern in the folder name
    participant_match = re.search(r'participant(\d+)', pilot_folder, re.IGNORECASE)
    if participant_match:
        participant_num = participant_match.group(1)
        return f"participant{participant_num}"
    
    # Default fallback
    print("Warning: No pilot/participant name pattern detected. Using default 'pilot_default'")
    return 'pilot_default'

def process_fsm_mode(pilot_name):
    """
    Process FSM feedback mode.
    
    Args:
        pilot_name: The pilot/participant name (e.g., "pilot0", "participant0")
    
    Returns:
        bool: True if successful, False otherwise
    """
    print("=" * 60)
    print(f"FSM FEEDBACK MODE: Processing pilot/participant {pilot_name}")
    print("=" * 60)
    
    # Start timing
    start_time = time.time()
    
    # Find the pilot folder
    pilot_folder = find_pilot_folder(pilot_name)
    if not pilot_folder:
        return False
    
    # Copy latest demonstration to fsm subdirectory
    print("Copying latest demonstration for FSM feedback...")
    demo_path = copy_latest_demonstration_to_pilot(pilot_folder, "fsm")
    if not demo_path:
        print("Failed to copy demonstration")
        return False
    
    # Get the latest scenic file for context
    pilot_dir = os.path.join(DATA_BASE_PATH, "_SYNTHESIZED_PROGRAM", pilot_name)
    
    # For FSM mode, prioritize FSM files over main scenic files
    # This ensures we build on the latest FSM for subsequent FSM runs
    latest_scenic_file = None
    context_source = None
    
    # First try to get from FSM files (for subsequent FSM runs)
    latest_fsm_file, fsm_number = get_latest_scenic_file(pilot_dir, "fsm")
    if latest_fsm_file:
        latest_scenic_file = latest_fsm_file
        context_source = "fsm"
        print(f"Using FSM file as context: {os.path.basename(latest_fsm_file)}")
    
    # If no FSM files, try main scenic files (for first-time FSM runs)
    if not latest_scenic_file:
        latest_main_file, main_number = get_latest_scenic_file(pilot_dir, "scenic")
        if latest_main_file:
            latest_scenic_file = latest_main_file
            context_source = "main"
            print(f"Using main scenic file as context: {os.path.basename(latest_main_file)}")
    
    if not latest_scenic_file:
        print("No scenic files found for context. Please run auto_synthesis.py first.")
        return False
    
    print(f"Context source: {context_source} file")
    print(f"Using context file: {os.path.basename(latest_scenic_file)}")
    
    # Find the original data subfolder (e.g., overlap-pilot0, check-participant12) within the pilot folder
    pilot_data_path = os.path.join(DATA_BASE_PATH, DEFAULT_DATA_FOLDER, pilot_folder)
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
        return False
    
    # Use the first data subfolder found
    data_subfolder = data_subfolders[0]
    
    # Detect parameters from the data subfolder name
    user_study_program_name = detect_user_study_program_name(data_subfolder)
    detected_pilot_name = detect_pilot_name(data_subfolder)
    
    print(f"Detected user study program name: {user_study_program_name}")
    print(f"Detected pilot/participant name: {detected_pilot_name}")
    
    # Load demonstrations
    print("Loading demonstrations...")
    # For FSM feedback, we need the original demonstrations from the data subfolder
    original_demos_path = os.path.join(DATA_BASE_PATH, DEFAULT_DATA_FOLDER, pilot_folder, data_subfolder)
    print(f"Loading original demos from: {original_demos_path}")
    
    # Calculate adaptive sample rate for original demos using token estimation
    original_sample_rate = calculate_optimal_sample_rate_on_tokens(original_demos_path, max_tokens=(max_tokens['gpt-5-mini'] // 2), tokens_per_frame=tokens_per_frame)
    print(f"Using sample rate {original_sample_rate} for original demos (calculated from token limits)")
    original_demos = UnityTranslator.get_from(original_demos_path, sample_rate=original_sample_rate)
    
    print(f"Loading feedback demos from: {demo_path}")
    
    # Check if the demonstration directory contains the expected files
    if not os.path.exists(demo_path):
        print(f"Error: Demonstration directory does not exist: {demo_path}")
        return False
    
    # List contents of the demonstration directory for debugging
    print(f"Contents of {demo_path}:")
    for item in os.listdir(demo_path):
        item_path = os.path.join(demo_path, item)
        if os.path.isdir(item_path):
            print(f"  Directory: {item}")
            # List contents of subdirectories
            try:
                sub_items = os.listdir(item_path)
                for sub_item in sub_items[:5]:  # Show first 5 items
                    print(f"    - {sub_item}")
                if len(sub_items) > 5:
                    print(f"    ... and {len(sub_items) - 5} more items")
            except Exception as e:
                print(f"    Error listing subdirectory: {e}")
        else:
            print(f"  File: {item}")
    
    print(f"Attempting to load demos with UnityTranslator...")
    try:
        # Calculate adaptive sample rate for feedback demos using token estimation
        feedback_sample_rate = calculate_optimal_sample_rate_on_tokens(demo_path, max_tokens=(max_tokens['gpt-5-mini'] // 2), tokens_per_frame=tokens_per_frame)
        print(f"Using sample rate {feedback_sample_rate} for feedback demos (calculated from token limits)")
        feedback_demos = UnityTranslator.get_from(demo_path, sample_rate=feedback_sample_rate)
        print(f"✓ Successfully loaded feedback demos: {len(feedback_demos) if hasattr(feedback_demos, '__len__') else 'single demo'}")
    except Exception as e:
        print(f"Error loading feedback demos: {e}")
        print("This might be because the demonstration folder structure doesn't match what UnityTranslator expects.")
        print("The TacticalMR output structure is different from narrated demos and may need special handling.")
        return False
    
    # Build paths
    suffix_path = os.path.join(
        TACTICAL_MR_DIR, 
        f"Scenic-main/examples/unity/user-study-program-{user_study_program_name}.scenic"
    )
    
    # Determine next FSM number
    fsm_dir = os.path.join(pilot_dir, "fsm")
    os.makedirs(fsm_dir, exist_ok=True)
    
    # Get the latest FSM number
    latest_fsm_file, fsm_number = get_latest_scenic_file(pilot_dir, "fsm")
    next_fsm_number = (fsm_number + 1) if latest_fsm_file else 0
    
    # Output path in _SYNTHESIZED_PROGRAM
    output_filename = f"{user_study_program_name}-{detected_pilot_name}-openai-fsm{next_fsm_number}.scenic"
    output_path = os.path.join(fsm_dir, output_filename)
    
    print(f"Context file: {latest_scenic_file}")
    print(f"Suffix path: {suffix_path}")
    print(f"Output path: {output_path}")
    
    # Generate FSM feedback program
    print("Generating FSM feedback Scenic program...")
    
    try:
        result = generate_final_scenic_with_syntax_check(
            context=latest_scenic_file,
            suffix_path=suffix_path,
            output_path=output_path,
            api=api,
            synth_demo=feedback_demos,
            demos=original_demos,
            model=OPENAI_MODEL,
            fsm=True
        )
        
        # Extract timing information if available
        if len(result) >= 4:
            fixed_code, llm_resp, syntax_issues, generation_timing = result
        else:
            # Fallback for older return format
            fixed_code, llm_resp, syntax_issues = result[:3]
            generation_timing = {'synthesis_time': 0, 'syntax_check_time': 0, 'total_time': 0}
        
        # Calculate elapsed time for the entire process
        elapsed_seconds = time.time() - start_time
        
        print(f"✓ FSM feedback program generated successfully: {output_filename}")
        print(f"Saved to: {fsm_dir}")
        
        # Display detailed timing information
        if generation_timing:
            print(f"\n=== Detailed Timing ===")
            print(f"Initial synthesis:     {generation_timing['synthesis_time']:.2f} seconds")
            print(f"Syntax checking:       {generation_timing['syntax_check_time']:.2f} seconds")
            print(f"Generation subtotal:   {generation_timing['total_time']:.2f} seconds")
            print(f"Setup and overhead:    {elapsed_seconds - generation_timing['total_time']:.2f} seconds")
            print(f"Total process time:    {elapsed_seconds:.2f} seconds")
        else:
            print(f"Total time: {elapsed_seconds:.2f} seconds")
        
        # Copy to Unity repo
        copy_to_unity_repo(output_path, detected_pilot_name, "fsm")
        
        return True
        
    except Exception as e:
        # Calculate elapsed time even on failure
        elapsed_seconds = time.time() - start_time
        print(f"Error generating FSM feedback program: {e}")
        print(f"Time elapsed before failure: {elapsed_seconds:.2f} seconds")
        return False

def process_feedback_mode(pilot_name):
    """
    Process regular feedback mode.
    
    Args:
        pilot_name: The pilot/participant name (e.g., "pilot0", "participant0")
    
    Returns:
        bool: True if successful, False otherwise
    """
    print("=" * 60)
    print(f"REGULAR FEEDBACK MODE: Processing pilot/participant {pilot_name}")
    print("=" * 60)
    
    # Start timing
    start_time = time.time()
    
    # Find the pilot folder
    pilot_folder = find_pilot_folder(pilot_name)
    if not pilot_folder:
        return False
    
    # Copy latest demonstration to feedback subdirectory
    print("Copying latest demonstration for regular feedback...")
    demo_path = copy_latest_demonstration_to_pilot(pilot_folder, "feedback")
    if not demo_path:
        print("Failed to copy demonstration")
        return False
    
    # Get the latest scenic file for context
    pilot_dir = os.path.join(DATA_BASE_PATH, "_SYNTHESIZED_PROGRAM", pilot_name)
    
    # For feedback mode, prioritize feedback files over FSM files
    # This ensures we build on the latest feedback, not the latest FSM
    latest_scenic_file = None
    context_source = None
    
    # First try to get from feedback files (for subsequent feedback runs)
    latest_feedback_file, feedback_number = get_latest_scenic_file(pilot_dir, "feedback")
    if latest_feedback_file:
        latest_scenic_file = latest_feedback_file
        context_source = "feedback"
        print(f"Using feedback file as context: {os.path.basename(latest_feedback_file)}")
    
    # If no feedback files, try FSM files (for first-time feedback when no feedback files exist)
    if not latest_scenic_file:
        latest_fsm_file, fsm_number = get_latest_scenic_file(pilot_dir, "fsm")
        if latest_fsm_file:
            latest_scenic_file = latest_fsm_file
            context_source = "fsm"
            print(f"Using FSM file as context: {os.path.basename(latest_fsm_file)}")
    
    # If still no files, try main scenic files as fallback
    if not latest_scenic_file:
        latest_main_file, main_number = get_latest_scenic_file(pilot_dir, "scenic")
        if latest_main_file:
            latest_scenic_file = latest_main_file
            context_source = "main"
            print(f"Using main scenic file as context: {os.path.basename(latest_main_file)}")
    
    if not latest_scenic_file:
        print("No scenic files found for context. Please run auto_synthesis.py first.")
        return False
    
    print(f"Context source: {context_source} file")
    
    # Find the original data subfolder (e.g., overlap-pilot0, check-participant12) within the pilot folder
    pilot_data_path = os.path.join(DATA_BASE_PATH, DEFAULT_DATA_FOLDER, pilot_folder)
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
        return False
    
    # Use the first data subfolder found
    data_subfolder = data_subfolders[0]
    
    # Detect parameters from the data subfolder name
    user_study_program_name = detect_user_study_program_name(data_subfolder)
    detected_pilot_name = detect_pilot_name(data_subfolder)
    
    print(f"Detected user study program name: {user_study_program_name}")
    print(f"Detected pilot/participant name: {detected_pilot_name}")
    
    # Load feedback demonstrations only (no original demos needed for regular feedback)
    print(f"Loading feedback demonstrations from: {demo_path}")
    
    # Check if the demonstration directory contains the expected files
    if not os.path.exists(demo_path):
        print(f"Error: Demonstration directory does not exist: {demo_path}")
        return False
    
    # List contents of the demonstration directory for debugging
    print(f"Contents of {demo_path}:")
    for item in os.listdir(demo_path):
        item_path = os.path.join(demo_path, item)
        if os.path.isdir(item_path):
            print(f"  Directory: {item}")
            # List contents of subdirectories
            try:
                sub_items = os.listdir(item_path)
                for sub_item in sub_items[:5]:  # Show first 5 items
                    print(f"    - {sub_item}")
                if len(sub_items) > 5:
                    print(f"    ... and {len(sub_items) - 5} more items")
            except Exception as e:
                print(f"    Error listing subdirectory: {e}")
        else:
            print(f"  File: {item}")
    
    print(f"Attempting to load demos with UnityTranslator...")
    try:
        # Calculate adaptive sample rate for feedback demos using token estimation
        feedback_sample_rate = calculate_optimal_sample_rate_on_tokens(demo_path, max_tokens=(max_tokens['gpt-5-mini'] // 2), tokens_per_frame=tokens_per_frame)
        print(f"Using sample rate {feedback_sample_rate} for feedback demos (calculated from token limits)")
        feedback_demos = UnityTranslator.get_from(demo_path, sample_rate=feedback_sample_rate)
        print(f"✓ Successfully loaded feedback demos: {len(feedback_demos) if hasattr(feedback_demos, '__len__') else 'single demo'}")
    except Exception as e:
        print(f"Error loading feedback demos: {e}")
        print("This might be because the demonstration folder structure doesn't match what UnityTranslator expects.")
        print("The TacticalMR output structure is different from narrated demos and may need special handling.")
        return False
    
    # Build paths
    suffix_path = os.path.join(
        TACTICAL_MR_DIR, 
        f"Scenic-main/examples/unity/user-study-program-{user_study_program_name}.scenic"
    )
    
    # Determine next feedback number
    feedback_dir = os.path.join(pilot_dir, "feedback")
    os.makedirs(feedback_dir, exist_ok=True)
    
    # Get the latest feedback number
    latest_feedback_file, feedback_number = get_latest_scenic_file(pilot_dir, "feedback")
    next_feedback_number = (feedback_number + 1) if latest_feedback_file else 0
    
    # Output path in _SYNTHESIZED_PROGRAM
    output_filename = f"{user_study_program_name}-{detected_pilot_name}-openai-feedback{next_feedback_number}.scenic"
    output_path = os.path.join(feedback_dir, output_filename)
    
    print(f"Context file: {latest_scenic_file}")
    print(f"Suffix path: {suffix_path}")
    print(f"Output path: {output_path}")
    
    # Generate regular feedback program
    print("Generating regular feedback Scenic program...")
    
    try:
        result = generate_final_scenic_with_syntax_check(
            context=latest_scenic_file,
            suffix_path=suffix_path,
            output_path=output_path,
            api=api,
            synth_demo=feedback_demos,
            demos=None,  # No original demos for regular feedback
            model=OPENAI_MODEL,
            fsm=False
        )
        
        # Extract timing information if available
        if len(result) >= 4:
            fixed_code, llm_resp, syntax_issues, generation_timing = result
        else:
            # Fallback for older return format
            fixed_code, llm_resp, syntax_issues = result[:3]
            generation_timing = {'synthesis_time': 0, 'syntax_check_time': 0, 'total_time': 0}
        
        # Calculate elapsed time for the entire process
        elapsed_seconds = time.time() - start_time
        
        print(f"✓ Regular feedback program generated successfully: {output_filename}")
        print(f"Saved to: {feedback_dir}")
        
        # Display detailed timing information
        if generation_timing:
            print(f"\n=== Detailed Timing ===")
            print(f"Initial synthesis:     {generation_timing['synthesis_time']:.2f} seconds")
            print(f"Syntax checking:       {generation_timing['syntax_check_time']:.2f} seconds")
            print(f"Generation subtotal:   {generation_timing['total_time']:.2f} seconds")
            print(f"Setup and overhead:    {elapsed_seconds - generation_timing['total_time']:.2f} seconds")
            print(f"Total process time:    {elapsed_seconds:.2f} seconds")
        else:
            print(f"Total time: {elapsed_seconds:.2f} seconds")
        
        # Copy to Unity repo
        copy_to_unity_repo(output_path, detected_pilot_name, "feedback")
        
        return True
        
    except Exception as e:
        # Calculate elapsed time even on failure
        elapsed_seconds = time.time() - start_time
        print(f"Error generating regular feedback program: {e}")
        print(f"Time elapsed before failure: {elapsed_seconds:.2f} seconds")
        return False

def main():
    """Main function that handles command line arguments and processes accordingly."""
    parser = argparse.ArgumentParser(description="Auto feedback generator for pilot/participant data")
    parser.add_argument("pilot_name", help="Pilot or participant name (e.g., pilot0, pilot13, participant0, participant12)")
    parser.add_argument("--fsm", action="store_true", help="Process FSM feedback mode")
    parser.add_argument("--feedback", action="store_true", help="Process regular feedback mode")
    
    args = parser.parse_args()
    
    # Validate pilot/participant name ("example" is the bundled standalone sample)
    if not (args.pilot_name.startswith("pilot") or args.pilot_name.startswith("participant") or args.pilot_name.startswith("example")):
        print("Error: Name must start with 'pilot', 'participant', or 'example' (e.g., pilot0, participant13, example)")
        sys.exit(1)
    
    print(f"Processing pilot/participant: {args.pilot_name}")
    
    # Start overall timing
    start_time = time.time()
    
    # Determine processing mode
    if args.fsm:
        success = process_fsm_mode(args.pilot_name)
    elif args.feedback:
        success = process_feedback_mode(args.pilot_name)
    else:
        print("Error: Must specify either --fsm or --feedback mode")
        print("Usage: python auto_feedback.py pilot0 --fsm")
        print("       python auto_feedback.py pilot0 --feedback")
        print("       python auto_feedback.py participant0 --fsm")
        print("       python auto_feedback.py participant12 --feedback")
        sys.exit(1)
    
    # Calculate overall elapsed time
    elapsed_seconds = time.time() - start_time
    
    if success:
        print(f"\n✓ Feedback processing completed successfully!")
        print(f"Total execution time: {elapsed_seconds:.2f} seconds")
    else:
        print(f"\n✗ Feedback processing failed!")
        print(f"Time elapsed before failure: {elapsed_seconds:.2f} seconds")
        sys.exit(1)

if __name__ == "__main__":
    main() 