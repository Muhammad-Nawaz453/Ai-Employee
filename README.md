# AI Employee - Silver Tier Implementation

A local-first, autonomous AI agent system that manages personal and business affairs using **Claude Code** as the reasoning engine and **Obsidian** as the knowledge base/dashboard.

## 🏆 Silver Tier Deliverables

✅ **All Bronze requirements** plus:

| Feature | Status | Description |
|---------|--------|-------------|
| **Gmail Watcher** | ✅ | Monitor Gmail for important emails |
| **WhatsApp Watcher** | ✅ | Monitor WhatsApp Web for keywords |
| **LinkedIn MCP Server** | ✅ | Auto-post about business to generate sales |
| **HITL Approval Workflow** | ✅ | Human-in-the-loop for sensitive actions |
| **Ralph Wiggum Loop** | ✅ | Autonomous multi-step task completion |
| **Plan.md Generation** | ✅ | Create plans for complex tasks |
| **Task Scheduler** | ✅ | Windows Task Scheduler / cron integration |
| **Scheduled Tasks** | ✅ | Daily briefing, weekly audit, health checks |

## 📁 Project Structure

```
Ai-Employee/
├── AI_Employee_Vault/       # Obsidian vault (open this in Obsidian)
│   ├── Dashboard.md         # Real-time status dashboard (Silver Tier)
│   ├── Company_Handbook.md  # Rules of engagement (v0.2 Silver)
│   ├── Business_Goals.md    # Q1/Q2 objectives
│   ├── Inbox/               # Raw incoming items
│   ├── Needs_Action/        # Items requiring attention
│   ├── Done/                # Completed tasks
│   ├── Plans/               # Multi-step task plans
│   ├── Pending_Approval/    # Awaiting human approval (HITL)
│   ├── Approved/            # Approved actions ready to execute
│   ├── Rejected/            # Rejected actions
│   ├── Accounting/          # Financial records, rates
│   ├── Briefings/           # CEO briefings (daily/weekly)
│   ├── Invoices/            # Generated invoices
│   └── Logs/                # Activity logs, health checks
├── watchers/
│   ├── base_watcher.py      # Abstract base class for all watchers
│   ├── filesystem_watcher.py # File system monitor (Bronze)
│   ├── gmail_watcher.py     # Gmail monitor (Silver)
│   ├── whatsapp_watcher.py  # WhatsApp Web monitor (Silver)
│   ├── hitl_approval.py     # Human-in-the-Loop approval (Silver)
│   └── plan_manager.py      # Plan.md generation (Silver)
├── mcp_servers/
│   └── linkedin-mcp/        # LinkedIn automation server (Silver)
│       ├── package.json
│       ├── index.js
│       └── start-server.bat
├── mcp_servers/
│   └── verify-linkedin-mcp.py  # MCP verification script
├── orchestrator.py          # Main coordination (Silver: Ralph Loop)
├── task_scheduler.py        # Windows Task Scheduler integration
├── scheduled_tasks.py       # Daily briefing, weekly audit, health check
├── verify_silver_tier.py    # Comprehensive verification script
├── requirements.txt         # Python dependencies (Silver Tier)
└── README.md                # This file
```

## 🚀 Quick Start

### Prerequisites

| Software | Version | Purpose |
|----------|---------|---------|
| [Python](https://www.python.org/downloads/) | 3.13+ | Watcher scripts |
| [Claude Code](https://claude.com/product/claude-code) | Latest | Reasoning engine |
| [Obsidian](https://obsidian.md/download) | v1.10.6+ | Knowledge base |
| [Node.js](https://nodejs.org/) | v24+ LTS | MCP servers |

### 1. Install Dependencies

```bash
cd D:\Ai-Employee
pip install -r requirements.txt
```

**Silver Tier includes:**
- `watchdog` - File system watching
- `google-api-python-client` - Gmail API
- `playwright` - WhatsApp automation
- `requests` - HTTP requests
- `python-dotenv` - Environment variables
- `jsonschema` - JSON validation
- `schedule` - Task scheduling
- `rich` - Terminal output

### 2. Verify Installation

```bash
# Run Silver Tier verification
python verify_silver_tier.py --vault-path "D:\Ai-Employee\AI_Employee_Vault"
```

### 3. Open the Vault in Obsidian

1. Open Obsidian
2. Click "Open folder as vault"
3. Select: `D:\Ai-Employee\AI_Employee_Vault`

### 4. Start Watchers

```bash
# Terminal 1: File System Watcher
python watchers/filesystem_watcher.py --vault-path "D:\Ai-Employee\AI_Employee_Vault" --watch-folder "D:\Ai-Employee\drop_folder"

# Terminal 2: Gmail Watcher (requires credentials)
python watchers/gmail_watcher.py --vault-path "D:\Ai-Employee\AI_Employee_Vault" --credentials "path/to/credentials.json"

# Terminal 3: WhatsApp Watcher (first run: scan QR code)
python watchers/whatsapp_watcher.py --vault-path "D:\Ai-Employee\AI_Employee_Vault" --session "D:\Ai-Employee\whatsapp_session" --no-headless
```

### 5. Start LinkedIn MCP Server

```bash
# Verify MCP server
python mcp_servers/verify-linkedin-mcp.py

# Start server
mcp_servers\linkedin-mcp\start-server.bat
```

### 6. Run the Orchestrator

```bash
# Interactive mode
python orchestrator.py --vault-path "D:\Ai-Employee\AI_Employee_Vault" --interactive

# Ralph Wiggum Loop (autonomous)
python orchestrator.py --vault-path "D:\Ai-Employee\AI_Employee_Vault" --ralph-loop

# Check status
python orchestrator.py --vault-path "D:\Ai-Employee\AI_Employee_Vault" --status
```

### 7. Install Scheduled Tasks

```bash
# Install all scheduled tasks
python task_scheduler.py install-all --vault-path "D:\Ai-Employee\AI_Employee_Vault"

# List installed tasks
python task_scheduler.py list --vault-path "D:\Ai-Employee\AI_Employee_Vault"
```

## 📖 Usage Guide

### How Silver Tier Works

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Gmail          │     │  Gmail Watcher   │     │  Needs_Action/  │
│  WhatsApp       │────▶│  WhatsApp Watcher│────▶│  (action files) │
│  Drop Folder    │     │  File Watcher    │     │                 │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
                                                          ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Done/          │◀────│  Ralph Wiggum    │◀────│  Orchestrator   │
│  (completed)    │     │  Loop            │     │                 │
└─────────────────┘     │  (autonomous)    │     └─────────────────┘
                        └────────┬─────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
            ┌──────────┐ ┌──────────┐ ┌──────────────┐
            │  Plans/  │ │ Pending_ │ │  Approved/   │
            │  (plans) │ │ Approval │ │  (execute)   │
            └──────────┘ └──────────┘ └──────────────┘
```

### Watcher Comparison

| Watcher | Purpose | Check Interval | Setup Complexity |
|---------|---------|----------------|------------------|
| File System | Monitor drop folder | 5 seconds | Easy |
| Gmail | Monitor important emails | 2 minutes | Medium (OAuth) |
| WhatsApp | Monitor urgent messages | 1 minute | Medium (QR scan) |

### Gmail Watcher Setup

1. **Enable Gmail API:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create new project
   - Enable Gmail API
   - Create OAuth 2.0 credentials
   - Download `credentials.json`

2. **First Run:**
   ```bash
   python watchers/gmail_watcher.py --vault-path "VAULT" --credentials "path/to/credentials.json"
   ```
   - Browser will open for authentication
   - Grant Gmail permissions
   - Token saved to `~/.gmail_token.json`

3. **Configure VIP Senders (optional):**
   ```bash
   set GMAIL_VIP_SENDERS=boss@company.com,client@example.com
   ```

### WhatsApp Watcher Setup

1. **First Run (with visible browser):**
   ```bash
   python watchers/whatsapp_watcher.py --vault-path "VAULT" --session "whatsapp_session" --no-headless
   ```

2. **Scan QR Code:**
   - Open WhatsApp on phone
   - Settings > Linked Devices
   - Scan QR code in browser

3. **Subsequent Runs (headless):**
   ```bash
   python watchers/whatsapp_watcher.py --vault-path "VAULT" --session "whatsapp_session"
   ```

### LinkedIn MCP Server Setup

1. **Install Dependencies:**
   ```bash
   cd mcp_servers\linkedin-mcp
   npm install
   ```

2. **Start Server:**
   ```bash
   mcp_servers\linkedin-mcp\start-server.bat
   ```

3. **Configure in Claude Code:**
   Add to `~/.config/claude-code/mcp.json`:
   ```json
   {
     "servers": [
       {
         "name": "linkedin",
         "command": "node",
         "args": ["D:/Ai-Employee/mcp_servers/linkedin-mcp/index.js"],
         "env": {
           "VAULT_PATH": "D:/Ai-Employee/AI_Employee_Vault",
           "LINKEDIN_SESSION_PATH": "D:/Ai-Employee/mcp_servers/linkedin-mcp/session"
         }
       }
     ]
   }
   ```

### Human-in-the-Loop (HITL) Workflow

For sensitive actions, the AI creates an approval request:

1. **AI Creates Request:**
   - File created in `/Pending_Approval/`
   - Contains full details of proposed action
   - Expires in 24 hours (default)

2. **Human Reviews:**
   - Read the request details
   - Move to `/Approved/` to approve
   - Move to `/Rejected/` to decline

3. **AI Executes:**
   - Approved actions executed automatically
   - Results logged
   - File moved to `/Done/`

**Example Approval Request:**
```markdown
---
type: approval_request
action: linkedin_post
created: 2026-03-10T10:00:00
status: pending
---

# LinkedIn Post Approval Request

## Post Content

Excited to announce our new AI Employee Silver Tier! 🚀

#AI #Automation #Productivity

## To Approve
Move this file to /Approved/ folder.
```

### Ralph Wiggum Loop

The Ralph Wiggum Loop keeps Claude Code working autonomously:

```bash
# Start autonomous processing
python orchestrator.py --vault-path "VAULT" --ralph-loop

# Custom prompt
python orchestrator.py --vault-path "VAULT" --ralph-loop "Process all pending items and create weekly report"
```

**How it works:**
1. Loop checks for pending items
2. Launches Claude Code with prompt
3. Claude processes items
4. Loop checks: Are tasks complete?
5. If NO → Repeat (up to max iterations)
6. If YES → Exit loop

### Scheduled Tasks

| Task | Schedule | Description |
|------|----------|-------------|
| Daily Briefing | 08:00 Daily | Morning status report |
| Weekly Audit | Sunday 19:00 | CEO briefing with revenue/bottlenecks |
| Health Check | Every Hour | System health monitoring |
| Dashboard Update | Every 15 min | Refresh dashboard stats |

**Manual execution:**
```bash
# Daily briefing
python scheduled_tasks.py --vault-path "VAULT" --task daily_briefing

# Weekly audit
python scheduled_tasks.py --vault-path "VAULT" --task weekly_audit

# Health check
python scheduled_tasks.py --vault-path "VAULT" --task health_check
```

## 📋 Company Handbook Rules (Silver Tier)

The AI Employee follows these rules:

### Communication Rules

| Action | Auto-Approve | Require Approval |
|--------|-------------|------------------|
| Email replies | Known contacts, routine | New contacts, sensitive |
| LinkedIn posts | Draft only | **All posts (HITL)** |
| WhatsApp | Read-only | All sends |

### LinkedIn Rules

1. **All posts require approval** before publishing
2. **Post frequency:** Maximum 2 posts per day
3. **Content guidelines:**
   - Focus on business value
   - Include 3-5 hashtags
   - Under 3000 characters
   - Professional tone

### Plan Creation

Create a Plan.md when:
- Task requires 3+ steps
- Task spans multiple categories
- Task has dependencies
- Estimated time >30 minutes

## 🧪 Testing Silver Tier

### Run Verification

```bash
python verify_silver_tier.py --vault-path "D:\Ai-Employee\AI_Employee_Vault"
```

### Test Checklist

- [ ] All Python dependencies installed
- [ ] Node.js and npm working
- [ ] Vault folders created
- [ ] Watchers start without errors
- [ ] Gmail watcher authenticates
- [ ] WhatsApp watcher connects
- [ ] LinkedIn MCP server starts
- [ ] Ralph Wiggum Loop runs
- [ ] Scheduled tasks installed
- [ ] Daily briefing generates

### Quick Functional Test

1. **Drop a test file:**
   ```bash
   echo "Test content" > drop_folder\test.txt
   ```

2. **Verify action file created:**
   - Check `AI_Employee_Vault/Needs_Action/`
   - Should see `FILE_test.txt.meta.md`

3. **Run orchestrator:**
   ```bash
   python orchestrator.py --vault-path "VAULT" --interactive
   ```

## 🔧 Configuration

### Environment Variables

```bash
# Gmail VIP senders
set GMAIL_VIP_SENDERS=boss@company.com,client@example.com

# LinkedIn MCP
set VAULT_PATH=D:\Ai-Employee\AI_Employee_Vault
set LINKEDIN_SESSION_PATH=D:\Ai-Employee\mcp_servers\linkedin-mcp\session
set HEADLESS=true
```

### Watcher Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--vault-path` | Required | Path to Obsidian vault |
| `--watch-folder` | Required | Folder to monitor (file watcher) |
| `--credentials` | Required | Gmail API credentials |
| `--session` | Required | WhatsApp session path |
| `--interval` | 5-120s | Check interval |

### Orchestrator Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--vault-path` | Required | Path to Obsidian vault |
| `--interval` | 60s | Check interval |
| `--interactive` | Off | Launch Claude Code |
| `--ralph-loop` | Off | Autonomous mode |
| `--status` | Off | Show status |

## 🐛 Troubleshooting

### Gmail Watcher Issues

**Problem:** Authentication fails
```bash
# Delete token and re-authenticate
del %USERPROFILE%\.gmail_token.json
python watchers/gmail_watcher.py --vault-path "VAULT" --credentials "creds.json"
```

**Problem:** No emails found
- Check Gmail API is enabled
- Verify credentials.json is correct
- Ensure emails are unread

### WhatsApp Watcher Issues

**Problem:** QR code not showing
```bash
# Run with visible browser
python watchers/whatsapp_watcher.py --vault-path "VAULT" --session "session" --no-headless
```

**Problem:** Session expired
- Delete session folder
- Re-scan QR code

### LinkedIn MCP Issues

**Problem:** Server won't start
```bash
# Check Node.js
node --version

# Reinstall dependencies
cd mcp_servers\linkedin-mcp
npm install
```

### Ralph Wiggum Loop Issues

**Problem:** Loop exits immediately
- Check for pending items in `Needs_Action/`
- Verify Claude Code is installed
- Check logs in `Logs/` folder

## 📊 Silver Tier vs Bronze Tier

| Feature | Bronze | Silver |
|---------|--------|--------|
| Watchers | 1 (File) | 3 (File, Gmail, WhatsApp) |
| MCP Servers | 0 | 1 (LinkedIn) |
| Approval Workflow | Basic | Full HITL |
| Task Completion | Manual | Ralph Wiggum Loop |
| Planning | None | Plan.md generation |
| Scheduling | None | Task Scheduler integration |
| Scheduled Tasks | None | 4 (briefing, audit, health, dashboard) |

## 📚 Resources

- [Full Hackathon Blueprint](./Personal%20AI%20Employee%20Hackathon%200_%20Building%20Autonomous%20FTEs%20in%202026.md)
- [Obsidian Documentation](https://help.obsidian.md/)
- [Claude Code Documentation](https://claude.com/product/claude-code)
- [Gmail API](https://developers.google.com/gmail/api)
- [Playwright Documentation](https://playwright.dev/)
- [Ralph Wiggum Plugin](https://github.com/anthropics/claude-code/tree/main/.claude/plugins/ralph-wiggum)

## 🤝 Community

Join the weekly meetings:
- **When:** Wednesdays 10:00 PM PKT
- **Zoom:** [Link in hackathon blueprint](./Personal%20AI%20Employee%20Hackathon%200_%20Building%20Autonomous%20FTEs%20in%202026.md)
- **YouTube:** [@panaversity](https://www.youtube.com/@panaversity)

## 🎯 Next Steps (Gold Tier)

To upgrade to Gold Tier, add:

1. **Odoo Accounting Integration** - Self-hosted accounting via MCP
2. **Facebook/Instagram Integration** - Social media posting
3. **Twitter (X) Integration** - Tweet posting
4. **Multiple MCP Servers** - Different action types
5. **Weekly Business Audit** - Full CEO briefing
6. **Error Recovery** - Graceful degradation
7. **Comprehensive Audit Logging** - Full history

---

*AI Employee v0.2 - Silver Tier | Built with Claude Code + Obsidian*
*Last updated: 2026-03-10*
