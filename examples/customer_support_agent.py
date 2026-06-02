"""
Customer Support Agent — AutoGen + MultiMail

An AutoGen AssistantAgent that monitors an inbox for incoming customer emails
and drafts helpful responses. Uses the MultiMail Python SDK for email operations
and GPT-4o for generating replies.

Usage:
    cp .env.example .env   # fill in your keys
    pip install -r requirements.txt
    python examples/customer_support_agent.py
"""

import asyncio
import json
import os

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv
from multimail import MultiMail

load_dotenv()

# --- Config ---

mm = MultiMail(api_key=os.environ["MULTIMAIL_API_KEY"])
MAILBOX_ID = os.environ["MULTIMAIL_MAILBOX_ID"]


# --- Tools (plain async functions — AutoGen wraps them automatically) ---


async def check_inbox(limit: int = 10) -> str:
    """Check the inbox for recent emails. Returns a JSON list of email summaries
    with id, from, subject, status, and received_at. Use this first to see
    what emails need attention."""
    result = mm.list_emails(MAILBOX_ID, limit=limit, direction="inbound")
    emails = result.get("emails", [])
    summaries = [
        {
            "id": e["id"],
            "from": e.get("from"),
            "subject": e.get("subject"),
            "status": e.get("status"),
            "received_at": e.get("received_at"),
        }
        for e in emails
    ]
    return json.dumps(summaries, default=str)


async def read_email(email_id: str) -> str:
    """Read the full content of an email by its ID. Returns the complete email
    including markdown body, sender, subject, and attachments metadata.
    Call this after check_inbox to read specific emails."""
    result = mm.get_email(MAILBOX_ID, email_id)
    return json.dumps(result, default=str)


async def reply_to_email(email_id: str, markdown: str) -> str:
    """Reply to a customer email. The markdown parameter is the reply body
    written in markdown format — it gets converted to HTML for delivery.
    Threading headers are set automatically. Always be professional and helpful."""
    result = mm.reply_email(MAILBOX_ID, email_id, markdown=markdown)
    return json.dumps(result, default=str)


async def send_email(to: str, subject: str, markdown: str) -> str:
    """Send a new email to a customer. Use this for outbound messages that
    are not replies to existing threads. The 'to' parameter is a single
    email address. The markdown body is converted to HTML."""
    result = mm.send_email(MAILBOX_ID, to=[to], subject=subject, markdown=markdown)
    return json.dumps(result, default=str)


async def search_contacts(query: str = "") -> str:
    """Search the address book for contacts by name or email. Returns matching
    contacts. Call with an empty query to list all contacts."""
    contacts = mm.list_contacts(q=query if query else None)
    return json.dumps(contacts, default=str)


async def tag_email(email_id: str, category: str, priority: str = "normal") -> str:
    """Tag an email with a category and priority for tracking. Categories might
    be things like 'billing', 'technical', 'feature-request', 'bug-report'.
    Priority can be 'low', 'normal', 'high', or 'urgent'."""
    result = mm.set_tags(MAILBOX_ID, email_id, {"category": category, "priority": priority})
    return json.dumps(result, default=str)


# --- Agent setup ---

SYSTEM_MESSAGE = """\
You are a customer support agent for a SaaS company. Your job is to:

1. Check the inbox for new customer emails
2. Read each unread email
3. Tag it with a category (billing, technical, feature-request, bug-report, general) and priority
4. Draft and send a helpful, professional reply

Guidelines:
- Be friendly and concise
- For billing issues, acknowledge the concern and say the billing team will follow up
- For technical issues, ask clarifying questions if needed
- For feature requests, thank them and say you've logged the request
- For bug reports, ask for reproduction steps if not provided
- Always reply to the existing thread (use reply_to_email), don't send new emails for responses
- After processing all emails, summarize what you handled
"""


async def main():
    model = OpenAIChatCompletionClient(model="gpt-4o")

    support_agent = AssistantAgent(
        name="support_agent",
        model_client=model,
        tools=[check_inbox, read_email, reply_to_email, send_email, search_contacts, tag_email],
        system_message=SYSTEM_MESSAGE,
        reflect_on_tool_use=True,
        max_tool_iterations=20,
    )

    team = RoundRobinGroupChat(
        participants=[support_agent],
        termination_condition=MaxMessageTermination(max_messages=30),
    )

    print("Customer Support Agent (AutoGen + MultiMail)")
    print("=" * 47)
    print("The agent will check your inbox and respond to customer emails.\n")

    result = await team.run(
        task="Check the inbox for any recent emails. Read each one, tag it with a category and priority, and send a helpful reply."
    )

    print("\n--- Agent Summary ---")
    for msg in result.messages:
        if hasattr(msg, "content") and isinstance(msg.content, str) and msg.content:
            print(f"[{msg.source}]: {msg.content[:200]}")


if __name__ == "__main__":
    asyncio.run(main())
