# Personal AI Employee (Digital FTE)

## Project Overview

This project implements a **Personal AI Employee** (Digital FTE - Full-Time Equivalent): a local-first, autonomous AI agent system that manages personal and business affairs 24/7. The architecture uses **Claude Code** as the reasoning engine and **Obsidian** as the knowledge base/dashboard, with lightweight Python "Watcher" scripts for perception and **MCP (Model Context Protocol)** servers for actions.

**Core Philosophy:** Transform AI from a reactive chatbot into a proactive business partner that works autonomously with human-in-the-loop oversight.

## Architecture

### Components

| Layer | Component | Purpose |
|-------|-----------|---------|
| **Brain** | Claude Code | Reasoning engine, task planning, decision-making |
| **Memory/GUI** | Obsidian Vault | Long-term memory, dashboard, task tracking (Markdown-based) |
| **Senses** | Python Watchers | Monitor Gmail, WhatsApp, filesystems, bank transactions |
| **Hands** | MCP Servers | External actions (email, browser automation, payments) |
| **Persistence** | Ralph Wiggum Loop | Keep Claude working until tasks complete |

### Folder Structure

```
Ai-Employee/
├── .qwen/skills/           # Qwen skills (browsing-with-playwright)
├── skills-lock.json        # Skill versioning
├── Personal AI Employee Hackathon 0_ Building Autonomous FTEs in 2026.md  # Full blueprint
└── QWEN.md                 # This file
```

### Obsidian Vault Structure (to be created)

```
Vault/
├── Dashboard.md            # Real-time summary (bank, tasks, projects)
├── Company_Handbook.md     # Rules of engagement
├── Business_Goals.md       # Q1/Q2 objectives, metrics
├── Inbox/                  # Raw incoming items
├── Needs_Action/           # Items requiring attention
├── In_Progress/<agent>/    # Claimed tasks (claim-by-move rule)
├── Pending_Approval/       # Human-in-the-loop approvals
├── Approved/               # Approved actions ready for execution
├── Done/                   # Completed tasks
├── Plans/                  # Multi-step task plans (Plan.md)
├── Accounting/             # Bank transactions, Current_Month.md
└── Briefings/              # Monday Morning CEO Briefings
```

## Key Concepts

### Watchers (Perception Layer)

Lightweight Python scripts that run continuously, monitoring inputs:

- **Gmail Watcher:** Monitors unread/important emails, creates `.md` files in `Needs_Action/`
- **WhatsApp Watcher:** Uses Playwright to monitor WhatsApp Web for keywords (urgent, invoice, payment)
- **File System Watcher:** Monitors drop folders for new files to process
- **Finance Watcher:** Downloads bank transactions, logs to `Accounting/Current_Month.md`

### Ralph Wiggum Loop (Persistence)

A Stop hook pattern that keeps Claude Code working autonomously until tasks are complete:

1. Orchestrator creates state file with prompt
2. Claude works on task
3. Claude tries to exit
4. Stop hook checks: Is task file in `/Done`?
5. If NO → Block exit, re-inject prompt (loop continues)
6. Repeat until complete or max iterations

Reference: https://github.com/anthropics/claude-code/tree/main/.claude/plugins/ralph-wiggum

### Human-in-the-Loop (HITL)

For sensitive actions (payments, sending messages), Claude writes an approval request file instead of acting directly:

```markdown
---
type: approval_request
action: payment
amount: 500.00
recipient: Client A
status: pending
---

## To Approve
Move this file to /Approved folder.

## To Reject
Move this file to /Rejected folder.
```

### Monday Morning CEO Briefing

Autonomous weekly audit (scheduled Sunday night) that generates:

- **Revenue:** Total earned this week, MTD progress
- **Bottlenecks:** Tasks that took too long
- **Proactive Suggestions:** Unused subscriptions, cost optimization

## Building and Running

### Prerequisites

| Component | Version | Purpose |
|-----------|---------|---------|
| [Claude Code](https://claude.com/product/claude-code) | Active subscription | Primary reasoning engine |
| [Obsidian](https://obsidian.md/download) | v1.10.6+ | Knowledge base & dashboard |
| [Python](https://www.python.org/downloads/) | 3.13+ | Watcher scripts, orchestration |
| [Node.js](https://nodejs.org/) | v24+ LTS | MCP servers |
| [GitHub Desktop](https://desktop.github.com/download/) | Latest | Version control |

**Hardware:** Minimum 8GB RAM, 4-core CPU, 20GB free disk. Recommended: 16GB RAM, 8-core CPU, SSD.

### Setup Steps

1. **Create Obsidian Vault:**
   ```bash
   mkdir AI_Employee_Vault
   cd AI_Employee_Vault
   mkdir Inbox Needs_Action In_Progress Pending_Approval Approved Done Plans Accounting Briefings
   ```

2. **Verify Claude Code:**
   ```bash
   claude --version
   ```

3. **Install Python dependencies (for watchers):**
   ```bash
   pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
   pip install playwright watchdog
   playwright install
   ```

4. **Start Playwright MCP Server (for WhatsApp/Browser automation):**
   ```bash
   # From project root
   bash .qwen/skills/browsing-with-playwright/scripts/start-server.sh
   ```

5. **Verify Playwright MCP:**
   ```bash
   python3 .qwen/skills/browsing-with-playwright/scripts/verify.py
   ```

### Running Watchers

```bash
# Gmail Watcher
python watchers/gmail_watcher.py --vault-path /path/to/vault --credentials /path/to/creds.json

# WhatsApp Watcher
python watchers/whatsapp_watcher.py --vault-path /path/to/vault --session /path/to/session

# File System Watcher
python watchers/filesystem_watcher.py --vault-path /path/to/vault --watch-folder /path/to/drops
```

### Running Claude Code with Ralph Wiggum Loop

```bash
# Start Ralph loop for task processing
claude "Process all files in /Needs_Action, move to /Done when complete" \
  --completion-promise "TASK_COMPLETE" \
  --max-iterations 10
```

### MCP Server Configuration

Configure in `~/.config/claude-code/mcp.json`:

```json
{
  "servers": [
    {
      "name": "email",
      "command": "node",
      "args": ["/path/to/email-mcp/index.js"],
      "env": {
        "GMAIL_CREDENTIALS": "/path/to/credentials.json"
      }
    },
    {
      "name": "browser",
      "command": "npx",
      "args": ["@anthropic/browser-mcp"],
      "env": {
        "HEADLESS": "true"
      }
    }
  ]
}
```

## Development Conventions

### Coding Style

- **Python:** Use type hints, follow PEP 8, docstrings for all public functions
- **Markdown:** Use YAML frontmatter for all `.md` files in vault
- **Watcher Scripts:** Inherit from `BaseWatcher` abstract class

### Testing Practices

- Each watcher should have unit tests for `check_for_updates()` and `create_action_file()`
- Integration tests for full watcher → Claude → MCP flow
- Use `verify.py` scripts for service health checks

### Security Rules

- **Secrets never sync:** `.env`, tokens, WhatsApp sessions, banking credentials stay local
- **Cloud vs Local split:** Cloud drafts only; Local executes sensitive actions
- **Single-writer rule:** Only Local writes to `Dashboard.md`

### Claim-by-Move Rule

To prevent double-work in multi-agent setups:

1. First agent to move item from `Needs_Action/` to `In_Progress/<agent>/` owns it
2. Other agents must ignore items in `In_Progress/`
3. Cloud writes updates to `/Updates/` or `/Signals/`; Local merges into `Dashboard.md`

## Achievement Tiers

| Tier | Description | Estimated Time |
|------|-------------|----------------|
| **Bronze** | Foundation: Obsidian vault, one watcher, Claude reading/writing | 8-12 hours |
| **Silver** | Functional: Multiple watchers, MCP server, HITL workflow | 20-30 hours |
| **Gold** | Autonomous: Full integration, Odoo accounting, weekly audit | 40+ hours |
| **Platinum** | Production: Cloud VM, domain specialization, A2A upgrade | 60+ hours |

## Available Skills

- **browsing-with-playwright:** Browser automation via Playwright MCP (navigate, fill forms, click, screenshots, data extraction)

## Resources

- **Full Blueprint:** `Personal AI Employee Hackathon 0_ Building Autonomous FTEs in 2026.md`
- **Playwright Tools:** `.qwen/skills/browsing-with-playwright/references/playwright-tools.md`
- **Ralph Wiggum Plugin:** https://github.com/anthropics/claude-code/tree/main/.claude/plugins/ralph-wiggum
- **Community Meetings:** Wednesdays 10:00 PM PKT on Zoom (link in blueprint)

## Common Commands

```bash
# Start Playwright MCP server
bash .qwen/skills/browsing-with-playwright/scripts/start-server.sh

# Stop Playwright MCP server
bash .qwen/skills/browsing-with-playwright/scripts/stop-server.sh

# Verify server running
python3 .qwen/skills/browsing-with-playwright/scripts/verify.py

# Navigate to URL (via MCP)
python3 scripts/mcp-client.py call -u http://localhost:8808 -t browser_navigate \
  -p '{"url": "https://example.com"}'

# Get page snapshot
python3 scripts/mcp-client.py call -u http://localhost:8808 -t browser_snapshot -p '{}'
```
