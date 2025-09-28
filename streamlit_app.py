#!/usr/bin/env python3
"""
ClickUp AI Analysis Dashboard
A Streamlit app for analyzing ClickUp tasks with AI-powered insights.
"""

import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import io
from user_task_analyzer import UserTaskAnalyzer
from genai_analyzer_simple import GenAIAnalyzer

load_dotenv()

st.set_page_config(
    page_title="ClickUp AI Analysis Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Default system prompt for AI analysis
DEFAULT_SYSTEM_PROMPT = """You are an expert productivity and time management analyst. Your mission is to analyze ClickUp task data for potential time estimation issues, productivity patterns, and signs of dishonesty.

Be direct and specific in identifying problems. Calculate and compare Total Estimated Time Allocated vs Total Actual Estimated Time (what tasks should realistically take).

Always include the date (YYYY-MM-DD format) beside task names when referencing them. For the "QUESTIONS REQUIRING EMPLOYEE RESPONSE" section, use a single "ASK USER:" header followed by numbered questions.

Focus on identifying time padding, unrealistic estimates, and tasks that need clarification. Calculate average daily hours based on both allocated and actual estimates, excluding weekends.

Look for patterns of overestimation, underestimation, and missing descriptions. Be especially critical of vague task names with high time estimates.

Balance your analysis by highlighting both positive findings and issues that need attention. Identify collaborative tasks (those with multiple assignees or watchers) and note them separately."""

DEFAULT_USER_PROMPT = """Analyze the following ClickUp task data for user: {username}
Period: Last {days_back} days

{structured_data}

Please provide a thorough analysis including:
1. Time estimation accuracy assessment
2. Productivity patterns and concerns
3. Specific tasks that need clarification
4. Questions requiring employee response
5. Summary and recommendations"""

@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_clickup_data(username, days_back, status_filter, team_id=None):
    """Fetch and process ClickUp data."""
    try:
        analyzer = UserTaskAnalyzer()

        if not team_id:
            teams = analyzer.get_teams()
            if not teams:
                return None, "No teams found"
            team_id = teams[0]["id"]

        user = analyzer.find_user_by_partial_name(username, team_id)
        if not user:
            return None, f"No user found matching '{username}'"

        from_date = datetime.now(timezone.utc) - timedelta(days=days_back)
        to_date = datetime.now(timezone.utc)

        all_tasks = []
        page = 0

        while True:
            params = {
                "assignees[]": [user["id"]],
                "include_closed": "true",
                "page": page,
                "date_updated_gt": str(int(from_date.timestamp() * 1000)),
                "date_updated_lt": str(int(to_date.timestamp() * 1000)),
                "subtasks": "true"
            }

            response = analyzer._make_request("GET", f"team/{team_id}/task", params=params)
            tasks = response.get("tasks", [])

            if not tasks:
                break

            if status_filter and "all" not in status_filter:
                filtered_tasks = []
                for task in tasks:
                    status_type = task.get("status", {}).get("type", "")
                    status_name = task.get("status", {}).get("status", "").lower()

                    if status_type == "closed" or status_name in [s.lower() for s in status_filter]:
                        filtered_tasks.append(task)

                tasks = filtered_tasks

            all_tasks.extend(tasks)

            if response.get("last_page", True):
                break
            page += 1

        time_analysis = analyzer.calculate_time_estimates(all_tasks, from_date, to_date)

        return {
            "user": user,
            "tasks": all_tasks,
            "time_analysis": time_analysis,
            "from_date": from_date,
            "to_date": to_date,
            "team_id": team_id
        }, None

    except Exception as e:
        return None, str(e)

def create_structured_output(data):
    """Create structured output for AI analysis."""
    output_buffer = io.StringIO()

    output_buffer.write("=" * 70 + "\n")
    output_buffer.write("TASK ANALYSIS DATA\n")
    output_buffer.write("=" * 70 + "\n")
    output_buffer.write(f"\n📅 Date Range: {data['from_date'].date()} to {data['to_date'].date()}\n")
    output_buffer.write(f"   Total Tasks: {data['time_analysis']['total_tasks']}\n")
    output_buffer.write(f"   Tasks with time estimates: {data['time_analysis']['tasks_with_estimates']}\n")
    output_buffer.write(f"   Total Estimated Time: {data['time_analysis']['total_estimate_hours']} hours\n")

    output_buffer.write("\n   Daily Breakdown:\n")

    current_date = data['from_date'].date()
    all_days = {}

    while current_date <= data['to_date'].date():
        date_str = str(current_date)
        day_of_week = current_date.weekday()
        is_weekend = day_of_week in [4, 5]
        weekend_day = "Friday" if day_of_week == 4 else "Saturday" if day_of_week == 5 else None

        hours = data['time_analysis']['daily_breakdown'].get(date_str, 0)

        day_tasks = []
        for task in data['tasks']:
            date_done = UserTaskAnalyzer().timestamp_to_datetime(task.get("date_done"))
            date_closed = UserTaskAnalyzer().timestamp_to_datetime(task.get("date_closed"))
            date_updated = UserTaskAnalyzer().timestamp_to_datetime(task.get("date_updated"))
            task_date = date_done or date_closed or date_updated

            if task_date and str(task_date.date()) == date_str:
                day_tasks.append(task)

        all_days[date_str] = {
            'hours': hours,
            'tasks': day_tasks,
            'is_weekend': is_weekend,
            'weekend_day': weekend_day
        }

        current_date += timedelta(days=1)

    for date_str in sorted(all_days.keys()):
        day_data = all_days[date_str]
        weekend_marker = f" (weekend-{day_data['weekend_day']})" if day_data['is_weekend'] else ""
        output_buffer.write(f"\n     {date_str}{weekend_marker}: Total {day_data['hours']} hours ({len(day_data['tasks'])} tasks)\n")

        for task in day_data['tasks']:
            task_name = task.get("name", "Unnamed")
            description = task.get("description", "")
            time_est = task.get("time_estimate", 0)
            est_hours = round(time_est / (1000 * 60 * 60), 2) if time_est else 0

            if est_hours > 0:
                output_buffer.write(f"        - {task_name}, Estimated time: {est_hours} hours\n")
            else:
                output_buffer.write(f"        - {task_name}, Estimated time: Not set\n")

            if description and description.strip():
                desc_cleaned = description.strip().replace('\n', ' ')
                if len(desc_cleaned) > 1000:
                    desc_lines = desc_cleaned[:1000] + "..."
                else:
                    desc_lines = desc_cleaned
                output_buffer.write(f"          Description: {desc_lines}\n")

    return output_buffer.getvalue()

def main():
    st.title("📊 ClickUp Task Analysis with AI")

    # Initialize session state
    if 'analysis_results' not in st.session_state:
        st.session_state.analysis_results = None
    if 'system_prompt' not in st.session_state:
        st.session_state.system_prompt = DEFAULT_SYSTEM_PROMPT
    if 'user_prompt' not in st.session_state:
        st.session_state.user_prompt = DEFAULT_USER_PROMPT
    if 'temperature' not in st.session_state:
        st.session_state.temperature = 0.7

    # Sidebar configuration
    with st.sidebar:
        # Logo at the top of sidebar
        st.logo("logo.svg")

        st.header("⚙️ Configuration")

        # API Keys check
        clickup_key = os.getenv("CLICKUP_API_KEY")
        gemini_key = os.getenv("GEMINI_API_KEY")

        if not clickup_key or not gemini_key:
            st.error("⚠️ API keys not configured!")
            st.info("Please set CLICKUP_API_KEY and GEMINI_API_KEY in your .env file")
            st.stop()

        # User input section
        st.subheader("🔍 Search Parameters")

        username = st.text_input(
            "Username (partial match)",
            value="Istiak",
            help="Enter partial name to search for user"
        )

        days_back = st.slider(
            "Days to analyze",
            min_value=1,
            max_value=90,
            value=25,
            help="Number of days back to fetch tasks"
        )

        status_options = ["completed", "done", "closed", "open", "in progress", "all"]
        status_filter = st.multiselect(
            "Task status filter",
            options=status_options,
            default=["completed", "done", "closed"],
            help="Select task statuses to include"
        )

        # AI Configuration section
        with st.expander("🤖 AI Configuration", expanded=False):
            # Option to reset to defaults
            if st.button("🔄 Reset to Defaults", use_container_width=True):
                st.session_state.system_prompt = DEFAULT_SYSTEM_PROMPT
                st.session_state.user_prompt = DEFAULT_USER_PROMPT
                st.session_state.temperature = 0.7
                st.rerun()

            # Temperature setting with user-friendly name
            st.subheader("Analysis Style")
            st.caption("Adjust how the AI analyzes: Precise (0) ← → Creative (1)")

            st.session_state.temperature = st.slider(
                "Analysis Style",
                min_value=0.0,
                max_value=1.0,
                value=st.session_state.temperature,
                step=0.1,
                format="%.1f",
                key="temperature_slider",
                label_visibility="collapsed",
                help="Lower values = more consistent and factual analysis. Higher values = more varied and creative insights."
            )

            # System Prompt
            st.subheader("System Prompt")
            st.caption("Define the AI's role and behavior")

            st.session_state.system_prompt = st.text_area(
                "System Prompt",
                value=st.session_state.system_prompt,
                height=250,
                key="system_prompt_input",
                label_visibility="collapsed"
            )

            # User Prompt
            st.subheader("User Prompt")
            st.caption("Use {username}, {days_back}, and {structured_data} as placeholders")

            st.session_state.user_prompt = st.text_area(
                "User Prompt",
                value=st.session_state.user_prompt,
                height=200,
                key="user_prompt_input",
                label_visibility="collapsed"
            )

        # Fetch data button
        fetch_button = st.button("🚀 Fetch & Analyze", type="primary", use_container_width=True)

    # Main content area
    if fetch_button:
        with st.spinner("Fetching data from ClickUp..."):
            data, error = fetch_clickup_data(username, days_back, status_filter)

            if error:
                st.error(f"Error: {error}")
                st.stop()

            st.session_state.clickup_data = data

        # Display user info
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("User", data['user']['username'])
        with col2:
            st.metric("Total Tasks", data['time_analysis']['total_tasks'])
        with col3:
            st.metric("Tasks with Estimates", data['time_analysis']['tasks_with_estimates'])
        with col4:
            st.metric("Total Hours", f"{data['time_analysis']['total_estimate_hours']:.1f}")

        # Create tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📈 Overview", "🤖 AI Analysis", "📋 Tasks", "📊 Daily Breakdown", "📄 Raw Data"])

        with tab1:
            st.header("Task Overview")

            # Daily hours chart
            daily_data = []
            current_date = data['from_date'].date()
            while current_date <= data['to_date'].date():
                date_str = str(current_date)
                hours = data['time_analysis']['daily_breakdown'].get(date_str, 0)
                daily_data.append({
                    'Date': current_date,
                    'Hours': hours,
                    'Day': current_date.strftime('%A')
                })
                current_date += timedelta(days=1)

            df_daily = pd.DataFrame(daily_data)

            st.subheader("Daily Hours Logged")
            # Prepare data for bar chart
            df_daily_chart = df_daily.set_index('Date')['Hours']
            st.bar_chart(df_daily_chart, height=400)

            # Show weekend days in caption
            weekend_days = df_daily[df_daily['Day'].isin(['Friday', 'Saturday'])]
            if not weekend_days.empty:
                st.caption(f"📍 Weekend days (Friday/Saturday) worked: {len(weekend_days[weekend_days['Hours'] > 0])}")

            # Task status breakdown
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Task Status Distribution")
                status_counts = {}
                for task in data['tasks']:
                    status = task.get('status', {}).get('status', 'Unknown')
                    status_counts[status] = status_counts.get(status, 0) + 1

                df_status = pd.DataFrame(list(status_counts.items()), columns=['Status', 'Count'])
                st.bar_chart(df_status.set_index('Status'))

            with col2:
                st.subheader("Tasks with Missing Estimates")
                tasks_without_estimates = [
                    task for task in data['tasks']
                    if not task.get('time_estimate')
                ]
                st.metric("Missing Estimates", len(tasks_without_estimates))

                if tasks_without_estimates:
                    st.caption("Top 5 tasks without estimates:")
                    for task in tasks_without_estimates[:5]:
                        st.write(f"• {task.get('name', 'Unnamed')}")

        with tab2:
            st.header("🤖 AI Analysis")

            with st.spinner("Analyzing with AI..."):
                structured_output = create_structured_output(data)

                # Prepare the user prompt
                user_prompt = st.session_state.user_prompt.format(
                    username=data['user']['username'],
                    days_back=days_back,
                    structured_data=structured_output
                )

                # Run AI analysis
                try:
                    analyzer = GenAIAnalyzer()
                    # Set system prompt as a list with one instruction
                    analyzer.system_instructions = [st.session_state.system_prompt]
                    ai_analysis = analyzer.analyze(user_prompt, temperature=st.session_state.temperature)

                    if ai_analysis:
                        st.session_state.analysis_results = ai_analysis
                        st.markdown(ai_analysis)

                        # Download button for analysis
                        st.download_button(
                            label="📥 Download Analysis",
                            data=ai_analysis,
                            file_name=f"{data['user']['username'].lower().replace(' ', '_')}_analysis.md",
                            mime="text/markdown"
                        )
                    else:
                        st.error("AI analysis failed. Please check your Gemini API key.")
                except Exception as e:
                    st.error(f"Error during AI analysis: {str(e)}")

        with tab3:
            st.header("📋 Task Details")

            # Convert tasks to DataFrame
            tasks_data = []
            for task in data['tasks']:
                time_est = task.get("time_estimate", 0)
                est_hours = round(time_est / (1000 * 60 * 60), 2) if time_est else 0

                tasks_data.append({
                    'Name': task.get('name', 'Unnamed'),
                    'Status': task.get('status', {}).get('status', 'Unknown'),
                    'Estimated Hours': est_hours,
                    'Created': UserTaskAnalyzer().timestamp_to_datetime(task.get('date_created')),
                    'Updated': UserTaskAnalyzer().timestamp_to_datetime(task.get('date_updated')),
                    'Assignees': len(task.get('assignees', [])),
                    'Has Description': bool(task.get('description', '').strip())
                })

            df_tasks = pd.DataFrame(tasks_data)

            # Filters
            col1, col2, col3 = st.columns(3)
            with col1:
                filter_status = st.selectbox("Filter by status", ["All"] + df_tasks['Status'].unique().tolist())
            with col2:
                filter_has_estimate = st.checkbox("Only tasks with estimates")
            with col3:
                filter_has_desc = st.checkbox("Only tasks with descriptions")

            # Apply filters
            filtered_df = df_tasks.copy()
            if filter_status != "All":
                filtered_df = filtered_df[filtered_df['Status'] == filter_status]
            if filter_has_estimate:
                filtered_df = filtered_df[filtered_df['Estimated Hours'] > 0]
            if filter_has_desc:
                filtered_df = filtered_df[filtered_df['Has Description'] == True]

            st.dataframe(filtered_df, use_container_width=True, height=600)

            # Download filtered tasks
            csv = filtered_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Tasks CSV",
                data=csv,
                file_name=f"{data['user']['username'].lower().replace(' ', '_')}_tasks.csv",
                mime="text/csv"
            )

        with tab4:
            st.header("📊 Daily Breakdown")

            # Create daily breakdown table
            daily_breakdown = []
            current_date = data['from_date'].date()

            while current_date <= data['to_date'].date():
                date_str = str(current_date)
                hours = data['time_analysis']['daily_breakdown'].get(date_str, 0)

                # Count tasks for this day
                day_tasks = 0
                for task in data['tasks']:
                    date_done = UserTaskAnalyzer().timestamp_to_datetime(task.get("date_done"))
                    date_closed = UserTaskAnalyzer().timestamp_to_datetime(task.get("date_closed"))
                    date_updated = UserTaskAnalyzer().timestamp_to_datetime(task.get("date_updated"))
                    task_date = date_done or date_closed or date_updated

                    if task_date and str(task_date.date()) == date_str:
                        day_tasks += 1

                daily_breakdown.append({
                    'Date': current_date,
                    'Day': current_date.strftime('%A'),
                    'Tasks': day_tasks,
                    'Hours': hours,
                    'Avg Hours/Task': round(hours/day_tasks, 2) if day_tasks > 0 else 0
                })

                current_date += timedelta(days=1)

            df_breakdown = pd.DataFrame(daily_breakdown)

            # Summary metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                avg_daily = df_breakdown[df_breakdown['Hours'] > 0]['Hours'].mean()
                st.metric("Avg Daily Hours", f"{avg_daily:.1f}" if avg_daily else "0")
            with col2:
                working_days = len(df_breakdown[(df_breakdown['Hours'] > 0) & ~df_breakdown['Day'].isin(['Friday', 'Saturday'])])
                st.metric("Working Days", working_days)
            with col3:
                weekend_days = len(df_breakdown[(df_breakdown['Hours'] > 0) & df_breakdown['Day'].isin(['Friday', 'Saturday'])])
                st.metric("Weekend Days Worked", weekend_days)

            st.dataframe(df_breakdown, use_container_width=True)

        with tab5:
            st.header("📄 Raw Data")

            # Export options
            col1, col2 = st.columns(2)

            with col1:
                # Raw JSON data
                export_data = {
                    "user": data['user'],
                    "date_range": {
                        "from": data['from_date'].isoformat(),
                        "to": data['to_date'].isoformat()
                    },
                    "summary": {
                        "total_tasks": len(data['tasks']),
                        "tasks_with_estimates": data['time_analysis']['tasks_with_estimates'],
                        "total_hours": data['time_analysis']['total_estimate_hours']
                    },
                    "daily_breakdown": data['time_analysis']['daily_breakdown'],
                    "tasks": data['tasks']
                }

                json_str = json.dumps(export_data, indent=2)
                st.download_button(
                    label="📥 Download JSON Data",
                    data=json_str,
                    file_name=f"{data['user']['username'].lower().replace(' ', '_')}_data.json",
                    mime="application/json"
                )

            with col2:
                # Structured output for LLM
                structured_output = create_structured_output(data)
                st.download_button(
                    label="📥 Download Structured Output",
                    data=structured_output,
                    file_name=f"{data['user']['username'].lower().replace(' ', '_')}_structured.txt",
                    mime="text/plain"
                )

            # Display raw JSON
            with st.expander("View Raw JSON"):
                st.json(export_data)

    else:
        # Initial state - show instructions
        st.info("👈 Configure your search parameters in the sidebar and click 'Fetch & Analyze' to start")

        # Show sample configuration
        st.subheader("Quick Start Guide")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("""
            **1. Set up your environment:**
            - Create a `.env` file with your API keys
            - `CLICKUP_API_KEY=your_key_here`
            - `GEMINI_API_KEY=your_key_here`

            **2. Configure search parameters:**
            - Enter a partial username to search
            - Select the date range to analyze
            - Choose task status filters
            """)

        with col2:
            st.markdown("""
            **3. Customize AI analysis (optional):**
            - Modify system instructions
            - Adjust the analysis prompt template
            - Reset to defaults anytime

            **4. View results:**
            - Overview charts and metrics
            - Detailed AI analysis
            - Task explorer with filters
            - Export data in multiple formats
            """)

if __name__ == "__main__":
    main()