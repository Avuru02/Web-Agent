"""
Browser Controller - Generic Playwright wrapper.

🚨 CRITICAL: All methods must be GENERIC and work on any web app.
No app-specific logic allowed.
"""

from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
from typing import List, Dict, Optional
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
        """
        if not self.page:
            raise RuntimeError("Browser not launched. Call launch() first.")
        
        elements = []
        
        try:
            # Get all buttons
            buttons = self.page.locator("button, [role='button'], a[role='button']").all()
            for button in buttons:
                try:
                    text = button.inner_text(timeout=1000).strip()
                    if text:
                        elements.append({"type": "button", "text": text})
                except:
                    # Try aria-label if no text
                    try:
                        aria_label = button.get_attribute("aria-label")
                        if aria_label:
                            elements.append({"type": "button", "text": aria_label})
                    except:
                        pass
            
            # Get all inputs
            inputs = self.page.locator("input, textarea, [role='textbox']").all()
            for input_elem in inputs:
                try:
                    placeholder = input_elem.get_attribute("placeholder")
                    label = input_elem.get_attribute("aria-label")
                    input_type = input_elem.get_attribute("type") or "text"
                    
                    if placeholder:
                        elements.append({"type": "input", "text": placeholder, "input_type": input_type})
                    elif label:
                        elements.append({"type": "input", "text": label, "input_type": input_type})
                except:
                    pass
            
            # Get all links
            links = self.page.locator("a[href]").all()
            for link in links:
                try:
                    text = link.inner_text(timeout=1000).strip()
                    if text:
                        elements.append({"type": "link", "text": text})
                except:
                    pass
                    
        except Exception as e:
            print(f"Error getting interactive elements: {e}")
            
        return elements
        
    def click_by_text(self, text: str):
        """
        Find ANY element containing text and click it.
        Uses natural language text, not CSS selectors.
        GENERIC - works on any page.
        """
        if not self.page:
            raise RuntimeError("Browser not launched. Call launch() first.")
        
        try:
            # Try exact match first
            try:
                self.page.get_by_text(text, exact=True).first.click(timeout=10000)
                return
            except:
                pass
            
            # Try partial match
            try:
                self.page.get_by_text(text, exact=False).first.click(timeout=10000)
                return
            except:
                pass
            
            # Try role-based with text
            try:
                self.page.get_by_role("button", name=text, exact=False).first.click(timeout=10000)
                return
            except:
                pass
            
            # Try link
            try:
                self.page.get_by_role("link", name=text, exact=False).first.click(timeout=10000)
                return
            except:
                pass
            
            raise Exception(f"Could not find element with text: {text}")
            
        except Exception as e:
            print(f"Error clicking by text '{text}': {e}")
            raise
            
    def fill_input(self, label: str, value: str):
        """
        Find ANY input by placeholder or aria-label and fill it.
        Uses accessible labels, not IDs.
        GENERIC - works on any page.
        """
        if not self.page:
            raise RuntimeError("Browser not launched. Call launch() first.")
        
        try:
            # Try by placeholder
            try:
                self.page.get_by_placeholder(label, exact=False).first.fill(value, timeout=10000)
                return
            except:
                pass
            
            # Try by label
            try:
                self.page.get_by_label(label, exact=False).first.fill(value, timeout=10000)
                return
            except:
                pass
            
            # Try by role textbox
            try:
                self.page.get_by_role("textbox", name=label, exact=False).first.fill(value, timeout=10000)
                return
            except:
                pass
            
            raise Exception(f"Could not find input with label/placeholder: {label}")
            
        except Exception as e:
            print(f"Error filling input '{label}': {e}")
            raise
            
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
            
    def wait_for_change(self):
        """
        Wait for page to settle after action.
        GENERIC - standard Playwright waiting.
        """
        if not self.page:
            raise RuntimeError("Browser not launched. Call launch() first.")
        
        try:
            # Wait for network to be idle (with short timeout)
            self.page.wait_for_load_state("networkidle", timeout=3000)
        except:
            # If networkidle times out, just wait a bit
            time.sleep(0.5)
            
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

