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

3. **Configure login credentials (optional):**
   - Add to your `.env` file:
     ```
     WEB_AGENT_USERNAME=your-email@example.com
     WEB_AGENT_PASSWORD=your-password
     ```
   - Or pass via command line: `--username` and `--password`

4. **Update task URLs:**
   - Edit `scripts/run_task.py` and update the URLs in the `TASKS` dictionary with your actual workspace/database links

## Running Your First Task

```bash
# Run a predefined task
python scripts/run_task.py notion create_page

# Run a custom task
python scripts/run_task.py --custom --url "https://example.com" --description "Find the contact page"
```

This will:
- Launch a browser (visible by default)
- Navigate to your Notion workspace
- Use the LLM to figure out how to create a page
- Take screenshots at each step
- Save results to `dataset/notion/create_page_[timestamp]/`

## Login Handling

The agent now intelligently handles multi-step login flows:

### Automatic Features:
- **Multi-step form detection**: Recognizes when password fields appear after username submission
- **Loop detection**: Prevents getting stuck in repeated failed actions
- **Page change tracking**: Detects when new elements appear (like password fields)
- **Smart retries**: Automatically retries with different strategies if an element isn't found

### Providing Credentials:

**Option 1: Environment Variables (Recommended)**
```bash
# In your .env file
WEB_AGENT_USERNAME=your-email@example.com
WEB_AGENT_PASSWORD=your-password
```

**Option 2: Command Line**
```bash
python scripts/run_task.py notion create_page --username "email@example.com" --password "pass123"
```

**Option 3: In Task Description**
Include credentials directly in your task description (not recommended for sensitive passwords).

## Command Line Options

```bash
python scripts/run_task.py [app] [task] [options]

Options:
  --headless          Run browser in headless mode
  --max-steps N       Maximum steps (default: 20)
  --username USER     Username for login
  --password PASS     Password for login
  
Custom task:
  --custom            Run a custom task
  --url URL           Starting URL
  --description TEXT  Task description
```

## Examples

```bash
# Predefined task
python scripts/run_task.py notion create_page

# With credentials
python scripts/run_task.py linear create_issue --username "me@example.com" --password "secret"

# Custom task
python scripts/run_task.py --custom --url "https://github.com/trending" --description "Find the top Python repository"

# Headless with more steps
python scripts/run_task.py notion filter_database --headless --max-steps 30
```

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

The `trace.json` file contains the complete execution trace including:
- All actions taken
- Success/failure status for each step
- Elements that appeared/disappeared after each action
- Screenshots at each step

## Adding New Tasks

To add a new task, edit `scripts/run_task.py`:

```python
TASKS = {
    "your_app": {
        "your_task": {
            "url": "https://your-app.com/starting-page",
            "description": "Natural language description of what to do",
            "requires_login": True  # Optional: indicates login is needed
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

### Login is failing
- Check that credentials are set correctly (env vars or command line)
- Some sites have CAPTCHAs that block automation
- Try running in non-headless mode to see what's happening
- Check `trace.json` for detailed action history

### Agent is stuck in a loop
- The loop detection will automatically try different approaches
- If it still fails, the agent will stop after 5 consecutive failures
- Increase `--max-steps` if the task is complex but making progress

