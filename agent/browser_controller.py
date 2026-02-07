"""
Browser Controller - Generic Playwright wrapper.

🚨 CRITICAL: All methods must be GENERIC and work on any web app.
No app-specific logic allowed.
"""

from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
from typing import List, Dict, Optional, Callable
import time


class BrowserController:
    """Generic browser controller using Playwright."""
    
    def __init__(self, headless: bool = False):
        """Initialize browser controller."""
        self.playwright = sync_playwright().start()
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.headless = headless
        
    def launch(self):
        """Launch browser and create context."""
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        self.context = self.browser.new_context(
            viewport={"width": 1920, "height": 1080}
        )
        self.page = self.context.new_page()
        
    def goto(self, url: str):
        """
        Navigate to URL and wait for network idle.
        GENERIC - works for any URL.
        """
        if not self.page:
            raise RuntimeError("Browser not launched. Call launch() first.")
        
        try:
            self.page.goto(url, wait_until="networkidle", timeout=30000)
        except Exception as e:
            # If networkidle times out, still proceed
            print(f"Warning: Network idle timeout, but page may have loaded: {e}")
            pass
            
    def screenshot(self, path: str):
        """
        Take full-page screenshot.
        GENERIC - works for any page.
        """
        if not self.page:
            raise RuntimeError("Browser not launched. Call launch() first.")
        
        try:
            self.page.screenshot(path=path, full_page=True)
        except Exception as e:
            print(f"Error taking screenshot: {e}")
            raise
            
    def get_text_snapshot(self) -> str:
        """
        Extract visible text from page.
        GENERIC - no app-specific parsing.
        """
        if not self.page:
            raise RuntimeError("Browser not launched. Call launch() first.")
        
        try:
            # Get text from body element
            text = self.page.locator("body").inner_text(timeout=5000)
            return text
        except Exception as e:
            print(f"Error getting text snapshot: {e}")
            return ""
            
    def get_interactive_elements(self) -> List[Dict]:
        """
        Extract ALL buttons, inputs, and other interactive elements with labels/text.
        Return format: [{"type": "button", "text": "Create"}, ...]
        GENERIC - finds elements by role, not by app-specific selectors.
        
        Enhanced to capture more element metadata for better LLM decisions.
        """
        if not self.page:
            raise RuntimeError("Browser not launched. Call launch() first.")
        
        elements = []
        seen_texts = set()  # Deduplicate elements with same text
        
        try:
            # Get all buttons (including submit buttons)
            button_selectors = "button, [role='button'], a[role='button'], input[type='submit'], input[type='button']"
            buttons = self.page.locator(button_selectors).all()
            for button in buttons:
                try:
                    # Check if visible
                    if not button.is_visible():
                        continue
                        
                    text = button.inner_text(timeout=1000).strip()
                    if not text:
                        # Try value for input[type=submit]
                        text = button.get_attribute("value") or ""
                    if not text:
                        # Try aria-label
                        text = button.get_attribute("aria-label") or ""
                    
                    if text and text not in seen_texts:
                        seen_texts.add(text)
                        elements.append({
                            "type": "button", 
                            "text": text,
                            "is_visible": True
                        })
                except:
                    pass
            
            # Get all inputs with enhanced metadata
            input_selectors = "input, textarea, [role='textbox'], [contenteditable='true']"
            inputs = self.page.locator(input_selectors).all()
            for input_elem in inputs:
                try:
                    # Check visibility
                    is_visible = input_elem.is_visible()
                    
                    # Skip hidden inputs that aren't password fields
                    input_type = input_elem.get_attribute("type") or "text"
                    if not is_visible and input_type != "password":
                        continue
                    
                    placeholder = input_elem.get_attribute("placeholder")
                    label = input_elem.get_attribute("aria-label")
                    name = input_elem.get_attribute("name")
                    
                    # Try to find associated label element
                    elem_id = input_elem.get_attribute("id")
                    label_text = None
                    if elem_id:
                        try:
                            label_elem = self.page.locator(f"label[for='{elem_id}']")
                            if label_elem.count() > 0:
                                label_text = label_elem.first.inner_text(timeout=500).strip()
                        except:
                            pass
                    
                    # Determine best text identifier
                    text = placeholder or label or label_text or name or ""
                    
                    # For password fields, always include them
                    is_password = input_type == "password"
                    
                    if text or is_password:
                        elem_key = f"{text}:{input_type}"
                        if elem_key not in seen_texts:
                            seen_texts.add(elem_key)
                            elements.append({
                                "type": "input", 
                                "text": text if text else f"[{input_type} field]",
                                "input_type": input_type,
                                "is_visible": is_visible,
                                "is_password": is_password
                            })
                except:
                    pass
            
            # Get all links
            links = self.page.locator("a[href]").all()
            for link in links:
                try:
                    if not link.is_visible():
                        continue
                        
                    text = link.inner_text(timeout=1000).strip()
                    if text and text not in seen_texts and len(text) < 100:  # Skip very long link texts
                        seen_texts.add(text)
                        elements.append({"type": "link", "text": text})
                except:
                    pass
            
            # Get select dropdowns
            selects = self.page.locator("select").all()
            for select in selects:
                try:
                    if not select.is_visible():
                        continue
                    label = select.get_attribute("aria-label") or select.get_attribute("name") or ""
                    if label and label not in seen_texts:
                        seen_texts.add(label)
                        elements.append({"type": "select", "text": label})
                except:
                    pass
                    
        except Exception as e:
            print(f"Error getting interactive elements: {e}")
            
        return elements
    
    def _retry_action(
        self, 
        action_fn: Callable, 
        max_retries: int = 3, 
        wait_between: float = 0.5
    ) -> bool:
        """
        Retry an action with exponential backoff.
        Useful for dynamic content that may take time to appear.
        
        Returns True if action succeeded, False otherwise.
        """
        for attempt in range(max_retries):
            try:
                action_fn()
                return True
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = wait_between * (2 ** attempt)
                    print(f"Retry {attempt + 1}/{max_retries} after {wait_time}s: {e}")
                    time.sleep(wait_time)
                else:
                    raise
        return False
        
    def click_by_text(self, text: str, retry: bool = True):
        """
        Find ANY element containing text and click it.
        Uses natural language text, not CSS selectors.
        GENERIC - works on any page.
        
        Args:
            text: Text to find and click
            retry: Whether to retry if element not immediately found
        """
        if not self.page:
            raise RuntimeError("Browser not launched. Call launch() first.")
        
        strategies = [
            # Strategy 1: Exact text match
            lambda: self.page.get_by_text(text, exact=True).first.click(timeout=5000),
            # Strategy 2: Partial text match
            lambda: self.page.get_by_text(text, exact=False).first.click(timeout=5000),
            # Strategy 3: Button by name
            lambda: self.page.get_by_role("button", name=text, exact=False).first.click(timeout=5000),
            # Strategy 4: Link by name
            lambda: self.page.get_by_role("link", name=text, exact=False).first.click(timeout=5000),
            # Strategy 5: Any clickable by text content
            lambda: self.page.locator(f"//*[contains(text(), '{text}')]").first.click(timeout=5000),
            # Strategy 6: By aria-label
            lambda: self.page.locator(f"[aria-label*='{text}']").first.click(timeout=5000),
        ]
        
        last_error = None
        for i, strategy in enumerate(strategies):
            try:
                strategy()
                return
            except Exception as e:
                last_error = e
                continue
        
        # If all strategies failed, maybe wait for element to appear
        if retry:
            print(f"Element '{text}' not found, waiting for it to appear...")
            time.sleep(1)
            for strategy in strategies[:3]:  # Try first 3 strategies again
                try:
                    strategy()
                    return
                except:
                    continue
        
        raise Exception(f"Could not find element with text: {text}. Last error: {last_error}")
            
    def fill_input(self, label: str, value: str, retry: bool = True):
        """
        Find ANY input by placeholder or aria-label and fill it.
        Uses accessible labels, not IDs.
        GENERIC - works on any page.
        
        Args:
            label: Label/placeholder to find
            value: Value to fill
            retry: Whether to retry if field not immediately found
        """
        if not self.page:
            raise RuntimeError("Browser not launched. Call launch() first.")
        
        strategies = [
            # Strategy 1: By placeholder
            lambda: self.page.get_by_placeholder(label, exact=False).first.fill(value, timeout=5000),
            # Strategy 2: By label
            lambda: self.page.get_by_label(label, exact=False).first.fill(value, timeout=5000),
            # Strategy 3: By role textbox
            lambda: self.page.get_by_role("textbox", name=label, exact=False).first.fill(value, timeout=5000),
            # Strategy 4: By aria-label attribute
            lambda: self.page.locator(f"input[aria-label*='{label}']").first.fill(value, timeout=5000),
            # Strategy 5: By name attribute
            lambda: self.page.locator(f"input[name*='{label.lower()}']").first.fill(value, timeout=5000),
            # Strategy 6: By placeholder contains
            lambda: self.page.locator(f"input[placeholder*='{label}']").first.fill(value, timeout=5000),
            # Strategy 7: Visible password field (for password inputs)
            lambda: self.page.locator("input[type='password']:visible").first.fill(value, timeout=5000) if 'password' in label.lower() else (_ for _ in ()).throw(Exception("Not a password")),
        ]
        
        last_error = None
        for strategy in strategies:
            try:
                strategy()
                return
            except Exception as e:
                last_error = e
                continue
        
        # If all strategies failed, maybe wait for element to appear
        if retry:
            print(f"Input '{label}' not found, waiting for it to appear...")
            time.sleep(1)
            for strategy in strategies[:4]:  # Try first 4 strategies again
                try:
                    strategy()
                    return
                except:
                    continue
        
        raise Exception(f"Could not find input with label/placeholder: {label}. Last error: {last_error}")
            
    def press_key(self, key: str):
        """
        Press keyboard key (e.g., "Enter", "Escape").
        GENERIC - works on any page.
        """
        if not self.page:
            raise RuntimeError("Browser not launched. Call launch() first.")
        
        try:
            self.page.keyboard.press(key)
        except Exception as e:
            print(f"Error pressing key '{key}': {e}")
            raise
    
    def scroll(self, direction: str = "down", amount: int = 300):
        """
        Scroll the page.
        
        Args:
            direction: "down" or "up"
            amount: Pixels to scroll
        """
        if not self.page:
            raise RuntimeError("Browser not launched. Call launch() first.")
        
        try:
            if direction == "down":
                self.page.evaluate(f"window.scrollBy(0, {amount})")
            else:
                self.page.evaluate(f"window.scrollBy(0, -{amount})")
        except Exception as e:
            print(f"Error scrolling {direction}: {e}")
            raise
            
    def wait_for_change(self, timeout: float = 3.0):
        """
        Wait for page to settle after action.
        GENERIC - standard Playwright waiting.
        
        Args:
            timeout: Max time to wait in seconds
        """
        if not self.page:
            raise RuntimeError("Browser not launched. Call launch() first.")
        
        try:
            # Wait for network to be idle (with short timeout)
            self.page.wait_for_load_state("networkidle", timeout=int(timeout * 1000))
        except:
            # If networkidle times out, just wait a bit
            time.sleep(0.5)
    
    def wait_for_element(self, text: str, timeout: float = 5.0) -> bool:
        """
        Wait for an element with specific text to appear.
        
        Args:
            text: Text to wait for
            timeout: Max time to wait in seconds
            
        Returns:
            True if element appeared, False otherwise
        """
        if not self.page:
            raise RuntimeError("Browser not launched. Call launch() first.")
        
        try:
            self.page.get_by_text(text).first.wait_for(timeout=int(timeout * 1000))
            return True
        except:
            return False
            
    def get_current_url(self) -> str:
        """Get current page URL."""
        if not self.page:
            raise RuntimeError("Browser not launched. Call launch() first.")
        return self.page.url
        
    def close(self):
        """Close browser gracefully."""
        try:
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
        except Exception as e:
            print(f"Error closing browser: {e}")

