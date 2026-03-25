# 🐱 ReAct Agent — Grinning Cat Plugin

[![Plugin Version](https://img.shields.io/badge/version-0.1.0-blue)](https://github.com/matteocacciola/cat-react)
[![Author](https://img.shields.io/badge/author-Matteo%20Cacciola-green)](https://github.com/matteocacciola)
[![Tags](https://img.shields.io/badge/tags-Agent%20%7C%20ReAct-orange)]()

A plugin for [Grinning Cat](https://github.com/matteocacciola/grinning-cat-core) that replaces the built-in single-agent
workflow with a **ReAct (Reasoning and Acting)** agent. Instead of a one-shot LLM call, the agent iteratively
_reasons_, _acts_ with tools, _observes_ the results, and refines its plan — all within the same conversation turn.

---

## 🎯 What is ReAct?

ReAct is a prompting paradigm that interleaves **reasoning traces** and **task-specific actions**, enabling the agent to:

- 🧠 Think step-by-step before acting
- ⚙️ Execute tools and procedures
- 👁️ Observe results and adjust the approach
- ✅ Produce a grounded, reasoned final answer

> **Reference:** [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629) — Yao et al., 2022

---

## ✨ Features

| Feature                     | Description                                                                         |
|-----------------------------|-------------------------------------------------------------------------------------|
| 🔄 Iterative reasoning loop | Up to `max_iterations` reasoning steps per conversation turn                        |
| 🛠️ Tool execution          | Executes any tool registered with the Cat, up to `max_procedures_calls` times       |
| 📚 Full memory integration  | Recalls episodic, declarative and procedural memories                               |
| 🧩 Drop-in replacement      | Registers via the `factory_allowed_agentic_workflows` hook — no core changes needed |
| 🔒 Budget limits            | Independent caps on reasoning iterations and procedure calls prevent runaway loops  |
| 🔌 Fallback support         | Gracefully falls back to a plain LLM call when tool-binding is not supported        |

---

## 📦 Installation

Drop the `cat-react` folder inside your plugins directory (by default `cat/plugins/`).
The plugin is auto-discovered at startup. No restart required if hot-reload is enabled.

```
cat/plugins/
└── cat-react/
    ├── __init__.py
    ├── agent.py
    ├── plugin.json
    └── README.md
```

Then, from the **Admin Panel** (or via REST API), navigate to:

> **Settings → Agentic Workflow → ReAct Agentic Workflow**

Select and configure it as the active workflow for your agent.

---

## ⚙️ Configuration

The plugin exposes three parameters, all editable from the Admin Panel or via the
`PUT /agentic_workflow/settings/ReActAgentConfig` endpoint.

| Parameter              | Type     | Default                      | Description                                                  |
|------------------------|----------|------------------------------|--------------------------------------------------------------|
| `system_prompt`        | `string` | *"You are a helpful agent…"* | System instruction that guides the agent's overall behaviour |
| `max_iterations`       | `int`    | `5`                          | Maximum number of reasoning steps (LLM calls) per turn       |
| `max_procedures_calls` | `int`    | `10`                         | Maximum number of tool invocations per turn                  |

> **Note:** `max_iterations` and `max_procedures_calls` must both be ≥ 1.

---

## 🔁 How It Works

### Conversation turn pipeline

```
User message
     │
     ▼
 Memory recall  ──►  episodic + declarative context
     │
     ▼
 Tool retrieval  ──►  procedural memory → StructuredTools
     │
     ▼
 ReAct loop (max_iterations)
 ┌───────────────────────────────────────────────┐
 │  1. LLM call with current messages            │
 │  2a. <answer>…</answer>  → return final reply │
 │  2b. <action>…<input>…   → execute tool       │
 │       └─► append Observation to conversation  │
 │  2c. neither             → exit loop          │
 └───────────────────────────────────────────────┘
     │
     ▼
 CatMessage  →  client
```

### LLM response format

The agent instructs the LLM to respond using one of two XML patterns:

**Use a tool:**
```
<action>tool_name</action><input>tool_input</input>
```

**Give the final answer:**
```
<answer>your final answer here</answer>
```

`tool_input` can be either a **plain string** or a **JSON object** — the agent tries JSON parsing first and
falls back to the raw string automatically.

---

## 🧩 Integration with the Plugin System

The plugin registers itself through the `factory_allowed_agentic_workflows` hook in `__init__.py`:

```python
@hook
def factory_allowed_agentic_workflows(allowed: List[AgenticWorkflowConfig], cat) -> List[AgenticWorkflowConfig]:
    allowed.append(ReActAgentConfig)
    return allowed
```

This makes `ReActAgentConfig` appear in the Admin Panel alongside the built-in
`Single-agent Workflow`, letting administrators switch between them without any code changes.

---

## 🛠️ Extending the Agent

You can further customise the agent's behaviour using the standard Grinning Cat hooks, for example:

```python
from cat import hook

# Override the system prompt at runtime
@hook
def agent_prompt_prefix(prefix, cat):
    return "You are a specialist in financial analysis.\n" + prefix

# Restrict which tools the agent can use
@hook
def agent_allowed_tools(tools, cat):
    return [t for t in tools if t.name in {"search_web", "calculator"}]
```

---

## 📋 Requirements

- [Grinning Cat Core](https://github.com/matteocacciola/grinning-cat-core) ≥ compatible version
- An LLM configured for the target agent (any LangChain-compatible model works)
- For tool execution: at least one `@tool`, `@form`, or MCP client registered via a plugin

---

## 👤 Author

**Matteo Cacciola** — [github.com/matteocacciola](https://github.com/matteocacciola)

Plugin repository: [github.com/matteocacciola/cat-react](https://github.com/matteocacciola/cat-react)

---

## 📄 License

See the [LICENSE](../../../LICENSE) file in the root of the Grinning Cat Core repository.

