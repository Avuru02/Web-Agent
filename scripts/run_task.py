"""
CLI entry point for running navigation tasks.

🚨 IMPORTANT: This file can have task CONFIGURATIONS (URLs, descriptions),
but NO LOGIC about how to execute tasks.
"""

import sys
import os
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path to import agent modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.orchestrator import run_task


# Define task configurations
# ✅ THIS IS OK - just storing URLs and descriptions
# ❌ NO LOGIC about how to execute the task
TASKS = {
    "notion": {
        "create_page": {
            "url": "https://notion.so/",
            "description": "Create a new page titled 'Softlight Demo'",
            "requires_login": True
        },
        "filter_database": {
            "url": "https://notion.so/",
            "description": "Filter the database to show only items with Status = 'In Progress'",
            "requires_login": True
        }
    },
    "linear": {
        "create_project": {
            "url": "https://linear.app/",
            "description": "Create a new project called 'Agent Test'",
            "requires_login": True
        },
        "create_issue": {
            "url": "https://linear.app/",
            "description": "Create a new issue titled 'Test Issue from Agent'",
            "requires_login": True
        }
    },
    "github": {
        "create_repo": {
            "url": "https://github.com/new",
            "description": "Create a new repository called 'test-agent-repo'",
            "requires_login": True
        },
        "explore_trending": {
            "url": "https://github.com/trending",
            "description": "Navigate to trending repositories and find the top Python project",
            "requires_login": False
        }
    }
}


def get_credentials_from_env() -> dict:
    """Get credentials from environment variables."""
    return {
        "username": os.getenv("WEB_AGENT_USERNAME", ""),
        "password": os.getenv("WEB_AGENT_PASSWORD", "")
    }


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run web navigation tasks with AI agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/run_task.py notion create_page
  python scripts/run_task.py linear create_issue --headless
  python scripts/run_task.py --custom --url "https://example.com" --task "Find the contact page"
  
Environment variables for credentials:
  WEB_AGENT_USERNAME - Username/email for login
  WEB_AGENT_PASSWORD - Password for login
        """
    )
    
    parser.add_argument("app", nargs="?", help="Application name (e.g., notion, linear)")
    parser.add_argument("task", nargs="?", help="Task name (e.g., create_page)")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--max-steps", type=int, default=20, help="Maximum steps (default: 20)")
    
    # Custom task options
    parser.add_argument("--custom", action="store_true", help="Run a custom task")
    parser.add_argument("--url", help="Starting URL for custom task")
    parser.add_argument("--description", "--task-desc", dest="description", help="Task description for custom task")
    
    # Credential options
    parser.add_argument("--username", help="Username for login (overrides env var)")
    parser.add_argument("--password", help="Password for login (overrides env var)")
    
    args = parser.parse_args()
    
    # Handle custom task
    if args.custom:
        if not args.url or not args.description:
            print("Error: --custom requires --url and --description")
            sys.exit(1)
        
        app_name = "custom"
        task_name = "custom_task"
        url = args.url
        description = args.description
        requires_login = bool(args.username or args.password or os.getenv("WEB_AGENT_USERNAME"))
    else:
        # Validate predefined app and task
        if not args.app or not args.task:
            print("Usage: python scripts/run_task.py <app_name> <task_name> [--headless]")
            print("       python scripts/run_task.py --custom --url <url> --description <task>")
            print("\nAvailable apps and tasks:")
            for app, tasks in TASKS.items():
                print(f"  {app}:")
                for task_name, config in tasks.items():
                    login_indicator = "🔐" if config.get("requires_login") else "🌐"
                    print(f"    - {task_name} {login_indicator}")
            print("\n🔐 = requires login, 🌐 = public")
            sys.exit(1)
        
        if args.app not in TASKS:
            print(f"Error: Unknown app '{args.app}'")
            print(f"Available apps: {', '.join(TASKS.keys())}")
            sys.exit(1)
        
        if args.task not in TASKS[args.app]:
            print(f"Error: Unknown task '{args.task}' for app '{args.app}'")
            print(f"Available tasks for {args.app}: {', '.join(TASKS[args.app].keys())}")
            sys.exit(1)
        
        app_name = args.app
        task_name = args.task
        config = TASKS[app_name][task_name]
        url = config["url"]
        description = config["description"]
        requires_login = config.get("requires_login", False)
    
    # Get credentials
    credentials = None
    if requires_login or args.username or args.password:
        credentials = get_credentials_from_env()
        if args.username:
            credentials["username"] = args.username
        if args.password:
            credentials["password"] = args.password
        
        if requires_login and not credentials.get("username"):
            print("⚠️  Warning: This task may require login but no credentials provided.")
            print("   Set WEB_AGENT_USERNAME and WEB_AGENT_PASSWORD environment variables,")
            print("   or use --username and --password flags.")
    
    # Run the task
    print(f"\n{'='*60}")
    print(f"🤖 Web Agent - Task Runner")
    print(f"{'='*60}")
    print(f"App: {app_name}")
    print(f"Task: {task_name}")
    print(f"URL: {url}")
    print(f"Description: {description}")
    print(f"Headless: {args.headless}")
    print(f"Max Steps: {args.max_steps}")
    print(f"Credentials: {'Provided' if credentials and credentials.get('username') else 'None'}")
    print(f"{'='*60}\n")
    
    result = run_task(
        app_name=app_name,
        task_name=task_name,
        start_url=url,
        task_description=description,
        max_steps=args.max_steps,
        headless=args.headless,
        credentials=credentials
    )
    
    if result["success"]:
        print(f"\n✅ Task completed successfully!")
        print(f"Results saved to: {result['output_dir']}")
    else:
        print(f"\n❌ Task failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()

