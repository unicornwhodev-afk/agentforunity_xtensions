# Remote AI Architecture

This folder contains the runtime-side documentation for AgentUnity's remote AI stack.

## Purpose

The main repository owns runtime behavior, editor connectivity, orchestration, retrieval integration, and operator setup. The external training repository owns dataset preparation, fine-tuning, export, and benchmark workflows.

## Topology

AgentUnity runs as a two-zone system:

1. Local editor zone
   - Unity Editor
   - MCP-Unity server
   - local tunnel endpoint
2. Remote runtime zone
   - API ingress
   - orchestrator
   - model serving
   - retrieval and vision services

## Core Components

### API gateway

- authenticates editor-side clients
- exposes runtime endpoints
- forwards requests to orchestration services

### Orchestrator

- interprets user intent
- selects tools and specialists
- coordinates MCP-Unity calls
- manages short-lived working context

### Retrieval stack

- indexes project and documentation knowledge
- provides embeddings and reranking
- assembles context for the primary model

### Vision stack

- processes Unity screenshots
- supports scene, UI, and error inspection workflows

### MCP-Unity bridge

- exposes safe editor operations
- returns structured scene, script, and error data
- acts as the remote control surface for Unity-side actions

## Boundary With Training Repo

This repo:

- runtime architecture
- orchestration and API behavior
- editor bridge integration
- retrieval and vision integration
- local operator setup

External training repo:

- dataset preparation
- fine-tuning configuration
- model export
- benchmark execution
- training artifacts and reports

## Runtime Model Roles

Keep runtime model roles distinct even if the exact models evolve:

- primary instruction model for orchestration and code reasoning
- vision model for editor captures
- embedding model for retrieval
- reranker for retrieval precision

## Related Docs

- `../../README.md`
- `../../local/SETUP.md`
- `./mcp-unity-contract.md`
- `../../roadmap.md`
