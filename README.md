# AgentforUnity Xtensions

This repository is the main application and tooling repo for AgentUnity: the multi-agent backend, the Unity integration bridge, the knowledge base, and the local developer setup used to drive a Unity FPS production workflow.

The operational training workflow is no longer vendored in this repository. Fine-tuning, export, Hugging Face publication, and benchmark tooling now live in a separate training repository.

## Main Scope

- LangGraph-based backend agents and orchestration
- MCP tooling used to connect editor-side workflows to the AI backend
- RAG indexing and retrieval services
- local setup helpers for Unity integration and RunPod connectivity
- project knowledge base and generation constraints

## Repository Structure

- `/src/` — Python backend code for agents, API, retrieval, and MCP integration
- `/kb/` — project knowledge base and generation rules
- `/docs/remote-ai/` — remote runtime architecture and MCP-Unity integration docs
- `/local/` — local setup scripts, editor integration, and VS Code-related assets
- `/scripts/` — utility scripts for backend services and model-serving helpers

## Quick Start

### Local Unity And Editor Integration

1. Mount `/local/unity-extension/` into the Unity project through the Package Manager.
2. Configure the local tunnel and MCP bridge.
3. Point your editor-side AI tooling to the configured endpoints.

Detailed instructions live in `local/SETUP.md`.

### Backend And Runtime Planning

- `roadmap.md` contains the high-level platform direction.
- `planrunpod.md` is the short index for runtime deployment notes.
- `docs/remote-ai/README.md` contains the remote AI architecture overview.
- `docs/remote-ai/mcp-unity-contract.md` contains the Unity bridge contract.
- `kb/` contains the project-specific implementation rules used by the agents.

## External Training Repo

The training workflow is maintained in a separate repository.

The Windows benchmark helper in `local/scripts/run-q6-benchmark.ps1` now targets that external repo via `-TrainingRepoPath` or the `AGENTUNITY_TRAINING_REPO` environment variable.

See the README in the training repository for:

- dataset preparation
- RunPod training pod setup
- export and Hugging Face publication flow
- WSL2 NVFP4 benchmark workflow
- benchmark reports and packaged workspace artifacts

## License

MIT License / Proprietary (replace with the final project license policy)
