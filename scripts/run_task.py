"""
CLI entry point for running navigation tasks.

🚨 IMPORTANT: This file can have task CONFIGURATIONS (URLs, descriptions),
but NO LOGIC about how to execute tasks.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path to import agent modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.orchestrator import run_task


# Define task configurations
# ✅ THIS IS OK - just storing URLs and descriptions
# ❌ NO LOGIC about how to execute the task
TASKS = {
    "notion": {
        "create_page": {
            "url": "https://notion.so/your-workspace",
            "description": "Create a new page titled 'Softlight Demo'"
        },
        "filter_database": {
            "url": "https://notion.so/your-database-link",
            "description": "Filter the database to show only items with Status = 'In Progress'"
        }
    },
    "linear": {
        "create_project": {
            "url": "https://linear.app/your-team/projects",
            "description": "Create a new project called 'Agent Test'"
        }
    }
}


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 3:
        print("Usage: python scripts/run_task.py <app_name> <task_name> [--headless]")
        print("\nAvailable apps and tasks:")
        for app, tasks in TASKS.items():
            print(f"  {app}:")
            for task_name in tasks.keys():
                print(f"    - {task_name}")
        sys.exit(1)
    
    app = sys.argv[1]
    task = sys.argv[2]
    headless = "--headless" in sys.argv
    
    # Validate app and task
    if app not in TASKS:
        print(f"Error: Unknown app '{app}'")
        print(f"Available apps: {', '.join(TASKS.keys())}")
        sys.exit(1)
    
    if task not in TASKS[app]:
        print(f"Error: Unknown task '{task}' for app '{app}'")
        print(f"Available tasks for {app}: {', '.join(TASKS[app].keys())}")
        sys.exit(1)
    
    # Get task configuration
    config = TASKS[app][task]
    
    # ✅ Generic orchestrator call - same for all apps
    print(f"Running task: {app}/{task}")
    print(f"URL: {config['url']}")
    print(f"Description: {config['description']}")
    print(f"Headless: {headless}\n")
    
    result = run_task(
        app_name=app,
        task_name=task,
        start_url=config["url"],
        task_description=config["description"],
        headless=headless
    )
    
    if result["success"]:
        print(f"\n✅ Task completed successfully!")
        print(f"Results saved to: {result['output_dir']}")
    else:
        print(f"\n❌ Task failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()

