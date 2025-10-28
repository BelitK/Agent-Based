## Quick orientation

This is a small Python project for experimenting with agent-based code built on the `mango` (mango-agents) library. The repo contains short example scripts and notebooks showing how to create TCP containers, register agents, and send messages.

Keep guidance concise and concrete: prefer direct references to `mango_test.py`, `ex1/answers/*.py`, and `async-test.py` when suggesting code changes.

## Important files
- `pyproject.toml` — project metadata and dependencies (Python >= 3.10, includes `mango-agents`).
- `mango_test.py` — canonical example showing container creation, agent registration, `async with mango.activate(...)` and inter-agent messaging.
- `ex1/ex1/answers/*.py` — multiple short examples demonstrating address formats and message sending (`create_tcp_container("127.0.0.1:9999")`, tuple `('127.0.0.1', 5555)`).
- `async-test.py` — an asyncio concurrency experiment (sensors + optional blocking sleep) useful when suggesting concurrency fixes or diagnostics.
- `main.py` — trivial entrypoint (keeps repo simple).

## What to know about architecture & runtime
- The project uses `mango` containers over TCP; containers are addressed by host:port strings or (host, port) tuples. Example usages in repo:
  - `mango.create_tcp_container("127.0.0.1:9999")`
  - `mango.create_tcp_container(addr=('127.0.0.1', 5555))`
- Typical flow: create container -> register agent -> activate container(s) (async context) -> send messages. See `mango_test.py` and `ex1/answers/ex3.py` for the canonical pattern:

  async with mango.activate(first_container, second_container):
      await second_agent.greet(first_agent.addr)

- Scripts sometimes call `container.send_message(...)` directly without activation — the examples are intentionally light-weight; prefer the canonical `activate` pattern for networked runs.

## Developer workflows (what to run)
- Create a venv and install dependencies (PowerShell):

  ```powershell
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  pip install -e .
  ```

- Quick runs (while venv active):
  - `python mango_test.py` — runs the mango example that shows multi-container activation and messaging.
  - `python async-test.py` — runs the asyncio sensor timing experiment.
  - `python main.py` — trivial entrypoint.

Notes: dependencies come from `pyproject.toml` (no requirements.txt). If `pip install -e .` fails, install `mango-agents` and `asyncio` from the project metadata first.

## Project-specific conventions and gotchas
- Address formats: both "host:port" strings and (host, port) tuples are used in examples — maintain compatibility when editing code that constructs addresses.
- Activation: prefer `async with mango.activate(...)` for networked tests; local direct calls to `send_message` are used in examples but may not work across processes without activation.
- Ports: examples use ports 5555, 5556 and 9999. Avoid collisions when running multiple examples locally.
- Logging: examples use plain `print()` for visibility. When suggesting changes, keep logging simple and synchronous unless proposing a focused refactor to structured logging.
- Async patterns: code uses `asyncio.run(...)`, `async with`, and `asyncio.gather(...)`. Respect these patterns and avoid introducing blocking calls into async flows (see `async-test.py` which intentionally contrasts blocking `time.sleep` vs `await asyncio.sleep`).

## Integration points & external deps
- `mango-agents` (imported as `mango`) is the primary external integration; the agent/container API (create_tcp_container, register, activate, send_message) is the main surface an AI should use.
- Network-based IPC: containers communicate over TCP. When changing message formats or agent addresses, update all example files to keep them consistent.

## What to recommend / change (actionable examples)
- If adding examples, include one fully-working `async with mango.activate(...)` case and avoid mixing address formats in the same example.
- When suggesting tests or CI, show a tiny smoke test that starts a container, registers an agent, activates, sends one message and asserts no exception — it's quicker than full integration testing.

## When you are unsure
- If a change affects message semantics, reference `mango_test.py` and update `ex1/answers/*.py` examples.
- If a change requires additional dependencies, update `pyproject.toml` and include exact package strings (the project uses pyproject-based dependency management).

---
If anything here is unclear or you want more detail on a specific script or test workflow, tell me which file and I will expand the instructions or add a runnable smoke test.
