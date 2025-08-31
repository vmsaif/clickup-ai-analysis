# ClickUp Task Analysis with AI

Analyze ClickUp tasks using Google's Gemini AI to detect time estimation issues, productivity patterns, and potential time padding.

## Features

- Fetches tasks from ClickUp API with date range and status filtering
- Analyzes day-by-day task breakdowns
- Uses Gemini 2.5 Pro to detect:
  - Unrealistic time estimates
  - Time padding patterns
  - Missing estimates
  - Vague task descriptions
- Generates markdown reports with specific questions for suspicious tasks

## Setup

1. Install dependencies:
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

Or using the existing venv:
```bash
source .venv/bin/activate
```

2. Create a `.env` file (copy from `.env.example`):
```bash
cp .env.example .env
```

3. Add your API keys to `.env`:
```
CLICKUP_API_KEY=your_clickup_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
```

## Usage

### Quick Start

```bash
source .venv/bin/activate
python main.py
```

### Configuration

Edit the configuration in `main.py`:

```python
USERNAME = "Istiak"  # Partial name to search for user
DAYS_BACK = 7  # How many days back to fetch tasks
STATUS_FILTER = "completed"  # Filter: "completed", "open", or "all"
```

### Output

The script generates:
- `output/{username}_analysis.md` - AI analysis report in markdown
- `output/{username}_data.json` - Raw task data and structured output

## Files

- `main.py` - Main entry point with configuration
- `user_task_analyzer.py` - ClickUp API client library
- `genai_analyzer_simple.py` - Simple Gemini AI analyzer
- `analyze_with_genai_structured.py` - Alternative runner (deprecated, use main.py)

## Example Output

The AI analysis will identify issues like:

```
ASK USER: Arbor Ai Studio Social Complete (8.0 hours) - 
An 8-hour estimate for a task this vague is a red flag for time padding. 
What specific deliverables were produced?

ASK USER: Covergen Generated Coverletter Review (0.5 hours) - 
Can you realistically review 10 cover letters in only 30 minutes (3 minutes per letter)?
```

## API Limits

- ClickUp Free Plan: 100 requests per minute
- The script respects rate limits automatically

## Requirements

- Python 3.7+
- ClickUp API key (personal token)
- Google Gemini API key