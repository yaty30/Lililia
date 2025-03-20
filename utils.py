import re
import os
from config import COMMAND_PATTERN

def extract_commands(text):
    """Extract commands from the text using the defined pattern."""
    if not text:
        return []
    return re.findall(COMMAND_PATTERN, text)

def expand_path(path):
    """Expand environment variables and user home in paths."""
    expanded = os.path.expandvars(path)
    expanded = os.path.expanduser(expanded)
    return expanded

def format_command_output(cmd, output):
    """Format command output for inclusion in messages."""
    result = f"Command: [[{cmd}]]\n"
    result += "Output:\n```\n"
    
    if isinstance(output, dict):
        if output.get("message"):
            result += f"{output['message']}\n"
        if output.get("stdout"):
            result += f"STDOUT:\n{output['stdout']}\n"
        if output.get("stderr"):
            result += f"STDERR:\n{output['stderr']}\n"
        if output.get("returncode") is not None:
            result += f"Exit code: {output['returncode']}\n"
    else:
        result += f"{output}\n"
    
    result += "```\n\n"
    return result