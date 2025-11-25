# Softlight Agent

An autonomous web navigation agent that uses LLM reasoning to navigate any web application without hardcoded workflows.

## Overview

The Softlight Agent is a general-purpose web automation tool that:

- Takes a natural language task + starting URL
- Uses an LLM (GPT-4) to decide actions step-by-step
- Navigates a live browser via Playwright
- Captures screenshots of each UI state (including non-URL states like modals)
- Outputs a structured dataset of the workflow

**Key Insight**: Screenshot after every action to capture all UI states, regardless of URL changes.

## 🚨 Critical Requirement: NO HARDCODING

The agent must be generalizable and work on any web app it hasn't seen before. It relies on the LLM to reason about page content dynamically, not on predefined selectors or workflows.

### What "No Hardcoding" Means

❌ **NEVER DO THIS:**
- Hardcoded selectors: `if app_name == "notion": browser.click("#new-page-button")`
- Hardcoded workflows: `if task == "create_project": ...`
- App-specific logic: `if "linear.app" in url: do_linear_specific_thing()`

✅ **DO THIS INSTEAD:**
- Generic actions based on LLM decisions
- Use natural language text to find elements: `browser.click_by_text("New Project")`
- Let the LLM figure out the workflow dynamically

## Project Structure

```
softlight-agent/
├── README.md
├── requirements.txt
├── .env                          # API keys
├── agent/
│   ├── __init__.py
│   ├── browser_controller.py    # Playwright wrapper - GENERIC ACTIONS ONLY
│   ├── page_serializer.py       # Converts page to LLM-friendly format - APP AGNOSTIC
│   ├── navigation_agent.py      # LLM decision-making - NO APP LOGIC
│   ├── orchestrator.py          # Main execution loop - WORKS FOR ANY APP
├── dataset/
│   ├── notion/
│   │   └── [task_timestamp]/
│   │       ├── step_00.png
│   │       ├── step_01.png
│   │       └── trace.json
│   └── linear/
├── scripts/
│   └── run_task.py              # CLI entry point - ONLY CONFIGS, NO LOGIC
└── tasks.md                     # Task descriptions
```

## Installation

1. **Clone the repository** (or create the project structure)

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

3. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env and add your OPENAI_API_KEY
   ```

## Usage

### Running a Task

```bash
python scripts/run_task.py <app_name> <task_name> [--headless]
```

**Example:**
```bash
python scripts/run_task.py notion create_page
```

### Available Tasks

See `tasks.md` and `scripts/run_task.py` for available tasks. To add a new task:

1. Add the task configuration to `TASKS` dictionary in `scripts/run_task.py`
2. Update `tasks.md` with the task description

**Important**: The task configuration only stores the URL and description. The agent figures out how to accomplish the task dynamically.

## How It Works

1. **Browser Controller** (`browser_controller.py`): Generic Playwright wrapper with simple actions (click, type, press) that work on any web app.

2. **Page Serializer** (`page_serializer.py`): Converts the current page state into a text format the LLM can understand, including:
   - Current URL
   - Interactive elements (buttons, inputs, links)
   - Visible text

3. **Navigation Agent** (`navigation_agent.py`): LLM-powered decision maker that:
   - Receives the task description, current page state, and action history
   - Decides the next action (click, type, press, wait, finish)
   - Returns structured JSON action

4. **Orchestrator** (`orchestrator.py`): Main execution loop that:
   - Launches browser and navigates to start URL
   - For each step:
     - Serializes current page
     - Asks LLM for next action
     - Takes screenshot BEFORE action
     - Executes action
     - Waits for page to settle
     - Takes screenshot AFTER action
     - Logs step to history
   - Saves trace.json with all step metadata

## Output Format

Each task execution creates a directory in `dataset/{app_name}/{task_name}_{timestamp}/` containing:

- `step_00_initial.png`: Initial page state
- `step_00_before.png`: State before first action
- `step_00_after.png`: State after first action
- `step_01_before.png`: State before second action
- ... (and so on)
- `trace.json`: Complete execution trace with all actions and metadata

### trace.json Structure

```json
{
  "task_description": "Create a new page titled 'Softlight Demo'",
  "start_url": "https://notion.so/...",
  "app_name": "notion",
  "task_name": "create_page",
  "timestamp": "20250101_120000",
  "total_steps": 5,
  "steps": [
    {
      "step": 0,
      "url": "https://notion.so/...",
      "action": {"action": "click", "target_text": "New page"},
      "screenshot_before": "step_00_before.png",
      "screenshot_after": "step_00_after.png",
      "success": true
    }
  ]
}
```

## Testing Generalizability

**The Test**: Could your agent handle a NEW app (e.g., Asana, ClickUp) without changing ANY code?

- ✅ If the answer is "yes, just give it a new URL and task description", you've succeeded.
- ❌ If the answer is "I'd need to add Asana-specific logic", you've hardcoded something.

## Key Design Principles

1. **Text-based selectors only**: Use `page.get_by_text()`, `page.get_by_placeholder()`, `page.get_by_label()` - never CSS/XPath selectors.

2. **LLM decides everything**: Don't tell it "first click New, then fill Name field" - just give it the task and let it figure out the steps.

3. **Simple action vocabulary**: `click`, `type`, `press` work on any web app. Don't add app-specific actions.

4. **App-agnostic page serialization**: Extract visible text and interactive elements generically, without app-specific parsing.

## Troubleshooting

### Browser doesn't launch
- Make sure Playwright browsers are installed: `playwright install chromium`

### LLM returns invalid JSON
- The agent includes error handling and will retry with a safe default action
- Check your OpenAI API key is set correctly in `.env`

### Actions fail to find elements
- The agent uses multiple fallback strategies (exact text, partial text, role-based)
- Check the screenshots to see what elements are actually visible
- The LLM may need to adjust its target text based on what's actually on the page

## License

This project is part of the Softlight assignment.

