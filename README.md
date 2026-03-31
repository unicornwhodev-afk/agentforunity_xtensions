# AgentforUnity Xtensions (AgentUnity)

AgentUnity is a multi-agent AI system deployed on RunPod and integrated via MCP-Unity to assist in Unity game development (Medieval Fantasy-Horror FPS). This repository contains the tools, AI orchestrators, custom MCP (Model Context Protocol) extensions, RunPod training pipelines, and the knowledge base needed for end-to-end game production using advanced AI workflows.

## Features

- **Multi-Agent Orchestration**: Powered by LangGraph, enabling specialized AI agents (Level Designer, Gameplay Programmer, DevOps) to collaborate on Unity tasks.
- **RunPod AI Backend**: Configurations and deployment scripts to host vLLM and RAG pipelines on RunPod GPU instances (Blackwell/NVFP4 compatible).
- **MCP-Unity Bridge**: A seamless WebSocket bridge connecting VS Code / AI Agents directly to the Unity Editor, allowing agents to manipulate the scene, scripts, and build process.
- **Fine-Tuning Pipeline**: End-to-end Qwen 3.5 fine-tuning pipeline tailored for Unity game development (using LoRA, TensorRT-LLM, and NVFP4 compilation).

## Repository Structure

- `/src/` - Core Python backend (LangGraph agents, RAG indexer/retriever, API, MCP tools).
- `/kb/` - Comprehensive AI knowledge base, providing agents with rules, architecture constraints, and game design documents.
- `/local/` - Scripts and Unity extensions (MCP-Unity bridge setup, VS Code configuration).
- `/setup-train-runpod/` - Dockerfiles and scripts for dataset preparation, Qwen 3.5 model fine-tuning, and NVFP4 compilation on RunPod.
- `/scripts/` - Execution scripts for downloading models, serving embeddings, and other backend tasks.

## Quick Start

### 1. Backend Deployment (RunPod)
Refer to the instructions in `/setup-train-runpod/README.md` to build and deploy the training image, fine-tune the model, and prepare the vLLM orchestration environment.

### 2. Local Setup
1. Mount the `/local/unity-extension/` package directly into your Unity project via the Package Manager.
2. Initialize the cloudflared tunnel to establish a secure connection with the RunPod backend.
3. Use the VS Code continue-config to point your AI extensions to the live endpoints. 
(Detailed instructions in `/local/SETUP.md`)

## Documentation

Full architectural documentation and workflow plans are available at:
- `roadmap.md` - Overall project timelines and phases.
- `planrunpod.md` - Deployment strategy and hardware requirements for the AI backend.
- `kb/` - Project-specific constraints (e.g., `#region` layouts, DI/ServiceLocator usage) that guide code generation tasks.

## License

MIT License / Proprietary (Replace with appropriate license)
