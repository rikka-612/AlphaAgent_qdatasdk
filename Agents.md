# AlphaAgent_qdatasdk

## Goal

Build an alpha-research agent around `qdatasdk`.

Each round should follow the same closed loop:

1. hypothesis generation
2. experiment generation
3. coder
4. runner
5. feedback
6. trace update and next round

This file is the workflow contract first, not the implementation detail dump.
At this stage, the most important thing is to make every stage's input/output
clear enough that we can later implement them one by one.

## Current Repo Reality

- `qdatasdk/QuantDataSDK.pdf` is currently the main function/data reference.
- `qdatasdk/test_run_query_demo.ipynb` is the example code for querying total
  shares and free shares.
- So the "function library" in this project is currently document-driven, not
  yet a cleaned Python abstraction inside this repo.
- Core contracts have been split by category under `alphaagent_qdatasdk/core/`.
- `alphaagent_qdatasdk/app/conf.py` defines the current loop config.
- `alphaagent_qdatasdk/app/cli.py` provides a runnable CLI entrypoint.
- `alphaagent_qdatasdk/llm/` now contains provider-aware LLM config and client
  logic.
- `alphaagent_qdatasdk/prompts/` now stores prompt content in repo-local YAML
  files, with thin Python builders only for dynamic field interpolation.
- `alphaagent_qdatasdk/workflow/alphaagent_loop.py` contains the current
  deterministic mock loop.

Current runnable check:
- `python -B -m alphaagent_qdatasdk.app.cli run --rounds 2`
- `python -B -m alphaagent_qdatasdk.app.cli health-check`

Important boundary:
- The loop is runnable now, but hypothesis generation, experiment generation,
  coder, and runner are not fully integrated yet.
- Real LLM is now wired for hypothesis generation, experiment generation, and
  feedback when `dry_run=False`.
- qdatasdk querying, code generation, and backtest execution still need to
  replace the current mock coder/runner one stage at a time.

## Core Loop

### 1. Hypothesis Generation

Target module/class:
- `AlphaAgentHypothesisGen`

Input:
- `trace`
- `direction`
- `scenario`

Process:
- Read previous rounds from `trace`.
- Combine long-term direction and current scenario.
- Ask LLM to propose one researchable factor hypothesis.
- Current implementation returns deterministic mock output from
  `AlphaAgentLoop.hypothesis_generation(...)`.

Output:
- `AlphaAgentHypothesis`

Minimum fields of `AlphaAgentHypothesis`:
- `hypothesis`
- `reason`
- `concise_reason`
- `concise_observation`
- `concise_justification`
- `concise_knowledge`

Compatibility note:
- These fields intentionally stay close to the existing AlphaAgent demo
  `Hypothesis` object.
- If we later prefer shorter internal names, map `observation` to
  `concise_observation`, `justification` to `concise_justification`, and
  `knowledge` to `concise_knowledge`.

### 2. Experiment Generation

Target module/class:
- `AlphaAgentHypothesis2FactorExpression`

Input:
- `hypothesis`
- `trace`
- `function library`
- `scenario`

Process:
- Ask LLM to translate the hypothesis into executable factor ideas.
- Run a `regulator` layer after LLM output.
- Filter out expressions that are invalid, unsafe, or unsupported by the
  current function library.
- Current implementation returns one deterministic mock `FactorTask` from
  `AlphaAgentLoop.experiment_generation(...)`.

Output:
- `FactorTask[]`
- `FactorExperiment`

Minimum fields of `FactorTask`:
- `task_id`
- `factor_name`
- `expression_text`
- `required_fields`
- `notes`

Minimum fields of `FactorExperiment`:
- `experiment_id`
- `hypothesis`
- `factor_tasks`
- `data_requirements`
- `run_config`
- `output_schema`

Boundary:
- `FactorExperiment` is the structured experiment package.
- It should describe what to run, but it should not execute itself in the first
  implementation.
- The runner owns execution.

### 3. Coder

Input:
- `FactorTask[]`
- `scenario`

Process:
- Materialize each `FactorTask` into runnable code.
- Place each task in an isolated sub workspace.
- Keep code generation independent enough that one bad task does not break the
  whole round.
- Current implementation only returns intended workspace paths from
  `AlphaAgentLoop.coder(...)`; it does not write task code yet.

Output:
- `sub_workspace_list`

Notes:
- Each sub workspace should be independently runnable.
- The coder should consume structured tasks, not raw free-form LLM text.

### 4. Runner

Input:
- `sub_workspace_list`
- `FactorExperiment`
- `scenario`

Process:
- Execute each sub workspace.
- Collect intermediate factor artifacts.
- Merge them into `combined_factors_df.pkl`.
- Pass the merged artifacts and `FactorExperiment.run_config` to the selected
  experiment backend.
- Current implementation returns deterministic dry-run `ExperimentResult` from
  `AlphaAgentLoop.runner(...)`; it does not execute qdatasdk/backtest code yet.

Output:
- `ExperimentResult`

Minimum fields of `ExperimentResult`:
- `status`
- `artifact_paths`
- `performance_summary`
- `baseline_comparison`
- `sota_comparison`
- `error_message`

### 5. Feedback

Input:
- `current result`
- `SOTA`
- `trace`
- `scenario`

Process:
- Compare the current experiment result against the current best known result.
- Ask LLM to judge whether the current direction is worth continuing.
- Produce a structured decision rather than a loose paragraph.
- Current implementation returns deterministic mock feedback from
  `AlphaAgentLoop.feedback(...)`.

Output:
- `HypothesisFeedback`

Minimum fields of `HypothesisFeedback`:
- `observations`
- `hypothesis_evaluation`
- `decision`
- `reason`
- `quality_score`
- `strengths`
- `weaknesses`
- `next_direction`
- `new_hypothesis`

Suggested values of `decision`:
- `continue`
- `refine`
- `branch`
- `stop`

Boundary:
- `decision` is an enum-like string, not a bool.
- The old AlphaAgent demo uses `decision: bool`; this project needs richer
  control flow, so we should not inherit that bool shape blindly.

### 6. Trace

Input:
- hypothesis
- experiment
- run result
- feedback

Process:
- Append one `RoundRecord` into `trace.hist`.
- Update the current best result if the new round beats SOTA.
- Preserve enough context so the next round can continue without re-reading raw
  logs.
- Current implementation appends via `AlphaAgentLoop.trace_update(...)`.

Output:
- updated `trace`
- next round continues from the updated trace

## Core Objects

### `Trace`

Minimum fields:
- `round_id`
- `hist`
- `failed_tasks`
- `current_sota`
- `active_direction`
- `scenario`

Role:
- `trace` is the cross-round memory of the whole agent.
- `hist` should store round summaries, not only final metrics.
- `failed_tasks` should record all failed `FactorTask` objects across stages.
- `trace` should point to the active scenario, so stages do not need to pass
  unrelated global state around.

### `RoundRecord`

Minimum fields:
- `round_id`
- `hypothesis`
- `experiment`
- `result`
- `feedback`
- `created_at`

Role:
- One append-only summary of a completed research round.
- This is what `trace.hist` stores.

### `FailedTaskRecord`

Minimum fields:
- `task`
- `round_id`
- `stage`
- `error_message`
- `created_at`

Role:
- Append-only record for a task that failed in regulator, coder, runner, or any
  later execution stage.
- This is what `trace.failed_tasks` stores.

### `AlphaAgentHypothesis`

Role:
- The semantic bridge between research intent and executable factor design.

Minimum fields:
- `hypothesis`
- `reason`
- `concise_reason`
- `concise_observation`
- `concise_justification`
- `concise_knowledge`

### `FactorTask`

Role:
- The smallest coding unit that the coder can implement directly.

Minimum fields:
- `task_id`
- `factor_name`
- `expression_text`
- `required_fields`
- `notes`

### `FactorExperiment`

Role:
- The executable experiment package for one round.
- In v1, this object is a data contract, not the executor.

Minimum fields:
- `experiment_id`
- `hypothesis`
- `factor_tasks`
- `data_requirements`
- `run_config`
- `output_schema`

### `ExperimentResult`

Role:
- The structured result produced by the runner.
- Feedback should read this object, not raw logs.

Minimum fields:
- `status`
- `artifact_paths`
- `performance_summary`
- `baseline_comparison`
- `sota_comparison`
- `error_message`

### `HypothesisFeedback`

Role:
- The structured judgment that decides whether the loop should continue,
  branch, refine, or stop.

Minimum fields:
- `observations`
- `hypothesis_evaluation`
- `decision`
- `reason`
- `quality_score`
- `strengths`
- `weaknesses`
- `next_direction`
- `new_hypothesis`

### `FactorQualityScore`

Minimum fields:
- `overall_score`
- `score_scale`
- `scorer_name`
- `score_version`
- `rationale`
- `details`
- `created_at`

Role:
- Flexible scoring container for factor quality.
- Do not hard-code final score dimensions yet.
- Future scoring systems can store sub-scores, formulas, thresholds, and
  diagnostics in `details`, or replace this with a richer scoring module.

## Design Rules

- Each stage must have stable structured input/output.
- LLM output should be machine-checkable before entering execution.
- `regulator` must sit between free-form generation and runnable execution.
- `runner` should never depend on raw LLM prose.
- `trace` should be append-only history, not an overwritten scratchpad.
- `contracts.py` should remain a compatibility export layer; class definitions
  should live in category-specific files.
- health check and formal LLM usage must share the same compatibility logic:
  final `api_base`, final `model`, and final request headers.

## Current Implementation Map

- `alphaagent_qdatasdk/core/enums.py`: `FeedbackDecision`, `ExperimentStatus`
- `alphaagent_qdatasdk/core/hypothesis.py`: `AlphaAgentHypothesis`
- `alphaagent_qdatasdk/core/factor.py`: `FactorTask`, `FactorExperiment`
- `alphaagent_qdatasdk/core/result.py`: `ExperimentResult`
- `alphaagent_qdatasdk/core/feedback.py`: `FactorQualityScore`,
  `HypothesisFeedback`
- `alphaagent_qdatasdk/core/trace.py`: `FailedTaskRecord`, `RoundRecord`,
  `Trace`
- `alphaagent_qdatasdk/core/contracts.py`: compatibility exports
- `alphaagent_qdatasdk/llm/config.py`: provider-aware LLM config and Kimi
  compatibility rules
- `alphaagent_qdatasdk/llm/client.py`: chat completion client
- `alphaagent_qdatasdk/llm/env.py`: local `.env` loader
- `alphaagent_qdatasdk/app/conf.py`: `AlphaAgentLoopConfig`, `build_loop_config`
- `alphaagent_qdatasdk/app/health_check.py`: minimal LLM connectivity check
- `alphaagent_qdatasdk/app/cli.py`: CLI entrypoint and health check command
- `alphaagent_qdatasdk/prompts/*.yaml`: system prompts and user prompt
  templates
- `alphaagent_qdatasdk/prompts/loader.py`: lightweight YAML prompt loader
- `alphaagent_qdatasdk/workflow/alphaagent_loop.py`: six-stage `AlphaAgentLoop`
  with optional real LLM text stages

## First Implementation Order

1. Done: define core data contracts.
2. Done: split core contracts by category.
3. Done: build a mock loop with fake outputs.
4. Done: add CLI and config entrypoints.
5. Done: add provider-aware LLM compatibility layer and health check.
6. Next: build the qdatasdk function library abstraction.
7. Next: replace mock coder with real task materialization.
8. Next: replace mock runner with real qdatasdk/backtest execution.
9. Later: refine feedback scoring and trace iteration.
