import asyncio
import os
import sys
import argparse
import re
import webbrowser
import tkinter as tk
from tkinter import scrolledtext, ttk
import subprocess
import threading

# Import the logger
from logger import get_logger

# Initialize logger
logger = get_logger("Lilia")

import queue
from poe_client import PoeClientWrapper
from utils import extract_commands, extract_image_prompt, extract_image_urls
from command_executor import execute_command, setup_git_credentials

# Try importing configuration, with fallback for missing variables
try:
    from config import POE_TOKENS, BOT_NAME, CHAT_CODE, IMAGE_BOT_CHAT_CODE
except ImportError as e:
    print(f"Error importing configuration: {e}")
    print("Please ensure config.py contains POE_TOKENS, BOT_NAME, CHAT_CODE, and IMAGE_BOT_CHAT_CODE.")
    IMAGE_BOT_CHAT_CODE = "39asqtk2h4diwi37p03"  # Fallback to the provided code
    sys.exit(1)

# Global variables
command_window = None
chat_window = None
message_queue = queue.Queue()
response_queue = queue.Queue()

class CommandDisplay(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Command Output Display")
        self.geometry("800x600")
        
        # Configure the grid
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=0)  # Header
        self.rowconfigure(1, weight=1)  # Command output
        
        # Header
        header_frame = ttk.Frame(self)
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        
        ttk.Label(header_frame, text="Command Output Display", font=("Arial", 14, "bold")).pack(side=tk.LEFT)
        
        # Clear button
        clear_button = ttk.Button(header_frame, text="Clear", command=self.clear_output)
        clear_button.pack(side=tk.RIGHT, padx=10)
        
        # Command output area
        self.output_text = scrolledtext.ScrolledText(self, wrap=tk.WORD, font=("Consolas", 10))
        self.output_text.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        
        # Configure text tags
        self.output_text.tag_configure("command", foreground="blue", font=("Consolas", 10, "bold"))
        self.output_text.tag_configure("output", foreground="black")
        self.output_text.tag_configure("success", foreground="green", font=("Consolas", 10, "bold"))
        self.output_text.tag_configure("error", foreground="red", font=("Consolas", 10, "bold"))
        
        # Keep window open even when main program exits
        self.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def clear_output(self):
        """Clear the output text area"""
        self.output_text.delete(1.0, tk.END)
    
    def on_close(self):
        """Hide the window instead of closing it"""
        self.withdraw()
    
    def display_command(self, command):
        """Display a command that's about to be executed"""
        self.deiconify()  # Make window visible if it was hidden
        self.output_text.insert(tk.END, f"\n\n[COMMAND] {command}\n", "command")
        self.output_text.see(tk.END)
        self.update()
    
    def display_output(self, output, is_error=False):
        """Display command output"""
        tag = "error" if is_error else "output"
        self.output_text.insert(tk.END, f"{output}\n", tag)
        self.output_text.see(tk.END)
        self.update()
    
    def display_result(self, exit_code):
        """Display command result"""
        if exit_code == 0:
            self.output_text.insert(tk.END, f"\n[SUCCESS] Command completed successfully (exit code: {exit_code})\n", "success")
        else:
            self.output_text.insert(tk.END, f"\n[ERROR] Command failed with exit code: {exit_code}\n", "error")
        self.output_text.see(tk.END)
        self.update()

class ChatInterface(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"Chat with {BOT_NAME}")
        self.geometry("900x700")
        
        # Configure the grid
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)  # Chat history
        self.rowconfigure(1, weight=0)  # Input area
        
        # Chat history area
        self.chat_frame = ttk.Frame(self)
        self.chat_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=5)
        
        self.chat_frame.columnconfigure(0, weight=1)
        self.chat_frame.rowconfigure(0, weight=1)
        
        self.chat_display = scrolledtext.ScrolledText(self.chat_frame, wrap=tk.WORD, font=("Arial", 11))
        self.chat_display.grid(row=0, column=0, sticky="nsew")
        self.chat_display.config(state=tk.DISABLED)
        
        # Configure tags
        self.chat_display.tag_configure("user", foreground="blue", font=("Arial", 11, "bold"))
        self.chat_display.tag_configure("bot", foreground="green", font=("Arial", 11))
        self.chat_display.tag_configure("system", foreground="gray", font=("Arial", 10, "italic"))
        self.chat_display.tag_configure("command", foreground="purple", font=("Arial", 11, "italic"))
        
        # Input area
        self.input_frame = ttk.Frame(self)
        self.input_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        
        self.input_frame.columnconfigure(0, weight=1)
        self.input_frame.columnconfigure(1, weight=0)
        
        self.message_input = scrolledtext.ScrolledText(self.input_frame, wrap=tk.WORD, height=4, font=("Arial", 11))
        self.message_input.grid(row=0, column=0, sticky="ew")
        self.message_input.bind("<Shift-Return>", self.on_shift_enter)
        self.message_input.bind("<Return>", self.on_enter)
        
        self.send_button = ttk.Button(self.input_frame, text="Send", command=self.send_message)
        self.send_button.grid(row=0, column=1, padx=5)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_bar = ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
        
        # Create the command window
        self.create_command_window()
        
        # Set up running flag for the async loop
        self.running = True
        self.client = None
        self.image_client = None
        
        # Processing flags
        self.is_processing = False
        self.processing_lock = threading.Lock()
        
        # Stored main event loop
        self.main_loop = None
        
        # Configure Git credentials once at startup
        setup_git_credentials()
        
        # Start the async loop in a separate thread
        self.loop_thread = threading.Thread(target=self.run_async_loop)
        self.loop_thread.daemon = True
        self.loop_thread.start()
        
        # Check for new responses periodically
        self.after(100, self.check_for_response)
        
        # Set focus to input box
        self.message_input.focus_set()
        
        # Start with system message
        self.add_message(f"Starting chat with {BOT_NAME}...", "system")
    
    def create_command_window(self):
        """Create the command display window"""
        global command_window
        command_window = CommandDisplay(self)
        command_window.withdraw()  # Hide initially
    
    def on_enter(self, event):
        """Handle Enter key to send message"""
        if not event.state & 0x1:  # Check if Shift key is not pressed
            self.send_message()
            return "break"  # Prevent default Enter behavior
    
    def on_shift_enter(self, event):
        """Handle Shift+Enter to add newline"""
        # Let default behavior happen
        return
    
    def send_message(self):
        """Send the current message"""
        message = self.message_input.get(1.0, tk.END).strip()
        if not message:
            return
        
        # Add user message to display
        self.add_message(message, "user")
        
        # Clear input
        self.message_input.delete(1.0, tk.END)
        
        # Put message in queue
        message_queue.put(message)
        print(f"Added message to queue: {message[:30]}...")
        
        # Update status
        self.status_var.set("Sending message...")
        self.send_button.config(state=tk.DISABLED)
    
    def add_message(self, message, sender):
        """Add a message to the chat display"""
        self.chat_display.config(state=tk.NORMAL)
        
        # Add sender label
        if sender == "user":
            self.chat_display.insert(tk.END, "\n\nYou: ", "user")
        elif sender == "bot":
            self.chat_display.insert(tk.END, f"\n\n{BOT_NAME}: ", "bot")
        elif sender == "system":
            self.chat_display.insert(tk.END, f"\n[SYSTEM] ", "system")
        elif sender == "command":
            self.chat_display.insert(tk.END, f"\n[COMMAND] ", "command")
        
        # Add message
        self.chat_display.insert(tk.END, message)
        
        # Scroll to bottom
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)
    
    def check_for_response(self):
        """Check if there's a new response to display"""
        try:
            # Try to get response without blocking
            response = None
            try:
                response = response_queue.get_nowait()
                print(f"Got response from queue: {response[:30] if response else 'None'}...")
            except queue.Empty:
                pass
            
            if response:
                # Add bot response to chat
                print("Adding bot response to chat display")
                self.add_message(response, "bot")
                
                # Check for commands in the response
                commands = extract_commands(response)
                if commands and not self.is_processing:
                    print(f"Found {len(commands)} commands in response")
                    # Process commands without waiting for user input
                    with self.processing_lock:
                        self.is_processing = True
                    self.status_var.set(f"Found {len(commands)} commands. Processing...")
                    
                    # Start execution in a separate thread
                    threading.Thread(target=self.execute_commands_thread, args=(commands, response)).start()
                else:
                    # Update status and re-enable send button only if not processing commands
                    if not self.is_processing:
                        self.status_var.set("Ready")
                        self.send_button.config(state=tk.NORMAL)
                        print("UI updated, ready for next message")
            
        except Exception as e:
            print(f"Error checking for response: {e}")
            import traceback
            traceback.print_exc()
            self.status_var.set(f"Error: {str(e)}")
            with self.processing_lock:
                self.is_processing = False
            self.send_button.config(state=tk.NORMAL)
        
        # Schedule next check
        if self.running:
            self.after(100, self.check_for_response)
    
    def execute_commands_thread(self, commands, original_response):
        """Execute commands in a separate thread to avoid blocking UI"""
        try:
            # Notify user that commands are being executed
            self.after(0, lambda: self.add_message(f"Executing {len(commands)} commands...", "system"))
            
            # We need to create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Run the execute_commands coroutine in this thread's event loop
                loop.run_until_complete(self.execute_commands(commands, original_response))
            finally:
                loop.close()
                
        except Exception as e:
            print(f"Error in execute_commands_thread: {e}")
            import traceback
            traceback.print_exc()
            with self.processing_lock:
                self.is_processing = False
            self.after(0, lambda: self.status_var.set(f"Error executing commands: {str(e)}"))
            self.after(0, lambda: self.send_button.config(state=tk.NORMAL))
    
    async def execute_commands(self, commands, original_response):
        """Execute commands and process results"""
        try:
            # Execute commands and collect results
            results = []
            for i, cmd in enumerate(commands):
                self.after(0, lambda i=i+1, total=len(commands): 
                           self.status_var.set(f"Executing command {i}/{total}..."))
                
                # Add command to chat display
                self.after(0, lambda c=cmd: self.add_message(f"Executing: {c}", "command"))
                
                # Execute the command using our command_executor
                result = await execute_system_command(cmd)
                results.append(result)
            
            # Build review message
            review_message = "I executed the commands found in your response. Here are the results:\n\n"
            
            for result in results:
                review_message += f"Command: `{result['command']}`\n"
                review_message += f"Exit Code: {result['returncode']}\n"
                review_message += "```\n"
                if result['stdout']:
                    review_message += f"STDOUT:\n{result['stdout']}\n"
                if result['stderr']:
                    review_message += f"STDERR:\n{result['stderr']}\n"
                review_message += "```\n\n"
            
            # Get a reference to the main event loop that has the client
            try:
                # Send results to bot using message queue
                print("Queueing command results to send to bot")
                message_queue.put(review_message)
                
                # Wait a bit for this to be processed
                await asyncio.sleep(0.5)
                
                # Don't proceed to additional commands, let the main loop handle the response
                
            except Exception as e:
                print(f"Error sending command results to bot: {e}")
                import traceback
                traceback.print_exc()
                self.after(0, lambda: self.add_message(f"Error sending command results to bot: {str(e)}", "system"))
            
        except Exception as e:
            print(f"Error executing commands: {e}")
            import traceback
            traceback.print_exc()
            # Notify user of error
            self.after(0, lambda: self.add_message(f"Error executing commands: {str(e)}", "system"))
        finally:
            # Reset processing state
            with self.processing_lock:
                self.is_processing = False
            self.after(0, lambda: self.status_var.set("Ready"))
            self.after(0, lambda: self.send_button.config(state=tk.NORMAL))
    
    def run_async_loop(self):
        """Run the asyncio event loop in a separate thread"""
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        self.main_loop = loop
        try:
            print("Starting async loop...")
            loop.run_until_complete(self.async_main())
            print("Async loop completed normally")
        except Exception as e:
            print(f"Error in async loop: {e}")
            import traceback
            traceback.print_exc()
            # Update status in GUI thread
            self.after(0, lambda: self.status_var.set(f"Error: {str(e)}"))
        finally:
            loop.close()
            print("Async loop closed")
    
    async def async_main(self):
        """Main async function that handles the bot conversation"""
        # Initialize clients
        print(f"Initializing connection to {BOT_NAME}...")
        try:
            self.client = await PoeClientWrapper(
                tokens=POE_TOKENS,
                bot_name=BOT_NAME,
                chat_code=CHAT_CODE
            ).initialize()
            
            self.image_client = await PoeClientWrapper(
                tokens=POE_TOKENS,
                bot_name="Lililia-image-gen",
                chat_code=IMAGE_BOT_CHAT_CODE
            ).initialize()
            
            # Update status in GUI thread
            self.after(0, lambda: self.status_var.set("Connected"))
            print("Bot clients initialized successfully")
            
        except Exception as e:
            error_msg = f"Failed to initialize Poe client: {e}"
            print(error_msg)
            # Update status in GUI thread
            self.after(0, lambda: self.status_var.set(error_msg))
            return
        
        # Main message processing loop
        while self.running:
            # Non-blocking check for messages
            try:
                # Check if there's a message in the queue
                if not message_queue.empty():
                    message = message_queue.get()
                    print(f"Got message from queue: {message[:30]}...")
                    
                    if message.lower() == 'exit':
                        print("Exit command received")
                        break
                    
                    # Send message to bot
                    print(f"Sending message to bot: {message[:30]}...")
                    try:
                        response = await self.client.send_message(message, use_chat_code=True)
                        print(f"Received response from bot: {response[:30]}...")
                        
                        # Add response to queue to be displayed
                        response_queue.put(response)
                        print("Added response to queue")
                        
                        # Process for image prompts immediately
                        image_prompts = extract_image_prompt(response)
                        if image_prompts:
                            await self.process_image_prompts(image_prompts)
                        
                    except Exception as e:
                        print(f"Error sending message to bot: {e}")
                        import traceback
                        traceback.print_exc()
                        response_queue.put(f"Error communicating with bot: {str(e)}")
                else:
                    # Sleep briefly to prevent CPU spinning
                    await asyncio.sleep(0.1)
            except Exception as e:
                print(f"Error in message processing loop: {e}")
                import traceback
                traceback.print_exc()
                await asyncio.sleep(1)  # Longer delay on error
    
    async def process_image_prompts(self, image_prompts):
        """Process image generation prompts"""
        try:
            for prompt in image_prompts:
                # Update status
                self.after(0, lambda p=prompt: self.status_var.set(f"Generating image: {p[:50]}..."))
                self.after(0, lambda p=prompt: self.add_message(f"Generating image for prompt: {p}", "system"))
                
                try:
                    # Send the prompt to the image generation bot
                    image_response = await self.image_client.send_message(prompt, use_chat_code=True)
                    
                    # Extract image URLs
                    image_urls = extract_image_urls(image_response)
                    
                    if image_urls:
                        # Open images in browser
                        for url in image_urls:
                            webbrowser.open(url)
                        
                        # Send confirmation back to main bot
                        await self.client.send_message(f"Here's the generated image based on your prompt:\n\n{image_response}")
                        # Add to response queue to be displayed
                        response_queue.put(f"I've generated an image based on your prompt. It should open in your browser.")
                    else:
                        await self.client.send_message(f"I tried to generate an image for your prompt, but couldn't detect any image URLs in the response.")
                        response_queue.put("I tried to generate an image but couldn't get a valid result.")
                        
                except Exception as e:
                    error_msg = f"Error generating image: {e}"
                    print(error_msg)
                    response_queue.put(f"Failed to generate image: {str(e)}")
        except Exception as e:
            print(f"Error in process_image_prompts: {e}")
            import traceback
            traceback.print_exc()

async def execute_system_command(command, display=True):
    """Execute a command and capture its output"""
    global command_window
    if display and command_window:
        try:
            command_window.display_command(command)
        except Exception as e:
            print(f"Error displaying command: {e}")
    
    try:
        # Use our command_executor's execute_command function
        output = execute_command(command)
        
        # Format the result to match the expected structure
        result = {
            'command': command,
            'stdout': output.get("stdout", ""),
            'stderr': output.get("stderr", ""),
            'returncode': output.get("returncode", -1)
        }
        
        # Display output if requested
        if display and command_window:
            try:
                if result['stdout']:
                    command_window.display_output(f"STDOUT:\n{result['stdout']}")
                if result['stderr']:
                    command_window.display_output(f"STDERR:\n{result['stderr']}", is_error=True)
                command_window.display_result(result['returncode'])
            except Exception as e:
                print(f"Error displaying command output: {e}")
        
        return result
    except Exception as e:
        print(f"Error executing command: {e}")
        return {
            'command': command,
            'stdout': '',
            'stderr': f"Error executing command: {str(e)}",
            'returncode': -1
        }

def on_closing():
    """Handle window closing"""
    global chat_window
    if chat_window:
        chat_window.running = False
        chat_window.destroy()
    sys.exit(0)

if __name__ == "__main__":
    # Set up proper asyncio event loop policy for Windows
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # Create and run the chat interface
    chat_window = ChatInterface()
    chat_window.protocol("WM_DELETE_WINDOW", on_closing)
    try:
        chat_window.mainloop()
    except KeyboardInterrupt:
        on_closing()
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        on_closing()
