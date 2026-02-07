"""
Orchestrator - Main execution loop for web navigation tasks.

🚨 CRITICAL: This is the SAME loop for every app. No special cases.
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

from agent.browser_controller import BrowserController
from agent.page_serializer import serialize_page, PageStateTracker, get_element_summary
from agent.navigation_agent import NavigationAgent


def run_task(
    app_name: str,
    task_name: str,
    start_url: str,
    task_description: str,
    max_steps: int = 20,  # Increased default for complex flows
    headless: bool = False,
    credentials: Optional[Dict[str, str]] = None
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
        credentials: Optional dict with 'username' and 'password' for login tasks
        
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
    page_tracker = PageStateTracker()
    
    # Enhance task description with credentials if provided
    enhanced_task = task_description
    if credentials:
        enhanced_task += f"\n\nCredentials available - Username: {credentials.get('username', 'N/A')}, Password: {credentials.get('password', '[hidden]')}"
    
    history: List[Dict] = []
    step_count = 0
    consecutive_failures = 0
    max_consecutive_failures = 5
    
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
        
        # Initialize page tracking with current state
        initial_elements = browser.get_interactive_elements()
        page_tracker.compute_changes(initial_elements, browser.get_current_url())
        
        # Main execution loop
        print(f"Starting task: {task_description}")
        
        while step_count < max_steps:
            print(f"\n{'='*50}")
            print(f"Step {step_count + 1}/{max_steps}")
            print(f"{'='*50}")
            
            # Serialize current page state (GENERIC)
            current_url = browser.get_current_url()
            visible_text = browser.get_text_snapshot()
            interactive_elements = browser.get_interactive_elements()
            
            # Compute page changes since last action
            page_changes = page_tracker.compute_changes(interactive_elements, current_url)
            
            if page_changes.get('has_changes'):
                print(f"📊 Page changes detected:")
                if page_changes.get('url_changed'):
                    print(f"  - URL changed")
                if page_changes.get('new_elements'):
                    print(f"  - {len(page_changes['new_elements'])} new elements appeared")
                if page_changes.get('removed_elements'):
                    print(f"  - {len(page_changes['removed_elements'])} elements removed")
            
            # Serialize page with highlighted new elements
            page_state = serialize_page(
                current_url, 
                visible_text, 
                interactive_elements,
                highlight_elements=page_changes.get('new_elements', [])
            )
            
            # Ask LLM for next action (GENERIC) with page changes context
            print("🤖 Asking LLM for next action...")
            action = agent.decide_next_action(
                enhanced_task, 
                page_state, 
                history,
                page_changes=page_changes
            )
            print(f"📋 Action: {json.dumps(action, indent=2)}")
            
            # Check if task is complete
            if action.get("action") == "finish":
                print(f"✅ Task complete: {action.get('summary', 'No summary provided')}")
                # Take final screenshot
                final_screenshot = output_dir / f"step_{step_count:02d}_final.png"
                browser.screenshot(str(final_screenshot))
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
                consecutive_failures = 0
                print(f"✓ Action executed successfully")
            except Exception as e:
                error_message = str(e)
                consecutive_failures += 1
                print(f"✗ Action failed: {error_message}")
                # Take error screenshot
                error_screenshot = output_dir / f"step_{step_count:02d}_error.png"
                browser.screenshot(str(error_screenshot))
            
            # Wait for page to settle (GENERIC)
            if action.get("action") == "wait":
                wait_seconds = action.get("seconds", 1)
                print(f"⏳ Waiting {wait_seconds} seconds...")
                time.sleep(wait_seconds)
            else:
                # Dynamic wait - longer after typing/clicking for form changes
                if action.get("action") in ["type", "click", "press"]:
                    browser.wait_for_change(timeout=3.0)
                    # Additional brief wait for dynamic content
                    time.sleep(0.5)
                else:
                    browser.wait_for_change()
            
            # Take screenshot AFTER action (shows result)
            screenshot_after = output_dir / f"step_{step_count:02d}_after.png"
            browser.screenshot(str(screenshot_after))
            
            # Get elements after action to track what appeared
            elements_after = browser.get_interactive_elements()
            post_action_changes = page_tracker.compute_changes(elements_after, browser.get_current_url())
            
            # Log step to history with enhanced info
            step_data = {
                "step": step_count,
                "url": current_url,
                "url_after": browser.get_current_url(),
                "action": action,
                "screenshot_before": screenshot_before.name,
                "screenshot_after": screenshot_after.name,
                "success": success,
                "elements_added": get_element_summary(post_action_changes.get('new_elements', [])),
                "elements_removed": get_element_summary(post_action_changes.get('removed_elements', []))
            }
            
            if error_message:
                step_data["error"] = error_message
                if "error_screenshot" in locals():
                    step_data["screenshot_error"] = error_screenshot.name
            
            history.append(step_data)
            
            # Check for too many consecutive failures
            if consecutive_failures >= max_consecutive_failures:
                print(f"⚠️ Too many consecutive failures ({consecutive_failures}), stopping...")
                break
            
            step_count += 1
        
        # Determine overall success
        task_completed = any(
            step.get('action', {}).get('action') == 'finish' 
            for step in history
        )
        
        # Save trace.json with all step metadata
        trace_data = {
            "task_description": task_description,
            "start_url": start_url,
            "app_name": app_name,
            "task_name": task_name,
            "timestamp": timestamp,
            "total_steps": step_count,
            "task_completed": task_completed,
            "steps": history
        }
        
        trace_file = output_dir / "trace.json"
        with open(trace_file, "w") as f:
            json.dump(trace_data, f, indent=2)
        
        print(f"\n{'='*50}")
        print(f"Task {'completed' if task_completed else 'ended'}. Results saved to {output_dir}")
        print(f"{'='*50}")
        
        return {
            "success": task_completed,
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
        
    elif action_type == "scroll":
        direction = action.get("direction", "down")
        browser.scroll(direction)
        
    elif action_type == "wait":
        # Wait is handled in orchestrator, but we can handle it here too
        seconds = action.get("seconds", 1)
        time.sleep(seconds)
        
    elif action_type == "finish":
        # Finish is handled in orchestrator
        pass
        
    else:
        raise ValueError(f"Unknown action type: {action_type}")

