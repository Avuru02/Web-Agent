"""
Setup script for Softlight Agent.
Run: python setup.py
"""

import subprocess
import sys
import os


def run_command(command, description):
    """Run a shell command and handle errors."""
    print(f"\n{description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(e.stderr)
        return False


def main():
    """Main setup function."""
    print("=" * 60)
    print("Softlight Agent Setup")
    print("=" * 60)
    
    # Check Python version
    python_version = sys.version_info
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 10):
        print("❌ Python 3.10+ is required")
        print(f"   Current version: {python_version.major}.{python_version.minor}")
        sys.exit(1)
    
    print(f"✅ Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    # Install Python dependencies
    if not run_command("pip install -r requirements.txt", "Installing Python dependencies"):
        print("\n⚠️  Failed to install dependencies. Please run manually:")
        print("   pip install -r requirements.txt")
        sys.exit(1)
    
    # Install Playwright browsers
    if not run_command("playwright install chromium", "Installing Playwright browsers"):
        print("\n⚠️  Failed to install Playwright browsers. Please run manually:")
        print("   playwright install chromium")
        sys.exit(1)
    
    # Check for .env file
    if not os.path.exists(".env"):
        print("\n⚠️  .env file not found. Creating from .env.example...")
        if os.path.exists(".env.example"):
            with open(".env.example", "r") as f:
                content = f.read()
            with open(".env", "w") as f:
                f.write(content)
            print("✅ Created .env file. Please edit it and add your OPENAI_API_KEY")
        else:
            print("❌ .env.example not found. Please create .env manually with OPENAI_API_KEY")
    else:
        print("✅ .env file exists")
    
    # Create dataset directory
    os.makedirs("dataset", exist_ok=True)
    print("✅ Created dataset directory")
    
    print("\n" + "=" * 60)
    print("Setup complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Edit .env and add your OPENAI_API_KEY")
    print("2. Update URLs in scripts/run_task.py with your actual workspace links")
    print("3. Run a task: python scripts/run_task.py notion create_page")
    print("\n")


if __name__ == "__main__":
    main()

