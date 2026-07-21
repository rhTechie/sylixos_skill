---
name: sylixos-long-run-validation
description: Use when debugging long-running SylixOS board-side issues that need staged validation, such as jitter, latency, stress sensitivity, timeout, soak, endurance, or hardware interaction problems where hypotheses must be tested first with short runs, then confirmed with longer A/B runs, and finally rechecked under the default real-world pressure mix.
---

# SylixOS Long-Run Validation

Use this skill when the problem is not credibly solved by a single quick run.

Typical trigger cases:

- jitter or latency spikes that appear under load
- soak or endurance failures that need tens of minutes or hours
- hardware-facing timing issues
- “optimization seems better, but short tests may miss regressions”
- pressure combinations where one must separate test-model effects from real path effects

This skill is about method, not one project conclusion.

## 1. Separate The Problem Into Layers

Before changing code, classify the issue into layers:

1. test-model problem
2. application/path problem
3. system-resource problem
4. environment/setup problem

Do not jump directly from “under load it gets worse” to “bandwidth is the cause”.

Ask instead:

- is the metric polluted by unrelated work inside the test loop?
- is the bottleneck on CPU scheduling, IRQ placement, memory traffic, I/O path, or process layout?
- does the failure depend on the synthetic pressure model, or also happen under the default real pressure mix?

## 2. Use A Staged Validation Ladder

Always validate in stages.

### Stage A: Reproduce Quickly

Start with a short run that is long enough to be meaningful but short enough to iterate quickly.

Default:

- 1 minute for smoke reproduction
- 20 to 30 minutes for short-long validation

Goal:

- confirm the issue is reproducible
- confirm the metric capture method works
- rank candidate hypotheses cheaply

Do not start with a 2-hour run unless the issue absolutely cannot be reproduced faster.

### Stage B: Hypothesis A/B

For each suspected cause:

- change one variable only
- keep load shape stable
- compare against the nearest baseline

Examples of single-variable changes:

- disable internal synthetic algorithm while keeping network path the same
- move IRQ to another CPU while keeping pressure unchanged
- limit pressure bandwidth while keeping worker count unchanged
- bind pressure tasks away from the real-time task while keeping the same binaries

If two things change at once, the result is not a clean conclusion.

### Stage C: Promote To Longer Validation

When a change looks promising in short-long validation:

- rerun it for 30 minutes
- then rerun it for 1 hour when the problem class justifies it

Do not present an optimization as solved from only a 1-minute run.

### Stage D: Restore Default Pressure Mix

After a custom stress model identifies a likely cause, always go back to the default or user-real workload mix.

This is mandatory.

Reason:

- a custom stress tool may isolate the cause
- but the optimization must still help under the real mixed pressure scenario

If the improvement disappears under the default mix, the result is not yet ready for handoff.

## 3. Prefer Progressive Narrowing Over Big Rewrites

For long-run issues, use this narrowing order:

1. reproduce with the existing test and default pressure
2. isolate with a simpler custom pressure model
3. parameterize the test so specific layers can be disabled or moved
4. confirm the result under the original default pressure mix

This avoids overfitting to a synthetic benchmark too early.

## 4. What To Parameterize First

When a test case is suspected of mixing multiple effects, first make these axes controllable:

- internal synthetic workload on/off
- worker or IRQ CPU placement
- pressure worker CPU placement
- pressure bandwidth or duty cycle
- result file output path
- poll vs non-poll path, if applicable

Good validation code changes usually add explicit switches instead of hardcoded one-off hacks.

Prefer:

- `--network-only`
- `--irq-cpu`
- `--main-cpu`
- `--algo-rounds`
- `--bandwidth`

over editing constants for each run.

## 5. Treat CPU Placement As A First-Class Hypothesis

When real-time board-side tests degrade under load, always consider CPU scheduling layout, not only bandwidth.

Check:

- where the real-time thread runs
- where IRQs run
- where pressure tasks run
- whether background pressure and critical path share the same CPU

Reusable rule:

- if moving pressure off the critical CPUs helps more than reducing nominal bandwidth, the dominant factor is likely scheduling contention rather than raw bandwidth alone

## 6. Metrics Interpretation Rules

When comparing runs:

- distinguish whole-loop latency from sub-path latency
- if whole-loop improves but send/recv does not, the optimization likely removed internal non-network work from the metric
- if send/recv improves after CPU isolation, the optimization likely helped the true path, not just the test model

Do not collapse these into one statement.

Report them separately.

## 7. Long-Run Result Hygiene

For each meaningful run, capture:

- exact command line
- run duration
- load mix
- CPU placement assumptions
- result file path
- max values of each tracked metric

Prefer file-based result capture over relying on live console output.

If telnet output is noisy or unstable:

- write results to a file
- fetch or print the file after the run

Also maintain a process document during the investigation:

- append each major round as it happens
- include the date to day precision
- record board roles, CPU placement, pressure model, result file path, and conclusion
- distinguish verified findings from candidate-only ideas
- write the document in Chinese by default; preserve commands, paths, source
  identifiers, logs, hashes, and API names verbatim

## 8. Board-Side Execution Practice

For repeated long-run experiments:

1. reboot before a new major validation round if state carry-over may matter
2. reconnect and verify the board is reachable
3. upload only the changed artifacts when possible
4. fix execute permissions explicitly
5. ensure old stress processes are fully cleaned up before the next run
6. if the setup uses a peer board, restore the peer board too when its leftover state could affect the next round

For every reboot caused by an image replacement, use a 60-second reconnect
deadline by default, or 30 seconds when explicitly requested. Poll both ping and
Telnet, and require at least one channel to recover unless the board acceptance
criteria explicitly require both. If the deadline expires with neither channel
available, classify the candidate as failed, stop further automated uploads and
reboots, preserve logs and backups, and request human or serial-console
intervention.

Do not trust a new result if the prior pressure processes may still be alive.

Practical default:

- if the next run changes the validation strategy, CPU placement, or core binaries, prefer reboot first
- if the next run only changes a minor command-line parameter and the prior run fully cleaned up, reboot is optional

Reusable rule:

- when in doubt, reboot between major rounds and treat the reboot cost as cheaper than trusting polluted long-run data

## 9. Shell And Harness Reliability Rules

Board-side orchestration often fails for incidental reasons:

- telnet control-character corruption
- shell redirection limitations
- harness special behavior for `.sh` arguments
- output flooding that hides prompts

Reusable rules:

- if a shell command sequence is brittle, upload a script and execute the script
- if a harness treats `.sh` specially, understand whether it skips other arguments
- if a session is too noisy, use a second session or fetch result files over FTP
- prefer saving board-side results to files instead of relying on continuous console capture for long or chatty tests

Do not confuse harness or shell behavior with the real root cause.

## 10. Instrumentation Escalation Rule

When progress stalls and no clean hypothesis remains:

1. split the end-to-end path into timed stages
2. add timestamps at the narrowest practical layer first
3. if needed, continue downward into driver or base code
4. keep one instrumentation revision per narrowing step and record which code version produced which data

This is a generic escalation method for timing issues; do not wait for complete uncertainty before using it.

## 11. Acceptance Standard For A Claimed Optimization

Do not claim success until all are true:

1. the short run shows improvement
2. a 30-minute run preserves the improvement
3. a 1-hour run preserves the improvement when the issue class justifies it
4. the improvement still helps under the default real pressure mix
5. the conclusion is specific about which metric improved and which did not

If one of these is missing, the work is still in-progress.

## 12. Reporting Template

Structure final findings as:

1. what was only a candidate hypothesis
2. what was disproved
3. what was verified by 30-minute or 1-hour runs
4. what optimization is currently recommended
5. what remains unproven and should be tested next

This keeps long-run debugging reports honest and reusable.
