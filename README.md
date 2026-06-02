# MultiMail + AutoGen Examples

Example agents that use [Microsoft AutoGen](https://microsoft.github.io/autogen/) with [MultiMail](https://multimail.dev) for AI-powered email workflows.

## Examples

### 1. Customer Support Agent (`examples/customer_support_agent.py`)

A single AutoGen `AssistantAgent` that monitors an inbox and auto-responds to customer emails. It reads each email, tags it by category and priority, and drafts a professional reply.

**What it demonstrates:**
- AutoGen tool calling with the MultiMail Python SDK
- `RoundRobinGroupChat` with a single agent
- Tagging emails for tracking
- Automated reply generation

### 2. Email Triage Agent (`examples/email_triage_agent.py`)

A two-agent team using `SelectorGroupChat`:
- **inbox_reader** — fetches and presents email content
- **triage_agent** — classifies emails by category, priority, and sentiment

**What it demonstrates:**
- Multi-agent coordination with `SelectorGroupChat`
- Separation of I/O (reading emails) from logic (classification)
- Contact management (auto-adding new senders)
- Structured output (summary table)

## Setup

1. **Install dependencies:**

```bash
pip install -r requirements.txt
```

2. **Configure environment:**

```bash
cp .env.example .env
```

Edit `.env` with your keys:
- `OPENAI_API_KEY` — your OpenAI API key ([platform.openai.com](https://platform.openai.com))
- `MULTIMAIL_API_KEY` — your MultiMail API key ([multimail.dev](https://multimail.dev))
- `MULTIMAIL_MAILBOX_ID` — your mailbox ID (find it in the MultiMail dashboard)

3. **Run an example:**

```bash
python examples/customer_support_agent.py
python examples/email_triage_agent.py
```

## How it works

AutoGen agents use **tool calling** to interact with MultiMail. Each tool is a plain Python function that calls the MultiMail SDK. AutoGen handles the LLM conversation loop, tool dispatch, and multi-agent coordination.

```
User Task
  |
  v
AutoGen Agent (GPT-4o)
  |-- decides which tool to call
  v
Tool Function (e.g., check_inbox)
  |-- calls MultiMail Python SDK
  v
MultiMail API (https://api.multimail.dev)
  |-- returns email data
  v
AutoGen Agent
  |-- processes result, calls next tool or responds
```

## Compliance

MultiMail handles regulatory compliance at the infrastructure layer — no SDK-side code changes needed:

- **EU AI Act Article 50**: Every AI-sent email includes a cryptographically signed `ai_generated` disclosure in the `X-MultiMail-Identity` header
- **US State Laws**: Maine, New York, California, Illinois — AI disclosure built into email delivery
- **CAN-SPAM**: Unsubscribe headers and physical address footers on all outbound email
- **Formally Verified**: Lean 4 proofs of identity header tamper evidence

These examples are current for MultiMail v0.5.4.

See [multimail.dev/use-cases/eu-ai-act-email-compliance](https://multimail.dev/use-cases/eu-ai-act-email-compliance) for details.

## MultiMail oversight modes

MultiMail supports graduated trust levels for agent email access:

| Mode | Behavior |
|------|----------|
| `gated_all` | Agent drafts, human approves everything |
| `gated_send` | Agent reads freely, human approves outbound (default) |
| `monitored` | Agent sends freely, human can review |
| `autonomous` | Full agent control |

Start with `gated_send` and increase autonomy as you build trust.

## Learn more

- [MultiMail documentation](https://multimail.dev)
- [MultiMail Python SDK](https://pypi.org/project/multimail/)
- [AutoGen documentation](https://microsoft.github.io/autogen/)
- [AutoGen AgentChat tutorial](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/agents.html)
