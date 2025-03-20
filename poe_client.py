from poe_api_wrapper import AsyncPoeApi
from utils import format_command_output

class PoeClientWrapper:
    def __init__(self, tokens, bot_name, chat_code=None):
        self.tokens = tokens
        self.bot_name = bot_name
        self.chat_code = chat_code
        self.client = None
    
    async def initialize(self):
        """Initialize the Poe API client."""
        self.client = await AsyncPoeApi(tokens=self.tokens).create()
        return self
    
    async def send_message(self, message, use_chat_code=True, file_path=None):
        """
        Send a message to the bot and return the response.
        
        Args:
            message (str): The message to send to the bot
            use_chat_code (bool): Whether to use chat code in the request
            file_path (list, optional): List of file paths to attach to the message
        
        Returns:
            str: The bot's response
        """
        if not self.client:
            raise ValueError("Client not initialized. Call initialize() first.")
        
        response = ""
        print(f"Bot is thinking...", end="", flush=True)
        
        try:
            if use_chat_code and self.chat_code:
                if file_path:
                    async for chunk in self.client.send_message(
                        self.bot_name, 
                        message, 
                        chatCode=self.chat_code,
                        file_path=file_path
                    ):
                        print(".", end="", flush=True)
                        response = chunk["text"]
                else:
                    async for chunk in self.client.send_message(
                        self.bot_name, 
                        message, 
                        chatCode=self.chat_code
                    ):
                        print(".", end="", flush=True)
                        response = chunk["text"]
            else:
                if file_path:
                    async for chunk in self.client.send_message(
                        self.bot_name, 
                        message,
                        file_path=file_path
                    ):
                        print(".", end="", flush=True)
                        response = chunk["text"]
                else:
                    async for chunk in self.client.send_message(
                        self.bot_name, 
                        message
                    ):
                        print(".", end="", flush=True)
                        response = chunk["text"]
            
            print("\n")
            return response
        except Exception as e:
            print(f"\nError sending message: {e}")
            raise
    
    async def send_outputs_for_review(self, command_outputs, output_file=None):
        """
        Send command outputs back to the bot for review.
        
        Args:
            command_outputs (dict): Dictionary of command outputs
            output_file (str, optional): Path to file containing command outputs
            
        Returns:
            str: The bot's response
        """
        if not command_outputs and not output_file:
            print("No command outputs to review.")
            return None
        
        if output_file:
            # Send the file as an attachment
            try:
                print(f"Sending output file as attachment: {output_file}")
                message = "I've executed the commands. Here are the results:"
                response = await self.send_message(
                    message=message,
                    file_path=[output_file]
                )
                return response
            except Exception as e:
                print(f"Error sending file attachment: {e}")
                print("Falling back to sending outputs in message body...")
                # Fall through to the text-based approach
        
        # Text-based approach (fallback or if no file)
        review_message = "I've executed the commands and here are the results:\n\n"
        
        for cmd, output in command_outputs.items():
            review_message += format_command_output(cmd, output)
        
        review_message += "Please review these outputs and provide feedback or next steps."
        
        print("\nSending outputs to bot for review in message body...")
        try:
            response = await self.send_message(review_message)
            return response
        except Exception as e:
            print(f"\nError sending outputs for review: {e}")
            return None