# ZOEY — FREE PERSONAL AI OPERATING SYSTEM
## Complete Architecture Specification — v1

> **Core requirement:** Everything in the base system must be free/open-source or run locally.
> No mandatory subscriptions, paid APIs, cloud AI, or paid hosting.
>
> **Wake word:** `Zoey`
>
> **Target:** A personal JARVIS-style assistant for Windows laptop + Android phone, synchronized, with voice, planning, notifications, memory, computer control, coding/building, email/message preparation, and controlled execution.

---

# 1. PRODUCT VISION

Zoey is not a chatbot.

Zoey is a personal operating layer that can:

- understand natural voice/text commands
- plan the user's day
- remember projects, tasks, people and decisions
- send notifications
- synchronize laptop and phone
- control the computer
- build websites/code/projects
- research the web
- prepare and send communications
- execute multi-step workflows
- ask for approval before risky actions
- proactively suggest useful actions

The user should be able to say:

> "Zoey, plan my day."

> "Zoey, build the landing page."

> "Zoey, remind me in 30 minutes."

> "Zoey, check who I need to follow up with."

> "Zoey, open the project and fix the error."

> "Zoey, draft an email to the client."

---

# 2. NON-NEGOTIABLE FREE-FIRST RULE

The base architecture must work without paid services.

## Use locally

- Local LLMs
- Local speech-to-text
- Local text-to-speech
- Local wake-word detection
- Local database
- Local vector/semantic memory
- Local notification engine
- Local desktop automation
- Local file storage
- Local task scheduler

## Optional integrations

External services can be added later, but Zoey must not depend on them for its core operation.

Examples:

- Gmail
- Google Calendar
- GitHub
- Vercel
- WhatsApp
- cloud AI models

If an integration requires money, it remains OPTIONAL.

---

# 3. HIGH-LEVEL ARCHITECTURE

```text
                         USER
                          |
                 +--------+--------+
                 |                 |
              LAPTOP             PHONE
                 |                 |
                 +--------+--------+
                          |
                   ZOEY SYNC LAYER
                          |
                 +--------+--------+
                 |                 |
              ZOEY CORE        EVENT BUS
                 |
        +--------+---------+
        |        |         |
     MEMORY   PLANNER   PERMISSIONS
        |        |         |
        +--------+---------+
                 |
           AGENT ROUTER
                 |
     +-----------+-----------+-----------+-----------+
     |           |           |           |           |
 Personal    Builder     Research   Communication  Computer
  Agent       Agent        Agent        Agent        Agent
     |           |           |           |           |
     +-----------+-----------+-----------+-----------+
                             |
                         TOOL SYSTEM
                             |
      +----------+-----------+----------+-----------+
      |          |           |          |           |
    Files     Browser    Terminal    Calendar   Notifications
      |          |           |          |           |
    Email     Computer    Git       Tasks       Phone
```

---

# 4. DEVICE ARCHITECTURE

## Windows laptop

The laptop is the primary execution device.

```text
Windows
 |
 +-- Zoey Desktop App
 |
 +-- Zoey Core Service
 |
 +-- Local AI Runtime
 |
 +-- Tool Runtime
 |
 +-- Local Database
 |
 +-- Notification Service
 |
 +-- Voice Service
 |
 +-- Computer Control Service
```

## Android phone

The phone is a synchronized companion.

```text
Android
 |
 +-- Zoey Mobile App
 |
 +-- Voice input
 |
 +-- Notifications
 |
 +-- Tasks
 |
 +-- Calendar
 |
 +-- Approval requests
 |
 +-- Quick commands
 |
 +-- Sync client
```

The phone should NOT contain a separate independent brain.

Both devices share Zoey's state.

---

# 5. CORE TECHNOLOGY STACK

## Desktop

- Tauri
- React
- TypeScript

Tauri provides the desktop application shell.

## Backend/core

- Python
- FastAPI/local service
- WebSocket communication
- asyncio

Python is preferred for AI, automation and local integrations.

## Database

- SQLite

SQLite is local, free and sufficient for a personal assistant.

## Memory

Start with:

- SQLite
- structured memory tables
- local embeddings

Optional:

- FAISS or another free local vector index

## Local AI

Use a local model runner such as:

- Ollama
- llama.cpp

Models can be downloaded locally and swapped without changing Zoey.

Recommended approach:

```text
Small local model
    -> routine commands

Larger local model
    -> planning/reasoning

Coding model
    -> software development

Embedding model
    -> semantic memory
```

No paid AI API is required.

---

# 6. VOICE ARCHITECTURE

## Wake word

The wake word is:

# ZOEY

Examples:

> "Zoey."

> "Hey Zoey."

Zoey should remain idle until the wake-word engine detects the name.

## Wake-word pipeline

```text
Microphone
   |
   v
Wake-word detector
   |
   | "Zoey" detected
   v
Speech-to-text
   |
   v
Intent parser
   |
   v
Planner / Agent Router
   |
   v
Tool execution
   |
   v
Text-to-speech
```

## Free/local components

Use local/open-source options for:

- wake word
- speech recognition
- speech synthesis

Do NOT make ElevenLabs mandatory.

The uploaded prototype's ElevenLabs integration can remain as an optional voice provider, but the free architecture must work without it.

---

# 7. ZOEY CORE

The core has six responsibilities.

```text
1. Understand
2. Remember
3. Plan
4. Delegate
5. Execute
6. Verify
```

Example:

User:

> "Zoey, get my dentist outreach done today."

Core:

```text
Understand goal
     |
Check tasks + leads + calendar
     |
Create plan
     |
Delegate to agents
     |
Execute safe actions
     |
Ask approval where necessary
     |
Verify completion
     |
Update memory
     |
Report result
```

---

# 8. MODEL ROUTER

Zoey must not depend on a single model.

```text
                 ZOEY
                   |
             MODEL ROUTER
                   |
        +----------+----------+
        |          |          |
     LOCAL 1    LOCAL 2    CODING
        |          |          |
    Routine     Reasoning   Coding
```

External models such as Claude, ChatGPT and Kimi can be connected later as OPTIONAL providers.

The system must still function if all external providers are unavailable.

## Provider interface

Every model should expose the same conceptual interface:

```text
generate()
stream()
tool_call()
summarize()
embed()
```

This allows models to be replaced without changing the rest of Zoey.

---

# 9. AGENTS

Start with five agents.

## 9.1 Personal Agent

Responsibilities:

- daily planning
- tasks
- routines
- reminders
- calendar
- personal organization
- morning briefing
- evening review

Example:

> "Zoey, organize tomorrow."

---

## 9.2 Builder Agent

Responsibilities:

- create projects
- inspect existing code
- write code
- modify files
- run commands
- debug
- test
- Git operations
- build websites
- build scripts
- prepare deployments

Example:

> "Zoey, build a landing page for this client."

---

## 9.3 Research Agent

Responsibilities:

- web research
- company research
- competitor research
- lead research
- documentation
- information extraction
- summarization

---

## 9.4 Communication Agent

Responsibilities:

- email drafts
- message drafts
- follow-ups
- communication history
- contact records

Default workflow:

```text
Draft
 |
Show user
 |
User approves
 |
Send
 |
Record action
```

---

## 9.5 Computer Agent

Responsibilities:

- launch applications
- control windows
- browser automation
- keyboard/mouse actions
- screenshots
- file operations
- terminal
- Windows automation

The uploaded Jarvis prototype can contribute reusable Windows automation concepts here.

---

# 10. TOOL SYSTEM

Agents NEVER directly control the operating system.

They request tools.

Example:

```text
Builder Agent
    |
    v
terminal.run(command)
```

or:

```text
Communication Agent
    |
    v
email.create_draft(...)
```

or:

```text
Personal Agent
    |
    v
tasks.create(...)
```

## Initial tools

```text
filesystem
terminal
browser
computer
tasks
calendar
notifications
clipboard
screenshot
process
email
contacts
git
```

---

# 11. PERMISSION SYSTEM

This is mandatory.

## LEVEL 0 — SAFE

No approval required.

Examples:

- read calendar
- search files
- research
- read project files
- create tasks
- create drafts
- generate code

## LEVEL 1 — REVIEW

User approval required.

Examples:

- send email
- send message
- publish content
- deploy website
- modify important project files

## LEVEL 2 — HIGH RISK

Always require explicit confirmation.

Examples:

- delete files
- execute destructive commands
- financial actions
- account/security changes
- exposing credentials

Zoey should never silently perform dangerous actions.

---

# 12. MEMORY ARCHITECTURE

Use structured memory first.

## Tables

```text
users
projects
tasks
events
contacts
conversations
memories
preferences
agent_runs
tool_runs
notifications
approvals
activity_log
```

## Memory types

### Short-term

Current conversation.

### Long-term

Stable user preferences and facts.

### Project memory

Information about ongoing projects.

### Event memory

Things that happened.

### Semantic memory

Embeddings for retrieving relevant historical information.

---

# 13. TASK SYSTEM

Each task should contain:

```text
id
title
description
priority
status
deadline
estimated_duration
project_id
dependencies
created_at
updated_at
completed_at
```

Statuses:

```text
inbox
planned
in_progress
waiting
completed
cancelled
```

---

# 14. DAILY PLANNER

The planner should consider:

```text
Calendar
Tasks
Deadlines
Priority
Available time
Energy/preferences
Existing commitments
Travel time if available
```

Example:

```text
07:00  Wake up
08:00  College
19:00  Return
19:30  Dinner
20:00  JEE revision
21:30  Haika
22:30  Review tomorrow
```

Zoey can dynamically reschedule tasks.

User:

> "I don't want to do JEE now."

Zoey:

```text
Current task: JEE revision
Move to: 21:30
Haika block: 20:00
No conflict detected.
```

---

# 15. NOTIFICATION ENGINE

The notification engine receives scheduled events from the planner.

Examples:

```text
Task reminder
Deadline warning
Calendar event
Follow-up reminder
Morning briefing
Evening review
Approval request
Agent completion
```

Notifications must sync to the phone.

---

# 16. PROACTIVE ZOEY

Eventually Zoey can initiate interactions.

Examples:

> "You have 35 minutes free. Want me to continue the website?"

> "Your client follow-up is overdue."

> "The build failed. I found the likely cause."

> "You have three unfinished tasks today. I rearranged them."

Proactive actions must obey the permission system.

---

# 17. COMPUTER CONTROL

The computer agent operates through controlled tools.

```text
Computer Agent
 |
 +-- screenshot()
 +-- mouse_move()
 +-- mouse_click()
 +-- keyboard_type()
 +-- keyboard_hotkey()
 +-- open_app()
 +-- close_app()
 +-- window_focus()
 +-- browser_open()
 +-- browser_click()
```

The uploaded prototype already demonstrates Windows-specific automation that can be refactored into this layer.

---

# 18. BUILDER WORKFLOW

When asked:

> "Zoey, build X."

Use:

```text
User request
     |
Analyze
     |
Create plan
     |
Inspect workspace
     |
Create/edit files
     |
Run code
     |
Run tests
     |
Inspect errors
     |
Fix
     |
Verify
     |
Show preview/result
     |
Ask deployment approval
```

Never blindly deploy.

---

# 19. COMMUNICATION WORKFLOW

Example:

> "Zoey, tell the client I'll send the website tonight."

```text
Understand recipient
     |
Find contact
     |
Generate message
     |
Show message
     |
User: "send it"
     |
Send
     |
Record timestamp
     |
Schedule follow-up
```

If a platform does not expose a free/legitimate automation interface, Zoey should not bypass its security controls.

---

# 20. PHONE SYNC

Use a free local-first sync architecture.

```text
Laptop Zoey
     |
     | encrypted connection
     |
Sync Service
     |
     +------ Phone Zoey
```

Synchronize:

```text
tasks
calendar state
notifications
approvals
conversation state
projects
agent status
```

For the first version, synchronization can operate over the user's local network.

Remote access can be added later.

---

# 21. ANDROID APP

Initial features:

```text
Home
Tasks
Calendar
Notifications
Voice
Approvals
Chat
Settings
```

Quick actions:

```text
"Ask Zoey"
"Plan my day"
"What's next?"
"Remind me"
"Approve"
"Reject"
```

---

# 22. DESKTOP APP

Main sections:

```text
Home
Tasks
Projects
Calendar
Agents
Memory
Activity
Approvals
Settings
```

Global shortcut:

```text
Ctrl + Space
```

opens the Zoey command interface.

Wake word remains:

```text
Zoey
```

---

# 23. EVENT BUS

All major system events pass through a central event bus.

Examples:

```text
TASK_CREATED
TASK_COMPLETED
TASK_OVERDUE
CALENDAR_CHANGED
NOTIFICATION_DUE
AGENT_STARTED
AGENT_FINISHED
APPROVAL_REQUIRED
MESSAGE_SENT
EMAIL_SENT
BUILD_FAILED
BUILD_COMPLETED
DEVICE_CONNECTED
```

This allows components to communicate without being tightly coupled.

---

# 24. ACTIVITY LOG

Every important action is recorded.

Example:

```text
14:02  Zoey started Builder Agent
14:03  Read project files
14:08  Modified homepage.tsx
14:09  Ran tests
14:10  Tests passed
14:11  Deployment approval requested
```

This makes debugging and trust much easier.

---

# 25. SECURITY

Never store secrets in plain text.

Use the operating system's secure credential storage where possible.

Never expose:

```text
API keys
passwords
tokens
cookies
private keys
```

to the LLM unless absolutely required.

The model receives a safe tool interface instead.

---

# 26. PROJECT STRUCTURE

Recommended repository:

```text
zoey/
│
├── apps/
│   ├── desktop/
│   └── android/
│
├── core/
│   ├── orchestrator/
│   ├── planner/
│   ├── memory/
│   ├── permissions/
│   ├── model_router/
│   └── event_bus/
│
├── agents/
│   ├── personal/
│   ├── builder/
│   ├── research/
│   ├── communication/
│   └── computer/
│
├── tools/
│   ├── filesystem/
│   ├── terminal/
│   ├── browser/
│   ├── computer/
│   ├── calendar/
│   ├── tasks/
│   ├── notifications/
│   ├── email/
│   ├── contacts/
│   └── git/
│
├── voice/
│   ├── wake_word/
│   ├── stt/
│   └── tts/
│
├── sync/
│
├── database/
│
├── security/
│
├── tests/
│
└── docs/
```

---

# 27. DEVELOPMENT PHASES

## PHASE 0 — Foundation

Build:

- repository
- desktop shell
- Python core
- SQLite
- event bus
- tool interface
- configuration system

No agents yet.

---

## PHASE 1 — Basic Zoey

Build:

- local LLM connection
- chat
- memory
- task system
- terminal tool
- filesystem tool

Goal:

> "Zoey, create a task to finish my website tomorrow."

Works end-to-end.

---

## PHASE 2 — Voice

Build:

- local wake-word detection
- `Zoey` wake word
- local STT
- local TTS
- microphone service

Goal:

> "Zoey, what's on my schedule?"

No cloud voice API required.

---

## PHASE 3 — Planner

Build:

- calendar
- task scheduling
- daily planning
- reminders
- notifications
- morning briefing
- evening review

---

## PHASE 4 — Computer Agent

Build:

- browser control
- Windows control
- application launching
- screenshots
- keyboard/mouse
- terminal

Refactor useful pieces from the uploaded prototype into this architecture.

---

## PHASE 5 — Builder

Build:

- project creation
- coding workflow
- tests
- debugging
- Git
- local development servers

Goal:

> "Zoey, build this."

---

## PHASE 6 — Communication

Build:

- email integration
- message preparation
- contact management
- follow-ups
- approval flow

Only use free/official APIs or user-approved local automation.

---

## PHASE 7 — Android

Build:

- Android app
- notifications
- voice commands
- tasks
- approvals
- sync

---

## PHASE 8 — Proactive Zoey

Build:

- intelligent reminders
- opportunity detection
- overdue detection
- schedule optimization
- project monitoring
- proactive suggestions

---

# 28. FINAL ZOEY LOOP

The completed system should operate like this:

```text
                 YOU
                  |
             "Zoey, ..."
                  |
                  v
             WAKE WORD
                  |
                  v
              STT / TEXT
                  |
                  v
             ZOEY CORE
                  |
          +-------+-------+
          |               |
       MEMORY          CONTEXT
          |               |
          +-------+-------+
                  |
                  v
               PLAN
                  |
                  v
             AGENT ROUTER
                  |
                  v
               AGENT
                  |
                  v
               TOOLS
                  |
                  v
             EXECUTION
                  |
                  v
              VERIFY
                  |
          +-------+-------+
          |               |
       APPROVAL       AUTOMATIC
          |               |
          +-------+-------+
                  |
                  v
               RESULT
                  |
                  v
               MEMORY
                  |
                  v
             NOTIFICATION
                  |
                  v
                 YOU
```

---

# 29. SUCCESS CRITERIA

Zoey v1 is successful when these work:

### 1. Voice

> "Zoey."

Zoey wakes.

### 2. Planning

> "Plan my day."

Zoey creates a realistic schedule.

### 3. Memory

> "What was I working on yesterday?"

Zoey remembers.

### 4. Notifications

Zoey reminds the user automatically.

### 5. Computer

> "Open my project."

Zoey opens it.

### 6. Building

> "Create the landing page."

Zoey actually creates it.

### 7. Communication

> "Draft an email to the client."

Zoey creates it and waits for approval.

### 8. Phone

A task created on the laptop appears on the phone.

### 9. Autonomy

> "Handle this."

Zoey plans, executes safe steps, asks when required, and reports the result.

---

# 30. THE MOST IMPORTANT DESIGN PRINCIPLE

Zoey is NOT:

```text
LLM + Chat UI
```

Zoey is:

```text
             ZOEY
               =
      Intelligence
    + Memory
    + Planning
    + Agents
    + Tools
    + Permissions
    + Automation
    + Voice
    + Notifications
    + Device Sync
```

The AI model is replaceable.

The **Zoey system belongs to you**.

---

# 31. FREE ARCHITECTURE SUMMARY

Required paid services:

```text
NONE
```

Base system:

```text
Windows laptop
       +
Android phone
       +
Open-source software
       +
Local AI
       +
Local database
       +
Local voice
       +
Local automation
```

Optional paid/cloud providers must never be required for core functionality.

The system should remain useful and functional with the internet disconnected, except for features that inherently require online data.

---

# 32. FIRST BUILD TARGET

Do NOT build everything at once.

The first executable milestone is:

```text
ZOEY DESKTOP

        ↓

Hear "Zoey"

        ↓

Understand command

        ↓

Local AI

        ↓

Remember context

        ↓

Execute:
    - terminal
    - files
    - applications

        ↓

Speak response

        ↓

Log action
```

Once this works reliably, everything else becomes an expansion of the same architecture.

**Project name: ZOEY**

**Wake word: ZOEY**

**Primary device: Windows laptop**

**Companion device: Android**

**Core requirement: Free / local-first**

**Goal: Personal JARVIS**
