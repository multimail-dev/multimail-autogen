"""
Email Triage — Multi-Agent Setup with AutoGen + MultiMail

Two-agent team using SelectorGroupChat:
  1. inbox_reader — reads and fetches emails from MultiMail
  2. triage_agent — analyzes content, categorizes, assigns priority, and tags

The selector model routes the conversation: inbox_reader fetches data,
triage_agent processes it. This demonstrates how to split email I/O from
classification logic across specialized agents.

Usage:
    cp .env.example .env   # fill in your keys
    pip install -r requirements.txt
    python examples/email_triage_agent.py
"""

import asyncio
import json
import os

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import SelectorGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv
from multimail import MultiMail

load_dotenv()

# --- Config ---

mm = MultiMail(api_key=os.environ["MULTIMAIL_API_KEY"])
MAILBOX_ID = os.environ["MULTIMAIL_MAILBOX_ID"]


# --- Tools for inbox_reader ---


async def check_inbox(limit: int = 20) -> str:
    """Check the inbox for recent inbound emails. Returns JSON summaries
    with id, from, subject, status, and received_at."""
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
    """Read the full content of an email by ID. Returns the complete email
    including markdown body, sender, subject, and any attachments."""
    result = mm.get_email(MAILBOX_ID, email_id)
    return json.dumps(result, default=str)


async def get_thread(thread_id: str) -> str:
    """Get all emails in a thread to understand the full conversation context."""
    result = mm.get_thread(MAILBOX_ID, thread_id)
    return json.dumps(result, default=str)


# --- Tools for triage_agent ---


async def tag_email(email_id: str, category: str, priority: str, sentiment: str) -> str:
    """Tag an email with triage results.
    - category: one of billing, technical, feature-request, bug-report, spam, general
    - priority: one of low, normal, high, urgent
    - sentiment: one of positive, neutral, negative, angry"""
    tags = {"category": category, "priority": priority, "sentiment": sentiment}
    result = mm.set_tags(MAILBOX_ID, email_id, tags)
    return json.dumps(result, default=str)


async def add_contact(email: str, name: str) -> str:
    """Add or update a contact in the address book. Use this when you encounter
    a new sender that should be tracked."""
    result = mm.add_contact(email, name)
    return json.dumps(result, default=str)


async def search_contacts(query: str) -> str:
    """Search contacts to check if a sender is already known."""
    contacts = mm.list_contacts(q=query)
    return json.dumps(contacts, default=str)


# --- Agent definitions ---

READER_SYSTEM = """\
You are the inbox reader. Your only job is to fetch emails from the inbox and
provide their content to the triage agent. You have tools to:
- check_inbox: list recent emails
- read_email: get full email content
- get_thread: get conversation history

Workflow:
1. Start by calling check_inbox to get recent emails
2. For each email, call read_email to get the full content
3. Present the email data clearly so the triage_agent can classify it
4. After presenting all emails, say "All emails have been read."
"""

TRIAGE_SYSTEM = """\
You are the triage agent. You analyze emails provided by the inbox_reader and
classify them. You have tools to tag emails and manage contacts.

For each email, determine:
1. **Category**: billing, technical, feature-request, bug-report, spam, or general
2. **Priority**:
   - urgent: service outage, security issue, payment failure
   - high: blocking bug, upgrade request, angry customer
   - normal: general question, feature request, minor bug
   - low: newsletter reply, informational, positive feedback
3. **Sentiment**: positive, neutral, negative, or angry

After analyzing each email:
1. Tag it using the tag_email tool
2. Check if the sender is a known contact; if not, add them

When all emails are triaged, output a summary table and say "TRIAGE_COMPLETE".

Example summary:
| # | From | Subject | Category | Priority | Sentiment |
|---|------|---------|----------|----------|-----------|
| 1 | alice@co.com | Can't login | technical | high | negative |
| 2 | bob@co.com | Love the product | general | low | positive |
"""


async def main():
    model = OpenAIChatCompletionClient(model="gpt-4o")

    inbox_reader = AssistantAgent(
        name="inbox_reader",
        model_client=model,
        tools=[check_inbox, read_email, get_thread],
        system_message=READER_SYSTEM,
        description="Reads and fetches emails from the inbox. Call this agent when you need to retrieve email data.",
        max_tool_iterations=15,
    )

    triage_agent = AssistantAgent(
        name="triage_agent",
        model_client=model,
        tools=[tag_email, add_contact, search_contacts],
        system_message=TRIAGE_SYSTEM,
        description="Analyzes email content and categorizes it by type, priority, and sentiment. Call this agent after emails have been read.",
        max_tool_iterations=15,
    )

    termination = MaxMessageTermination(max_messages=40) | TextMentionTermination("TRIAGE_COMPLETE")

    team = SelectorGroupChat(
        participants=[inbox_reader, triage_agent],
        model_client=model,
        termination_condition=termination,
        selector_prompt=(
            "Select the next agent to speak. The inbox_reader should go first to "
            "fetch emails, then the triage_agent should classify them. If the "
            "inbox_reader has more emails to read, select inbox_reader. If emails "
            "have been presented and need classification, select triage_agent. "
            "Available agents: {roles}. Current conversation context: {history}"
        ),
    )

    print("Email Triage — Multi-Agent (AutoGen + MultiMail)")
    print("=" * 50)
    print("inbox_reader fetches emails, triage_agent categorizes them.\n")

    result = await team.run(
        task="Fetch all recent inbound emails from the inbox, read each one, and triage them by category, priority, and sentiment."
    )

    print("\n--- Conversation Log ---")
    for msg in result.messages:
        if hasattr(msg, "content") and isinstance(msg.content, str) and msg.content:
            source = getattr(msg, "source", "system")
            # Print full content for the final summary, truncate intermediate messages
            if "TRIAGE_COMPLETE" in msg.content or "|" in msg.content:
                print(f"\n[{source}]:\n{msg.content}")
            else:
                print(f"[{source}]: {msg.content[:150]}...")


if __name__ == "__main__":
    asyncio.run(main())
