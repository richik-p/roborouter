# Codex Handoff

Paste the prompt below into Codex from the root of this repository.

---

## Initial handoff prompt

You are taking over the engineering planning for **RoboRouter**.

Do not implement the full product yet.

First, read the repository's `AGENTS.md` and all source-of-truth docs in the order it specifies. Treat the repository documentation as the durable replacement for prior ChatGPT/Claude conversations.

Your task for this first pass is to prepare the repository for disciplined implementation.

### 1. Restate the product

In your own words, summarize:

- the user problem;
- the MVP;
- the five core product objects;
- why this is not limited to arms;
- the policy-adapter vs robot-adapter split;
- how simulation and an external collaborator's robot fit the launch path.

If your interpretation differs from the docs, flag it rather than silently resolving it.

### 2. Audit the plan

Identify:

- contradictions across the docs;
- underspecified decisions that block the first milestone;
- assumptions that should be validated with a spike rather than designed on paper;
- areas where the current plan is overbuilt;
- any safety boundary that is ambiguous.

Do not broaden scope merely because an interesting feature is possible.

### 3. Verify key upstream dependencies

Using primary sources/current repositories, verify the current state and practical integration boundary of:

- XPolicyLab;
- Hugging Face LeRobot;
- RoboDojo/RoboTwin where relevant;
- ROS 2 / ros2_control;
- PX4 ROS 2 integration;
- Physical Intelligence openpi remote inference;
- NVIDIA GR00T N1.7/LeRobot support where relevant.

Record any material change since the research snapshot in `docs/research/CURRENT_ECOSYSTEM.md` with the date checked.

### 4. Propose the codebase structure

Propose a minimal monorepo/package structure that can grow into the architecture in `docs/ARCHITECTURE.md` without requiring premature microservices.

Prefer a small number of deployable units.

Explain each top-level directory and package boundary.

### 5. Convert the roadmap into GitHub-sized work

Use `docs/ROADMAP.md` and create a proposed issue list grouped into milestones.

Each issue should contain:

- user/engineering outcome;
- scope;
- non-goals;
- acceptance criteria;
- dependencies;
- likely files/packages;
- whether an ExecPlan is required.

The first milestone must produce a visible end-to-end vertical slice, not only schemas and scaffolding.

### 6. Recommend the first vertical slice

Recommend the smallest feature that proves the core architecture and can be demonstrated without physical hardware.

It should ideally cover:

`Policy catalog entry → compatibility query → one simulator/eval runner → saved Rollout → web result page`

Choose the simplest policy/evaluation combination after checking current upstream tooling.

### 7. Stop before broad implementation

You may make documentation-only corrections if they are clearly necessary and explain them, but do not start building the full backend/frontend until you have presented:

- the audit;
- proposed structure;
- milestone/issue plan;
- first vertical slice;
- unresolved questions.

Optimize for a repository that one or two engineers can actually finish, not an enterprise architecture diagram.

---

## After the first plan is accepted

Future prompts should reference one issue/milestone at a time, for example:

```text
Implement issue M0-02 from the approved roadmap. Read AGENTS.md first. Create an ExecPlan if required. Keep the change scoped to the acceptance criteria and update docs/tests before finishing.
```

Avoid prompts such as:

```text
Build all of RoboRouter.
```
