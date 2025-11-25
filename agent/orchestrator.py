"""
Orchestrator - Main execution loop for web navigation tasks.

🚨 CRITICAL: This is the SAME loop for every app. No special cases.
"""

import os
import json
from datetime import datetime
from typing import Dict, List
from pathlib import Path

from agent.browser_controller import BrowserController
from agent.page_serializer import serialize_page
from agent.navigation_agent import NavigationAgent


def run_task(
    app_name: str,
    task_name: str,
    start_url: str,
    task_description: str,
    max_steps: int = 15,
    headless: bool = False
) -> Dict:
    """
    Main execution loop for running a navigation task.
    
    Args:
        app_name: Name of app (e.g., "notion") - ONLY FOR LOGGING, NOT LOGIC
        task_name: Name of task (e.g., "create_page") - ONLY FOR LOGGING, NOT LOGIC
        start_url: Starting URL to navigate to
        task_description: Natural language description of what to accomplish
        max_steps: Maximum number of steps to take
        headless: Whether to run browser in headless mode
        
    Returns:
        Dictionary with execution summary
    """
    
    # Create output directory (app_name is just for organizing files, NOT for logic)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("dataset") / app_name / f"{task_name}_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize components
    browser = BrowserController(headless=headless)
    agent = NavigationAgent()
    
    history: List[Dict] = []
    step_count = 0
    
    try:
        # Launch browser and navigate to start URL
        print(f"Launching browser and navigating to {start_url}...")
        browser.launch()
        browser.goto(start_url)
        
        # Initial wait for page to load
        browser.wait_for_change()
        
        # Take initial screenshot
        initial_screenshot = output_dir / "step_00_initial.png"
        browser.screenshot(str(initial_screenshot))
        
        # Main execution loop
        print(f"Starting task: {task_description}")
        
        while step_count < max_steps:
            print(f"\n--- Step {step_count} ---")
            
            # Serialize current page state (GENERIC)
            current_url = browser.get_current_url()
            visible_text = browser.get_text_snapshot()
            interactive_elements = browser.get_interactive_elements()
            page_state = serialize_page(current_url, visible_text, interactive_elements)
            
            # Ask LLM for next action (GENERIC)
            print("Asking LLM for next action...")
            action = agent.decide_next_action(task_description, page_state, history)
            print(f"Action: {action}")
            
            # Check if task is complete
            if action.get("action") == "finish":
                print(f"Task complete: {action.get('summary', 'No summary provided')}")
                break
            
            # Take screenshot BEFORE action (shows current state)
            screenshot_before = output_dir / f"step_{step_count:02d}_before.png"
            browser.screenshot(str(screenshot_before))
            
            # Execute action (GENERIC)
            success = False
            error_message = None
            
            try:
                execute_action(browser, action)
                success = True
                print(f"Action executed successfully")
            except Exception as e:
                error_message = str(e)
                print(f"Action failed: {error_message}")
                # Take error screenshot
                error_screenshot = output_dir / f"step_{step_count:02d}_error.png"
                browser.screenshot(str(error_screenshot))
            
            # Wait for page to settle (GENERIC)
            if action.get("action") == "wait":
                wait_seconds = action.get("seconds", 1)
                import time
                time.sleep(wait_seconds)
            else:
                browser.wait_for_change()
            
            # Take screenshot AFTER action (shows result)
            screenshot_after = output_dir / f"step_{step_count:02d}_after.png"
            browser.screenshot(str(screenshot_after))
            
            # Log step to history
            step_data = {
                "step": step_count,
                "url": current_url,
                "action": action,
                "screenshot_before": screenshot_before.name,
                "screenshot_after": screenshot_after.name,
                "success": success
            }
            
            if error_message:
                step_data["error"] = error_message
                if "error_screenshot" in locals():
                    step_data["screenshot_error"] = error_screenshot.name
            
            history.append(step_data)
            
            # If action failed, decide whether to continue or abort
            if not success:
                # For now, continue but log the error
                # In a production system, you might want to retry or abort
                print("Warning: Action failed, but continuing...")
            
            step_count += 1
        
        # Save trace.json with all step metadata
        trace_data = {
            "task_description": task_description,
            "start_url": start_url,
            "app_name": app_name,
            "task_name": task_name,
            "timestamp": timestamp,
            "total_steps": step_count,
            "steps": history
        }
        
        trace_file = output_dir / "trace.json"
        with open(trace_file, "w") as f:
            json.dump(trace_data, f, indent=2)
        
        print(f"\nTask completed. Results saved to {output_dir}")
        
        return {
            "success": True,
            "output_dir": str(output_dir),
            "total_steps": step_count,
            "trace_file": str(trace_file)
        }
        
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "output_dir": str(output_dir) if "output_dir" in locals() else None
        }
        
    finally:
        # Close browser gracefully
        browser.close()


def execute_action(browser: BrowserController, action: Dict):
    """
    Execute a single action on the browser.
    
    🚨 CRITICAL: Generic action execution - works for any app.
    """
    action_type = action.get("action")
    
    if action_type == "click":
        target_text = action.get("target_text")
        if not target_text:
            raise ValueError("Click action requires 'target_text'")
        browser.click_by_text(target_text)
        
    elif action_type == "type":
        target_field = action.get("target_field")
        text = action.get("text")
        if not target_field or text is None:
            raise ValueError("Type action requires 'target_field' and 'text'")
        browser.fill_input(target_field, text)
        
    elif action_type == "press":
        key = action.get("key")
        if not key:
            raise ValueError("Press action requires 'key'")
        browser.press_key(key)
        
    elif action_type == "wait":
        # Wait is handled in orchestrator, but we can handle it here too
        seconds = action.get("seconds", 1)
        import time
        time.sleep(seconds)
        
    elif action_type == "finish":
        # Finish is handled in orchestrator
        pass
        
    else:
        raise ValueError(f"Unknown action type: {action_type}")

