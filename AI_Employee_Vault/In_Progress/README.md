# In Progress Tasks

This folder contains tasks that are currently being worked on.

## Claim-by-Move Rule

When an agent (Claude Code instance) starts working on a task from `/Needs_Action/`, it MUST:

1. Move the task file to `/In_Progress/<agent_name>/`
2. This claims ownership of the task
3. Other agents must ignore files in `/In_Progress/`

## Structure

```
In_Progress/
├── agent1/
│   ├── TASK_email_reply.md
│   └── TASK_invoice_create.md
├── agent2/
│   └── TASK_social_post.md
```

## Rules

- **Single-writer rule:** Only one agent can claim a task at a time
- **Timeout:** If a task sits in In_Progress for > 24 hours, it should be moved back to Needs_Action
- **Completion:** When done, move task to `/Done/` folder
- **Failure:** If task fails, move back to `/Needs_Action/` with error notes
