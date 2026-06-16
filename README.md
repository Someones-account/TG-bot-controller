# TG-bot-controller 
### Project consists of two parts: the bot manager and the bot itself.

A feature-rich Telegram bot designed for community management, moderation, announcements, and AI-powered interactions. The bot combines traditional moderation tools with Large Language Model (LLM) capabilities, image understanding, and subscriber-based notifications.

## Features

### Moderation

* Ban users directly from group chats.
* Automatic anti-spam protection.
* Forbidden phrase filtering.
* Temporary user timeouts.
* AI-assisted content moderation.
* Moderation logging and user tracking.

### AI Assistant

Interact with integrated LLMs through multiple modes:

* `/ai` — Single prompt, single response.
* `/chat` — Persistent AI chat sessions per user.
* `/context_chat` — Context-aware conversations with memory.

### Vision & OCR

Analyze images directly in Telegram:

* Extract text from screenshots and photos.
* Ask questions about uploaded images.
* Perform OCR and visual understanding tasks.

### Group Announcements

Users can subscribe to group notifications.

Administrators can broadcast announcements to subscribers by including:

```text
!News!
```

in a group message.

### Dashboard Authentication

Group administrators can generate credentials for an external management dashboard.

### Database Persistence

Stores:

* User information
* Subscriber lists
* Banned users
* Forbidden phrases
* Dashboard credentials
* Moderation history

---

## Available Commands

| Command                   | Description                          |
| ------------------------- | ------------------------------------ |
| `/start`                  | Start the bot                        |
| `/help`                   | Show available commands              |
| `/ban`                    | Ban a user (reply to user's message) |
| `/show_banned`            | Show banned users                    |
| `/subscribe`              | Subscribe to group announcements     |
| `/unsubscribe`            | Remove subscription                  |
| `/ai <prompt>`            | Query the language model             |
| `/chat <message>`         | Start/Continue a personal AI chat session  |
| `/context_chat <message>` | Chat with telegram group message history  |
| `/vision [prompt]`        | Analyze an image or extract text     |
| `/password <group_id>`    | Generate dashboard credentials       |

---

## Moderation Features

### Spam Protection

The bot tracks user message frequency.

Default behavior:

* More than 10 messages within 60 seconds
* User receives a temporary timeout
* Incident is logged

### Forbidden Phrase Detection

Messages containing configured forbidden phrases are:

1. Deleted automatically
2. Logged
3. Followed by a temporary timeout

### AI Content Moderation

When enabled, messages are sent to an LLM for classification.

Example workflow:

```text
User Message
      ↓
 Moderation LLM
      ↓
    YES / NO
      ↓
 Moderation Action
```

---

## Vision Examples

Extract text from an image:

```text
/vision
```

Analyze an image:

```text
/vision What error is shown in this screenshot?
```

Describe a diagram:

```text
/vision Explain this architecture diagram.
```

---

## Announcement System

### Subscribe

In a group chat:

```text
/subscribe
```

### Unsubscribe

```text
/unsubscribe
```

### Broadcast News

Administrator message:

```text
!News!
Server maintenance starts at 20:00 UTC.
```

The announcement will be delivered via private messages to all subscribers.

---

## Architecture

```text
InputHandlers
│
├── Moderation
│   ├── Ban Management
│   ├── Timeouts
│   └── Spam Detection
│
├── QueryManager
│   ├── User Records
│   ├── Subscribers
│   ├── Forbidden Phrases
│   └── Dashboard Credentials
│
├── ChatSession
│   └── User AI Conversations
│
├── ContextChat
│   └── Shared Memory Context
│
├── LLM Integration
│   ├── Prompt Responses
│   ├── Chat Sessions
│   └── Moderation
│
└── Vision Model
    ├── OCR
    ├── Image Understanding
    └── Visual Question Answering
```

---

## Installation

### Clone Repository

```bash
git clone https://github.com/Someones-account/TG-bot-controller.git
cd TG-bot-controller/
```

### Create Virtual Environment

Linux
```bash
python -m venv venv
source venv/bin/activate
```

Windows:

```powershell
venv\Scripts\activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Configure Environment

Create a configuration file keys.py in env folder (TG-bot-controller/env/keys.py) with contents:
```python
API_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
PASSWORD = "YOUR_TELEGRAM_BOT_PASSWORD"
```

Configure database credentials according to your environment.

### Run

```bash
python BotMain.py
python app.py
```

---

## Permissions

For full functionality, the bot should be granted:

* Delete messages
* Restrict members
* Ban users
* Read messages
* Send messages

Administrator privileges are recommended in moderated groups.

---

## Technology Stack

* Python
* python-telegram-bot
* Asyncio
* SQL Database
* Ollama
  - Large Language Models - (by default granite4.1:3b)
  - Vision Models / OCR - (by default minicpm-v4.6:1b)

