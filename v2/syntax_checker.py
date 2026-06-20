import os
import json
import requests
from typing import List, Dict, Tuple
import nlp_utils
import nlp_utils_gemini as gemini_utils
from api_utils import API
from apiKey import OPENAI_API_KEY, GEMINI_API_KEY
from openai import OpenAI

client = OpenAI(api_key=OPENAI_API_KEY)

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

class ScenicSyntaxChecker:
    """
    A simple syntax checker for Scenic programs that uses LLMs to detect and fix issues.
    Only modifies the section between ####HEADER ENDS#### and ####Environment Behavior START####.
    """
    
    def __init__(self, api: dict, openai_model: str = "gpt-5-mini", gemini_model: str = "gemini-2.5-pro"):
        self.api = api
        self.constraintAPI = api[API.constraints]
        self.actionAPI = api[API.actions]
        self.openai_model = openai_model
        self.gemini_model = gemini_model
        self.doc_cache = {}
        self.last_token_usage = None
    
    def load_cache(self, cache_file="doc_cache.json"):
        """Load documentation cache."""
        if os.path.exists(cache_file):
            with open(cache_file, "r") as f:
                return json.load(f)
        return {}
    
    def save_cache(self, cache, cache_file="doc_cache.json"):
        """Save documentation cache."""
        with open(cache_file, "w") as f:
            json.dump(cache, f)
    
    def fetch_documentation(self, url, cache):
        """Fetch Scenic documentation with caching."""
        if url in cache:
            print("Using cached Scenic documentation")
            return cache[url]
        else:
            print("Fetching Scenic documentation")
            response = requests.get(url)
            if response.status_code == 200:
                cache[url] = response.text
                self.save_cache(cache)
                return response.text
            else:
                raise Exception(f"Failed to fetch URL content: {response.status_code}")
    
    def load_scenic_file(self, file_path: str) -> str:
        """Load a Scenic file and return its content."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Scenic file not found: {file_path}")
        except Exception as e:
            raise Exception(f"Error reading file {file_path}: {e}")
    
    def save_scenic_file(self, file_path: str, content: str) -> None:
        """Save content to a Scenic file, overwriting the original."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed Scenic file saved to: {file_path}")
        except Exception as e:
            raise Exception(f"Error saving file {file_path}: {e}")
    
    def extract_coach_behavior_section(self, content: str) -> Tuple[str, str, str]:
        """
        Extract the CoachBehavior section between ####HEADER ENDS#### and ####Environment Behavior START####.
        Returns (header, coach_behavior_section, footer).
        """
        header_end = "####HEADER ENDS####"
        env_behavior_start = "####Environment Behavior START####"
        
        # Find the markers
        header_end_pos = content.find(header_end)
        env_behavior_start_pos = content.find(env_behavior_start)
        
        if header_end_pos == -1:
            raise ValueError("Could not find ####HEADER ENDS#### marker")
        
        if env_behavior_start_pos == -1:
            # If no environment behavior marker, take everything after header
            header = content[:header_end_pos + len(header_end)]
            coach_behavior_section = content[header_end_pos + len(header_end):]
            footer = ""
        else:
            # Extract the three sections
            header = content[:header_end_pos + len(header_end)]
            coach_behavior_section = content[header_end_pos + len(header_end):env_behavior_start_pos]
            footer = content[env_behavior_start_pos:]
        
        return header, coach_behavior_section.strip(), footer
    
    def reconstruct_file_content(self, header: str, coach_behavior_section: str, footer: str) -> str:
        """Reconstruct the full file content from header, coach behavior section, and footer."""
        if footer:
            return header + "\n\n" + coach_behavior_section + "\n\n" + footer
        else:
            return header + "\n\n" + coach_behavior_section
    
    def check_and_fix_with_llm(self, content: str, full_file_content: str = None) -> Tuple[str, List[Dict]]:
        """
        Use LLM to check and fix syntax issues in Scenic code.
        Returns (fixed_content, list_of_issues_found).
        
        Args:
            content: The CoachBehavior section to fix
            full_file_content: The complete file content for context
        """
        
        # Load documentation and APIs
        doc_url = "https://docs.scenic-lang.org/en/latest/tutorials/dynamics.html"
        cache = self.load_cache()
        doc_text = self.fetch_documentation(doc_url, cache)
        
        system_prompt = f"""
You are a Scenic syntax expert. Your task is to check and fix ONLY syntax errors that would cause execution failures.

Available Actions: {list(self.actionAPI.keys())}
Available Constraints: {list(self.constraintAPI.keys())}

You will be provided with:
1. Scenic programming language syntax and semantics documentation from the official docs.
2. A library of APIs for modeling actions and constraints.
3. The complete Scenic file for context.
4. The specific section between ####HEADER ENDS#### and ####Environment Behavior START#### that needs to be fixed. 
5. An example Scenic program for you to reference the structure of the code to maintain in your fixed code. 

Your task is to:
Fix any syntax errors *only within* the section between ####HEADER ENDS#### and ####Environment Behavior START####.
You must not modify any code outside this section.

Guidelines:
1. Scenic is a programming language embedded in Python so it inherits Python syntax and semantics. Check for any Python syntax errors.
2. Do not try to optimize the code. Do not remove any code that is syntactically correct, even if it seems unused.
   Do NOT provide optimization suggestions or style improvements. 
3. Make sure all the variables are defined before they are used. 
   If they are used before they are defined, then delete them throughout the code in a manner to avoid compilation errors.
4. Make sure the variables you delete are not reflected in the descriptions within Speak() lines.
5. Regarding Speak() lines, make sure that the description is consistent with the code in the same style as shown in the example Scenic program.
   Each Speak() line explains the code that comes immediately underneath it. 
6. Try to make minimal changes to the code and maintain the same structure of the code. 
7. Do not import any packages or statements. Assume that all the provided APIs are imported in the file.
8. The following are examples of syntax errors that you need to fix:
   - Incorrect API usage (type mismatch in the input parameters, typo or hallucination in API names)
   - Missing parentheses in function calls
   - Missing colons after behavior/function definitions
   - Incorrect indentation
   - Missing quotes in strings
   - Invalid Python syntax
   - headers, markdowns, backticks, like ```scenic, ```python, ``` need to be removed and the code should be indented properly.
     In your output, however, make sure you include the ```scenic header as stated below. 
9. Make sure there is no reference to API that is not defined in the API documentation. If there are references to APIs that are not 
   defined in the API documentation, try to understand what that code is trying to do and replace it with APIs that are defined in the API documentation,
   which has the same or similar functionality to preserve the same semantics. Note that before each line of code, there is a do Speak("...") line which explains the code.
   So, you can reference the description of the SpeakAction() to understand what the code is trying to do and replace it with the closest API that is defined in the API documentation,

IMPORTANT: 
- 'do Speak("...")' lines are valid and should NOT be changed. These are intentional speech actions for the coach and should be preserved exactly as they are.
- Return the COMPLETE section between ####HEADER ENDS#### and ####Environment Behavior START#### including:
  * The behavior CoachBehavior(): block
  * All constraint instantiations (e.g., A1target_0 = AtAngle({...}))
  * All lambda functions (e.g., def λ_target0(): ...)
  * Any other code that was in the original section between the markers
- Do *NOT* include the markers themselves (####HEADER ENDS#### or ####Environment Behavior START####) in your output
- Do *NOT* include any code outside this section
- ONLY fix syntax errors that would prevent the code from running

Format your response as:
ISSUES: Provide this information in text first.  
- Issue 1 : <issue 1 description>
- Issue 2 : <issue 2 description>
...

FIXED_CODE: Underneath the description of the ISSUES above, provide the fixed code in the following format. Make sure the outputted fixed code starts with ``` and ends with ```.
```scenic
[corrected section between ####HEADER ENDS#### and ####Environment Behavior START#### with ALL code, including constraints and lambda functions and CoachBehavior()]
```

"""
        
        # Build message entries for OpenAI
        openai_entries = [
            nlp_utils.Chat.Entry(role='system', text=system_prompt),
            nlp_utils.Chat.Entry(role='user', text="Scenic documentation:\n" + doc_text),
            nlp_utils.Chat.Entry(role='system', text='Library of actionAPIs:\n\n' + '\n\n'.join([f'[API ID] {i}\n{c.doc()}' for i, c in self.actionAPI.items()])),
            nlp_utils.Chat.Entry(role='system', text='Library of constraintAPIs:\n\n' + '\n\n'.join([f'[API ID] {i}\n{c.doc()}' for i, c in self.constraintAPI.items()]))
        ]
        
        # Add full file context as separate entry
        if full_file_content:
            openai_entries.append(
                nlp_utils.Chat.Entry(role='user', text="Complete Scenic file (for context only):\n" + full_file_content)
            )
        
        # Add the specific section to fix as separate entry
        openai_entries.append(
            nlp_utils.Chat.Entry(role='user', text="CoachBehavior section to fix:\n" + content)
        )

        # Add example Scenic program
        openai_entries.append(nlp_utils.Chat.Entry(role='user', text="Example Scenic program:\n" + EX_SCRIPT))
        
        # # Build message entries for Gemini
        # gemini_entries = [
        #     gemini_utils.Chat.Entry(role='system', text=system_prompt),
        #     gemini_utils.Chat.Entry(role='user', text="Scenic documentation:\n" + doc_text),
        #     gemini_utils.Chat.Entry(role='system', text='Library of actionAPIs:\n\n' + '\n\n'.join([f'[API ID] {i}\n{c.doc()}' for i, c in self.actionAPI.items()])),
        #     gemini_utils.Chat.Entry(role='system', text='Library of constraintAPIs:\n\n' + '\n\n'.join([f'[API ID] {i}\n{c.doc()}' for i, c in self.constraintAPI.items()]))
        # ]
        
        # # Add full file context as separate entry
        # if full_file_content:
        #     gemini_entries.append(
        #         gemini_utils.Chat.Entry(role='user', text="Complete Scenic file (for context only):\n" + full_file_content)
        #     )
        
        # # Add the specific section to fix as separate entry
        # gemini_entries.append(
        #     gemini_utils.Chat.Entry(role='user', text="CoachBehavior section to fix:\n" + content)
        # )
        
        # Try OpenAI first
        try:
            chat_openai = nlp_utils.Chat(client, model=self.openai_model)
            print(f"Checking syntax errors with OpenAI model: {self.openai_model}")
            response_openai = chat_openai(openai_entries)
            
            # Store token usage
            self.last_token_usage = chat_openai.get_last_token_usage()
            
            fixed_content, issues = self._parse_llm_response(response_openai)
            if fixed_content:
                return fixed_content, issues
                
        except Exception as e:
            print(f"OpenAI fix failed: {e}")
            self.last_token_usage = None
        
        # Try Gemini as fallback
        # try:
        #     chat_gemini = gemini_utils.Chat(model=self.gemini_model)
        #     response_gemini = chat_gemini(gemini_entries)
            
        #     fixed_content, issues = self._parse_llm_response(response_gemini)
        #     if fixed_content:
        #         return fixed_content, issues
                
        # except Exception as e:
        #     print(f"Gemini fix failed: {e}")
        
        # If both LLMs fail, return original content
        print("Warning: Could not check syntax with LLM, returning original content")
        self.last_token_usage = None
        return content, []
    
    def get_last_token_usage(self):
        """Return token usage from the last syntax check."""
        return self.last_token_usage
    
    def _parse_llm_response(self, response: str) -> Tuple[str, List[Dict]]:
        """Parse LLM response to extract issues and fixed code."""
        issues = []
        fixed_code = ""
        
        # Look for ISSUES section
        if "ISSUES:" in response:
            issues_start = response.find("ISSUES:")
            issues_end = response.find("FIXED_CODE:", issues_start)
            if issues_end == -1:
                issues_end = response.find("```", issues_start)
            
            if issues_end != -1:
                issues_text = response[issues_start:issues_end].strip()
                # Parse issues (simple parsing)
                for line in issues_text.split('\n'):
                    line = line.strip()
                    if line.startswith('-') or line.startswith('•'):
                        issues.append({
                            'type': 'syntax_issue',
                            'message': line[1:].strip()
                        })
        
        # Look for FIXED_CODE section
        if "FIXED_CODE:" in response:
            code_start = response.find("FIXED_CODE:")
            code_section = response[code_start:]
            
            # Extract code from markdown blocks
            if '```' in code_section:
                start = code_section.find('```')
                end = code_section.find('```', start + 3)
                if end != -1:
                    code = code_section[start + 3:end].strip()
                    # Remove language identifier if present
                    if code.startswith('scenic') or code.startswith('python'):
                        code = code.split('\n', 1)[1] if '\n' in code else ''
                    fixed_code = code
        
        # If no FIXED_CODE section, try to extract code from the end
        if not fixed_code and '```' in response:
            start = response.rfind('```')
            end = response.rfind('```', 0, start)
            if start != -1 and end != -1:
                code = response[end + 3:start].strip()
                if code.startswith('scenic') or code.startswith('python'):
                    code = code.split('\n', 1)[1] if '\n' in code else ''
                fixed_code = code
        
        return fixed_code, issues
    
    def check_and_fix_file(self, file_path: str, overwrite: bool = True) -> Tuple[str, List[Dict]]:
        """
        Check and fix syntax issues in a Scenic file.
        Only modifies the section between ####HEADER ENDS#### and ####Environment Behavior START####.
        
        Args:
            file_path: Path to the Scenic file
            overwrite: Whether to overwrite the original file
            
        Returns:
            Tuple of (fixed_content, issues)
        """
        print(f"Checking syntax for: {file_path}")
        
        # Load the file
        content = self.load_scenic_file(file_path)
        
        try:
            # Extract the sections
            header, coach_behavior_section, footer = self.extract_coach_behavior_section(content)
            
            # Check and fix only the coach behavior section
            fixed_coach_behavior, issues = self.check_and_fix_with_llm(coach_behavior_section, content)
            
            # Reconstruct the full content
            fixed_content = self.reconstruct_file_content(header, fixed_coach_behavior, footer)
            
            if not issues:
                print("No syntax issues found!")
            else:
                print(f"Found {len(issues)} syntax issues:")
                for issue in issues:
                    print(f"  - {issue['message']}")
            
            # Save the fixed content
            if overwrite:
                self.save_scenic_file(file_path, fixed_content)
            else:
                # Create backup file
                backup_path = file_path + '.backup'
                self.save_scenic_file(backup_path, content)
                self.save_scenic_file(file_path, fixed_content)
                print(f"Original file backed up to: {backup_path}")
            
            return fixed_content, issues
            
        except Exception as e:
            print(f"Error processing file: {e}")
            return content, [{'type': 'error', 'message': str(e)}]
    
    def check_multiple_files(self, file_paths: List[str], overwrite: bool = True) -> Dict[str, Tuple[str, List[Dict]]]:
        """
        Check and fix multiple Scenic files.
        Only modifies the section between ####HEADER ENDS#### and ####Environment Behavior START####.
        
        Args:
            file_paths: List of file paths to check
            overwrite: Whether to overwrite original files
            
        Returns:
            Dictionary mapping file paths to (fixed_content, issues) tuples
        """
        results = {}
        
        for file_path in file_paths:
            try:
                fixed_content, issues = self.check_and_fix_file(file_path, overwrite)
                results[file_path] = (fixed_content, issues)
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
                results[file_path] = (None, [{'type': 'error', 'message': str(e)}])
        
        return results
    
    def find_scenic_files(self, directory: str) -> List[str]:
        """Find all .scenic files in a directory recursively."""
        scenic_files = []
        
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.scenic'):
                    scenic_files.append(os.path.join(root, file))
        
        return scenic_files


def main():
    """Main function for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Check and fix Scenic syntax issues')
    parser.add_argument('files', nargs='+', help='Scenic files to check')
    parser.add_argument('--api', required=True, help='Path to API configuration')
    parser.add_argument('--no-overwrite', action='store_true', help='Create backup instead of overwriting')
    parser.add_argument('--openai-model', default='gpt-4o', help='OpenAI model to use')
    parser.add_argument('--gemini-model', default='gemini-2.5-pro', help='Gemini model to use')
    
    args = parser.parse_args()
    
    # Load API configuration
    # This would need to be adapted based on your API loading mechanism
    # For now, we'll use a placeholder
    api = {
        API.actions: {},
        API.constraints: {},
        API.domain: 'soccer',
        API.default_obj: 'Coach'
    }
    
    # Create syntax checker
    checker = ScenicSyntaxChecker(
        api=api,
        openai_model=args.openai_model,
        gemini_model=args.gemini_model
    )
    
    # Check files
    results = checker.check_multiple_files(args.files, overwrite=not args.no_overwrite)
    
    # Print summary
    print("\n=== Summary ===")
    for file_path, (content, issues) in results.items():
        if content is None:
            print(f"{file_path}: ERROR")
        elif not issues:
            print(f"{file_path}: OK")
        else:
            print(f"{file_path}: FIXED ({len(issues)} issues)")


if __name__ == "__main__":
    main()
