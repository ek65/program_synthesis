import os
import sys
import time
import glob
import shutil
import argparse
from pathlib import Path

"""
Auto-FSM script for generating FSM JSON files from Scenic programs.

USAGE:
    python v2/auto_fsm.py <pilot_name>
    python v2/auto_fsm.py <pilot_name> --fsm
    python v2/auto_fsm.py <pilot_name> --feedback
    
    Examples:
        python v2/auto_fsm.py pilot0
        python v2/auto_fsm.py pilot0 --fsm
        python v2/auto_fsm.py pilot0 --feedback
        python v2/auto_fsm.py participant0

REQUIREMENTS:
    - Must specify a pilot/participant name as a command line argument
    - Name must start with 'pilot' or 'participant' (e.g., pilot0, participant13)
    - Pilot/participant directory must exist in _NARRATED_DEMOS/
    - Must have existing synthesized programs from auto_synthesis.py first
    - Requires json_fsm.py module in the v2 directory
    - Generates FSM JSON files and copies them to Unity _FSM folder
"""

# Hardcoded constants
DATA_BASE_PATH = os.environ.get("DATA_BASE_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"))
TACTICAL_MR_DIR = os.environ.get("TACTICAL_MR_DIR", "/path/to/TacticalMR")
UNITY_FSM_PATH = os.environ.get("UNITY_FSM_PATH", os.path.join(TACTICAL_MR_DIR, "UnityProject/Assets/Resources/_FSM"))
DEFAULT_DATA_FOLDER = "_NARRATED_DEMOS"

def find_pilot_folder(pilot_name):
    """
    Find the pilot/participant folder within _NARRATED_DEMOS.
    
    Args:
        pilot_name: The pilot/participant name (e.g., "pilot0", "pilot13", "participant0", "participant13")
    
    Returns:
        The pilot/participant folder path (e.g., "pilot0") or None if not found
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

def generate_fsm_json(scenic_file_path, output_path):
    """
    Generate FSM JSON from scenic file using the json_fsm module.
    
    Args:
        scenic_file_path: Path to the input scenic file
        output_path: Path to save the output JSON file
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Import the json_fsm module
        sys.path.append(os.path.join(DATA_BASE_PATH, ".."))
        from json_fsm import scenic_to_fsm_json_with_llm
        
        print(f"Generating FSM from: {os.path.basename(scenic_file_path)}")
        print(f"Output to: {output_path}")
        
        # Generate the FSM
        scenic_to_fsm_json_with_llm(scenic_file_path, output_path, model="gpt-4.1")
        
        print(f"✓ FSM generated successfully: {os.path.basename(output_path)}")
        return True
        
    except ImportError as e:
        print(f"Error importing json_fsm module: {e}")
        print("Make sure json_fsm.py is in the v2 directory")
        return False
    except Exception as e:
        print(f"Error generating FSM: {e}")
        return False

def copy_to_unity_fsm(json_file_path):
    """
    Copy the generated FSM JSON file to Unity's _FSM folder.
    This ensures Unity always has the latest FSM file.
    
    Args:
        json_file_path: Path to the source JSON file
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Skip the Unity copy when TacticalMR isn't available (standalone runs).
        if not os.path.isdir(TACTICAL_MR_DIR):
            print(f"Note: TACTICAL_MR_DIR ('{TACTICAL_MR_DIR}') not found — skipping copy "
                  f"to the Unity project. Set TACTICAL_MR_DIR to enable Unity integration.")
            return False
        # Ensure Unity FSM directory exists
        os.makedirs(UNITY_FSM_PATH, exist_ok=True)
        
        # Remove any existing JSON files in Unity FSM folder
        existing_files = glob.glob(os.path.join(UNITY_FSM_PATH, "*.json"))
        for file_path in existing_files:
            os.remove(file_path)
            print(f"Removed existing FSM file: {os.path.basename(file_path)}")
        
        # Copy the new FSM file
        unity_fsm_file = os.path.join(UNITY_FSM_PATH, "fsm.json")
        shutil.copy2(json_file_path, unity_fsm_file)
        
        print(f"✓ FSM copied to Unity: {unity_fsm_file}")
        return True
        
    except Exception as e:
        print(f"Error copying FSM to Unity: {e}")
        return False

def process_fsm_mode(pilot_name):
    """
    Process FSM generation mode.
    
    Args:
        pilot_name: The pilot/participant name (e.g., "pilot0", "participant0")
    
    Returns:
        bool: True if successful, False otherwise
    """
    print("=" * 60)
    print(f"FSM GENERATION MODE: Processing pilot/participant {pilot_name}")
    print("=" * 60)
    
    # Find the pilot folder
    pilot_folder = find_pilot_folder(pilot_name)
    if not pilot_folder:
        return False
    
    # Construct paths
    pilot_dir = os.path.join(DATA_BASE_PATH, "_SYNTHESIZED_PROGRAM", pilot_name)
    fsm_dir = os.path.join(pilot_dir, "fsm")
    designated_fsm_dir = os.path.join(DATA_BASE_PATH, "_FSM", pilot_name)
    
    # Ensure directories exist
    os.makedirs(fsm_dir, exist_ok=True)
    os.makedirs(designated_fsm_dir, exist_ok=True)
    
    # Get the latest FSM scenic file
    latest_fsm_file, fsm_number = get_latest_scenic_file(pilot_dir, "fsm")
    if not latest_fsm_file:
        print("No FSM scenic files found. Please generate some FSM files first.")
        return False
    
    # Determine next FSM number
    next_fsm_number = fsm_number + 1
    
    # Generate FSM JSON
    base_name = os.path.splitext(os.path.basename(latest_fsm_file))[0]
    # For FSM mode, we need to create the next FSM number
    # Extract the base name without the FSM number (e.g., "overlap-pilot0-openai" from "overlap-pilot0-openai-fsm0")
    if "-fsm" in base_name:
        # Remove the FSM number suffix
        base_name = base_name.rsplit("-fsm", 1)[0]
    
    output_filename = f"{base_name}-fsm{next_fsm_number}.json"
    output_path = os.path.join(designated_fsm_dir, output_filename)
    
    success = generate_fsm_json(latest_fsm_file, output_path)
    if success:
        # Copy to Unity FSM folder
        copy_to_unity_fsm(output_path)
        
        print(f"\nFSM generation complete!")
        print(f"Generated: {output_filename}")
        print(f"Saved to: {designated_fsm_dir}")
        if os.path.isdir(TACTICAL_MR_DIR):
            print(f"Copied to Unity: {UNITY_FSM_PATH}")
    
    return success

def process_feedback_mode(pilot_name):
    """
    Process feedback FSM generation mode (like FSM mode, but reads from feedback folder).

    Args:
        pilot_name: The pilot/participant name (e.g., "pilot0", "participant0")

    Returns:
        bool: True if successful, False otherwise
    """
    print("=" * 60)
    print(f"FEEDBACK FSM GENERATION MODE: Processing pilot/participant {pilot_name}")
    print("=" * 60)

    # Find the pilot folder
    pilot_folder = find_pilot_folder(pilot_name)
    if not pilot_folder:
        return False

    # Construct paths
    pilot_dir = os.path.join(DATA_BASE_PATH, "_SYNTHESIZED_PROGRAM", pilot_name)
    feedback_dir = os.path.join(pilot_dir, "fsm")
    designated_fsm_dir = os.path.join(DATA_BASE_PATH, "_FSM", pilot_name)

    # Ensure directories exist
    os.makedirs(feedback_dir, exist_ok=True)
    os.makedirs(designated_fsm_dir, exist_ok=True)

    # Get the latest feedback scenic file
    latest_feedback_file, feedback_number = get_latest_scenic_file(pilot_dir, "feedback")
    if not latest_feedback_file:
        print("No feedback scenic files found. Please generate some feedback files first.")
        return False

    # Determine next feedback number
    next_feedback_number = feedback_number + 1

    # Generate FSM JSON from feedback scenic file
    base_name = os.path.splitext(os.path.basename(latest_feedback_file))[0]
    if "-feedback" in base_name:
        base_name = base_name.rsplit("-feedback", 1)[0]
    output_filename = f"{base_name}-feedback{next_feedback_number}.json"
    output_path = os.path.join(designated_fsm_dir, output_filename)

    print(f"Feedback FSM generation for: {os.path.basename(latest_feedback_file)}")
    print(f"Output: {output_filename}")
    print(f"Saved to: {designated_fsm_dir}")

    success = generate_fsm_json(latest_feedback_file, output_path)
    if success:
        # Copy to Unity FSM folder
        copy_to_unity_fsm(output_path)
        print(f"\nFeedback FSM generation complete!")
        print(f"Generated: {output_filename}")
        print(f"Saved to: {designated_fsm_dir}")
        if os.path.isdir(TACTICAL_MR_DIR):
            print(f"Copied to Unity: {UNITY_FSM_PATH}")

    return success

def process_scenic_mode(pilot_name):
    """
    Process scenic file mode (default behavior).
    
    Args:
        pilot_name: The pilot/participant name (e.g., "pilot0", "participant0")
    
    Returns:
        bool: True if successful, False otherwise
    """
    print("=" * 60)
    print(f"SCENIC PROCESSING MODE: Processing pilot/participant {pilot_name}")
    print("=" * 60)
    
    # Find the pilot folder
    pilot_folder = find_pilot_folder(pilot_name)
    if not pilot_folder:
        return False
    
    # Construct paths
    pilot_dir = os.path.join(DATA_BASE_PATH, "_SYNTHESIZED_PROGRAM", pilot_name)
    designated_fsm_dir = os.path.join(DATA_BASE_PATH, "_FSM", pilot_name)
    
    # Ensure directories exist
    os.makedirs(designated_fsm_dir, exist_ok=True)
    
    # Get the latest scenic file
    latest_scenic_file, scenic_number = get_latest_scenic_file(pilot_dir, "scenic")
    if not latest_scenic_file:
        print("No scenic files found. Please generate some scenic files first.")
        return False
    
    # Generate FSM JSON
    base_name = os.path.splitext(os.path.basename(latest_scenic_file))[0]
    output_filename = f"{base_name}-fsm0.json"
    output_path = os.path.join(designated_fsm_dir, output_filename)
    
    success = generate_fsm_json(latest_scenic_file, output_path)
    if success:
        # Copy to Unity FSM folder
        copy_to_unity_fsm(output_path)
        
        print(f"\nScenic processing complete!")
        print(f"Generated: {output_filename}")
        print(f"Saved to: {designated_fsm_dir}")
        if os.path.isdir(TACTICAL_MR_DIR):
            print(f"Copied to Unity: {UNITY_FSM_PATH}")
    
    return success

def main():
    """Main function that handles command line arguments and processes accordingly."""
    parser = argparse.ArgumentParser(description="Auto FSM generator for pilot/participant data")
    parser.add_argument("pilot_name", help="Pilot/participant name (e.g., pilot0, pilot13, participant0, participant13)")
    parser.add_argument("--fsm", action="store_true", help="Process FSM mode (use latest FSM scenic file)")
    parser.add_argument("--feedback", action="store_true", help="Process feedback mode (use latest feedback scenic file)")
    
    args = parser.parse_args()
    
    # Validate pilot/participant name ("example" is the bundled standalone sample)
    if not (args.pilot_name.startswith("pilot") or args.pilot_name.startswith("participant") or args.pilot_name.startswith("example")):
        print("Error: Name must start with 'pilot', 'participant', or 'example' (e.g., pilot0, participant13, example)")
        sys.exit(1)
    
    print(f"Processing pilot/participant: {args.pilot_name}")
    
    # Start timing
    start_time = time.time()
    
    # Determine processing mode
    if args.fsm:
        success = process_fsm_mode(args.pilot_name)
    elif args.feedback:
        success = process_feedback_mode(args.pilot_name)
    else:
        # Default: process scenic mode
        success = process_scenic_mode(args.pilot_name)
    
    # Calculate elapsed time
    elapsed_seconds = time.time() - start_time
    
    if success:
        print("\n✓ Processing completed successfully!")
        print(f"Total time: {elapsed_seconds:.2f} seconds")
    else:
        print("\n✗ Processing failed!")
        print(f"Total time: {elapsed_seconds:.2f} seconds")
        sys.exit(1)

if __name__ == "__main__":
    main()
