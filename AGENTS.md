# MSTracker — Agent Instructions

## Scope

These instructions apply to work in this MSTracker's repository. More specific
`AGENTS.md` files in subdirectories may add instructions for those directories.
Keep this document focused on project-wide goals and working agreements. Put
feature-specific designs, parameters, implementation details, and results in
that feature's implementation record, tests, and documentation. Distinguish
established requirements from current behavior and proposals.

## Project purpose

MSTracker is an app that will help instrument admins maintain Thermo mass spectrometers in our academic lab. The scientists maintaining the instruments currently. Currently, we talk to each other and have a biweekly (every other week) meeting to discuss what the instruments need. We want to be able to effectively communicate the maintenance that's already done on the instrument so that we can know what has been done and what needs to be done next.


- Connect each proposed change to the intended analysis outcome and define
  measurable acceptance criteria.
- Support maintainable, testable analysis workflows with clear inputs, outputs,
  parameters, and evidence for scientific claims.
- Define current priorities, exclusions, and deferred work in the relevant
  feature record rather than treating one feature's choices as project policy.
- Keep docume

## Read before working

- Read `README.md` for project usage and build instructions.
- Read the relevant feature record, approved canonical plan, and root `TASKS.md`
  when present before starting or resuming implementation.
- Inspect relevant source, tests, fixture documentation, configuration, and
  existing changes before proposing or changing behavior.
- Verify dependency APIs against the version actually used by the repository.
  Consult relevant upstream documentation or source when necessary.

## How I want to collaborate

- Preferred explanation style and level of detail: Explain classes, functions, 
required inputs, and how stages connect. For implementation proposals, include 
an overview, detailed code-change steps, useful tests, a recommended approach 
with reasons, and alternatives. Give concise direct answers to individual 
clarification questions.
- When I want a plan before implementation: Before each feature implementation, 
develop a guide using the Feature Implementation Record template below, then 
prepare a checklist in root `TASKS.md` for Ariana's approval. A proposal or 
guide request is not permission to implement.
- Please organize the implementation into tasks that are recorded in TASKS.md 
file located in the repo's root directory. 
- Actions that require my explicit approval: Obtain approval of the feature 
checklist before implementation, and renewed approval for any material plan 
change, whether caused by an error, new requirements, or an architectural 
decision. Record which guide revision was approved. Respect explicit pauses; 
previous authorization does not override a later request to stop making changes.
- Preferred frequency of progress updates: Please organize progress updates 
according to task, and record updates in a log.  Updates are not required to 
be given at a specific frequency, but it is recommended to provide at least 1 
update every 10 minutes. 
- Preferences about subagents or parallel agent work: If different agents are
used to perform different tasks, there should be a "roles" section of the report
that details what agents were used, and what tasks they were responsible for. 

## Feature planning, task tracking, and reports

Use the [Feature Implementation Record template](https://docs.google.com/document/d/1B7Itzd_OCdvqwze6T4R4VTH2StEi5YfZ_JbKh7Pq9HU/edit?usp=sharing)
OR a specific document Ariana supplies to develop each implementation guide with Ariana. 
Start a separate record from this blank template for each feature and fill it with that feature's requirements,
constraints, and evidence. Keep its ID identical to the backlog when assigned;
do not invent an existing backlog ID. The template's instruction to place new
features at the top applies to the backlog/record collection. New tasks in
`TASKS.md` still go at the end, as specified below.

1. **Prepare the guide.** Read the relevant implementation record and repository
   code. Record the feature ID/name, status, priority, date, and issue/PR links
   when available. Cover the template's ten sections: problem and desired
   behavior (including exclusions); requirements and acceptance criteria;
   proposed approach; implementation plan; work log and experiments; decision
   log; validation and test notes; files, code, and references; open questions
   and follow-up; and completion summary. Include an overview, affected classes
   and functions, required inputs, detailed code-change steps, useful tests,
   the recommended approach and reasons, and alternatives. Record unknowns
   honestly; fill results and completion sections as work occurs. Keep a local
   guide under `docs/` with a revision/date and a link to the source record.
   When using Until Useful, write the settled plan to the single canonical
   `docs/uu-<task-slug>.md` before implementation. Link the guide and `TASKS.md`
   to that plan and its approved revision; do not maintain competing approved
   plans. Keep the canonical plan unchanged during the implementation/review
   loop. Put evolving logs, results, and completion notes in `TASKS.md` and the
   implementation record rather than editing that frozen plan.
2. **Prepare the checklist for approval.** Once the guide is complete enough to
   implement, append a feature section at the end of root `TASKS.md`. Include
   the feature ID/name, guide path and revision, acceptance criteria, approval
   status (`Pending` initially), and numbered tasks with stable IDs and Markdown
   checkboxes. Each task should identify the planned change, relevant files,
   dependencies, and how completion will be checked. Include validation,
   documentation, applicable Until Useful review, final human review, and report
   creation tasks. Group implementation tasks into proposed commits of 1–5
   related tasks each, with task IDs, intended scope, and a proposed commit
   message, following Git and delivery below. Present this concrete checklist
   to Ariana and wait for approval before implementing the feature. Record
   approval and its date only when actually given.
3. **Maintain the checklist and log.** Read `TASKS.md` before resuming work.
   Treat it as the shared, human-readable working record for Ariana and the
   agent, not merely an internal checklist or an end-of-work summary. Keep it
   current during implementation so both can see what is planned, in progress,
   completed, blocked, or awaiting approval. Record meaningful updates when
   starting a task, reaching a result, encountering a blocker, or changing its
   status; make the next action clear without logging every tool call.
   Append new tasks at the end of the file, labeled with their feature ID;
   preserve existing tasks and their IDs. Mark a task `[x]` only when its stated
   work and checks are complete. Add dated log entries referencing each task
   ID with the attempt/change, result or error, evidence (including test commands
   and failures/skips), and conclusion/next action. Record progress as it happens,
   including partial progress and blockers; organize user-facing updates by task.
   Do not erase completed tasks or rewrite earlier log entries during the feature.
4. **Pause for any material plan change.** Stop implementation and log the
   trigger, its impact, and why the approved approach must change. This includes
   errors, new requirements, and decisions that change scope, architecture,
   scientific behavior, dependencies, or acceptance criteria. Prepare a proposed
   guide revision and future tasks for approval before continuing. For Until
   Useful, preserve the canonical plan while approval is pending; adopt the
   approved revision only at the human-approved handoff before the next loop.
   Preserve completed work and history; label obsolete unfinished tasks `Superseded` rather than
   deleting them or marking them complete, and append replacement tasks with
   new IDs. Set approval to `Pending` for the revised guide/checklist and obtain
   Ariana's approval before resuming implementation. Routine fixes within the
   approved plan can proceed with logged results.
5. **Complete review before declaring success.** Passing tests alone does not
   complete an Until Useful feature. Review the diff for the smallest practical
   change: remove unnecessary edits, check for existing code that can be reused,
   and justify any dependency modifications.
   Apply the minimal-change criteria under Code organization and style in the
   review guide and reviewer handoff. Finish its review/correction cycle and
   record findings, evidence-backed dispositions, checks, residual risks, and
   the actual review outcome in `TASKS.md`. Continue routine corrections within
   approved scope without repeated permission requests. In scripted runs,
   `NEEDS_INPUT`, `FAILED`, and `STOPPED` halt automatic continuation; preserve
   evidence and report the public outcome separately from the detailed runtime
   state. Do not bypass these outcomes or describe them as successful completion.
   Resolve missing human decisions or prerequisites through the applicable
   resume/input protocol before proceeding. Even `APPROVE` means ready for
   Ariana's final review, not that she has accepted the feature.
6. **Create the Report and hand off.** When implementation and applicable
   automated/independent review are complete, finish the implementation record's
   validation notes and completion summary and update `TASKS.md`. Record
   `Awaiting Ariana's final review` until she accepts the feature; do not mark
   the final human-review task complete on her behalf. Create the Report outside
   the repository in `/Users/arianashannon/Downloads/MSTrackerReports`, named
   `YYYY-MM-DD-MSTracker-Implementation-Report.md`. Use the day's date in Ariana's local timezone
   (America/Chicago). If that filename already
   exists, append a time or sequence suffix to keep each Report unique.
   Copy the feature's complete checklist and dated
   log verbatim from `TASKS.md`, including approvals, revisions, errors,
   superseded tasks, decisions, validation results, and review evidence. For a
   scripted Until Useful run, include the runtime report and preserve its exact
   `UU Summary result` section and title; surface that section in the handoff
   as well. A summary may accompany the copied log but must not replace it.
   Include the guide and canonical-plan paths/revisions, when applicable.
   Never overwrite a previous report. If the final archive task/log entry is
   updated after copying, refresh this new report so it includes that final state.
7. **Archive before clearing.** After Ariana's final acceptance, record it and
   create a new final Report snapshot if the earlier handoff Report is already
   finalized. Verify the Report exists and contains the full
   final feature record before clearing that completed feature's entries from
   `TASKS.md`. Clearing is optional and only permitted after feature completion
   and this verified copy. Preserve all other features and pending work; carry
   forward any follow-up tasks explicitly. Share the local Report path with
   Ariana so she can catalog it.

Until Useful review approval never authorizes Git operations. Ariana performs
final review and Git operations by default; an agent may commit, push, create a
pull request, or release only with her explicit authorization for that action,
as specified under Git and delivery. These instructions define the integration points;
they do not automatically invoke Until Useful or its scripted runtime.

Keep `TASKS.md` in the repository root and eligible for version control. Store
implementation Reports only in `/Users/arianashannon/Downloads/MSTrackerReports`, outside the
repository, so they are not part of MSTracker's Git history. Do not copy Reports
into the repository or publish them. Share an absolute clickable path to each
Report with Ariana. If writing to Downloads requires filesystem permission,
request it rather than silently saving inside the repository; retain the task
history until the Report has been written and verified.

## Code organization and style

Current project structure:

- `src/test/resources/`: Test fixtures and their provenance.
- `docs/`: Implementation guides and canonical plans.
- `libs/`: Bundled dependencies.
- `build-cache/`: Downloaded build tools, dependency sources, and Maven artifacts.
- `tmp/`: Local experiment outputs; not committed.
- `TASKS.md`: Root implementation checklist and work log, when created.

Implementation Reports live outside this structure in
`/Users/arianashannon/Downloads/MSTrackerReports`.

Follow nearby naming, formatting, and error-handling conventions. Extend
existing modules and reuse established helpers and test infrastructure before
adding abstractions. Keep responsibilities and data flow clear; justify new
wrappers or interfaces by the feature's needs. Consider memory use, runtime,
and resource ownership when running on an instrument computer. 

Make each change small, concise, and efficient. Change the fewest practical
lines and files needed to satisfy the approved behavior and its validation.
Prefer targeted edits over rewrites; avoid incidental formatting, renaming,
cleanup, or abstraction changes. Keep correctness, readability, and necessary
tests intact rather than compressing code solely to reduce the line count.

Before writing new logic, search the repo and feature-related documents to ensure there is not 
an existing implementation. Reuse or narrowly extend suitable code rather than
copying or reimplementing it. In the proposal and review guide, identify the
reuse points and explain why any new implementation is necessary.

Prioritize changes within the repository over modifying dependencies.
Prefer existing supported infrastructure and small adaptations
when they meet the requirements. If a dependency change is necessary, explain
why a Context-only solution is insufficient, describe the smallest upstream
change and its compatibility impact, and include it in the plan for approval.

Preserve existing behavior unless the approved plan explicitly changes it.
Avoid unrelated refactoring. Report invalid inputs and failed prerequisites
clearly; do not silently substitute a scientifically different analysis.

## Testing expectations

- Develop unit and implementation tests as needed. 
- Choose focused tests for the changed behavior and relevant regression risks.
- For parsing, scoring, or model changes, cover relevant malformed inputs,
  population partitioning, identity preservation, numerical validity, and
  model application. Use integration tests where unit tests cannot establish
  that the affected components work together.
- Use documented fixtures and record their provenance. Identify external tools,
  datasets, and environment settings required for integration tests.
- Add test resources when needed, keeping each fixture as small as possible
  while preserving the behavior and edge cases the test must exercise. Reuse
  existing fixtures first; prefer a small synthetic input or a documented subset
  over a full dataset when it provides equivalent coverage. Store reusable
  fixtures under `src/test/resources/` and document their purpose, provenance,
  and any reduction procedure. Do not shrink away scientifically relevant
  structure or failure conditions merely to reduce file size. Keep large
  integration datasets external with documented setup when a small fixture
  cannot provide the required validation.
- Record commands, expected and observed results, failures, skips, and
  limitations in `TASKS.md` and the implementation record. Missing prerequisites
  mean a check is unrun or skipped, not passed.
- Distinguish compilation, unit tests, small-fixture integration checks, and
  representative scientific validation. Do not treat them as equivalent.

## Data and generated files

Keep input datasets intact during validation; use copies or temporary outputs
when tools may modify inputs. Record output locations in the implementation
record. Use `tmp/` for local storage. Save task archive Reports outside
the repository in `/Users/arianashannon/Downloads/MSTrackerReports` using the date and feature
ID number as specified above.

Document output overwrite and cache-reuse behavior for the affected workflow.
Ensure reused results correspond to the intended inputs, parameters, and engine
versions. Record enough provenance to explain and reproduce an analysis, and
distinguish an intermediate stage's success from completion of the whole run.

Respect repository ignore rules and packaging restrictions. Local access to
data does not authorize publishing it; keep secrets out of guides and logs.

## Git and delivery

Preserve unrelated existing changes. Follow the approval and final-review
workflow above. Local implementation authorization and review approval do not
authorize Git delivery actions.

- **Plan commit groups.** During planning, organize implementation tasks into
  cohesive proposed commits containing 1–5 related tasks each. Record each
  group's task IDs, intended files/behavior, proposed commit message, and scope
  approval in `TASKS.md` so Ariana can approve what belongs in each commit. 
  Tasks should be granular, that is they should accomplish one thing per task. 
  Do not include unrelated edits or external Reports. Keep local-only tracking
  and archival tasks outside code commits where appropriate.
- **Ask before committing.** Approval of the plan or commit grouping approves
  scope, not execution of `git commit`. Once the changes and relevant checks
  are ready, present the actual proposed commit scope and validation results
  and ask Ariana before making the commit. Only explicit authorization to make
  that commit permits execution; do not ask again if she has already explicitly
  authorized that exact action and scope. If the scope changes materially,
  revise the grouping and obtain approval before committing. Record the
  authorization and resulting commit hash in the task log.
- **Push, pull requests, and releases require separate explicit instructions.**
  Never push, create a pull request (including a draft), or publish a release
  unless Ariana specifically tells you to perform that action. Ask for explicit
  authorization before any proposed push or pull request when it has not
  already been given. A commit approval does not authorize any of these actions,
  and permission for one does not imply permission for the others. Do not infer
  authorization from phrases such as "implement," "finish," or "looks good."
- **Until Useful remains a review workflow.** Its `APPROVE` outcome is not
  permission to commit or publish. Leave Git operations to Ariana unless she
  explicitly delegates the specific action under the rules above. Do not infer
  permission to merge, rebase, or rewrite history.

Use the repository's existing review and release checks as applicable. Report
what was actually checked, what changed, and any remaining limitations, with
links to relevant files.

## Documentation

Keep this file focused on durable repo-wide instructions. Update the relevant
feature record and user documentation when behavior changes; update `README.md`
and manual when usage changes. Include practical examples and explain required
versus optional inputs. Use pseudocode or diagrams when they clarify the workflow.

Record feature decisions, alternatives, experiments, and validation in its
implementation record and `TASKS.md`, with complete task history archived in the
local Report. Keep fixture provenance alongside fixtures. When using Until
Useful, preserve the approved canonical plan during the work loop as described
above.

After each round of implementing what is in an "Implementation Guide," a report 
should be provided. The report should detail all references used for the task, 
and description of how agents were used. Additionally, the report should state 
any unresolved issues that were exposed during implementation, and a description 
of each "turn" (in our Codex conversation) taken during the implementation. 
