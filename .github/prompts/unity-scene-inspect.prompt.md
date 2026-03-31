---
description: "Inspect the current Unity scene: list all GameObjects, hierarchy, components"
---
Use the MCP-Unity tools to get the current scene info and provide a clear summary:

1. Call `get_scene_info` to get the full scene hierarchy
2. Summarize the root GameObjects and their children
3. Highlight any issues (missing references, disabled objects, empty transforms)
