# Milestone 2 — How to Complete This Template

Use these AI prompts to help draft each document. You will need to supply facts about
your specific project — the AI cannot know what you have built.

---

## Before You Start

Make sure your `src/` folder is runnable per `src/SETUP.md` before submitting.
A grader will follow those instructions exactly. Test this yourself from a clean environment.

---

## manifest.yaml

Fill in your team's GWIDs, what features are working, and set checklist items to `true`
only when that item is genuinely complete.

**Prompt:**

```
Here is the Milestone 2 manifest template for my security course project.
Fill it in with the following information:

Team GWIDs: [list]
Demo video URL: [URL or "TBD"]
Features working right now: [list the specific flows that work]
Security properties implemented: [list]
Security properties still incomplete: [list]
Did the design change significantly from the Milestone 1 proposal? [yes/no — if yes, briefly describe]
AI tools used: [list]

Set checklist items to true only for things that are genuinely done.
Keep all YAML field names and structure exactly as in the template.
```

---

## progress-report-template.md — Part A

**Prompt for Build Status section:**

```
I am writing a build status report for a security course project.

My application is: [describe it briefly]
Language/framework: [e.g., Python/Flask]

What is working right now:
[describe each feature — be specific about what a grader can run to verify it]

What is not yet complete:
[describe each missing feature and what is blocking it]

Changes from the original plan:
[describe any deviations, or say "none"]

Unexpected challenges during development:
[describe what surprised you — technical issues, AI limitations, security tradeoffs]

AI tools I used and what for:
[describe]

Where AI needed significant correction:
[describe specific cases]

Write the progress report in a clear, honest, engineering tone. Include a
table showing features and their status. Include a section on AI usage
with specific examples of corrections or surprises.
```

---

## demo-template.md

Fill in your video URL. The demo video itself must be recorded by your team —
the AI cannot do this for you. Use the checklist in the template to verify your video
meets all requirements before submitting.

**For narration guidance, prompt your AI:**

```
I am recording a 3–6 minute narrated screen demo of my security application for a
university course. My application is: [describe].

The demo must show: [list what the application does, and which 2 security properties
you will demonstrate].

Write a narration script outline that covers:
1. 30-second intro (team names, application name, one-sentence description)
2. Primary user flow walkthrough (registration, login, core functionality)
3. Two security properties demonstrated in action — be specific about what to show
4. Brief honest status of what is still in progress

Keep the tone natural and technical. Total runtime should be 3–6 minutes.
```

---

## ai-usage-template.md — Summary Section

**Prompt:**

```
Help me write the AI Usage Summary section for a university project report.
I used AI tools to help build a security web application.

Here is what I actually did:

Tools used: [list]
Used AI for: [e.g., initial scaffold, debugging, test case generation, architecture questions]
What AI got right: [specific examples]
What AI got wrong or required correction: [specific examples — be concrete]
Security-critical code we chose not to use AI for: [and why]

Write a clear, honest 1–2 page summary covering these points. Avoid making AI sound
either perfect or useless — the goal is an honest reflection on what AI assistance
actually contributed to the project.
```

For the **Transcripts** section, paste your actual AI interactions. You cannot generate
fake transcripts — they must be real conversations from your project.

---

## audit-plan-template.md

**Prompt for Attack Surface Map:**

```
I am writing a security audit plan for my application. Help me map the attack surface.

My application: [describe — what it does, how it works]
Components: [frontend, backend, database, file storage, etc.]
Security properties implemented: [list]

Identify:
1. Where untrusted data enters the system (all input points)
2. Key security-sensitive operations (auth, encryption, access control, data storage)
3. Trust boundaries between components

Format this as a table and a short paragraph for each category.
```

**Prompt for Threat Scenarios:**

```
For each of my security properties, help me define one concrete, testable attack scenario.

My security properties and how they are implemented:
1. [Property]: [specific implementation, e.g., "Argon2id via argon2-cffi, 5 failed login = 60s lockout"]
2. [Property]: [implementation]
3. [Property]: [implementation]

For each property, write one attack scenario in this format:
- Property being tested
- Specific attack (what an adversary would do)
- Exact test steps (command-line commands, curl requests, or browser actions — be specific enough that someone could follow them without knowing the application)
- Expected result if the defense is working
- Expected result if the system is vulnerable

Make the test steps concrete and reproducible.
```

---

## src/README.md and src/SETUP.md

**Prompt for README.md:**

```
Write a README.md for my security course project.

Application: [name and one-sentence description]
Team: [names and roles]
Security properties implemented: [list each with the specific mechanism and key file/function]
Project structure: [describe your files and folders]

The README should be clear enough that a grader can understand the security architecture
from reading it without looking at the code.
```

**Prompt for SETUP.md:**

```
Write a SETUP.md for my security course project that lets someone unfamiliar with the
project get it running from scratch.

Language/runtime: [Python 3.11 / Node 20 / etc.]
Framework: [Flask / Express / etc.]
Database: [SQLite / PostgreSQL / etc.]
Dependencies: [list key packages]
Environment variables required: [list them and what they are for]
How to start the application: [exact commands]
Default test accounts (if any): [describe]
Known platform issues: [e.g., "does not run on Windows without WSL"]

Write clear numbered steps. Include a Troubleshooting section with the most likely
errors and how to fix them. Include a CLI documentation section if the app has a CLI.
```

---

## Submission Checklist

Before zipping and submitting:

- [ ] `manifest.yaml` — filled in accurately, checklist items reflect reality
- [ ] `progress-report.pdf` — converted from filled-in progress-report-template.md
- [ ] `demo.pdf` — one-pager with your video URL clearly visible
- [ ] `ai-usage.pdf` — includes real transcripts (not generated)
- [ ] `audit-plan.pdf` — converted from filled-in audit-plan-template.md
- [ ] `src/` — code runs following `src/SETUP.md` from a clean environment
- [ ] `src/README.md` — describes the application and security properties
- [ ] `src/SETUP.md` — has been tested from scratch
- [ ] ZIP named `lastname1-lastname2-lastname3.m2.zip` using your actual GWIDs
