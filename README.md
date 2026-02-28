# AI Employee - Bronze Tier Implementation

A local-first, autonomous AI agent system that manages personal and business affairs using **Claude Code** as the reasoning engine and **Obsidian** as the knowledge base/dashboard.

## 🏆 Bronze Tier Deliverables

✅ **Obsidian vault** with Dashboard.md and Company_Handbook.md  
✅ **One working Watcher script** (File System monitoring)  
✅ **Claude Code** reading from and writing to the vault  
✅ **Basic folder structure:** /Inbox, /Needs_Action, /Done, /Plans, /Pending_Approval, /Approved, /Rejected, /Accounting, /Briefings  

## 📁 Project Structure

```
Ai-Employee/
├── AI_Employee_Vault/       # Obsidian vault (open this in Obsidian)
│   ├── Dashboard.md         # Real-time status dashboard
│   ├── Company_Handbook.md  # Rules of engagement
│   ├── Business_Goals.md    # Q1/Q2 objectives
│   ├── Inbox/               # Raw incoming items
│   ├── Needs_Action/        # Items requiring attention
│   ├── Done/                # Completed tasks
│   ├── Plans/               # Multi-step task plans
│   ├── Pending_Approval/    # Awaiting human approval
│   ├── Approved/            # Approved actions ready to execute
│   ├── Rejected/            # Rejected actions
│   ├── Accounting/          # Financial records, rates
│   ├── Briefings/           # CEO briefings
│   ├── Invoices/            # Generated invoices
│   └── Logs/                # Activity logs
├── watchers/
│   ├── base_watcher.py      # Abstract base class for all watchers
│   └── filesystem_watcher.py # File system monitor (Bronze tier)
├── orchestrator.py          # Main coordination script
├── requirements.txt         # Python dependencies
└── README.md                # This file
```

## 🚀 Quick Start

### Prerequisites

| Software | Version | Purpose |
|----------|---------|---------|
| [Python](https://www.python.org/downloads/) | 3.13+ | Watcher scripts |
| [Claude Code](https://claude.com/product/claude-code) | Latest | Reasoning engine |
| [Obsidian](https://obsidian.md/download) | v1.10.6+ | Knowledge base |
| [Node.js](https://nodejs.org/) | v24+ LTS | For future MCP servers |

### 1. Install Python Dependencies

```bash
cd D:\Ai-Employee
pip install -r requirements.txt
```

### 2. Verify Claude Code Installation

```bash
claude --version
```

If not installed:
```bash
npm install -g @anthropic/claude-code
```

### 3. Open the Vault in Obsidian

1. Open Obsidian
2. Click "Open folder as vault"
3. Select: `D:\Ai-Employee\AI_Employee_Vault`

### 4. Create a Drop Folder

Create a folder to drop files into for processing:

```bash
mkdir D:\Ai-Employee\drop_folder
```

### 5. Start the File System Watcher

```bash
# Terminal 1: Start the watcher
python watchers/filesystem_watcher.py --vault-path "D:\Ai-Employee\AI_Employee_Vault" --watch-folder "D:\Ai-Employee\drop_folder"
```

Leave this running in the background.

### 6. Test the System

1. **Drop a test file:**
   ```bash
   # Copy the test file to the drop folder
   copy "D:\Ai-Employee\AI_Employee_Vault\Inbox\test_file.md" "D:\Ai-Employee\drop_folder\"
   ```

2. **Watch for the action file:**
   - Check `AI_Employee_Vault/Needs_Action/` for new files
   - The watcher should create a `.meta.md` file

3. **Run the Orchestrator (Interactive Mode):**
   ```bash
   # Terminal 2: Process items with Claude
   python orchestrator.py --vault-path "D:\Ai-Employee\AI_Employee_Vault" --interactive
   ```

## 📖 Usage Guide

### How It Works

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Drop Folder    │────▶│  File Watcher    │────▶│  Needs_Action/  │
│  (you drop)     │     │  (monitors)      │     │  (created)      │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
                                                          ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Done/          │◀────│  Claude Code     │◀────│  Orchestrator   │
│  (completed)    │     │  (processes)     │     │  (triggers)     │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

### File Drop Workflow

1. **Drop a file** into the watch folder (`D:\Ai-Employee\drop_folder\`)
2. **Watcher detects** the new file within 5 seconds
3. **Action file created** in `Needs_Action/` with metadata
4. **Orchestrator triggers** Claude Code to process
5. **Claude reads** Company Handbook and processes the item
6. **Result logged** and file moved to `Done/`

### Running Modes

#### Continuous Mode (Background)

```bash
# Run watcher continuously
python watchers/filesystem_watcher.py --vault-path "D:\Ai-Employee\AI_Employee_Vault" --watch-folder "D:\Ai-Employee\drop_folder"

# Run orchestrator continuously (auto mode)
python orchestrator.py --vault-path "D:\Ai-Employee\AI_Employee_Vault"
```

#### Interactive Mode (Manual Processing)

```bash
# Process items manually with Claude
python orchestrator.py --vault-path "D:\Ai-Employee\AI_Employee_Vault" --interactive
```

#### Process Once

```bash
# Process all pending items once and exit
python orchestrator.py --vault-path "D:\Ai-Employee\AI_Employee_Vault" --process-once
```

## 📋 Company Handbook Rules

The AI Employee follows these rules (defined in `Company_Handbook.md`):

### Financial Rules
- **Payments over $500:** Always require approval
- **New subscriptions:** Always require approval
- **Invoices:** Auto-generate for known clients <$100

### Communication Rules
- **Email replies:** Auto-draft for known contacts
- **Urgent messages:** Flag immediately for human review
- **Unknown senders:** Require approval before responding

### File Operations
- **Create/Read:** Always allowed
- **Move within vault:** Allowed
- **Delete:** Never without approval

## 🔧 Configuration

### Watcher Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--vault-path` | Required | Path to Obsidian vault |
| `--watch-folder` | Required | Folder to monitor |
| `--interval` | 5 seconds | Check interval |

### Orchestrator Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--vault-path` | Required | Path to Obsidian vault |
| `--interval` | 60 seconds | Check interval |
| `--interactive` | Off | Launch Claude Code |
| `--process-once` | Off | Process and exit |

## 🧪 Testing the Bronze Tier

### Test Checklist

- [ ] Vault folders created
- [ ] Dashboard.md exists and updates
- [ ] Company_Handbook.md readable
- [ ] File watcher starts without errors
- [ ] Dropping a file creates action file in Needs_Action/
- [ ] Orchestrator can trigger Claude Code
- [ ] Claude can read and write to vault
- [ ] Completed items move to Done/

### Run Verification

```bash
# 1. Check Python installation
python --version  # Should be 3.13+

# 2. Check dependencies
pip list | findstr watchdog  # Should show watchdog>=4.0.0

# 3. Check Claude Code
claude --version

# 4. Test watcher (run for 10 seconds)
python watchers/filesystem_watcher.py --vault-path "D:\Ai-Employee\AI_Employee_Vault" --watch-folder "D:\Ai-Employee\drop_folder"

# 5. Drop a test file and verify action file is created
```

## 📝 Next Steps (Silver Tier)

To upgrade to Silver Tier, add:

1. **Gmail Watcher** - Monitor Gmail for important emails
2. **WhatsApp Watcher** - Monitor WhatsApp Web for keywords
3. **MCP Server** - Send emails automatically
4. **Human-in-the-Loop** - Approval workflow for sensitive actions
5. **Scheduled Tasks** - Cron/Task Scheduler integration
6. **Plan.md Creation** - Claude creates multi-step plans

## 🐛 Troubleshooting

### Watcher Not Detecting Files

1. Check the watch folder path is correct
2. Ensure folder exists and has read permissions
3. Check logs in `AI_Employee_Vault/Logs/`

### Claude Code Not Found

```bash
# Install globally
npm install -g @anthropic/claude-code

# Verify installation
claude --version
```

### Action Files Not Created

1. Check Python has write access to vault
2. Verify `Needs_Action/` folder exists
3. Check logs for errors

### Dashboard Not Updating

1. Ensure `Dashboard.md` exists in vault root
2. Check orchestrator has write permissions
3. Run orchestrator with `--verbose` flag

## 📚 Resources

- [Full Hackathon Blueprint](./Personal%20AI%20Employee%20Hackathon%200_%20Building%20Autonomous%20FTEs%20in%202026.md)
- [Obsidian Documentation](https://help.obsidian.md/)
- [Claude Code Documentation](https://claude.com/product/claude-code)
- [Watchdog Documentation](https://pythonhosted.org/watchdog/)

## 🤝 Community

Join the weekly meetings:
- **When:** Wednesdays 10:00 PM PKT
- **Zoom:** [Link in hackathon blueprint](./Personal%20AI%20Employee%20Hackathon%200_%20Building%20Autonomous%20FTEs%20in%202026.md)
- **YouTube:** [@panaversity](https://www.youtube.com/@panaversity)

---

*AI Employee v0.1 - Bronze Tier | Built with Claude Code + Obsidian*
