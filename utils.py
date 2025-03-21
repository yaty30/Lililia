import re
import os
from config import COMMAND_PATTERN

def extract_commands(text):
    """Extract commands from the text using the defined pattern."""
    if not text:
        return []
    return re.findall(COMMAND_PATTERN, text)

def extract_image_prompt(text):
    """Extract image generation prompts from text."""
    if not text:
        return []
    
    # Pattern for image generation requests
    image_patterns = [
        r"(?i)Generate\s+an\s+image\s+of\s*:(.*?)(?:$|(?=\n\n))",
        r"(?i)Create\s+an\s+image\s+showing\s*:(.*?)(?:$|(?=\n\n))",
        r"(?i)Visualize\s+this\s*:(.*?)(?:$|(?=\n\n))",
        r"(?i)Make\s+an\s+image\s+of\s*:(.*?)(?:$|(?=\n\n))",
        r"(?i)I\s+want\s+an\s+image\s+of\s*:(.*?)(?:$|(?=\n\n))",
    ]
    
    prompts = []
    for pattern in image_patterns:
        matches = re.findall(pattern, text, re.DOTALL)
        prompts.extend([match.strip() for match in matches if match.strip()])
    
    return prompts

def extract_image_urls(text):
    """Extract image URLs from text."""
    if not text:
        return []
    
    # Pattern for URLs
    url_pattern = r'https?://\S+\.(?:jpg|jpeg|png|gif|webp)(?:\?\S*)?'
    
    return re.findall(url_pattern, text)

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