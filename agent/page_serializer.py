"""
Page Serializer - Convert page state into LLM-friendly format.

🚨 CRITICAL: Must work for ANY web app. No app-specific parsing.
"""

from typing import List, Dict, Optional, Tuple, Set


class PageStateTracker:
    """Tracks page state changes between actions to detect new/removed elements."""
    
    def __init__(self):
        self.previous_elements: Set[str] = set()
        self.previous_url: Optional[str] = None
        
    def _element_key(self, elem: Dict) -> str:
        """Create a unique key for an element."""
        return f"{elem.get('type')}:{elem.get('text', '')}:{elem.get('input_type', '')}"
    
    def compute_changes(
        self, 
        current_elements: List[Dict],
        current_url: str
    ) -> Dict:
        """
        Compare current page state with previous and return changes.
        
        Returns:
            Dict with 'new_elements', 'removed_elements', 'url_changed'
        """
        current_set = {self._element_key(e) for e in current_elements}
        
        # Find new and removed elements
        new_keys = current_set - self.previous_elements
        removed_keys = self.previous_elements - current_set
        
        # Convert keys back to element info
        new_elements = [e for e in current_elements if self._element_key(e) in new_keys]
        
        # For removed, we only have the key, reconstruct minimal info
        removed_elements = []
        for key in removed_keys:
            parts = key.split(":", 2)
            if len(parts) >= 2:
                removed_elements.append({"type": parts[0], "text": parts[1]})
        
        url_changed = self.previous_url is not None and self.previous_url != current_url
        
        # Update state for next comparison
        self.previous_elements = current_set
        self.previous_url = current_url
        
        return {
            "new_elements": new_elements,
            "removed_elements": removed_elements,
            "url_changed": url_changed,
            "has_changes": len(new_elements) > 0 or len(removed_elements) > 0 or url_changed
        }
    
    def reset(self):
        """Reset state tracking (call when starting new task)."""
        self.previous_elements = set()
        self.previous_url = None


def serialize_page(
    url: str, 
    visible_text: str, 
    interactive_elements: List[Dict],
    highlight_elements: Optional[List[Dict]] = None
) -> str:
    """
    Returns a string representation of the page state for the LLM.
    
    MUST BE APP-AGNOSTIC: This format should work whether you're on
    Notion, Linear, Asana, or a completely new app.
    
    Args:
        url: Current page URL
        visible_text: Extracted visible text from page
        interactive_elements: List of buttons, inputs, links
        highlight_elements: Optional list of elements to highlight (e.g., newly appeared)
    """
    
    # Create a set of highlighted elements for quick lookup
    highlighted_set = set()
    if highlight_elements:
        for elem in highlight_elements:
            highlighted_set.add(f"{elem.get('type')}:{elem.get('text', '')}")
    
    # Build interactive elements section
    elements_text = "INTERACTIVE ELEMENTS:\n"
    
    if not interactive_elements:
        elements_text += "- (No interactive elements found)\n"
    else:
        # Group by type for readability
        buttons = [e for e in interactive_elements if e.get("type") == "button"]
        inputs = [e for e in interactive_elements if e.get("type") == "input"]
        links = [e for e in interactive_elements if e.get("type") == "link"]
        
        if inputs:
            elements_text += "\nInputs (forms, text fields):\n"
            for inp in inputs[:25]:  # Increased limit for form fields
                input_type = inp.get("input_type", "text")
                text = inp.get('text', '')
                elem_key = f"input:{text}"
                
                # Mark new elements with a special indicator
                new_marker = " 🆕" if elem_key in highlighted_set else ""
                
                # Add visibility info if available
                visibility = ""
                if inp.get("is_visible") is False:
                    visibility = " (hidden)"
                elif inp.get("is_password"):
                    visibility = " (password field)"
                    
                elements_text += f"  - Input ({input_type}): \"{text}\"{visibility}{new_marker}\n"
        
        if buttons:
            elements_text += "\nButtons:\n"
            for btn in buttons[:25]:
                text = btn.get('text', '')
                elem_key = f"button:{text}"
                new_marker = " 🆕" if elem_key in highlighted_set else ""
                elements_text += f"  - Button: \"{text}\"{new_marker}\n"
        
        if links:
            elements_text += "\nLinks:\n"
            for link in links[:20]:
                text = link.get('text', '')
                elem_key = f"link:{text}"
                new_marker = " 🆕" if elem_key in highlighted_set else ""
                elements_text += f"  - Link: \"{text}\"{new_marker}\n"
    
    # Truncate visible text to avoid token limits
    max_text_length = 4000
    truncated_text = visible_text
    if len(visible_text) > max_text_length:
        truncated_text = visible_text[:max_text_length] + "\n... (truncated)"
    
    # Build final serialization
    serialized = f"""URL: {url}

{elements_text}

VISIBLE TEXT (truncated to {max_text_length} chars):
{truncated_text}
"""
    
    return serialized


def get_element_summary(elements: List[Dict]) -> List[str]:
    """Get a brief summary of elements for history tracking."""
    summary = []
    for elem in elements[:5]:  # Limit to first 5
        elem_type = elem.get("type", "unknown")
        text = elem.get("text", "")[:30]  # Truncate long text
        summary.append(f"{elem_type}: '{text}'")
    return summary

