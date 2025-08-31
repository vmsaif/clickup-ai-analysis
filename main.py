#!/usr/bin/env python3
"""
Main entry point for ClickUp Task Analysis with GenAI.

This script fetches tasks from ClickUp and analyzes them using Google's Gemini AI
to detect time estimation issues and productivity patterns.
"""

from user_task_analyzer import UserTaskAnalyzer
from genai_analyzer_simple import analyze_clickup_data
from datetime import datetime, timedelta, timezone
import json
import os
import io
import sys

# ==================== CONFIGURATION ====================
USERNAME = "Istiak"  # Partial name to search for user
DAYS_BACK = 25 # How many days back to fetch tasks
STATUS_FILTER = ["completed", "done", "closed"]  # List of statuses to include
MODEL_NAME = "Gemini 2.5 Pro"  # AI model being used
# ========================================================


def main():
    """Main function to run ClickUp task analysis with GenAI."""

    print("=" * 80)
    print("CLICKUP TASK ANALYSIS WITH GENAI")
    print("=" * 80)
    print(f"Configuration:")
    print(f"  User: {USERNAME}")
    print(f"  Days Back: {DAYS_BACK}")
    print(f"  Status Filter: {', '.join(STATUS_FILTER)}")
    print(f"  AI Model: {MODEL_NAME}")
    print("=" * 80)

    try:
        # Ensure output directory exists
        os.makedirs("output", exist_ok=True)

        # Initialize ClickUp analyzer
        clickup = UserTaskAnalyzer()

        # Get team
        teams = clickup.get_teams()
        if not teams:
            print("❌ No teams found. Check your CLICKUP_API_KEY in .env")
            return 1

        team_id = teams[0]["id"]
        print(f"\nTeam: {teams[0]['name']}")

        # Find user
        user = clickup.find_user_by_partial_name(USERNAME, team_id)
        if not user:
            print(f"❌ No user found matching '{USERNAME}'")
            return 1
        print(f"User: {user['username']} ({user['email']})")

        # Set date range
        from_date = datetime.now(timezone.utc) - timedelta(days=DAYS_BACK)
        to_date = datetime.now(timezone.utc)
        print(f"Date Range: {from_date.date()} to {to_date.date()}")

        # Fetch tasks
        print("\n📋 Fetching tasks from ClickUp...")
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

            response = clickup._make_request("GET", f"team/{team_id}/task", params=params)
            tasks = response.get("tasks", [])

            if not tasks:
                break

            # Filter by status
            if STATUS_FILTER and STATUS_FILTER != ["all"]:
                filtered_tasks = []
                for task in tasks:
                    status_type = task.get("status", {}).get("type", "")
                    status_name = task.get("status", {}).get("status", "").lower()

                    # Check if task matches any of the status filters
                    if status_type == "closed" or status_name in [s.lower() for s in STATUS_FILTER]:
                        filtered_tasks.append(task)

                tasks = filtered_tasks

            all_tasks.extend(tasks)

            if response.get("last_page", True):
                break
            page += 1

        print(f"✅ Found {len(all_tasks)} tasks with status: {', '.join(STATUS_FILTER)}")

        if not all_tasks:
            print("⚠️  No tasks found for the specified criteria")
            return 0

        # Calculate time estimates
        time_analysis = clickup.calculate_time_estimates(all_tasks, from_date, to_date)

        # Build structured output for AI
        print("\n📊 Building task breakdown...")
        output_buffer = io.StringIO()

        output_buffer.write("=" * 70 + "\n")
        output_buffer.write("TASK ANALYSIS DATA\n")
        output_buffer.write("=" * 70 + "\n")
        output_buffer.write(f"\n📅 Date Range: {from_date.date()} to {to_date.date()}\n")
        output_buffer.write(f"   Total Tasks: {time_analysis['total_tasks']}\n")
        output_buffer.write(f"   Tasks with time estimates: {time_analysis['tasks_with_estimates']}\n")
        output_buffer.write(f"   Total Estimated Time: {time_analysis['total_estimate_hours']} hours\n")

        # Daily breakdown - include all days in range
        output_buffer.write("\n   Daily Breakdown:\n")

        # Generate all days in the date range
        current_date = from_date.date()
        all_days = {}
        while current_date <= to_date.date():
            date_str = str(current_date)
            # Check if it's a weekend (Friday or Saturday in Bangladesh)
            day_of_week = current_date.weekday()
            is_weekend = day_of_week in [4, 5]  # 4=Friday, 5=Saturday
            weekend_day = "Friday" if day_of_week == 4 else "Saturday" if day_of_week == 5 else None

            # Get hours from time_analysis or default to 0
            hours = time_analysis['daily_breakdown'].get(date_str, 0)

            # Get tasks for this day
            day_tasks = []
            for task in all_tasks:
                date_done = clickup.timestamp_to_datetime(task.get("date_done"))
                date_closed = clickup.timestamp_to_datetime(task.get("date_closed"))
                date_updated = clickup.timestamp_to_datetime(task.get("date_updated"))
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

        # Sort and display all days
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

                # Add description if available
                if description and description.strip():
                    desc_cleaned = description.strip().replace('\n', ' ')
                    if len(desc_cleaned) > 1000:
                        desc_lines = desc_cleaned[:1000] + "..."
                    else:
                        desc_lines = desc_cleaned
                    output_buffer.write(f"          Description: {desc_lines}\n")

        structured_output = output_buffer.getvalue()

        # Display the structured data
        print("\n" + structured_output)

        # Run AI analysis
        print("\n🤖 Running AI Analysis...")
        print("=" * 80)
        print(f"Analyzing with {MODEL_NAME}...")

        ai_analysis = analyze_clickup_data(structured_output, user, DAYS_BACK)

        if not ai_analysis:
            print("❌ AI analysis failed - no response received from Gemini")
            ai_analysis = "Analysis failed - please check your GEMINI_API_KEY and try again."
            return 1

        # Save outputs
        # 1. Save markdown report
        report_file = f"output/{user['username'].lower().replace(' ', '_')}_analysis.md"
        with open(report_file, "w") as f:
            f.write(ai_analysis)
        print(f"\n📝 Analysis report saved to: {report_file}")

        # 2. Save raw data as JSON
        json_file = f"output/{user['username'].lower().replace(' ', '_')}_data.json"
        export_data = {
            "user": user,
            "date_range": {
                "from": from_date.isoformat(),
                "to": to_date.isoformat()
            },
            "summary": {
                "total_tasks": len(all_tasks),
                "tasks_with_estimates": time_analysis['tasks_with_estimates'],
                "total_hours": time_analysis['total_estimate_hours']
            },
            "daily_breakdown": time_analysis['daily_breakdown'],
            "structured_output_for_llm": structured_output,
            "tasks": all_tasks
        }

        with open(json_file, "w") as f:
            json.dump(export_data, f, indent=2)
        print(f"💾 Raw data saved to: {json_file}")

        # Show full AI analysis (no truncation)
        print("\n" + "=" * 80)
        print("AI ANALYSIS RESULTS")
        print("=" * 80)
        print(ai_analysis)

        print("\n✅ Analysis complete!")
        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())