# Quick Start Guide

## Installation

1. **Run the setup script:**
   ```bash
   python setup.py
   ```

   Or manually:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

2. **Configure your API key:**
   - Copy `.env.example` to `.env` (or create `.env` manually)
   - Add your OpenAI API key:
     ```
     OPENAI_API_KEY=sk-your-key-here
     ```

3. **Update task URLs:**
   - Edit `scripts/run_task.py` and update the URLs in the `TASKS` dictionary with your actual workspace/database links

## Running Your First Task

```bash
python scripts/run_task.py notion create_page
```

This will:
- Launch a browser (visible by default)
- Navigate to your Notion workspace
- Use the LLM to figure out how to create a page
- Take screenshots at each step
- Save results to `dataset/notion/create_page_[timestamp]/`

## Viewing Results

After a task completes, check the output directory:
```
dataset/notion/create_page_20250101_120000/
├── step_00_initial.png
├── step_00_before.png
├── step_00_after.png
├── step_01_before.png
├── step_01_after.png
└── trace.json
```

The `trace.json` file contains the complete execution trace with all actions taken.

## Adding New Tasks

To add a new task, edit `scripts/run_task.py`:

```python
TASKS = {
    "your_app": {
        "your_task": {
            "url": "https://your-app.com/starting-page",
            "description": "Natural language description of what to do"
        }
    }
}
```

Then run:
```bash
python scripts/run_task.py your_app your_task
```

**Remember**: The agent figures out HOW to accomplish the task - you just provide the WHAT (description) and WHERE (URL).

## Running in Headless Mode

To run without showing the browser window:

```bash
python scripts/run_task.py notion create_page --headless
```

## Troubleshooting

### "OPENAI_API_KEY not found"
- Make sure you created `.env` file with your API key
- Check that the key is correct

### "Browser doesn't launch"
- Run: `playwright install chromium`

### Actions fail to find elements
- Check the screenshots to see what's actually on the page
- The LLM may need more context - try being more specific in your task description
- Some pages may require login first - navigate to a logged-in state before running the task

