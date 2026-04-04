# RunPod Deployment Notes

This file is the short index for the remote AgentUnity runtime.

## Scope

- remote AI runtime topology
- MCP-Unity connectivity
- inference-side orchestration and model serving
- boundary between this repository and the external training repository

Out of scope:

- dataset curation
- fine-tuning and LoRA workflows
- model export and benchmark pipelines
- training pod lifecycle

Those workflows live in the separate training repository.

## Canonical Docs

- `docs/remote-ai/README.md` for the remote AI architecture overview
- `docs/remote-ai/mcp-unity-contract.md` for the Unity bridge contract
- `local/SETUP.md` for local operator setup

## Deployment Summary

AgentUnity is split into two operational zones:

1. Local workstation
   - Unity Editor
   - MCP-Unity bridge
   - tunnel and client connectivity
2. Remote runtime
   - API gateway
   - multi-agent orchestrator
   - primary model serving
   - retrieval and vision services

## Reading Order

1. `README.md`
2. `local/SETUP.md`
3. `docs/remote-ai/README.md`
4. `docs/remote-ai/mcp-unity-contract.md`

## Maintenance Rule

Keep this file short. Detailed runtime documentation belongs under `docs/remote-ai/`.
