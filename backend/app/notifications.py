# Email notification service for FlatWatch (POC Mock)
# In production, integrate with SendGrid/AWS SES/Resend
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from dataclasses import dataclass
from enum import Enum

from .config import FRONTEND_URL
from .database import get_db_connection


class NotificationFrequency(str, Enum):
    """Email summary frequency."""
    DAILY = "daily"
    WEEKLY = "weekly"


@dataclass
class EmailSummary:
    """Email summary data."""
    recipient_email: str
    recipient_name: str
    frequency: str
    period_start: str
    period_end: str
    balance: float
    total_inflow: float
    total_outflow: float
    transaction_count: int
    pending_challenges: int
    red_flags: int
    yellow_flags: int


class EmailService:
    """POC mock email service."""

    # In production: store actual email delivery status
    _sent_emails: List[dict] = []

    @classmethod
    def send_email(cls, to: str, subject: str, html_body: str, text_body: str) -> bool:
        """
        Send email (POC mock - logs to console).

        In production:
        - Use SendGrid Python SDK
        - Or AWS SES boto3
        - Or Resend API
        """
        email_record = {
            "to": to,
            "subject": subject,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "sent"  # In production: check actual delivery status
        }
        cls._sent_emails.append(email_record)
        return True

    @classmethod
    def get_sent_emails(cls) -> List[dict]:
        """Get list of sent emails (for testing)."""
        return cls._sent_emails.copy()

    @classmethod
    def clear_sent_emails(cls) -> None:
        """Clear sent emails (for testing)."""
        cls._sent_emails.clear()


def generate_summary_html(summary: EmailSummary) -> str:
    """Generate HTML email body."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #ff611a 0%, #ff9666 100%); color: white; padding: 20px; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9f9f9; padding: 20px; border-radius: 0 0 10px 10px; }}
            .metric {{ display: inline-block; margin: 10px 20px 10px 0; }}
            .metric-value {{ font-size: 24px; font-weight: bold; color: #ff611a; }}
            .metric-label {{ font-size: 14px; color: #666; }}
            .red-flag {{ color: #e74c3c; }}
            .yellow-flag {{ color: #f39c12; }}
            .section {{ margin: 20px 0; padding: 15px; background: white; border-radius: 8px; }}
            .footer {{ text-align: center; margin-top: 20px; color: #999; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>FlatWatch {summary.frequency.capitalize()} Summary</h1>
                <p>Financial Transparency for Your Society</p>
            </div>
            <div class="content">
                <p>Hi {summary.recipient_name},</p>
                <p>Here's your {summary.frequency} financial summary for the period ending {summary.period_end}:</p>

                <div class="section">
                    <div class="metric">
                        <div class="metric-value">₹{summary.balance:,.0f}</div>
                        <div class="metric-label">Current Balance</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">₹{summary.total_inflow:,.0f}</div>
                        <div class="metric-label">Total Inflow</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">₹{summary.total_outflow:,.0f}</div>
                        <div class="metric-label">Total Outflow</div>
                    </div>
                </div>

                <div class="section">
                    <h3>Activity Summary</h3>
                    <ul>
                        <li>{summary.transaction_count} transactions recorded</li>
                        <li>{summary.pending_challenges} pending challenges</li>
                        <li class="red-flag">{summary.red_flags} red flags (requires attention)</li>
                        <li class="yellow-flag">{summary.yellow_flags} yellow flags (review recommended)</li>
                    </ul>
                </div>

                <div class="section">
                    <p><a href="{FRONTEND_URL}/dashboard" style="background: #ff611a; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">View Full Dashboard</a></p>
                </div>

                <div class="footer">
                    <p>You're receiving this because you're a member of FlatWatch Society Transparency System.</p>
                    <p>To unsubscribe, update your notification preferences in Settings.</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """


def generate_summary_text(summary: EmailSummary) -> str:
    """Generate plain text email body."""
    return f"""
FLATWATCH {summary.frequency.upper()} SUMMARY
{"=" * 40}

Hi {summary.recipient_name},

Here's your {summary.frequency} financial summary:

CURRENT STATUS
--------------
Balance: ₹{summary.balance:,.2f}
Total Inflow: ₹{summary.total_inflow:,.2f}
Total Outflow: ₹{summary.total_outflow:,.2f}

ACTIVITY
--------
Transactions: {summary.transaction_count}
Pending Challenges: {summary.pending_challenges}
Red Flags: {summary.red_flags} (requires attention)
Yellow Flags: {summary.yellow_flags} (review recommended)

View full dashboard: {FRONTEND_URL}/dashboard

---
FlatWatch Society Transparency System
Financial transparency for housing societies
    """


def get_summary_data(user_email: str, frequency: NotificationFrequency) -> EmailSummary:
    """Get summary data for a user."""
    from .auth import MOCK_USERS

    # Get user info
    user = MOCK_USERS.get(user_email)
    if not user:
        raise ValueError(f"User not found: {user_email}")

    conn = get_db_connection()

    # Calculate period
    now = datetime.now(timezone.utc)
    if frequency == NotificationFrequency.DAILY:
        period_start = now - timedelta(days=1)
    else:  # weekly
        period_start = now - timedelta(weeks=1)

    # Get financial stats
    cursor = conn.execute("""
        SELECT
            COALESCE(SUM(CASE WHEN transaction_type = 'inflow' THEN amount ELSE 0 END), 0) as inflow,
            COALESCE(SUM(CASE WHEN transaction_type = 'outflow' THEN amount ELSE 0 END), 0) as outflow,
            COUNT(*) as count
        FROM transactions
        WHERE timestamp > ?
    """, (period_start.isoformat(),))
    stats = cursor.fetchone()

    # Get pending challenges
    cursor = conn.execute("SELECT COUNT(*) as count FROM challenges WHERE status = 'pending'")
    challenges = cursor.fetchone()["count"]

    # Calculate balance (inflow - outflow)
    cursor = conn.execute("""
        SELECT
            COALESCE(SUM(CASE WHEN transaction_type = 'inflow' THEN amount ELSE 0 END), 0) -
            COALESCE(SUM(CASE WHEN transaction_type = 'outflow' THEN amount ELSE 0 END), 0) as balance
        FROM transactions
    """)
    balance = cursor.fetchone()["balance"]

    conn.close()

    # POC: Simplified flag counts
    red_flags = 0
    yellow_flags = 0

    return EmailSummary(
        recipient_email=user_email,
        recipient_name=user.get("name", "Resident"),
        frequency=frequency.value,
        period_start=period_start.isoformat(),
        period_end=now.isoformat(),
        balance=balance or 0,
        total_inflow=stats["inflow"] or 0,
        total_outflow=stats["outflow"] or 0,
        transaction_count=stats["count"],
        pending_challenges=challenges,
        red_flags=red_flags,
        yellow_flags=yellow_flags,
    )


def send_summary_email(user_email: str, frequency: NotificationFrequency) -> bool:
    """
    Send summary email to user.

    Returns:
        True if email sent successfully
    """
    summary = get_summary_data(user_email, frequency)
    subject = f"FlatWatch {frequency.value.capitalize()} Financial Summary"

    html_body = generate_summary_html(summary)
    text_body = generate_summary_text(summary)

    return EmailService.send_email(user_email, subject, html_body, text_body)


def send_daily_summaries() -> dict:
    """
    Send daily summaries to all users (called by cron job).

    Returns:
        Summary of emails sent
    """
    from .auth import MOCK_USERS

    results = {"sent": 0, "failed": 0, "recipients": []}

    for email in MOCK_USERS.keys():
        try:
            success = send_summary_email(email, NotificationFrequency.DAILY)
            if success:
                results["sent"] += 1
                results["recipients"].append(email)
            else:
                results["failed"] += 1
        except Exception as e:
            results["failed"] += 1

    return results


def send_weekly_summaries() -> dict:
    """Send weekly summaries to all users (called by cron job)."""
    from .auth import MOCK_USERS

    results = {"sent": 0, "failed": 0, "recipients": []}

    for email in MOCK_USERS.keys():
        try:
            success = send_summary_email(email, NotificationFrequency.WEEKLY)
            if success:
                results["sent"] += 1
                results["recipients"].append(email)
            else:
                results["failed"] += 1
        except Exception as e:
            results["failed"] += 1

    return results
