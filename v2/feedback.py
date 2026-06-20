import os
from typing import List, Optional, Union, Tuple, Any
from nlp_utils import Chat, client
from fix_openai_scenic import Fix_OpenAI_Scenic
from vanilla_scenic import load_python_file_as_string, prepend_text_to_file, HEADER_LINES


def reformat_code_with_llm(code: str, model: str = "gpt-5-mini") -> str:
    system_prompt = (
        "You are a Scenic code formatter. "
        "Format the following Scenic code according to PEP8 and Scenic style guidelines. "
        "Return only the formatted code without any additional commentary."
        "Don't start with syntax like this '```scenic', the code has to be runnable without deleting any anottations, markdowns or backticks!"
    )
    chat = Chat(client, model=model)
    messages = [
        Chat.Entry(role="system", text=system_prompt),
        Chat.Entry(role="user", text=f"```python\n{code}\n```"),
    ]
    response = chat(messages)
    start = response.find("```")
    if start != -1:
        end = response.find("```", start + 3)
        return response[start+3:end].strip() if end != -1 else response[start+3:].strip()
    return response.strip()


def _load_if_path(obj: Union[str, object]) -> object:
    if isinstance(obj, str) and os.path.exists(obj):
        return load_python_file_as_string(obj)
    return obj


def _extract_scenic_from_context(context: str) -> str:
    start_marker = "####HEADER ENDS####"
    end_marker = "####Environment Behavior START####"
    start_idx = context.find(start_marker)
    if start_idx < 0:
        raise ValueError(f"Missing start marker '{start_marker}' in context")
    start_idx += len(start_marker)
    end_idx = context.find(end_marker, start_idx)
    if end_idx < 0:
        raise ValueError(f"Missing end marker '{end_marker}' in context")
    return context[start_idx:end_idx].strip()


def generate_final_scenic(
    context: str,
    suffix_path: str,
    output_path: str,
    api,
    model: str = "gpt-5-mini",
    synth_demo: Optional[object] = None,
    demos: Optional[List[object]] = None,
    fsm: bool = False
) -> Tuple[str, Any]:
    """
    Extract & fix Scenic code from `context`, format, prepend header, merge with existing suffix file, and save.

    Args:
        context: path or content of full Scenic program.
        suffix_path: path to file whose content should follow the formatted snippet.
        output_path: where to write the merged result.
        model: LLM model name.
        synth_demo: optional synthetic demo object.
        demos: optional list of demo objects.

    Returns:
        fixed_code: raw output from Fix_Gemini_Scenic.
        llm_resp: the LLM response (for debugging or logs).
    """
    # Load context
    context = _load_if_path(context)

    # Extract snippet
    scenic_code = _extract_scenic_from_context(context)

    # Prepare demos
    demos_list: List[object] = []
    if demos:
        demos_list = [_load_if_path(d) for d in demos]

    # Fix via OpenAI scenic
    fixer = Fix_OpenAI_Scenic(
        scenic_code=scenic_code,
        feedback="NONE",
        scenic_docs_url="https://docs.scenic-lang.org/en/latest/syntax_guide.html",
        api = api,
        context=context,
        synth_demo=synth_demo,
        demos=demos_list,
        fsm=fsm,
        model=model
    )
    fixed_code, llm_resp = fixer.run()

    # Format code with LLM
    # formatted_core = reformat_code_with_llm(fixed_code, model=model)

    # Prepend header to formatted snippet
    header_text = "\n".join(HEADER_LINES) + "\n"
    formatted_with_header = header_text + fixed_code

    # Merge formatted_with_header with suffix file and save
    prepend_text_to_file(suffix_path, output_path, formatted_with_header)

    print(f"Final Scenic program saved to {output_path}")
    return fixed_code, llm_resp

# Example usage:
# generate_final_scenic(
#     context="full_program.scenic",
#     suffix_path="custom_suffix.scenic",
#     output_path="final_output.scenic",
#     synth_demo=my_synth,
#     demos=[demo1, demo2]
# )
