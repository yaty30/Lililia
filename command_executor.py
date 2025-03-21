import os
import subprocess
import shlex
from config import CMD_PREFIX_FILE, CMD_PREFIX_DIR, CMD_PREFIX_RUN, CMD_PREFIX_GIT, CMD_PREFIX_INSTALL
from utils import expand_path

# Add a flag to track if we've set up Git credentials
git_credentials_configured = False

def execute_command(cmd):
    """Execute a command extracted from the bot response and return the output."""
    global git_credentials_configured
    
    print(f"\nProcessing: {cmd}")
    result = {"stdout": "", "stderr": "", "returncode": None, "message": ""}
    
    # Automatically set up Git credentials if this is a git command and we haven't done it yet
    if cmd.startswith(CMD_PREFIX_GIT) and not git_credentials_configured:
        setup_git_credentials()
        git_credentials_configured = True
    
    # File creation command
    if cmd.startswith(CMD_PREFIX_FILE):
        result = handle_file_command(cmd)
    
    # Directory creation command
    elif cmd.startswith(CMD_PREFIX_DIR):
        result = handle_dir_command(cmd)
    
    # Shell command
    elif cmd.startswith(CMD_PREFIX_RUN):
        result = handle_run_command(cmd)
    
    # Git command
    elif cmd.startswith(CMD_PREFIX_GIT):
        result = handle_git_command(cmd)
    
    # Install command
    elif cmd.startswith(CMD_PREFIX_INSTALL):
        result = handle_install_command(cmd)
    
    # Generic command
    else:
        result = handle_generic_command(cmd)
    
    return result

def setup_git_credentials():
    """Configure Git to store credentials permanently to avoid prompts."""
    try:
        print("Setting up Git credentials storage...")
        
        # Configure Git to store credentials
        store_result = subprocess.run(
            "git config --global credential.helper store",
            shell=True,
            capture_output=True,
            text=True
        )
        
        if store_result.returncode == 0:
            print("Git credential storage configured successfully")
        else:
            print(f"Failed to configure Git credential storage: {store_result.stderr}")
        
        # For Windows: ensure we don't use modal dialogs for auth
        if os.name == 'nt':
            modal_result = subprocess.run(
                "git config --global core.askPass \"\"",
                shell=True,
                capture_output=True,
                text=True
            )
            
            if modal_result.returncode == 0:
                print("Git modal dialogs disabled")
            else:
                print(f"Failed to disable Git modal dialogs: {modal_result.stderr}")
        
        # Set default pull behavior to avoid merge commit messages
        pull_result = subprocess.run(
            "git config --global pull.rebase false",
            shell=True,
            capture_output=True,
            text=True
        )
        
        if pull_result.returncode == 0:
            print("Git pull behavior configured")
        
        # Configure username and email if not already set
        try:
            username_check = subprocess.run(
                "git config --global user.name",
                shell=True,
                capture_output=True,
                text=True
            )
            
            if not username_check.stdout.strip():
                subprocess.run(
                    "git config --global user.name \"Lililia User\"",
                    shell=True
                )
                print("Default Git username configured")
            
            email_check = subprocess.run(
                "git config --global user.email",
                shell=True,
                capture_output=True,
                text=True
            )
            
            if not email_check.stdout.strip():
                subprocess.run(
                    "git config --global user.email \"lililia@example.com\"",
                    shell=True
                )
                print("Default Git email configured")
        except Exception as e:
            print(f"Error checking Git user configuration: {e}")
            
        return True
    except Exception as e:
        print(f"Error configuring Git credentials: {e}")
        return False

def handle_file_command(cmd):
    """Handle file creation commands."""
    result = {"stdout": "", "stderr": "", "returncode": None, "message": ""}
    
    parts = cmd.split("]]", 1)  # Split at the first ']]'
    if len(parts) < 2:
        result["message"] = "Error: Invalid FILE command format"
        print(result["message"])
        return result
        
    file_path = parts[0][len(CMD_PREFIX_FILE):].strip()  # Remove prefix
    file_path = expand_path(file_path)
    content = parts[1].strip()
    
    # Create directory if it doesn't exist
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        try:
            os.makedirs(directory)
            result["message"] += f"Created directory: {directory}\n"
            print(f"Created directory: {directory}")
        except Exception as e:
            result["stderr"] = str(e)
            result["message"] += f"Error creating directory: {e}\n"
            print(f"Error creating directory: {e}")
            return result
    
    # Write the file
    try:
        with open(file_path, 'w') as f:
            f.write(content)
        result["message"] += f"File created: {file_path}"
        print(f"File created: {file_path}")
    except Exception as e:
        result["stderr"] = str(e)
        result["message"] += f"Error creating file: {e}"
        print(f"Error creating file: {e}")
    
    return result

def handle_dir_command(cmd):
    """Handle directory creation commands."""
    result = {"stdout": "", "stderr": "", "returncode": None, "message": ""}
    
    dir_path = cmd[len(CMD_PREFIX_DIR):].strip()
    dir_path = expand_path(dir_path)
    
    try:
        os.makedirs(dir_path, exist_ok=True)
        result["message"] = f"Directory created: {dir_path}"
        print(result["message"])
    except Exception as e:
        result["stderr"] = str(e)
        result["message"] = f"Error creating directory: {e}"
        print(result["message"])
    
    return result

def handle_run_command(cmd):
    """Handle shell run commands."""
    result = {"stdout": "", "stderr": "", "returncode": None, "message": ""}
    
    shell_cmd = cmd[len(CMD_PREFIX_RUN):].strip()
    try:
        print(f"Executing: {shell_cmd}")
        
        # Use shell=True on Windows for commands with && or environment variables
        use_shell = os.name == 'nt' and ('&&' in shell_cmd or '%' in shell_cmd or '$' in shell_cmd)
        proc_result = subprocess.run(
            shell_cmd if use_shell else shlex.split(shell_cmd),
            shell=use_shell,
            capture_output=True,
            text=True
        )
        
        result["stdout"] = proc_result.stdout
        result["stderr"] = proc_result.stderr
        result["returncode"] = proc_result.returncode
        
        print("Output:")
        if proc_result.stdout:
            print(proc_result.stdout)
        if proc_result.stderr:
            print("Error output:")
            print(proc_result.stderr)
        print(f"Command completed with exit code: {proc_result.returncode}")
    except Exception as e:
        result["stderr"] = str(e)
        result["message"] = f"Error executing command: {e}"
        print(result["message"])
    
    return result

def handle_git_command(cmd):
    """Handle git commands."""
    result = {"stdout": "", "stderr": "", "returncode": None, "message": ""}
    
    git_cmd = cmd[len(CMD_PREFIX_GIT):].strip()
    try:
        print(f"Executing git command: {git_cmd}")
        full_cmd = f"git {git_cmd}"
        
        # Additional environment variables to prevent credential popups
        env = os.environ.copy()
        if os.name == 'nt':  # Windows
            env['GIT_TERMINAL_PROMPT'] = '0'
        else:  # Unix
            env['GIT_TERMINAL_PROMPT'] = '0'
            env['GIT_ASKPASS'] = '/bin/echo'
        
        # Use shell=True on Windows if needed
        use_shell = os.name == 'nt' and ('&&' in git_cmd or '%' in git_cmd or '$' in git_cmd)
        proc_result = subprocess.run(
            full_cmd if use_shell else shlex.split(full_cmd),
            shell=use_shell,
            capture_output=True,
            text=True,
            env=env
        )
        
        result["stdout"] = proc_result.stdout
        result["stderr"] = proc_result.stderr
        result["returncode"] = proc_result.returncode
        
        print("Output:")
        if proc_result.stdout:
            print(proc_result.stdout)
        if proc_result.stderr:
            print("Error output:")
            print(proc_result.stderr)
        print(f"Git command completed with exit code: {proc_result.returncode}")
    except Exception as e:
        result["stderr"] = str(e)
        result["message"] = f"Error executing git command: {e}"
        print(result["message"])
    
    return result

def handle_install_command(cmd):
    """Handle package installation commands."""
    result = {"stdout": "", "stderr": "", "returncode": None, "message": ""}
    
    package = cmd[len(CMD_PREFIX_INSTALL):].strip()
    try:
        # Detect package manager
        pm_cmd = detect_package_manager(package)
        if not pm_cmd:
            result["message"] = "Could not detect package manager. Please install manually."
            print(result["message"])
            return result
            
        print(f"Installing {package} using command: {pm_cmd}")
        use_shell = os.name == 'nt'  # Use shell=True on Windows for better compatibility
        proc_result = subprocess.run(
            pm_cmd if use_shell else shlex.split(pm_cmd),
            shell=use_shell,
            capture_output=True,
            text=True
        )
        
        result["stdout"] = proc_result.stdout
        result["stderr"] = proc_result.stderr
        result["returncode"] = proc_result.returncode
        
        print("Output:")
        if proc_result.stdout:
            print(proc_result.stdout)
        if proc_result.stderr:
            print("Error output:")
            print(proc_result.stderr)
        print(f"Installation completed with exit code: {proc_result.returncode}")
    except Exception as e:
        result["stderr"] = str(e)
        result["message"] = f"Error installing package: {e}"
        print(result["message"])
    
    return result

def handle_generic_command(cmd):
    """Handle generic commands."""
    result = {"stdout": "", "stderr": "", "returncode": None, "message": ""}
    
    try:
        print(f"Executing generic command: {cmd}")
        
        # Use shell=True on Windows for better compatibility
        use_shell = os.name == 'nt' and ('&&' in cmd or '%' in cmd or '$' in cmd)
        proc_result = subprocess.run(
            cmd if use_shell else shlex.split(cmd),
            shell=use_shell,
            capture_output=True,
            text=True
        )
        
        result["stdout"] = proc_result.stdout
        result["stderr"] = proc_result.stderr
        result["returncode"] = proc_result.returncode
        
        print("Output:")
        if proc_result.stdout:
            print(proc_result.stdout)
        if proc_result.stderr:
            print("Error output:")
            print(proc_result.stderr)
        print(f"Command completed with exit code: {proc_result.returncode}")
    except Exception as e:
        result["stderr"] = str(e)
        result["message"] = f"Error executing command: {e}"
        print(result["message"])
    
    return result

def detect_package_manager(package):
    """Detect the appropriate package manager for installation."""
    if os.name == 'nt':  # Windows
        # Check for Python packages first
        if os.path.exists(os.path.join(os.environ.get('SYSTEMDRIVE', 'C:'), 'Python')) or \
           os.path.exists(os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Python')):
            return f"pip install {package}"
        # Check for npm
        elif os.path.exists(os.path.join(os.environ.get('PROGRAMFILES', ''), 'nodejs')) or \
             os.path.exists(os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), 'nodejs')):
            return f"npm install -g {package}"
        # Check for chocolatey
        elif os.path.exists(os.path.join(os.environ.get('PROGRAMDATA', ''), 'chocolatey')):
            return f"choco install {package} -y"
        return None
    else:  # Unix-like systems
        if os.path.exists("/usr/bin/apt") or os.path.exists("/bin/apt"):
            return f"apt-get install -y {package}"
        elif os.path.exists("/usr/bin/yum") or os.path.exists("/bin/yum"):
            return f"yum install -y {package}"
        elif os.path.exists("/usr/bin/dnf") or os.path.exists("/bin/dnf"):
            return f"dnf install -y {package}"
        elif os.path.exists("/usr/bin/brew") or os.path.exists("/usr/local/bin/brew"):
            return f"brew install {package}"
        elif os.path.exists("/usr/bin/pip") or os.path.exists("/usr/local/bin/pip"):
            return f"pip install {package}"
        elif os.path.exists("/usr/bin/npm") or os.path.exists("/usr/local/bin/npm"):
            return f"npm install -g {package}"
        return None