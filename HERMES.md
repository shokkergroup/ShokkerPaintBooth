# Hermes Agent — Quick Reference for Ricky

## Starting Hermes

Open a terminal and run:
```
wsl -d Ubuntu-24.04 -u ricky
cd ~/.hermes/hermes-agent && source venv/bin/activate && python cli.py
```

Or to start with a specific model:
```
cd ~/.hermes/hermes-agent && source venv/bin/activate && python cli.py --model qwen/qwen3-coder-480b-a35b-instruct
```

## Switching Models

**From bash (before starting Hermes):**
```
python cli.py --model MODEL_NAME
```

**The model names you'll use (copy-paste these exactly):**

| Model | OpenRouter Name | Cost | Use For |
|-------|----------------|------|---------|
| Qwen3 Coder 480B | `qwen/qwen3-coder-480b-a35b-instruct` | FREE | Overnight autonomous work |
| DeepSeek V3.2 | `deepseek/deepseek-chat-v3-0324` | $0.28/$1.10 per M | Overnight if Qwen struggles |
| Gemini 3 Flash | `google/gemini-3-flash` | $0.10/$0.40 per M | Fast cheap tasks |
| Claude Sonnet | `anthropic/claude-sonnet-4.6` | $3/$15 per M | Daytime work with you |
| Claude Opus | `anthropic/claude-opus-4-6` | $15/$75 per M | Hard problems ONLY |

## Overnight Workflow

1. Open WSL terminal
2. Start Hermes on the FREE model:
```
cd ~/.hermes/hermes-agent && source venv/bin/activate
python cli.py --model qwen/qwen3-coder-480b-a35b-instruct
```
3. Type `/yolo` (skips all confirmations so it works unattended)
4. Paste your task
5. Leave terminal open, go to bed

## Key Commands Inside Hermes

| Command | What it does |
|---------|-------------|
| `/help` | Show all commands |
| `/yolo` | Skip all confirmations (for overnight) |
| `/new` | Start fresh session |
| `/save` | Save current conversation |
| `/usage` | Show token usage this session |
| `/provider` | Show current model and provider |
| `/tools` | List available tools |
| `/skills` | Browse 71 skills |
| `/cron` | Schedule recurring tasks |
| `/quit` | Exit Hermes |

## Pasting in WSL Terminal

- **Right-click** to paste (not Ctrl+V)
- **Shift+Insert** also works
- **Alt+Enter** for multi-line input

## Our Project Workspace

Hermes sees the SPB project at:
```
/mnt/e/Koda/Shokker Paint Booth Gold to Platinum
```

This is the same folder as `E:\Koda\Shokker Paint Booth Gold to Platinum` on Windows.

## The 3-Copy Sync Rule

When Hermes edits ANY file in `engine/`, it must sync to all 3 locations:
1. `engine/` (root)
2. `electron-app/server/engine/` (server copy)
3. `electron-app/server/pyserver/_internal/engine/` (internal copy)

Always remind Hermes of this in your task prompt.

## Cost Control

Last night burned $26 because it ran on Opus. Here's what the SAME work costs on different models:

| Model | Estimated cost for 10 tasks |
|-------|---------------------------|
| Opus | $26 (DON'T do this overnight) |
| Sonnet | $4-5 |
| DeepSeek V3.2 | $0.50 |
| Qwen3 Coder | $0 (FREE) |
| Gemini 3 Flash | $0.20 |

**Rule of thumb:** FREE model overnight, Sonnet when you're directing, Opus only for the hardest problems.

## Sample Overnight Task Prompt

```
Your workspace is /mnt/e/Koda/Shokker Paint Booth Gold to Platinum.
Read .claude/INSTRUCTIONS.md first to understand the project rules.
Read the last 30 lines of CHANGELOG.md to see recent work.

[YOUR SPECIFIC TASKS HERE]

Remember: sync all file changes to 3 copies (root + electron-app/server +
electron-app/server/pyserver/_internal). Log everything to CHANGELOG.md.
```

## If Hermes Gets Stuck

- Type `/retry` to resend the last message
- Type `/new` to start a fresh session (keeps memory)
- Type `/quit` then restart with a different model
- If terminal freezes: close the window, open a new one, start fresh

## OpenRouter Credits

Check your balance at: https://openrouter.ai/credits
Your API key works with ALL models — you just change the model name, not the key.
