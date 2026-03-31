"""LangGraph orchestrator — routes user requests to specialised agents.

Features:
- Cross-tool access: specialists can use limited tools from other groups
- Self-correction: auto-detect and fix compilation/runtime errors
- Short-term memory: maintain context within specialist sessions
"""

from __future__ import annotations

import logging
from typing import Annotated, Any, Literal

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

from src.agents.specialists import (
    create_animation_agent,
    create_audio_agent,
    create_build_agent,
    create_code_agent,
    create_scene_agent,
    create_vision_agent,
)
from src.config import settings
from src.rag.retriever import build_context, retrieve
from src.tools.tool_defs import ALL_TOOLS, BUILD_TOOLS, CODE_TOOLS, SCENE_TOOLS, VISION_TOOLS

logger = logging.getLogger(__name__)


# ── State ────────────────────────────────────────────────────────────


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    rag_context: str
    route: str
    active_specialist: str
    iteration: int
    error_count: int  # Track errors for self-correction
    last_error: str  # Last error message
    specialist_context: str  # Short-term memory for specialist


# ── Planner / Router ────────────────────────────────────────────────

PLANNER_SYSTEM = """\
You are the planning agent for a Unity AI assistant controlling an FPS game project.
You have a comprehensive Knowledge Base covering: Architecture, Core Systems, Scripts Library (80+ scripts),
Prompts & Templates, Skills, Camera FPS, Animations, Stats & Progression, HUD/UI, Player Controller,
Advanced AI, Economy, Combat, Map Builder, Pipeline & Workflow, Quality Rules.

Analyse the user's request and decide which specialist to delegate to.

Respond with EXACTLY one of these route labels:
- "code"      — C# scripting, patching, refactoring, creating scripts, stats, economy logic, AI behaviour
- "scene"     — GameObjects, components, materials, hierarchy, prefabs, map building, level design
- "vision"    — analysing screenshots or visual state of the editor, HUD review
- "build"     — running tests, checking logs, compilation, packages, quality audits, performance checks
- "animation" — Animator Controllers, Animation Clips, Blend Trees, transitions, animation events
- "audio"     — AudioSource, AudioMixer, sound effects, music, ambient audio
- "rag"       — the user asks a question about game design rules, conventions, or needs KB context before acting
- "direct"    — simple questions you can answer without tools

Respond with ONLY the route label, nothing else.
"""


def _planner_llm() -> ChatOpenAI:
    return ChatOpenAI(
        base_url=settings.vllm_llm_url,
        api_key=settings.api_secret_key,
        model=settings.vllm_llm_model,
        temperature=0.0,
        max_tokens=16,
    )


# ── Node functions ──────────────────────────────────────────────────


async def planner_node(state: AgentState) -> dict[str, Any]:
    """Determine which specialist should handle the request."""
    llm = _planner_llm()
    messages = [SystemMessage(content=PLANNER_SYSTEM)] + state["messages"]
    response = await llm.ainvoke(messages)
    route = response.content.strip().lower().strip('"\'')
    valid = {"code", "scene", "vision", "build", "animation", "audio", "rag", "direct"}
    if route not in valid:
        logger.warning("Planner returned invalid route '%s', falling back to 'code'", route)
        route = "code"
    logger.info("Planner routed to: %s", route)
    return {"route": route, "iteration": state.get("iteration", 0)}


async def rag_node(state: AgentState) -> dict[str, Any]:
    """Retrieve relevant context from the vector store."""
    last_human = ""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            last_human = msg.content
            break
    chunks = await retrieve(last_human)
    context = build_context(chunks)
    logger.info("RAG retrieved %d chunks", len(chunks))

    if context:
        rag_msg = SystemMessage(content=f"Relevant project context:\n{context}")
        # Determine best specialist from original planner route or fallback to code
        next_route = state.get("route", "code")
        if next_route in ("rag", "direct"):
            next_route = "code"
        return {"rag_context": context, "messages": [rag_msg], "route": next_route}
    return {"rag_context": "", "route": "direct"}


async def code_node(state: AgentState) -> dict[str, Any]:
    agent = create_code_agent()
    response = await agent.ainvoke({"messages": state["messages"]})
    return {"messages": [response], "active_specialist": "code", "iteration": state.get("iteration", 0) + 1}


async def scene_node(state: AgentState) -> dict[str, Any]:
    agent = create_scene_agent()
    response = await agent.ainvoke({"messages": state["messages"]})
    return {"messages": [response], "active_specialist": "scene", "iteration": state.get("iteration", 0) + 1}


async def vision_node(state: AgentState) -> dict[str, Any]:
    agent = create_vision_agent()
    response = await agent.ainvoke({"messages": state["messages"]})
    return {"messages": [response], "active_specialist": "vision", "iteration": state.get("iteration", 0) + 1}


async def build_node(state: AgentState) -> dict[str, Any]:
    agent = create_build_agent()
    response = await agent.ainvoke({"messages": state["messages"]})
    return {"messages": [response], "active_specialist": "build", "iteration": state.get("iteration", 0) + 1}


async def animation_node(state: AgentState) -> dict[str, Any]:
    agent = create_animation_agent()
    response = await agent.ainvoke({"messages": state["messages"]})
    return {"messages": [response], "active_specialist": "animation", "iteration": state.get("iteration", 0) + 1}


async def audio_node(state: AgentState) -> dict[str, Any]:
    agent = create_audio_agent()
    response = await agent.ainvoke({"messages": state["messages"]})
    return {"messages": [response], "active_specialist": "audio", "iteration": state.get("iteration", 0) + 1}


async def self_correction_node(state: AgentState) -> dict[str, Any]:
    """Self-correction: analyze errors and suggest fixes.

    Detects compilation errors, runtime errors, and common issues.
    Routes back to the appropriate specialist with fix instructions.
    """
    last_error = state.get("last_error", "")
    active_specialist = state.get("active_specialist", "code")
    error_count = state.get("error_count", 0) + 1

    if error_count > 3:
        logger.error("Max self-correction attempts (%d) reached, ending", error_count)
        return {"error_count": error_count, "route": "direct"}

    # Analyze error type
    error_lower = last_error.lower()

    if "compilation" in error_lower or "compile" in error_lower or "syntax" in error_lower:
        # Compilation error → stay with code agent
        fix_message = SystemMessage(
            content=f"SELF-CORRECTION: Compilation error detected (attempt {error_count}/3).\n"
            f"Error: {last_error}\n"
            f"Action: Read the script, identify the syntax/logic error, and apply a minimal patch."
        )
        return {
            "messages": [fix_message],
            "error_count": error_count,
            "last_error": last_error,
            "route": "code",
        }

    if "nullreference" in error_lower or "null reference" in error_lower:
        fix_message = SystemMessage(
            content=f"SELF-CORRECTION: Null reference exception detected (attempt {error_count}/3).\n"
            f"Error: {last_error}\n"
            f"Action: Check for uninitialized references, missing SerializeField assignments, or destroyed objects."
        )
        return {
            "messages": [fix_message],
            "error_count": error_count,
            "last_error": last_error,
            "route": active_specialist,
        }

    if "missing" in error_lower and ("component" in error_lower or "script" in error_lower):
        fix_message = SystemMessage(
            content=f"SELF-CORRECTION: Missing component/script detected (attempt {error_count}/3).\n"
            f"Error: {last_error}\n"
            f"Action: Add the missing component or create the required script."
        )
        return {
            "messages": [fix_message],
            "error_count": error_count,
            "last_error": last_error,
            "route": "scene" if "component" in error_lower else "code",
        }

    if "navmesh" in error_lower:
        fix_message = SystemMessage(
            content=f"SELF-CORRECTION: NavMesh issue detected (attempt {error_count}/3).\n"
            f"Error: {last_error}\n"
            f"Action: Bake NavMesh and verify agent configuration."
        )
        return {
            "messages": [fix_message],
            "error_count": error_count,
            "last_error": last_error,
            "route": "scene",
        }

    # Generic error → route to build agent for diagnosis
    fix_message = SystemMessage(
        content=f"SELF-CORRECTION: Error detected (attempt {error_count}/3).\n"
        f"Error: {last_error}\n"
        f"Action: Diagnose the issue using console logs and suggest a fix."
    )
    return {
        "messages": [fix_message],
        "error_count": error_count,
        "last_error": last_error,
        "route": "build",
    }


async def direct_node(state: AgentState) -> dict[str, Any]:
    """Answer directly without tools."""
    llm = ChatOpenAI(
        base_url=settings.vllm_llm_url,
        api_key=settings.api_secret_key,
        model=settings.vllm_llm_model,
        temperature=0.2,
    )
    system = SystemMessage(
        content="You are the AgentUnity assistant — a helpful Unity game development AI "
        "specialized in FPS projects. Answer concisely and accurately. "
        "If the question requires modifying the project, suggest routing to the appropriate specialist."
    )
    response = await llm.ainvoke([system] + state["messages"])
    return {"messages": [response], "iteration": state.get("iteration", 0) + 1}


# ── Routing logic ───────────────────────────────────────────────────


def route_after_planner(state: AgentState) -> str:
    return state["route"]


def should_continue_tools(state: AgentState) -> Literal["tools", "__end__"]:
    """Check if the last message has tool calls that need execution."""
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and last.tool_calls:
        if state.get("iteration", 0) >= 15:
            logger.warning("Max iterations reached, stopping")
            return "__end__"
        return "tools"
    return "__end__"


# ── Cross-tool access configuration ──────────────────────────────────

# Limited cross-tool permissions for specialists
# Each specialist can access specific tools from other groups
CROSS_TOOLS = {
    "code": ["unity_get_screenshot", "unity_get_console_logs", "unity_run_tests", "unity_recompile_scripts"],
    "scene": ["unity_get_script", "unity_get_screenshot", "unity_list_assets", "unity_bake_navmesh"],
    "vision": ["unity_get_scene_info", "unity_get_gameobject", "unity_list_scripts"],
    "build": ["unity_list_scripts", "unity_get_script", "unity_get_screenshot"],
    "animation": ["unity_get_script", "unity_get_gameobject", "unity_get_animator_controller"],
    "audio": ["unity_get_gameobject", "unity_get_scene_info", "unity_list_assets"],
}

# ── Build the graph ──────────────────────────────────────────────────


def build_graph() -> StateGraph:
    tool_node = ToolNode(ALL_TOOLS)

    graph = StateGraph(AgentState)

    # nodes
    graph.add_node("planner", planner_node)
    graph.add_node("rag", rag_node)
    graph.add_node("code", code_node)
    graph.add_node("scene", scene_node)
    graph.add_node("vision", vision_node)
    graph.add_node("build", build_node)
    graph.add_node("animation", animation_node)
    graph.add_node("audio", audio_node)
    graph.add_node("self_correction", self_correction_node)
    graph.add_node("direct", direct_node)
    graph.add_node("tools", tool_node)

    # entry
    graph.set_entry_point("planner")

    # planner → specialist or self_correction
    graph.add_conditional_edges(
        "planner",
        route_after_planner,
        {
            "code": "code",
            "scene": "scene",
            "vision": "vision",
            "build": "build",
            "animation": "animation",
            "audio": "audio",
            "rag": "rag",
            "direct": "direct",
            "self_correction": "self_correction",
        },
    )

    # rag → re-route to appropriate specialist (with context injected)
    graph.add_conditional_edges(
        "rag",
        route_after_planner,
        {
            "code": "code",
            "scene": "scene",
            "vision": "vision",
            "build": "build",
            "animation": "animation",
            "audio": "audio",
            "direct": "direct",
        },
    )

    # each specialist → tools or end
    for node_name in ("code", "scene", "vision", "build", "animation", "audio"):
        graph.add_conditional_edges(node_name, should_continue_tools, {"tools": "tools", "__end__": END})

    # tools → back to the correct specialist or self_correction on error
    def route_after_tools(state: AgentState) -> str:
        # Check if last tool message contains an error
        last_msg = state["messages"][-1] if state["messages"] else None
        if isinstance(last_msg, ToolMessage):
            content = last_msg.content if isinstance(last_msg.content, str) else str(last_msg.content)
            content_lower = content.lower()
            if any(err in content_lower for err in ["error", "exception", "failed", "missing", "null"]):
                logger.warning("Tool error detected, routing to self_correction")
                return "self_correction"
        return state.get("active_specialist", "code")

    graph.add_conditional_edges(
        "tools",
        route_after_tools,
        {
            "code": "code",
            "scene": "scene",
            "vision": "vision",
            "build": "build",
            "animation": "animation",
            "audio": "audio",
            "self_correction": "self_correction",
        },
    )

    # self_correction → specialist (routes based on error type)
    graph.add_conditional_edges(
        "self_correction",
        route_after_planner,
        {
            "code": "code",
            "scene": "scene",
            "vision": "vision",
            "build": "build",
            "animation": "animation",
            "audio": "audio",
            "direct": "direct",
        },
    )

    # direct → end
    graph.add_edge("direct", END)

    return graph


# compiled graph singleton
app = build_graph().compile()
