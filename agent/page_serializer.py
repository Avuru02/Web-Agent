"""
Page Serializer - Convert page state into LLM-friendly format.

🚨 CRITICAL: Must work for ANY web app. No app-specific parsing.
"""

from typing import List, Dict


def serialize_page(url: str, visible_text: str, interactive_elements: List[Dict]) -> str:
    """
    Returns a string representation of the page state for the LLM.
    
    MUST BE APP-AGNOSTIC: This format should work whether you're on
    Notion, Linear, Asana, or a completely new app.
    """
    
    # Build interactive elements section
    elements_text = "INTERACTIVE ELEMENTS:\n"
    
    if not interactive_elements:
        elements_text += "- (No interactive elements found)\n"
    else:
        # Group by type for readability
        buttons = [e for e in interactive_elements if e.get("type") == "button"]
        inputs = [e for e in interactive_elements if e.get("type") == "input"]
        links = [e for e in interactive_elements if e.get("type") == "link"]
        
        if buttons:
            elements_text += "\nButtons:\n"
            for btn in buttons[:20]:  # Limit to first 20 to avoid overwhelming
                elements_text += f"  - Button: \"{btn.get('text', '')}\"\n"
        
        if inputs:
            elements_text += "\nInputs:\n"
            for inp in inputs[:20]:
                input_type = inp.get("input_type", "text")
                elements_text += f"  - Input ({input_type}): \"{inp.get('text', '')}\"\n"
        
        if links:
            elements_text += "\nLinks:\n"
            for link in links[:20]:
                elements_text += f"  - Link: \"{link.get('text', '')}\"\n"
    
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

