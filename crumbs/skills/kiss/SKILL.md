---
name: kiss
description: Implements super simple development flow with coding agents. Use when user wants to work on, continue, finish, repair, analyse software develpoment task.
---

Execution flags:
`--status` - when provided check which of the following points (from Main rules, Workspace, Analyse, Implement, Final verification sections) are done in the current task context and report to user
`--continue` - when provided check which of the following points (from Main rules, Workspace, Analyse, Implement, Final verification sections) are done and start executing first not done and then next ones. If all points done just report and propose next not done task.

# Main rules
1. Current directory is your kingdom, and your main source of documentation for this project.
2. This is your github repository: https://github.com/roche-private/kiakia-ai-native
3. In JIRA you project key is KIAKIA, label used for tasks: `kiakia-ai-native`
4. When preparing text for a human (for conversation or files) - strive for simplicity and empathy for user, follow @references/simple-talk.md
5. Simplicity is the goal, especially in communication with human.
6. Work rather on higher level (architect, designer, tech lead) than implementation details.
7. Implementation details are defined by rules injected to agent.
8. Depending on size of the task consider spawning subagents for analysing, implementation and testing for context window management and work parallelization.
9. When communicating use software engineering language, design patterns language, architecture patterns of Fowler language, DDD language, uncle bob clean code language.
10. Don't use Polish language words / translations for technical terms (like liveness, probes etc.) nor for domain words (like assessment, review, protocl).


## Workspace
1. Every task should be in backlog first (`backlog.md`).
2. Tasks in backlog are extremely simple, short but specific (verb oriented, goal oriented - one sentence) - easy for human to understand. Render each section as a markdown table with columns ID and Title; the ID stays plain text, the whole title is the link to the task file (no separate link, no id inside the link)
3. When new task / subject arrive after discussion propose to save to backlog
4. Number tasks sequentially - it is their id (4 digit number 0000 aligned)
5. When task is planned create a separate yaml file with notes about it ie. id, goal, acceptance criteria, and later plan if needed (`<id>-<task-kebab-name>.md`)
6. Task state is expressed only by its section in `backlog.md` ("In progress" / "To do") or by moving it to `done.md` - never as a status field in the task file. Within "To do" the order IS the priority - no priority labels
7. Workspace for a this skill files is `./.kiss`

## Analyse
1. Based on user provided input analyse current repository to better understand the problem (if task needs repo information)
2. Evaluate task complexity and level of information provided by human to decide if more questions are needed to better define the task. Don't hesitate to ask questions, but also don't ask questions that are easily defferable from context or with deeper analysis or with codebase search.
3. Propose in human friendly way (follow @references/simple-talk.md) main goal of the task as you understand and short acceptance criteria. Agree with user.
4. If needed do additional analysis (any kind: web search, codebase search, tools or just thinking) to prepare a proposition of main (crucial) assumptions (design, critical corner cases, influence on current solution) about how you'd like to solve the task (follow @references/simple-talk.md). Don't talk about details if human can live without them. Agree finally with user on approach.
If task implementation can be very simple, then just propose implementation as usual, no quirks.
5. If needed (task is big enough) Prapare plan for yourself (agent, not for human user). Part of the plan should be creating or modifying tests according to the used testing approach
6. Save backlog item with goal, acceptance criteria, and optional plan

## Implement
1. Implement task based on created plan for backlog times including tests (domain, e2e).
2. On the other hand be flexible about the plan especially when implementation exposes cource changing findings.
3. To ensure mechanical quality run compilation, static analysis and tests.
4. Choose the frequency and amount of check to fit the task size and complexity.
5. At the end use one or more subagents (depending on task complexity) to verify task outcomes against goal and acceptance criteria. When issues found correct them.
6. Finally use one or more subagents (depending on task complexity) to do code review based on general good practices related to used tech stach and rules defined in `.claude\rules`. Uber rule to verify is to ensure no comments (almost no comment).

## Final verification
1. Key phase is real verification of application when whole real app must locally started and clicked through to ensure application works in real usage. Use `agent-browser` skill for it. If not available or cannot connect STOP! Report.
2. Verification should be one or more user journey that requires a set of steps to be done to verify behaviour
3. User journey should be selected to base match current task scope.
4. Found problems should be repaired. In edge cased should be elevated to the human if a new backlog item / task is needed.
5. After user journey success describe to user the exact scenario(s) clicked using simple talk (references/simple-talk.md). If 
6. Remove obselete, not used code if left after any refactor.
7. Spawn independent set of subagents to check if every rule in every point in this SKILL (`kiss/SKILL.md`) is fulfilled. Everything must be effectively done to move to 8. Use also subagents to repair found issues to parallelize work.
8. Task fully done move from `backlog.md` to `done.md`, and from `.kiss/<id>-<task-kebab-name>.md` to `.kiss/done/<id>-<task-kebab-name>.md`