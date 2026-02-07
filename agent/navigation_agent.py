"""
Navigation Agent - LLM decision-making for web navigation.

🚨 CRITICAL: The LLM does ALL the reasoning. No app-specific logic.
"""

import json
import os
import re
from typing import Dict, List, Optional, Set, Tuple
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class NavigationAgent:
    """LLM-powered navigation agent that decides actions dynamically."""
    
    def __init__(self, model: str = "gpt-4", temperature: float = 0.2):
        """
        Initialize navigation agent.
        
        Args:
            model: OpenAI model to use (default: gpt-4)
            temperature: Temperature for LLM (lower = more deterministic)
        """
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.recent_actions: List[str] = []  # Track recent actions for loop detection
        self.max_identical_actions = 3  # Max times same action can repeat
        
    def _detect_loop(self, action: Dict) -> Tuple[bool, str]:
        """
        Detect if we're stuck in a loop of repeated actions.
        
        Returns:
            Tuple of (is_loop, reason)
        """
        action_key = json.dumps(action, sort_keys=True)
        
        # Count how many times this exact action appears in recent history
        recent_count = self.recent_actions[-5:].count(action_key)
        
        if recent_count >= self.max_identical_actions - 1:
            return True, f"Action '{action.get('action')}' has been attempted {recent_count + 1} times"
        
        return False, ""
    
    def _get_loop_breaker_prompt(self, failed_action: Dict, reason: str) -> str:
        """Generate additional prompt context when stuck in a loop."""
        return f"""
⚠️ LOOP DETECTED: {reason}

The previous action is NOT working. You MUST try something DIFFERENT:
- If trying to find an element, look for alternative text or nearby elements
- If waiting for content to load, try scrolling or clicking elsewhere first
- If a form field isn't appearing, check if you need to submit previous field first (press Enter)
- For multi-step forms (like login), the next field may appear AFTER you complete the current field

DO NOT repeat: {json.dumps(failed_action)}
"""
        
    def decide_next_action(
        self,
        task_description: str,
        current_page: str,
        history: List[Dict],
        page_changes: Optional[Dict] = None
    ) -> Dict:
        """
        Ask LLM to decide the next action based on task, page state, and history.
        
        Args:
            task_description: What the user wants to accomplish
            current_page: Serialized page state from page_serializer
            history: List of previous actions taken
            page_changes: Optional dict describing what changed since last action
            
        Returns:
            Dictionary with action details (e.g., {"action": "click", "target_text": "New"})
        """
        
        # Build history context with success/failure info
        history_text = ""
        if history:
            history_text = "\nPREVIOUS ACTIONS (most recent last):\n"
            for i, step in enumerate(history[-7:]):  # Last 7 steps for more context
                action_info = step.get('action', {})
                success = "✓" if step.get('success', False) else "✗"
                error = f" - Error: {step.get('error', '')}" if step.get('error') else ""
                
                history_text += f"{i+1}. [{success}] {action_info.get('action', 'unknown')}: "
                
                if action_info.get('action') == 'type':
                    history_text += f"field='{action_info.get('target_field')}'"
                elif action_info.get('action') == 'click':
                    history_text += f"target='{action_info.get('target_text')}'"
                elif action_info.get('action') == 'press':
                    history_text += f"key='{action_info.get('key')}'"
                else:
                    history_text += str(action_info)
                    
                history_text += f"{error}\n"
                
                # Include page changes after this action if available
                if step.get('elements_added'):
                    history_text += f"   → New elements appeared: {step.get('elements_added')[:3]}\n"
        
        # Build page changes context
        changes_text = ""
        if page_changes:
            if page_changes.get('new_elements'):
                changes_text += "\n🆕 NEW ELEMENTS APPEARED (after last action):\n"
                for elem in page_changes['new_elements'][:10]:
                    changes_text += f"  - {elem.get('type')}: \"{elem.get('text')}\"\n"
            if page_changes.get('removed_elements'):
                changes_text += "\n❌ ELEMENTS DISAPPEARED:\n"
                for elem in page_changes['removed_elements'][:5]:
                    changes_text += f"  - {elem.get('type')}: \"{elem.get('text')}\"\n"
        
        # System prompt - defines action vocabulary with login/form awareness
        system_prompt = """You are a web navigation agent controlling a browser.

Your job: Output the NEXT action as a valid JSON object based on the task, current page state, and history.

ALLOWED ACTIONS (output as JSON object):
- {"action": "click", "target_text": "text on clickable element"}
- {"action": "type", "target_field": "placeholder or label", "text": "value to type"}
- {"action": "press", "key": "Enter" | "Escape" | "Tab" | etc.}
- {"action": "scroll", "direction": "down" | "up"}
- {"action": "wait", "seconds": 2}
- {"action": "finish", "summary": "what was accomplished"}

CRITICAL RULES FOR FORMS & LOGIN:
1. Many login forms are MULTI-STEP: Enter username → Press Enter or Click Continue → Password field appears
2. After typing in a field, you often need to PRESS ENTER or CLICK A BUTTON to reveal the next field
3. ALWAYS check "NEW ELEMENTS APPEARED" section - these are fields/buttons that just became visible
4. If you see only a username/email field, type it, then press Enter or click "Next"/"Continue"
5. Password fields often appear ONLY AFTER submitting the username - this is normal
6. Watch for ✓ and ✗ in history - ✗ means that action FAILED, don't repeat it the same way

GENERAL RULES:
1. Only use text that exists on the current page (check INTERACTIVE ELEMENTS)
2. Be precise with target_text (use exact visible text from buttons/links)
3. For inputs, use the placeholder or label text shown in INTERACTIVE ELEMENTS
4. If the task appears complete, use "finish" action
5. Output ONLY a valid JSON object, no explanation or markdown
6. You must work on ANY web application - don't assume anything about the app's structure
7. If an action fails, try ALTERNATIVE approaches (different text, different element)
8. Don't repeat the same failed action - the page state tells you what's available NOW

COMMON PATTERNS:
- Google/Microsoft login: Email → Next → Password → Next
- Magic link login: Email → Send link (no password)
- Traditional login: Email and Password visible together
- SSO: Click "Sign in with Google/Microsoft/etc"

You must respond with a valid JSON object only, no other text."""

        # User prompt with task and context
        user_prompt = f"""TASK: {task_description}

{current_page}
{changes_text}
{history_text}

What is the next action? Output JSON only."""

        # Check for loops before making the request
        loop_breaker = ""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt + loop_breaker}
                ],
                temperature=self.temperature,
                response_format={"type": "json_object"}  # Force JSON response
            )
            
            # Parse JSON response
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from LLM")
            
            action = json.loads(content)
            
            # Validate action structure
            if "action" not in action:
                raise ValueError("Action missing 'action' field")
            
            # Check for loop
            is_loop, loop_reason = self._detect_loop(action)
            if is_loop:
                print(f"⚠️ Loop detected: {loop_reason}")
                # Ask LLM again with loop-breaker prompt
                loop_breaker = self._get_loop_breaker_prompt(action, loop_reason)
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt + loop_breaker}
                    ],
                    temperature=min(self.temperature + 0.3, 1.0),  # Increase temperature to get different response
                    response_format={"type": "json_object"}
                )
                
                content = response.choices[0].message.content
                if content:
                    action = json.loads(content)
            
            # Track this action for loop detection
            self.recent_actions.append(json.dumps(action, sort_keys=True))
            if len(self.recent_actions) > 10:
                self.recent_actions.pop(0)
            
            return action
            
        except json.JSONDecodeError as e:
            print(f"Error parsing LLM response as JSON: {e}")
            content_str = content if 'content' in locals() else "No content"
            print(f"Response was: {content_str}")
            # Try to extract JSON from markdown code blocks if present
            if 'content' in locals() and content:
                json_match = re.search(r'\{[^}]+\}', content)
                if json_match:
                    try:
                        action = json.loads(json_match.group())
                        if "action" in action:
                            return action
                    except:
                        pass
            # Return a safe default action
            return {"action": "wait", "seconds": 1}
        except Exception as e:
            print(f"Error calling LLM: {e}")
            import traceback
            traceback.print_exc()
            # Return a safe default action
            return {"action": "wait", "seconds": 1}
    
    def reset_loop_detection(self):
        """Reset loop detection state (call when starting new task)."""
        self.recent_actions = []

