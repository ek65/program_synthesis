#!/usr/bin/env python3
"""
Scenic Runner Script

This script runs the scenic command on a specified Scenic file.
Usage: python scenic_runner.py
"""

import os
import sys
import subprocess

def run_scenic_file(scenic_file_path):
    """
    Run a Scenic file using the scenic command.
    
    Args:
        scenic_file_path: Path to the .scenic file to run
    
    Returns:
        bool: True if successful, False otherwise
    """
    if not os.path.exists(scenic_file_path):
        print(f"Error: Scenic file does not exist: {scenic_file_path}")
        return False
    
    if not scenic_file_path.endswith('.scenic'):
        print(f"Error: File must be a .scenic file: {scenic_file_path}")
        return False
    
    print(f"Running Scenic file: {scenic_file_path}")
    print("=" * 60)
    
    try:
        # Run the scenic command
        cmd = ["scenic", "-S", "-b", scenic_file_path]
        print(f"Executing: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=False, text=True)
        
        if result.returncode == 0:
            print("✓ Scenic file executed successfully")
            return True
        else:
            print(f"✗ Scenic file execution failed with return code: {result.returncode}")
            return False
            
    except FileNotFoundError:
        print("Error: 'scenic' command not found. Please ensure Scenic is installed and in your PATH.")
        return False
    except Exception as e:
        print(f"Error running scenic command: {e}")
        return False

def main():
    """Main function that always runs the synthesized_program.scenic from Unity repo."""
    # Hardcoded path to Unity repo
    TACTICAL_MR_DIR = "/Users/tcdanielh/TacticalMR"
    UNITY_SYNTHESIZED_PROGRAM_DIR = os.path.join(TACTICAL_MR_DIR, "Scenic-main/examples/unity/_SYNTHESIZED_PROGRAM")
    
    # Construct path to the synthesized_program.scenic file
    scenic_file_path = os.path.join(UNITY_SYNTHESIZED_PROGRAM_DIR, "synthesized_program.scenic")
    
    print("Running scenic from Unity repo...")
    print(f"File path: {scenic_file_path}")
    
    success = run_scenic_file(scenic_file_path)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main() 