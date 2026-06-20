import os
import time
from typing import List, Optional, Union, Tuple, Any, Dict
from feedback import generate_final_scenic
from syntax_checker import ScenicSyntaxChecker


def generate_final_scenic_with_syntax_check(
    context: str,
    suffix_path: str,
    output_path: str,
    api,
    synth_demo,
    demos,
    model: str = "gpt-5-mini",
    openai_model: str = "gpt-5-mini",
    gemini_model: str = "gemini-2.5-pro",
    fsm: bool = False,
) -> Tuple[str, Any, List[Dict], Dict[str, float]]:
    """
    Generate final Scenic code using feedback.py and then check/fix syntax issues.
    
    Args:
        context: path or content of full Scenic program.
        suffix_path: path to file whose content should follow the formatted snippet.
        output_path: where to write the merged result.
        api: API configuration dictionary.
        model: LLM model name for code generation.
        synth_demo: optional synthetic demo object.
        demos: optional list of demo objects.
        openai_model: OpenAI model for syntax checking.
        gemini_model: Gemini model for syntax checking.
        
    Returns:
        Tuple of (fixed_code, llm_resp, syntax_issues, timing_info)
    """
    print("=== Step 1: Generating Scenic code using feedback.py ===")
    
    # Start timing for synthesis step
    synthesis_start_time = time.time()
    
    # Generate the initial Scenic code using feedback.py
    fixed_code, llm_resp = generate_final_scenic(
        context=context,
        suffix_path=suffix_path,
        output_path=output_path,
        api=api,
        model=model,
        synth_demo=synth_demo,
        demos=demos,
        fsm=fsm
    )
    
    # Calculate synthesis time
    synthesis_time = time.time() - synthesis_start_time
    print(f"Initial synthesis completed in {synthesis_time:.2f} seconds")
    
    print("\n=== Step 2: Checking and fixing syntax issues ===")
    
    # Start timing for syntax checking step
    syntax_check_start_time = time.time()
    
    # Initialize syntax checker
    syntax_checker = ScenicSyntaxChecker(
        api=api,
        openai_model=openai_model,
        gemini_model=gemini_model
    )
    
    # Check and fix syntax issues in the generated file
    try:
        fixed_content, issues = syntax_checker.check_and_fix_file(output_path, overwrite=True)
        
        if issues:
            print(f"Found and fixed {len(issues)} syntax issues:")
            for issue in issues:
                print(f"  - {issue.get('message', 'Unknown issue')}")
        else:
            print("No syntax issues found!")
        
        # Calculate syntax checking time
        syntax_check_time = time.time() - syntax_check_start_time
        print(f"Syntax checking completed in {syntax_check_time:.2f} seconds")
        
        # Prepare timing information
        timing_info = {
            'synthesis_time': synthesis_time,
            'syntax_check_time': syntax_check_time,
            'total_time': synthesis_time + syntax_check_time
        }
        
        print(f"\n=== Timing Summary ===")
        print(f"Initial synthesis: {timing_info['synthesis_time']:.2f} seconds")
        print(f"Syntax checking:   {timing_info['syntax_check_time']:.2f} seconds")
        print(f"Total generation:  {timing_info['total_time']:.2f} seconds")
            
        return fixed_code, llm_resp, issues, timing_info
        
    except Exception as e:
        # Calculate syntax checking time even on failure
        syntax_check_time = time.time() - syntax_check_start_time
        
        # Prepare timing information
        timing_info = {
            'synthesis_time': synthesis_time,
            'syntax_check_time': syntax_check_time,
            'total_time': synthesis_time + syntax_check_time
        }
        
        print(f"Error during syntax checking: {e}")
        print(f"Synthesis time: {timing_info['synthesis_time']:.2f} seconds")
        print(f"Time before syntax error: {timing_info['syntax_check_time']:.2f} seconds")
        return fixed_code, llm_resp, [{'type': 'error', 'message': str(e)}], timing_info 