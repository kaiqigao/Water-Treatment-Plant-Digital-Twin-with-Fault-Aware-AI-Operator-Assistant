# TUMA206 — Modern Developments in Industry

**Group XX — Digital Twin Project**

Lecturer: Eldhose Abraham · Semester 2 · 2025/26

---

This repo is yours. Build the digital twin of the chemical process your group chose in your Week 1 proposal, using the technology stack you committed to. Every file in this repo — including this README — is yours to modify, delete, or replace.

## What you're building

Across the 8-week module, you will extend a simulated chemical plant through every layer of an industrial automation stack:

| Week | Layer to add |
|---|---|
| 2 | Field instrumentation + PLC control (one closed loop) |
| 3 | MQTT broker + tag publishing |
| 4 | SCADA / HMI dashboard |
| 5 | Historian + alarm log |
| 6 | Edge gateway + ERP stub |
| 7 | Cloud + LLM-based AI agent |
| 8 | Fault injection demo (one fault per layer) |

Refer to your Week 1 project proposal for the specific process, tech stack, and LLM you chose.

## Day 1 — getting set up

1. **Install prerequisites** on your laptop:
   - Python 3.11 or newer
   - Git
   - A code editor (VS Code, PyCharm, your choice)

2. **Clone this repo:**
   ```bash
   git clone https://github.com/eldhosekallookaran/tuma206-group-XX.git
   cd tuma206-group-XX
   ```

3. **Create a `.gitignore`** before you commit anything else. At minimum it must exclude:
   - `.env` (any file holding API keys)
   - `.venv/` (your virtual environment)
   - `__pycache__/`, `*.pyc`
   - `*.db`, `*.sqlite` (local databases)

4. **Make your first real commit** — replace this README with one that describes YOUR project:
   - Group number and team members
   - Chemical process being simulated
   - Tech stack chosen
   - How to install and run your code (once it exists)

5. **Tag your milestones** at the end of each week:
   ```bash
   git tag v2-plc
   git push --tags
   ```

## Rules of engagement

- **No secrets in git.** API keys belong in a `.gitignore`-d `.env` file. A leaked key is a 5-mark deduction.
- **Every team member commits.** Grading inspects the contribution graph. A team member with zero commits gets zero individual marks.
- **Meaningful commit messages.** "wip" / "fix" / "update" without context will be marked down.
- **Defendable code.** You must explain every line in viva. LLM-generated code you cannot defend = zero on that section.

## Grading (top-level)

| Component | Marks |
|---|---|
| 8 weekly milestones (~7.5 each) | 60 |
| Final demo (Week 8) | 15 |
| Individual viva | 15 |
| Code quality + documentation | 10 |
| **Total** | **100** |

Detailed rubric will be circulated on Asana.

## Questions

Asana, or open an Issue in this repo (good practice — that's what GitHub Issues are for).
