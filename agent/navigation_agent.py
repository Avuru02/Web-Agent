"""
Navigation Agent - LLM decision-making for web navigation.

🚨 CRITICAL: The LLM does ALL the reasoning. No app-specific logic.
"""

import json
import os
import re
from typing import Dict, List, Optional
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
        
    def decide_next_action(
        self,
        task_description: str,
        current_page: str,
        history: List[Dict]
    ) -> Dict:
        """
        Ask LLM to decide the next action based on task, page state, and history.
        
        Args:
            task_description: What the user wants to accomplish
            current_page: Serialized page state from page_serializer
            history: List of previous actions taken
            
        Returns:
            Dictionary with action details (e.g., {"action": "click", "target_text": "New"})
        """
        
        # Build history context
        history_text = ""
        if history:
            history_text = "\nPREVIOUS ACTIONS:\n"
            for i, step in enumerate(history[-5:]):  # Last 5 steps
                history_text += f"{i+1}. {step.get('action', {}).get('action', 'unknown')}: {step.get('action', {})}\n"
        
        # System prompt - defines action vocabulary
        system_prompt = """You are a web navigation agent controlling a browser.

Your job: Output the NEXT action as a valid JSON object based on the task, current page state, and history.

ALLOWED ACTIONS (output as JSON object):
- {"action": "click", "target_text": "text on clickable element"}
- {"action": "type", "target_field": "placeholder or label", "text": "value to type"}
- {"action": "press", "key": "Enter" | "Escape" | "Tab" | etc.}
- {"action": "wait", "seconds": 2}
- {"action": "finish", "summary": "what was accomplished"}

RULES:
1. Only use text that exists on the current page (check INTERACTIVE ELEMENTS)
2. Be precise with target_text (use exact visible text from buttons/links)
3. For inputs, use the placeholder or label text shown in INTERACTIVE ELEMENTS
4. If the task appears complete, use "finish" action
5. If you're unsure, try the most likely next step
6. Output ONLY a valid JSON object, no explanation or markdown
7. You must work on ANY web application - don't assume anything about the app's structure
8. If an action fails, try alternative approaches (different text matching, etc.)

IMPORTANT: You don't know which app you're navigating. You must rely solely on
what you see on the current page (buttons, inputs, text) to accomplish the task.

You must respond with a valid JSON object only, no other text."""

        # User prompt with task and context
        user_prompt = f"""TASK: {task_description}

{current_page}

{history_text}

What is the next action? Output JSON only."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
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

