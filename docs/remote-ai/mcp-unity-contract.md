# MCP-Unity Contract

This document defines the runtime contract between the remote AI stack and the local Unity editor bridge.

## Design Rules

- expose structured editor operations instead of raw file access
- keep commands idempotent where practical
- return machine-readable payloads
- separate reads from mutations
- prefer narrow endpoints over generic remote execution

## Transport

- MCP-Unity runs beside the Unity Editor
- remote runtime connects through HTTPS or WebSocket transport
- all remote requests must be authenticated

## Minimum Read Surface

- list scripts
- get script content
- list scene objects
- inspect components
- get compile and runtime errors
- capture editor screenshots
- retrieve current selection and editor mode

## Minimum Write Surface

- create script
- patch script
- create, rename, move, or delete GameObject
- add or remove component
- update serialized component fields
- change selection or editor mode when required

## Build And Diagnostics Surface

- fetch compile errors
- fetch runtime logs
- request build start
- request build status

## Safety Constraints

- no unrestricted shell execution from the remote agent
- no arbitrary C# execution by default
- destructive actions must be explicit and narrow
- responses should include enough context for rollback or retry

## Versioning

Recommended headers:

- `X-MCP-Token`
- `X-MCP-Version`
- `Content-Type: application/json`

Contract changes should be additive where possible. Breaking changes should bump the protocol version and be reflected in both the local bridge and the remote runtime.
