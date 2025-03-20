import asyncio
import os
import sys
import time
from poe_client import PoeClientWrapper
from config import POE_TOKENS, BOT_NAME, CHAT_CODE

async def test_file_attachment():
    # Initialize the client
    print("Initializing Poe client...")
    client = await PoeClientWrapper(
        tokens=POE_TOKENS,
        bot_name=BOT_NAME,
        chat_code=CHAT_CODE
    ).initialize()
    
    # Create a test directory if it doesn't exist
    test_dir = os.path.join(os.getcwd(), "test_files")
    if not os.path.exists(test_dir):
        os.makedirs(test_dir)
    
    # Create a test file with timestamp to avoid caching
    timestamp = int(time.time())
    test_file_path = os.path.join(test_dir, f"test_attachment_{timestamp}.txt")
    
    print(f"Creating test file at: {test_file_path}")
    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write(f"This is a test file for attachment sending (created at {timestamp}).\n")
        f.write("It contains some sample content to verify the file attachment functionality.\n")
        f.write("\n")
        f.write("System info:\n")
        f.write(f"Python version: {sys.version}\n")
        f.write(f"Current directory: {os.getcwd()}\n")
        f.write(f"Operating system: {os.name}\n")
        f.write(f"Test timestamp: {timestamp}\n")
    
    # Test Method 1: Direct attachment with file_path
    print("\n----- TEST 1: Sending file with file_path parameter -----")
    try:
        print("Sending message with file attachment...")
        response = await client.send_message(
            f"Here's a test file (timestamp: {timestamp}) I'm sending as an attachment. Please confirm if you can see it and tell me what's in it.",
            file_path=[test_file_path]
        )
        print("\nSuccess! Bot's response:")
        print(response)
    except Exception as e:
        print(f"Error sending file attachment: {e}")
    
    # Short delay between tests
    await asyncio.sleep(2)
    
    # Test Method 2: via send_outputs_for_review
    print("\n----- TEST 2: Using send_outputs_for_review with output_file -----")
    try:
        # Create a simple command output dictionary
        command_outputs = {
            "echo Hello": "Hello",
            "dir": "Directory listing would appear here"
        }
        
        print("Sending file via send_outputs_for_review...")
        response = await client.send_outputs_for_review(
            command_outputs=command_outputs,
            output_file=test_file_path
        )
        print("\nSuccess! Bot's response:")
        print(response)
    except Exception as e:
        print(f"Error with send_outputs_for_review: {e}")
    
    # Short delay between tests
    await asyncio.sleep(2)
    
    # Test Method 3: Fallback to chat code if needed
    print("\n----- TEST 3: Using chat code as fallback -----")
    try:
        # First attempt with file_path but prepare for fallback
        try:
            response = await client.send_message(
                f"Testing fallback mechanism with timestamp {timestamp}.",
                file_path=[test_file_path]
            )
            print("\nPrimary method succeeded! Bot's response:")
            print(response)
        except Exception as e:
            print(f"Primary method failed: {e}")
            print("Trying fallback with chat code...")
            
            response = await client.send_message(
                f"Using fallback method to access the file: [[RUN:more {test_file_path}]]",
                use_chat_code=True
            )
            print("\nFallback succeeded! Bot's response:")
            print(response)
    except Exception as e:
        print(f"All methods failed: {e}")
    
    # Final confirmation
    try:
        print("\nAsking for final confirmation...")
        response = await client.send_message(
            f"To confirm our file attachment tests: Were you able to see the contents of file(s) with timestamp {timestamp}? Please summarize what you saw."
        )
        print("\nBot's confirmation response:")
        print(response)
    except Exception as e:
        print(f"Error getting confirmation: {e}")
    
    print("\nTest complete!")
    
    # Optional cleanup
    try:
        os.remove(test_file_path)
        print(f"Removed test file: {test_file_path}")
    except Exception as e:
        print(f"Could not remove test file: {e}")

if __name__ == "__main__":
    asyncio.run(test_file_attachment())