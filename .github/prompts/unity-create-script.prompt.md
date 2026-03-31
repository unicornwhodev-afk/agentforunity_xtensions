---
description: "Create a new C# Unity script following project conventions (namespace, regions, SerializeField, XML docs)"
---
Create a new Unity C# script for: $input

Requirements:
- Proper namespace: `namespace ProjectName.SystemName { }`
- `[SerializeField] private` for all inspector fields with `[Header]` and `[Tooltip]`
- Regions: Variables, Unity Callbacks, Public Methods, Private Methods
- XML docs on all public methods
- No magic numbers — use constants
- EventBus for inter-system communication
- Object pooling if spawning objects frequently
