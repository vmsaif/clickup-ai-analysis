from google import genai
from google.genai import types
import json
import os
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from typing import Dict, Any

load_dotenv()


class GenAIAnalyzer:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("Gemini API key is required. Set it in .env file as GEMINI_API_KEY")

        self.client = genai.Client(api_key=self.api_key)
        self.model_name = 'models/gemini-2.5-pro'

        # System instructions for task analysis
        self.system_instructions = [
            'You are an expert productivity and time management analyst.',
            f'Today\'s date is {datetime.now().strftime("%Y-%m-%d")}. Use this for any current date references.',
            'Your mission is to analyze ClickUp task data for potential time estimation issues, productivity patterns, and signs of dishonesty.',
            'Be direct and specific in identifying problems.',
            'CRITICAL: Calculate and compare Total Estimated Time Allocated (what employee claimed) vs Total Actual Estimated Time (what tasks should realistically take).',
            'IMPORTANT: Always include the date (YYYY-MM-DD format) beside task names when referencing them.',
            'For the "QUESTIONS REQUIRING EMPLOYEE RESPONSE" section, use a single "ASK USER:" header followed by numbered questions.',
            'Focus on identifying time padding, unrealistic estimates, and tasks that need clarification.',
            'Calculate average daily hours based on both allocated and actual estimates, excluding weekends.',
            'Look for patterns of overestimation, underestimation, and missing descriptions.',
            'Be especially critical of vague task names with high time estimates.',
            'Balance your analysis by highlighting both positive findings ("The Goods") and issues that need attention.',
            'Identify collaborative tasks (those with multiple assignees or watchers) and note them separately.'
        ]

    async def analyze_async(self, prompt: str, temperature: float = 0.7) -> str:
        """
        Single method to analyze any prompt with the configured model.
        """
        try:
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instructions,
                    temperature=temperature,
                    max_output_tokens=8192,
                )
            )
            return response.text
        except Exception as e:
            error_msg = f"Error analyzing: {str(e)}"
            print(f"❌ Gemini API Error: {error_msg}")
            return error_msg

    def analyze(self, prompt: str, temperature: float = 0.7) -> str:
        """
        Synchronous wrapper for analyze_async.
        """
        try:
            return asyncio.run(self.analyze_async(prompt, temperature))
        except Exception as e:
            print(f"Error in analyze: {str(e)}")
            return None

    def save_markdown(self, content: str, output_file: str):
        """
        Save content as markdown file.
        """
        os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)

        # Ensure .md extension
        if not output_file.endswith('.md'):
            output_file = output_file.replace('.txt', '.md').replace('.json', '.md')
            if not output_file.endswith('.md'):
                output_file += '.md'

        with open(output_file, 'w') as f:
            f.write(content)

        print(f"Report saved to: {output_file}")
        return output_file


# Example usage function
def analyze_clickup_data(structured_text: str, user_info: Dict[str, Any] = None, days_back: int = None) -> str:
    """
    Helper function to analyze ClickUp data with proper prompt formatting.
    """
    analyzer = GenAIAnalyzer()
    
    # Determine the period type based on days_back
    if days_back:
        if days_back <= 7:
            period_type = f"{days_back}-DAY"
        elif days_back <= 14:
            period_type = "TWO-WEEK"
        elif days_back <= 31:
            period_type = "MONTHLY"
        else:
            period_type = f"{days_back}-DAY"
    else:
        period_type = "PERIOD"

    prompt = f"""
    Generate a {period_type} EMPLOYEE AUDIT REPORT for '{user_info.get('username', 'Unknown') if user_info else 'Unknown'}' based on their ClickUp task data.

    IMPORTANT: Task descriptions are limited to 1000 characters.

    TASK DATA:
    {structured_text}

    Create a professional audit report with the following sections:

    # {period_type} EMPLOYEE PRODUCTIVITY AUDIT REPORT

    ## EMPLOYEE INFORMATION
    - **Name:** {user_info.get('username', 'Unknown') if user_info else 'Unknown'}
    - **Email:** {user_info.get('email', 'Unknown') if user_info else 'Unknown'}
    - **Review Period:** [Extract date range from the task data provided]
    - **Report Generated:** {datetime.now().strftime('%Y-%m-%d')}

    ## EXECUTIVE SUMMARY
    Provide a professional 3-4 sentence overview of the employee's performance, highlighting key strengths, concerns, and overall productivity assessment for the period.

    ## PRODUCTIVITY METRICS

    ### Overall Statistics
    - **Total Tasks Completed:** X
    - **Total Estimated Time Allocated (Employee):** X hours (sum of all task estimates provided)
    - **Total Actual Estimated Time (Auditor Assessment):** X hours (realistic time these tasks should take)
    - **Time Allocation Efficiency:** X% (actual/allocated * 100)
    - **Average Daily Hours (Based on Actual Estimate):** X hours (actual estimated time / working days)
    - **Average Daily Hours (Based on Employee Estimates):** X hours (allocated time / working days)
    - **Days with Activity:** X days
    - **Working Days (excluding weekends):** X days
    - **Tasks with Missing Estimates:** X (X%)

    ### Performance Indicators
    - **Most Productive Day:** [Date] - X hours
    - **Least Productive Day:** [Date] - X hours
    - **Consistency Score:** [High/Medium/Low] - Explanation
    - **Task Completion Rate:** X%

    ## TIME MANAGEMENT ANALYSIS

    ### 🟢 THE GOODS (Positive Findings)
    - **Well-Documented Tasks:** List tasks with clear descriptions and appropriate time estimates
    - **Efficient Completions:** Tasks completed within reasonable timeframes
    - **Collaborative Tasks:** Identify tasks that appear to be team efforts (multiple assignees, watchers, or coordination required)
    - **Good Practices:** Positive patterns observed in time management
    - **Consistent Work:** Days with steady productivity
    - **Proper Planning:** Tasks with realistic time estimates

    ### 🔴 THE ISSUES (Areas of Concern)
    - **Time Estimation Problems:**
      - Overestimated tasks (potential padding)
      - Underestimated tasks (poor planning)
      - Missing estimates (lack of planning)

    - **Task Definition Problems:**
      - Vague task descriptions
      - Generic task names
      - Lack of deliverable clarity
      
    - **Productivity Gaps:**
      - Days with unusually low activity
      - Unexplained time gaps
      - Holiday work patterns (if any)

    ## AUDIT FLAGS & COMPLIANCE ISSUES

    ### 🔴 Critical Issues
    Tasks requiring immediate management review:
    - **[Task Name] (Date: YYYY-MM-DD, X hours)** - Reason for concern

    ### 🟡 Moderate Concerns
    Tasks needing clarification:
    - **[Task Name] (Date: YYYY-MM-DD, X hours)** - Issue identified

    ### 🟢 Minor Issues
    Tasks with minor problems:
    - **[Task Name] (Date: YYYY-MM-DD)** - Suggestion for improvement

    ## QUESTIONS REQUIRING EMPLOYEE RESPONSE

    **ASK USER:**

    The following items require written explanation from the employee:

    1. **[Task Name] (Date: YYYY-MM-DD)** - Please explain why this task required X hours and provide detailed breakdown of work performed
    2. **[Task Name] (Date: YYYY-MM-DD)** - Please provide deliverables and clarify the scope of this task
    3. **Missing Time Estimates** - The following tasks lack time estimates: [List tasks with dates]. Please add appropriate estimates and explain the omission
    4. **Activity Gaps** - No tasks logged for [Date(s)]. Please clarify if these were holidays, days off, or provide explanation for absence

    ## RECOMMENDATIONS FOR MANAGEMENT

    ### Immediate Actions Required
    - Specific steps management should take

    ### Process Improvements
    - Suggestions for better oversight
    - Training needs identified

    ### Long-term Considerations
    - Pattern-based recommendations
    - Performance improvement plan suggestions

    ## DAILY ACTIVITY LOG

    Detailed breakdown for each day in the period:

    **[Date]** | Tasks: X | Hours: X
    - Key tasks completed
    - Any concerns or anomalies noted
    
    Note: Weekend days (Friday/Saturday) are marked accordingly in the data above.

    ## AUDIT CONCLUSION

    ### Overall Assessment
    [Professional assessment of employee's time tracking and productivity]

    ### Compliance Score
    [Score/Rating] - Explanation of rating

    ### Follow-up Actions
    - Next review date
    - Specific items to monitor
    - Documentation required

    ---

    **Auditor Notes:**
    - This is a {period_type.lower()} report covering {days_back if days_back else 'the specified'} days
    - Analysis includes both positive findings ("The Goods") and areas needing improvement ("The Issues")
    - Fridays and Saturdays are marked as holidays (Bangladesh schedule)
    - Any additional observations for HR/Management records

    Provide a professional, objective, and BALANCED analysis suitable for HR records and performance reviews. 
    IMPORTANT: Always highlight both the positive aspects AND the issues. Be specific with examples but maintain a constructive tone focused on improvement.
    Remember to acknowledge good work while also identifying areas that need attention.
    """

    return analyzer.analyze(prompt)


if __name__ == "__main__":
    # Example: Analyze from a JSON file
    import sys

    if len(sys.argv) > 1:
        input_file = sys.argv[1]

        if os.path.exists(input_file):
            with open(input_file, 'r') as f:
                data = json.load(f)

            # Extract structured output if available
            structured_text = data.get('structured_output_for_llm', str(data))
            user_info = data.get('user', {})

            print("Analyzing with GenAI...")
            result = analyze_clickup_data(structured_text, user_info)

            # Save result
            analyzer = GenAIAnalyzer()
            output_file = input_file.replace('.json', '_analysis.md')
            analyzer.save_markdown(result, output_file)

            print("\nAnalysis Preview:")
            print("=" * 80)
            print(result[:500])
            print("...")
        else:
            print(f"File not found: {input_file}")
    else:
        print("Usage: python genai_analyzer_simple.py <input_file.json>")