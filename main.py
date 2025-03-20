import asyncio
from config import POE_TOKENS, BOT_NAME, CHAT_CODE
from poe_client import PoeClientWrapper
from utils import extract_commands
from command_manager import execute_commands_with_review

async def main():
    # Initialize Poe client
    client = await PoeClientWrapper(
        tokens=POE_TOKENS,
        bot_name=BOT_NAME,
        chat_code=CHAT_CODE
    ).initialize()
    
    print(f"Starting conversation with bot: {BOT_NAME}")
    print("Type 'exit' to quit the application")
    print("Type 'execute' to execute the last set of commands without sending a new message")
    print("Commands will be executed automatically")
    
    successful_method = None  # 1 = with chat code, 2 = without chat code
    last_commands = []
    
    while True:
        # Get user input
        user_message = input("\nYou: ")
        
        # Exit condition
        if user_message.lower() == 'exit':
            print("Exiting application...")
            break
            
        # Execute last commands
        if user_message.lower() == 'execute':
            if last_commands:
                await execute_commands_with_review(client, last_commands)
            else:
                print("No commands to execute.")
            continue
        
        # Send message and handle response
        response = await send_message_with_fallback(client, user_message, successful_method)
        if response:
            method, message = response  # Unpack the tuple
            print(f"Bot: {message}")    # Only print the message part
            successful_method = method
            
            # Extract and execute commands
            commands = extract_commands(message)  # Use just the message part
            last_commands = commands
            
            if commands:
                await execute_commands_with_review(client, commands)

async def send_message_with_fallback(client, message, preferred_method=None):
    """Send message with fallback if preferred method fails."""
    # Try with chat code first or if it was previously successful
    if preferred_method is None or preferred_method == 1:
        try:
            response = await client.send_message(message, use_chat_code=True)
            return (1, response)
        except Exception as e:
            if preferred_method == 1:
                print(f"Error with previously working method: {e}")
            else:
                print(f"First method failed: {e}")
    
    # Try without chat code as fallback
    if preferred_method is None or preferred_method == 2:
        try:
            response = await client.send_message(message, use_chat_code=False)
            return (2, response)
        except Exception as e:
            if preferred_method == 2:
                print(f"Error with previously working method: {e}")
            else:
                print(f"All methods failed. Last error: {e}")
                print("Please check your tokens and bot configuration.")
    
    return None

if __name__ == "__main__":
    asyncio.run(main())