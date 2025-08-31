import requests
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from dotenv import load_dotenv
import os
import argparse
import time

load_dotenv()


class UserTaskAnalyzer:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("CLICKUP_API_KEY")
        if not self.api_key:
            raise ValueError("ClickUp API key is required. Set it in .env file or pass it to the constructor.")
        
        self.base_url = "https://api.clickup.com/api/v2"
        self.headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json"
        }
    
    def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None, data: Optional[Dict] = None) -> Dict:
        url = f"{self.base_url}/{endpoint}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params,
                json=data
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error making request to {url}: {e}")
            if hasattr(e.response, 'text'):
                print(f"Response: {e.response.text}")
            raise
    
    def get_teams(self) -> List[Dict[str, Any]]:
        """Get all teams the user has access to."""
        response = self._make_request("GET", "team")
        return response.get("teams", [])
    
    def find_user_by_partial_name(self, partial_name: str, team_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Find a user by partial name match."""
        if not team_id:
            teams = self.get_teams()
            if not teams:
                raise ValueError("No teams found for this API key")
            team_id = teams[0]["id"]
            print(f"Using team: {teams[0]['name']} (ID: {team_id})")
        
        # Get team info with members
        response = self._make_request("GET", f"team/{team_id}")
        members = response.get("team", {}).get("members", [])
        
        # Search for user by partial name (case-insensitive)
        partial_lower = partial_name.lower()
        matched_users = []
        
        for member in members:
            user = member.get("user", {})
            username = user.get("username", "")
            email = user.get("email", "")
            
            if partial_lower in username.lower() or partial_lower in email.lower():
                matched_users.append(user)
        
        if not matched_users:
            print(f"No user found matching '{partial_name}'")
            return None
        
        if len(matched_users) > 1:
            print(f"Multiple users found matching '{partial_name}':")
            for i, user in enumerate(matched_users, 1):
                print(f"  {i}. {user['username']} ({user['email']})")
            print("Using the first match.")
        
        selected_user = matched_users[0]
        print(f"Selected user: {selected_user['username']} (ID: {selected_user['id']}, Email: {selected_user['email']})")
        return selected_user
    
    def timestamp_to_datetime(self, timestamp: str) -> datetime:
        """Convert ClickUp timestamp (milliseconds) to datetime."""
        if not timestamp:
            return None
        try:
            # ClickUp uses milliseconds since epoch
            return datetime.fromtimestamp(int(timestamp) / 1000, tz=timezone.utc)
        except (ValueError, TypeError):
            return None
    
    def datetime_to_timestamp(self, dt: datetime) -> str:
        """Convert datetime to ClickUp timestamp (milliseconds)."""
        return str(int(dt.timestamp() * 1000))
    
    def get_task_comments(self, task_id: str) -> List[Dict[str, Any]]:
        """Get all comments for a specific task."""
        try:
            response = self._make_request("GET", f"task/{task_id}/comment")
            return response.get("comments", [])
        except Exception as e:
            print(f"Error fetching comments for task {task_id}: {e}")
            return []
    
    def get_task_time_tracking(self, task_id: str) -> Dict[str, Any]:
        """Get time tracking entries for a task."""
        try:
            response = self._make_request("GET", f"task/{task_id}/time")
            return response
        except Exception as e:
            print(f"Error fetching time tracking for task {task_id}: {e}")
            return {"data": []}
    
    def get_user_tasks(self, user_id: str, team_id: str, from_date: datetime, to_date: datetime, 
                      status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch all tasks assigned to a specific user within a date range.
        
        Args:
            user_id: The user's ID
            team_id: The team ID
            from_date: Start date for filtering
            to_date: End date for filtering
            status_filter: 'completed', 'done', 'open', or None for all
        """
        
        # Convert dates to timestamps
        from_timestamp = self.datetime_to_timestamp(from_date)
        to_timestamp = self.datetime_to_timestamp(to_date)
        
        all_tasks = []
        page = 0
        
        while True:
            params = {
                "assignees[]": [user_id],
                "include_closed": "true",
                "page": page,
                "date_updated_gt": from_timestamp,
                "date_updated_lt": to_timestamp,
                "subtasks": "true"
            }
            
            try:
                response = self._make_request("GET", f"team/{team_id}/task", params=params)
                tasks = response.get("tasks", [])
                
                if not tasks:
                    break
                
                # Filter by status if specified
                if status_filter:
                    filtered_tasks = []
                    for task in tasks:
                        task_status = task.get("status", {})
                        status_type = task_status.get("type", "")
                        status_name = task_status.get("status", "").lower()
                        
                        if status_filter in ["completed", "done", "closed"]:
                            if status_type == "closed" or status_name in ["complete", "completed", "done", "closed"]:
                                filtered_tasks.append(task)
                        elif status_filter == "open":
                            if status_type == "open":
                                filtered_tasks.append(task)
                    tasks = filtered_tasks
                
                all_tasks.extend(tasks)
                
                # Check if there are more pages
                last_page = response.get("last_page", True)
                if last_page:
                    break
                
                page += 1
                
            except Exception as e:
                print(f"Error fetching tasks on page {page}: {e}")
                break
        
        # Add comments and activity to each task (with rate limiting)
        if len(all_tasks) > 0:
            print(f"Fetching comments and activity for {len(all_tasks)} tasks...")
            print("Note: This may take a while due to API rate limits...")
            
            for i, task in enumerate(all_tasks):
                task_id = task["id"]
                
                # Add rate limiting - 100 requests per minute = 0.6 seconds between requests
                # We make 2 requests per task (comments + time), so 0.3 seconds per request
                time.sleep(0.3)
                
                # Get comments
                comments = self.get_task_comments(task_id)
                task["comments"] = comments
                task["comment_count"] = len(comments)
                
                # Add another small delay
                time.sleep(0.3)
                
                # Get time tracking
                time_tracking = self.get_task_time_tracking(task_id)
                task["time_entries"] = time_tracking.get("data", [])
                
                # Show progress
                if (i + 1) % 5 == 0:
                    print(f"  Processed {i + 1}/{len(all_tasks)} tasks...")
        
        return all_tasks
    
    def calculate_time_estimates(self, tasks: List[Dict[str, Any]], from_date: datetime, 
                                to_date: datetime) -> Dict[str, Any]:
        """
        Calculate time estimates from tasks.
        
        Returns:
            Dictionary with daily breakdown and totals
        """
        daily_estimates = defaultdict(int)  # date -> milliseconds
        total_estimate = 0
        tasks_with_estimates = 0
        tasks_without_estimates = 0
        
        for task in tasks:
            time_estimate = task.get("time_estimate")
            
            if time_estimate and time_estimate > 0:
                tasks_with_estimates += 1
                total_estimate += time_estimate
                
                # For daily breakdown, distribute estimate based on task dates
                date_done = self.timestamp_to_datetime(task.get("date_done"))
                date_closed = self.timestamp_to_datetime(task.get("date_closed"))
                date_updated = self.timestamp_to_datetime(task.get("date_updated"))
                
                # Use the most relevant date
                task_date = date_done or date_closed or date_updated
                
                if task_date:
                    # Convert to date only (no time)
                    task_day = task_date.date()
                    daily_estimates[str(task_day)] += time_estimate
            else:
                tasks_without_estimates += 1
        
        # Convert milliseconds to hours for readability
        daily_hours = {}
        for date_str, ms in daily_estimates.items():
            hours = ms / (1000 * 60 * 60)
            daily_hours[date_str] = round(hours, 2)
        
        total_hours = total_estimate / (1000 * 60 * 60)
        
        return {
            "total_estimate_ms": total_estimate,
            "total_estimate_hours": round(total_hours, 2),
            "daily_breakdown": daily_hours,
            "tasks_with_estimates": tasks_with_estimates,
            "tasks_without_estimates": tasks_without_estimates,
            "total_tasks": len(tasks)
        }
    
    def get_current_month_tasks(self, user_id: str, team_id: str, status_filter: Optional[str] = None) -> Tuple[List[Dict[str, Any]], datetime, datetime]:
        """
        Get tasks for the current calendar month.
        
        Returns:
            Tuple of (tasks, month_start_date, month_end_date)
        """
        now = datetime.now(timezone.utc)
        
        # Get first day of current month
        month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        
        # Get last day of current month
        if now.month == 12:
            month_end = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc) - timedelta(seconds=1)
        else:
            month_end = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc) - timedelta(seconds=1)
        
        tasks = self.get_user_tasks(user_id, team_id, month_start, month_end, status_filter)
        
        return tasks, month_start, month_end
    
    def format_comment_summary(self, comments: List[Dict[str, Any]]) -> str:
        """Format comments into a summary."""
        if not comments:
            return "No comments"
        
        summary = []
        for comment in comments:  # Show all comments, no limit
            user = comment.get("user", {}).get("username", "Unknown")
            text = comment.get("comment_text", "")
            if text:
                # No truncation
                summary.append(f"{user}: {text}")
        
        return " | ".join(summary)
    
    def format_analysis_report(self, user: Dict[str, Any], tasks: List[Dict[str, Any]], 
                              time_analysis: Dict[str, Any], from_date: datetime, 
                              to_date: datetime, month_tasks: List[Dict[str, Any]], 
                              month_analysis: Dict[str, Any], month_start: datetime,
                              month_end: datetime) -> str:
        """Format the analysis into a readable report."""
        report = []
        report.append("=" * 70)
        report.append("USER TASK ANALYSIS REPORT WITH ACTIVITY")
        report.append("=" * 70)
        
        # User info
        report.append(f"\nUser: {user['username']}")
        report.append(f"Email: {user['email']}")
        report.append(f"User ID: {user['id']}")
        
        # Date range analysis
        report.append(f"\n{'=' * 70}")
        report.append(f"SPECIFIED DATE RANGE: {from_date.date()} to {to_date.date()}")
        report.append(f"{'=' * 70}")
        
        report.append(f"\nTotal Tasks: {time_analysis['total_tasks']}")
        report.append(f"Tasks with time estimates: {time_analysis['tasks_with_estimates']}")
        report.append(f"Tasks without time estimates: {time_analysis['tasks_without_estimates']}")
        report.append(f"\nTotal Estimated Time: {time_analysis['total_estimate_hours']} hours")
        
        if time_analysis['daily_breakdown']:
            report.append("\nDaily Breakdown:")
            sorted_days = sorted(time_analysis['daily_breakdown'].items())
            for date_str, hours in sorted_days:
                report.append(f"  {date_str}: {hours} hours")
        
        # Current month analysis
        report.append(f"\n{'=' * 70}")
        report.append(f"CURRENT MONTH ({month_start.strftime('%B %Y')}): {month_start.date()} to {month_end.date()}")
        report.append(f"{'=' * 70}")
        
        report.append(f"\nTotal Tasks: {month_analysis['total_tasks']}")
        report.append(f"Tasks with time estimates: {month_analysis['tasks_with_estimates']}")
        report.append(f"Tasks without time estimates: {month_analysis['tasks_without_estimates']}")
        report.append(f"\nTotal Estimated Time: {month_analysis['total_estimate_hours']} hours")
        
        if month_analysis['daily_breakdown']:
            report.append("\nDaily Breakdown (Current Month):")
            sorted_days = sorted(month_analysis['daily_breakdown'].items())
            for date_str, hours in sorted_days[-10:]:  # Show last 10 days with activity
                report.append(f"  {date_str}: {hours} hours")
            if len(sorted_days) > 10:
                report.append(f"  ... and {len(sorted_days) - 10} more days")
        
        # Tasks with activity details
        if tasks:
            report.append(f"\n{'=' * 70}")
            report.append("TASKS WITH ACTIVITY (Showing tasks with comments/activity)")
            report.append(f"{'=' * 70}")
            
            # Filter tasks with comments or significant activity
            tasks_with_activity = [t for t in tasks if t.get("comment_count", 0) > 0 or t.get("time_entries")]
            
            if tasks_with_activity:
                for i, task in enumerate(tasks_with_activity, 1):  # Show ALL tasks with activity, no limit
                    name = task.get("name", "Unnamed")  # No truncation
                    status = task.get("status", {}).get("status", "Unknown")
                    time_est = task.get("time_estimate", 0)
                    time_hours = round(time_est / (1000 * 60 * 60), 2) if time_est else 0
                    
                    report.append(f"\n{i}. {name}")
                    report.append(f"   Status: {status}")
                    report.append(f"   Time Estimate: {time_hours} hours" if time_hours else "   Time Estimate: Not set")
                    
                    # Show comments summary
                    comment_count = task.get("comment_count", 0)
                    if comment_count > 0:
                        report.append(f"   Comments ({comment_count}): {self.format_comment_summary(task.get('comments', []))}")
                    
                    # Show time entries summary
                    time_entries = task.get("time_entries", [])
                    if time_entries:
                        total_tracked = sum(int(e.get("duration", 0)) for e in time_entries)
                        tracked_hours = round(total_tracked / (1000 * 60 * 60), 2)
                        report.append(f"   Time Tracked: {tracked_hours} hours ({len(time_entries)} entries)")
                    
                    date_done = self.timestamp_to_datetime(task.get("date_done"))
                    if date_done:
                        report.append(f"   Completed: {date_done.date()}")
            else:
                report.append("\nNo tasks with comments or time tracking activity found.")
            
            # Summary statistics
            report.append(f"\n{'=' * 70}")
            report.append("ACTIVITY SUMMARY")
            report.append(f"{'=' * 70}")
            
            total_comments = sum(t.get("comment_count", 0) for t in tasks)
            tasks_with_comments = len([t for t in tasks if t.get("comment_count", 0) > 0])
            tasks_with_time_entries = len([t for t in tasks if t.get("time_entries")])
            
            report.append(f"Total tasks: {len(tasks)}")
            report.append(f"Tasks with comments: {tasks_with_comments}")
            report.append(f"Total comments across all tasks: {total_comments}")
            report.append(f"Tasks with time tracking: {tasks_with_time_entries}")
        
        return "\n".join(report)


def parse_date(date_str: str) -> datetime:
    """Parse date string to datetime object."""
    try:
        # Try different date formats
        for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%m-%d-%Y", "%m/%d/%Y"]:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        
        # If no format worked, try to parse as days ago
        if date_str.lower().endswith("d") or date_str.lower().endswith("days"):
            days = int(date_str.replace("d", "").replace("days", "").strip())
            return datetime.now(timezone.utc) - timedelta(days=days)
        
        raise ValueError(f"Could not parse date: {date_str}")
    except Exception as e:
        raise ValueError(f"Invalid date format: {date_str}. Use YYYY-MM-DD or 'Xd' for X days ago")


def main():
    parser = argparse.ArgumentParser(description="Analyze ClickUp tasks for a specific user")
    parser.add_argument("username", help="Partial username to search for (e.g., 'Anamul')")
    parser.add_argument("--from", dest="from_date", required=True, 
                       help="Start date (YYYY-MM-DD or 'Xd' for X days ago)")
    parser.add_argument("--to", dest="to_date", required=True,
                       help="End date (YYYY-MM-DD or 'Xd' for X days ago)")
    parser.add_argument("--status", choices=["completed", "done", "closed", "open", "all"],
                       default="completed", help="Filter by task status (default: completed)")
    parser.add_argument("--team-id", help="Specific team ID to use")
    parser.add_argument("--export", help="Export detailed results to JSON file")
    
    args = parser.parse_args()
    
    try:
        # Parse dates
        from_date = parse_date(args.from_date)
        to_date = parse_date(args.to_date)
        
        # Initialize analyzer
        analyzer = UserTaskAnalyzer()
        
        # Get team ID
        team_id = args.team_id
        if not team_id:
            teams = analyzer.get_teams()
            if not teams:
                print("Error: No teams found")
                return 1
            team_id = teams[0]["id"]
        
        # Find user
        user = analyzer.find_user_by_partial_name(args.username, team_id)
        if not user:
            return 1
        
        print(f"\nFetching tasks from {from_date.date()} to {to_date.date()}...")
        
        # Get tasks for specified date range
        status_filter = None if args.status == "all" else args.status
        tasks = analyzer.get_user_tasks(user["id"], team_id, from_date, to_date, status_filter)
        
        print(f"Found {len(tasks)} tasks in date range")
        
        # Calculate time estimates for date range
        time_analysis = analyzer.calculate_time_estimates(tasks, from_date, to_date)
        
        # Get current month tasks
        print(f"\nFetching current month tasks...")
        month_tasks, month_start, month_end = analyzer.get_current_month_tasks(user["id"], team_id, status_filter)
        
        print(f"Found {len(month_tasks)} tasks in current month")
        
        # Calculate time estimates for current month
        month_analysis = analyzer.calculate_time_estimates(month_tasks, month_start, month_end)
        
        # Generate and print report
        report = analyzer.format_analysis_report(
            user, tasks, time_analysis, from_date, to_date,
            month_tasks, month_analysis, month_start, month_end
        )
        
        print("\n" + report)
        
        # Export to JSON if requested
        if args.export:
            export_data = {
                "user": user,
                "analysis_date": datetime.now().isoformat(),
                "date_range": {
                    "from": from_date.isoformat(),
                    "to": to_date.isoformat(),
                    "tasks": tasks,
                    "analysis": time_analysis
                },
                "current_month": {
                    "from": month_start.isoformat(),
                    "to": month_end.isoformat(),
                    "tasks": month_tasks,
                    "analysis": month_analysis
                }
            }
            
            with open(args.export, "w") as f:
                json.dump(export_data, f, indent=2)
            
            print(f"\nDetailed results exported to: {args.export}")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())