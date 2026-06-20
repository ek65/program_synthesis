# Scenic Syntax Checker

A comprehensive syntax checker for Scenic programs that can automatically detect and fix syntax issues in outputs from `vanilla_scenic.py` and `fix_gemini_scenic.py`.

## Features

- **Automatic Syntax Detection**: Identifies common Scenic syntax errors
- **LLM-Powered Fixes**: Uses OpenAI and Gemini to intelligently fix syntax issues
- **File Overwriting**: Automatically overwrites original files with fixed versions
- **Backup Support**: Option to create backups before overwriting
- **Batch Processing**: Check multiple files at once
- **Comprehensive Validation**: Checks behavior definitions, lambda functions, constraints, and more

## Common Issues Detected

1. **Missing Colons**: After behavior definitions and lambda functions
2. **Invalid Do Statements**: Incorrect syntax in action calls
3. **Missing Parentheses**: In function calls
4. **Invalid Constraint Syntax**: Wrong constraint names or parameter formats
5. **Missing Simulation Calls**: In lambda functions
6. **Invalid Dictionary Syntax**: In constraint parameters
7. **Missing Required Components**: Behavior definitions, lambda functions, etc.

## Usage

### Basic Usage

```python
from syntax_checker import ScenicSyntaxChecker
from api_utils import API

# Load your API configuration
api = {
    API.actions: {...},  # Your action APIs
    API.constraints: {...},  # Your constraint APIs
    API.domain: 'soccer',
    API.default_obj: 'Coach'
}

# Create syntax checker
checker = ScenicSyntaxChecker(api=api)

# Check and fix a single file
fixed_content, issues = checker.check_and_fix_file("path/to/file.scenic", overwrite=True)
```

### Check Multiple Files

```python
# Check multiple files
file_paths = [
    "Scenic-main/examples/unity/user-synthesized-openai-with-example.scenic",
    "Scenic-main/examples/unity/user-synthesized-gemini-with-example.scenic"
]

results = checker.check_multiple_files(file_paths, overwrite=True)

# Print results
for file_path, (content, issues) in results.items():
    if issues:
        print(f"{file_path}: Fixed {len(issues)} issues")
    else:
        print(f"{file_path}: No issues found")
```

### Command Line Usage

```bash
# Check specific files
python syntax_checker.py file1.scenic file2.scenic --api path/to/api/config

# Create backups instead of overwriting
python syntax_checker.py file1.scenic --api path/to/api/config --no-overwrite

# Use different models
python syntax_checker.py file1.scenic --api path/to/api/config --openai-model gpt-4o --gemini-model gemini-2.5-pro
```

### Example Usage with Outputs from vanilla_scenic.py

```python
from syntax_checker import ScenicSyntaxChecker
from scenic_fc.api import api  # Your API configuration

# Create checker
checker = ScenicSyntaxChecker(api=api)

# Check outputs from vanilla_scenic.py
vanilla_outputs = [
    "Scenic-main/examples/unity/user-synthesized-openai-with-example.scenic",
    "Scenic-main/examples/unity/user-synthesized-gemini-with-example.scenic"
]

for file_path in vanilla_outputs:
    if os.path.exists(file_path):
        fixed_content, issues = checker.check_and_fix_file(file_path, overwrite=True)
        print(f"Fixed {len(issues)} issues in {file_path}")
```

### Example Usage with Outputs from fix_gemini_scenic.py

```python
# Check outputs from fix_gemini_scenic.py
gemini_outputs = [
    "Scenic-main/examples/unity/user-fixed-gemini.scenic",
    "Scenic-main/examples/unity/user-fixed-openai.scenic"
]

for file_path in gemini_outputs:
    if os.path.exists(file_path):
        fixed_content, issues = checker.check_and_fix_file(file_path, overwrite=True)
        print(f"Fixed {len(issues)} issues in {file_path}")
```

## Integration with Existing Workflow

### After vanilla_scenic.py

```python
from vanilla_scenic import generate_combined_program_from_demos
from syntax_checker import ScenicSyntaxChecker

# Generate Scenic programs
results = generate_combined_program_from_demos(demos, example_demos, ex_script, api, tactical_mr_dir)

# Check and fix syntax issues
checker = ScenicSyntaxChecker(api=api)
for model, file_path in results.items():
    if os.path.exists(file_path):
        fixed_content, issues = checker.check_and_fix_file(file_path, overwrite=True)
        print(f"Fixed {len(issues)} issues in {model} output")
```

### After fix_gemini_scenic.py

```python
from fix_gemini_scenic import Fix_Gemini_Scenic
from syntax_checker import ScenicSyntaxChecker

# Fix Scenic program
fixer = Fix_Gemini_Scenic(scenic_code, feedback, scenic_docs_url, api, context, synth_demo, demos)
fixed_code, response = fixer.run()

# Save to file
output_path = "fixed_program.scenic"
with open(output_path, 'w') as f:
    f.write(fixed_code)

# Check and fix syntax issues
checker = ScenicSyntaxChecker(api=api)
fixed_content, issues = checker.check_and_fix_file(output_path, overwrite=True)
print(f"Fixed {len(issues)} issues in fixed program")
```

## Configuration

### API Configuration

The syntax checker requires an API configuration that includes:

- **Actions**: Available action APIs (e.g., MoveTo, Pass, Shoot)
- **Constraints**: Available constraint APIs (e.g., AtAngle, DistanceTo, HasPath)
- **Domain**: The domain name (e.g., 'soccer')
- **Default Object**: The main actor (e.g., 'Coach')

### Model Configuration

You can specify which LLM models to use:

```python
checker = ScenicSyntaxChecker(
    api=api,
    openai_model="gpt-4o",  # OpenAI model
    gemini_model="gemini-2.5-pro"  # Gemini model
)
```

## Error Handling

The syntax checker handles various error scenarios:

- **File Not Found**: Graceful error handling with informative messages
- **LLM Failures**: Falls back from OpenAI to Gemini, then to original content
- **Invalid Syntax**: Attempts to fix with LLM, reports issues if unable
- **API Errors**: Continues processing other files if one fails

## Output

The syntax checker provides detailed feedback:

```
Checking syntax for: path/to/file.scenic
Found 3 syntax issues:
  Line 5: Missing colon after behavior definition
  Line 12: Missing simulation() call in λ_target0
  Line 20: Invalid constraint name: InvalidConstraint
Fixed Scenic file saved to: path/to/file.scenic
```

## Example Test File

Run the example script to see the syntax checker in action:

```bash
python example_syntax_checker_usage.py
```

This will:
1. Create a test file with syntax issues
2. Check and fix the issues
3. Check outputs from vanilla_scenic.py and fix_gemini_scenic.py
4. Check all .scenic files in the directory

## Dependencies

- `nlp_utils`: For OpenAI integration
- `nlp_utils_gemini`: For Gemini integration
- `api_utils`: For API configuration
- `apiKey`: For API keys
- `openai`: OpenAI client

## Notes

- The syntax checker uses LLMs as a fallback for complex syntax issues
- Simple issues (like missing colons) are fixed automatically
- Complex issues require LLM intervention
- The checker preserves the original file structure and logic
- All fixes are applied to the original file (unless backup is requested) 