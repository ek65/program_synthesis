import os
import json
import requests
import re
from typing import List, Dict, Tuple, Optional
import nlp_utils
import nlp_utils_gemini as gemini_utils
from api_utils import API
from apiKey import OPENAI_API_KEY, GEMINI_API_KEY
from openai import OpenAI

client = OpenAI(api_key=OPENAI_API_KEY)

class ScenicErrorFixer:
    """
    A comprehensive error fixer for Scenic programs that uses LLMs to detect and fix both syntax issues and runtime errors.
    Only modifies the section between ####HEADER ENDS#### and ####Environment Behavior START####.
    """
    
    def __init__(self, api: dict, openai_model: str = "gpt-5-mini", gemini_model: str = "gemini-2.5-pro"):
        self.api = api
        self.constraintAPI = api[API.constraints]
        self.actionAPI = api[API.actions]
        self.openai_model = openai_model
        self.gemini_model = gemini_model
        self.doc_cache = {}
    
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
    
    def parse_error_message(self, error_message: str) -> Dict[str, any]:
        """
        Parse terminal error message to extract relevant information.
        Returns a dictionary with error details.
        """
        error_info = {
            'error_type': 'unknown',
            'line_number': None,
            'error_description': error_message,
            'suggested_fixes': []
        }
        
        # Common error patterns
        patterns = {
            'syntax_error': r'SyntaxError: (.+?)(?: at line (\d+))?',
            'name_error': r'NameError: name \'(.+?)\' is not defined',
            'attribute_error': r'AttributeError: \'(.+?)\' object has no attribute \'(.+?)\'',
            'type_error': r'TypeError: (.+?)',
            'value_error': r'ValueError: (.+?)',
            'index_error': r'IndexError: (.+?)',
            'key_error': r'KeyError: (.+?)',
            'import_error': r'ImportError: (.+?)',
            'module_not_found': r'ModuleNotFoundError: No module named \'(.+?)\'',
            'indentation_error': r'IndentationError: (.+?)',
            'scenic_error': r'ScenicError: (.+?)',
        }
        
        for error_type, pattern in patterns.items():
            match = re.search(pattern, error_message, re.IGNORECASE)
            if match:
                error_info['error_type'] = error_type
                error_info['error_description'] = match.group(1)
                
                # Extract line number if available
                if len(match.groups()) > 1 and match.group(2):
                    try:
                        error_info['line_number'] = int(match.group(2))
                    except ValueError:
                        pass
                break
        
        return error_info
    
    def check_and_fix_with_llm(self, content: str, full_file_content: str = None, error_message: str = None) -> Tuple[str, List[Dict]]:
        """
        Use LLM to check and fix syntax issues and runtime errors in Scenic code.
        Returns (fixed_content, list_of_issues_found).
        
        Args:
            content: The CoachBehavior section to fix
            full_file_content: The complete file content for context
            error_message: Terminal error message if available
        """
        
        # Load documentation and APIs
        doc_url = "https://docs.scenic-lang.org/en/latest/tutorials/dynamics.html"
        cache = self.load_cache()
        doc_text = self.fetch_documentation(doc_url, cache)
        
        # Parse error message if provided
        error_info = None
        if error_message:
            error_info = self.parse_error_message(error_message)
            print(f"Parsed error: {error_info['error_type']} - {error_info['error_description']}")
        
        system_prompt = f"""
You are a Scenic error fixer. Your task is to fix the specific error described in the terminal error message.

Available Actions: {list(self.actionAPI.keys())}
Available Constraints: {list(self.constraintAPI.keys())}

You will be provided with:
1. Scenic documentation from the official docs
2. Action and constraint API information
3. The complete Scenic file for context
4. The specific section between ####HEADER ENDS#### and ####Environment Behavior START#### that needs to be fixed
5. A terminal error message that occurred when running the code

Your job is to:
1. Read the terminal error message carefully
2. Identify the specific error described in the message
3. Fix ONLY that error in the section between ####HEADER ENDS#### and ####Environment Behavior START####
4. Consider the full file context when making the fix
5. Do NOT remove or modify code that is syntactically correct
6. Do NOT provide optimization suggestions or style improvements
7. Return the ENTIRE fixed section between ####HEADER ENDS#### and ####Environment Behavior START####

IMPORTANT: 
- 'do Speak("...")' lines are valid and should NOT be changed. These are intentional speech actions for the coach and should be preserved exactly as they are.
- Return the COMPLETE section between ####HEADER ENDS#### and ####Environment Behavior START#### including:
  * The behavior CoachBehavior(): block
  * All constraint instantiations (e.g., A1target_0 = AtAngle({...}))
  * All lambda functions (e.g., def λ_target0(): ...)
  * Any other code that was in the original section between the markers
- Do NOT include the markers themselves (####HEADER ENDS#### or ####Environment Behavior START####) in your output
- Do NOT include any code outside this section
- Focus ONLY on fixing the specific error mentioned in the terminal message

Format your response as:
ISSUES:
- Issue 1
- Issue 2
...

FIXED_CODE:
```scenic
[corrected section between ####HEADER ENDS#### and ####Environment Behavior START#### with ALL code, including constraints and lambda functions and CoachBehavior()]
```
"""
        
        # Add error message context if available
        if error_info:
            system_prompt += f"\n\nSPECIFIC ERROR TO FIX:\nError Type: {error_info['error_type']}\nError Description: {error_info['error_description']}"
            if error_info['line_number']:
                system_prompt += f"\nLine Number: {error_info['line_number']}"
        
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
        
        # Add error message if available
        if error_message:
            openai_entries.append(
                nlp_utils.Chat.Entry(role='user', text="Terminal error message:\n" + error_message)
            )
        
        # Add the specific section to fix as separate entry
        openai_entries.append(
            nlp_utils.Chat.Entry(role='user', text="CoachBehavior section to fix:\n" + content)
        )
        
        # Build message entries for Gemini
        gemini_entries = [
            gemini_utils.Chat.Entry(role='system', text=system_prompt),
            gemini_utils.Chat.Entry(role='user', text="Scenic documentation:\n" + doc_text),
            gemini_utils.Chat.Entry(role='system', text='Library of actionAPIs:\n\n' + '\n\n'.join([f'[API ID] {i}\n{c.doc()}' for i, c in self.actionAPI.items()])),
            gemini_utils.Chat.Entry(role='system', text='Library of constraintAPIs:\n\n' + '\n\n'.join([f'[API ID] {i}\n{c.doc()}' for i, c in self.constraintAPI.items()]))
        ]
        
        # Add full file context as separate entry
        if full_file_content:
            gemini_entries.append(
                gemini_utils.Chat.Entry(role='user', text="Complete Scenic file (for context only):\n" + full_file_content)
            )
        
        # Add error message if available
        if error_message:
            gemini_entries.append(
                gemini_utils.Chat.Entry(role='user', text="Terminal error message:\n" + error_message)
            )
        
        # Add the specific section to fix as separate entry
        gemini_entries.append(
            gemini_utils.Chat.Entry(role='user', text="CoachBehavior section to fix:\n" + content)
        )
        
        # Try OpenAI first
        try:
            chat_openai = nlp_utils.Chat(client, model=self.openai_model)
            response_openai = chat_openai(openai_entries)
            
            fixed_content, issues = self._parse_llm_response(response_openai)
            if fixed_content:
                return fixed_content, issues
                
        except Exception as e:
            print(f"OpenAI fix failed: {e}")
        
        # Try Gemini as fallback
        try:
            chat_gemini = gemini_utils.Chat(model=self.gemini_model)
            response_gemini = chat_gemini(gemini_entries)
            
            fixed_content, issues = self._parse_llm_response(response_gemini)
            if fixed_content:
                return fixed_content, issues
                
        except Exception as e:
            print(f"Gemini fix failed: {e}")
        
        # If both LLMs fail, return original content
        print("Warning: Could not check syntax with LLM, returning original content")
        return content, []
    
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
                            'type': 'error_issue',
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
    
    def check_and_fix_file(self, file_path: str, error_message: str = None, overwrite: bool = True) -> Tuple[str, List[Dict]]:
        """
        Check and fix syntax issues and runtime errors in a Scenic file.
        Only modifies the section between ####HEADER ENDS#### and ####Environment Behavior START####.
        
        Args:
            file_path: Path to the Scenic file
            error_message: Terminal error message if available
            overwrite: Whether to overwrite the original file
            
        Returns:
            Tuple of (fixed_content, issues)
        """
        print(f"Checking errors for: {file_path}")
        if error_message:
            print(f"Error message provided: {error_message[:100]}...")
        
        # Load the file
        content = self.load_scenic_file(file_path)
        
        try:
            # Extract the sections
            header, coach_behavior_section, footer = self.extract_coach_behavior_section(content)
            
            # Check and fix only the coach behavior section
            fixed_coach_behavior, issues = self.check_and_fix_with_llm(coach_behavior_section, content, error_message)
            
            # Reconstruct the full content
            fixed_content = self.reconstruct_file_content(header, fixed_coach_behavior, footer)
            
            if not issues:
                print("No errors found!")
            else:
                print(f"Found {len(issues)} issues:")
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
    
    def check_multiple_files(self, file_paths: List[str], error_messages: Dict[str, str] = None, overwrite: bool = True) -> Dict[str, Tuple[str, List[Dict]]]:
        """
        Check and fix multiple Scenic files.
        Only modifies the section between ####HEADER ENDS#### and ####Environment Behavior START####.
        
        Args:
            file_paths: List of file paths to check
            error_messages: Dictionary mapping file paths to error messages
            overwrite: Whether to overwrite original files
            
        Returns:
            Dictionary mapping file paths to (fixed_content, issues) tuples
        """
        results = {}
        
        for file_path in file_paths:
            try:
                error_message = error_messages.get(file_path) if error_messages else None
                fixed_content, issues = self.check_and_fix_file(file_path, error_message, overwrite)
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
    
    parser = argparse.ArgumentParser(description='Check and fix Scenic syntax issues and runtime errors')
    parser.add_argument('files', nargs='+', help='Scenic files to check')
    parser.add_argument('--api', required=True, help='Path to API configuration')
    parser.add_argument('--error-message', help='Terminal error message to fix')
    parser.add_argument('--error-file', help='File containing error messages (one per line)')
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
    
    # Create error fixer
    fixer = ScenicErrorFixer(
        api=api,
        openai_model=args.openai_model,
        gemini_model=args.gemini_model
    )
    
    # Handle error messages
    error_messages = {}
    if args.error_message:
        # Apply same error message to all files
        for file_path in args.files:
            error_messages[file_path] = args.error_message
    elif args.error_file:
        # Load error messages from file
        try:
            with open(args.error_file, 'r') as f:
                error_lines = f.readlines()
                for i, file_path in enumerate(args.files):
                    if i < len(error_lines):
                        error_messages[file_path] = error_lines[i].strip()
        except Exception as e:
            print(f"Error reading error file: {e}")
    
    # Check files
    results = fixer.check_multiple_files(args.files, error_messages, overwrite=not args.no_overwrite)
    
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