import os
import tempfile
from command_executor import execute_command
from utils import extract_commands
from logger import get_logger

# Initialize logger
logger = get_logger("CommandManager")

# Create a dedicated folder for output files
OUTPUT_DIR = os.path.join(os.getcwd(), "command_outputs")
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)
    logger.info(f"Created output directory: {OUTPUT_DIR}")


async def execute_commands_with_review(client, commands):
    """Execute commands, save outputs to a file, and send file to bot for review."""
    if not commands:
        return
        
    print("\nExecuting commands:")
    for cmd in commands:
        print(f"  - {cmd}")
    
    # Execute all commands and collect outputs
    command_outputs = {}
    for cmd in commands:
        try:
            output = execute_command(cmd)
            command_outputs[cmd] = output
            
            # Safely print the output preview
            if output:
                preview = output[:100] + ('...' if len(output) > 100 else '')
            else:
                preview = "(no output or error occurred)"
            print(f"Command: {cmd}\nOutput: {preview}\n")
        except Exception as e:
            error_message = f"Error executing command: {str(e)}"
            command_outputs[cmd] = error_message
            print(f"Command: {cmd}\nOutput: {error_message}\n")
    
    # Create a file in the dedicated output directory
    output_file = os.path.join(OUTPUT_DIR, "command_outputs.txt")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("Command Execution Results:\n\n")
        for cmd, output in command_outputs.items():
            f.write(f"Command: {cmd}\n")
            f.write(f"Output:\n{output}\n")
            f.write("-" * 50 + "\n\n")
    
    print(f"Saved command outputs to: {output_file}")
    
    # Try to send the file as an attachment
    try:
        print("Sending file as attachment to bot...")
        response = await client.send_message("I've executed the commands. Here are the results:", file_path=[output_file])
        print(f"\nBot's review: {response}")
    except Exception as e:
        print(f"Error sending file attachment: {e}")
        # Fallback to reading the file using the PoeBot itself
        try:
            # Use a relative path command that doesn't expose full system path
            review_message = "I've executed the commands. Let me show you the results:"
            response = await client.send_message(review_message)
            
            # Now send another message with the file contents
            with open(output_file, "r", encoding="utf-8") as f:
                file_contents = f.read()
            
            chunk_size = 1500  # Reasonable chunk size to avoid message limits
            for i in range(0, len(file_contents), chunk_size):
                chunk = file_contents[i:i+chunk_size]
                await client.send_message(f"Command output (part {i//chunk_size + 1}):\n\n```\n{chunk}\n```")
            
            # Ask for the bot's analysis after sending all chunks
            response = await client.send_message("That's all the output. What do you think?")
            print(f"\nBot's review: {response}")
        except Exception as e2:
            print(f"Error with fallback method: {e2}")
        
    # Extract and execute any commands from the review
    new_commands = extract_commands(response)
    if new_commands:
        print("\nBot suggested new commands in review:")
        for cmd in new_commands:
            print(f"  - {cmd}")
        
        # Execute new commands automatically
        await execute_commands_recursive(client, new_commands)

async def execute_commands_recursive(client, commands, depth=0):
    """Execute commands recursively, saving outputs to files."""
    if not commands or depth > 3:  # Limit recursion depth
        return
        
    print(f"\nExecuting {'follow-up ' if depth > 0 else ''}commands:")
    for cmd in commands:
        print(f"  - {cmd}")
    
    # Execute all commands and collect outputs
    command_outputs = {}
    for cmd in commands:
        try:
            output = execute_command(cmd)
            command_outputs[cmd] = output
        except Exception as e:
            error_message = f"Error executing command: {str(e)}"
            command_outputs[cmd] = error_message
            print(f"Command: {cmd}\nOutput: {error_message}\n")
    
    # Create a file in the dedicated output directory
    output_file = os.path.join(OUTPUT_DIR, f"followup_outputs_{depth}.txt")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"Follow-up Command Results (Level {depth+1}):\n\n")
        for cmd, output in command_outputs.items():
            f.write(f"Command: {cmd}\n")
            f.write(f"Output:\n{output}\n")
            f.write("-" * 50 + "\n\n")
    
    print(f"Saved follow-up outputs to: {output_file}")
    
    # Try to send the file as an attachment
    try:
        print("Sending file as attachment to bot...")
        response = await client.send_message(f"I've executed the follow-up commands (level {depth+1}). Here are the results:", file_path=[output_file])
        print(f"\nBot's follow-up response: {response}")
    except Exception as e:
        print(f"Error sending file attachment: {e}")
        # Fallback to sending the file contents directly
        try:
            # Use a relative path command that doesn't expose full system path
            review_message = f"I've executed the follow-up commands (level {depth+1}). Let me show you the results:"
            response = await client.send_message(review_message)
            
            # Now send another message with the file contents
            with open(output_file, "r", encoding="utf-8") as f:
                file_contents = f.read()
            
            chunk_size = 1500  # Reasonable chunk size to avoid message limits
            for i in range(0, len(file_contents), chunk_size):
                chunk = file_contents[i:i+chunk_size]
                await client.send_message(f"Command output (part {i//chunk_size + 1}):\n\n```\n{chunk}\n```")
            
            # Ask for the bot's analysis after sending all chunks
            response = await client.send_message("That's all the output. What do you think?")
            print(f"\nBot's follow-up response: {response}")
        except Exception as e2:
            print(f"Error with fallback method: {e2}")
    
    # Extract and execute any further commands
    more_commands = extract_commands(response)
    if more_commands:
        await execute_commands_recursive(client, more_commands, depth + 1)
