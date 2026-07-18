# Building VRChat Worlds With unity3d-mcp

**Created**: 2026-07-18. Everything below is verified against unity3d-mcp's
actual source (`src/unity3d_mcp/tools/portmanteau/*.py`), not its README —
that README currently mixes an older flat tool list (`import_vrm_avatar`,
`build_unity_project`, `upload_vrchat_avatar`, etc.) with the current
"Agent Lab v1.5.0" portmanteau tools. **The portmanteau tools below are the
real, currently-registered ones** (confirmed via `@app.tool` decorators in
source); the flat-list names in unity3d-mcp's README further down are stale
and shouldn't be relied on. That's a housekeeping gap in unity3d-mcp itself,
noted here so it doesn't cause confusion, not fixed in this doc.

## Why this doc exists

vrchat-mcp has **zero world-authoring capability**, by design — its six
portmanteau tools (`manage_avatar`, `manage_osc`, `manage_world`,
`manage_economy`, `manage_input`, `manage_system`) are all runtime/OSC/REST
telemetry for a *world you've already deployed*. `manage_world`'s only
operations are `get_info` and `search` (REST metadata; `search` is
currently a placeholder returning empty results) — nothing about creating
or modifying world content. That's correct scope for this repo: it's a
control-plane server, not a content pipeline. Building the world itself
happens in Unity, via `unity3d-mcp`. This doc is the missing link between
the two.

## The honest pipeline

### Prerequisites
- A Unity project with the **VRChat Worlds SDK** installed (not the
  Avatars SDK — `multiplatform`/`vrchat` tools distinguish `sdk_type:
  "avatars"` vs `"worlds"` when checking installation, but note the
  `vrchat` portmanteau tool's actual operations below only cover avatars —
  see the gap section).
- For live scene editing: copy `unity3d-mcp/src/unity3d_mcp/resources/MCPBridge.cs`
  into the project's `Assets/Editor/` folder and have the Unity Editor open.
  This is unity3d-mcp's **Hands-In** mode (bridge on port 10835). Without
  it, unity3d-mcp falls back to **Hands-Off** disk-only operations via
  UnityPy (asset import/audit still works; live create/transform doesn't).
  Check current mode: `unity_bridge(operation="status")`.

### Step 1 — Get content into the Unity project
- From Blender: `unity_import(operation="import_blender", file_path=...,
  project_path=...)` — single GLB/VRM/FBX/OBJ from a `blender-mcp` export.
- Batch: `unity_import(operation="import_fleet_batch", input_dir=...,
  project_path=..., pattern="*.glb")`.
- From World Labs Marble: `worldlabs(operation="import_marble", ...)`,
  with `check_gaussian`/`install_gaussian` if the source is a splat rather
  than a mesh, and `optimize_for_vrchat` for platform-specific tips.

### Step 2 — Assemble the scene (Hands-In only)
`unity_bridge` talks live to the running Editor via MCPBridge.cs:
- `get_hierarchy` — read the current scene tree.
- `create_object(name, object_type, position, rotation)` — GameObject,
  Light, or Camera.
- `transform_object(target, position, rotation)` — move/rotate an existing
  object by name or instance ID.
- `delete_object(target)`.

This is genuinely comparable in spirit to what ResoniteLink gave us for
Resonite this week (live, external, no-Editor-clicking scene mutation) —
the meaningful difference is this one requires the Unity Editor to be
open with the bridge script loaded, where ResoniteLink talks to an
already-running Resonite session over a plain WebSocket. Still real
automation, just with a heavier prerequisite.

### Step 3 — Preflight validation
`unity_validation`:
- `validate_scene`, `check_polycount`, `check_materials` — scene-level
  checks against VRChat limits.
- `validate_model`, `validate_avatar` — asset-level checks.
- `unified_audit` — everything at once.

### Step 4 — Interactivity (Udon)
**Not automatable via unity3d-mcp.** Udon Node Graph or UdonSharp scripts
still have to be authored by hand in the Unity Editor — no tool here
creates or edits Udon graphs/behaviours. This matches what
`mcp-central-docs/projects/resonite-living/PLATFORM_ALTERNATIVES.md`
already flagged: VRChat's interactivity layer is deliberately sandboxed
and there's no external authoring API for it, unlike ProtoFlux/ResoniteLink.

### Step 5 — Build & publish — **the actual gap**
There is no `upload_world`/`build_world` operation anywhere in
unity3d-mcp. The `vrchat` portmanteau tool's operations are
`check_auth`, `authenticate`, `check_sdk`, `validate_avatar`,
`setup_descriptor`, `upload_avatar` — **avatars only** (confirmed by
reading `tools/portmanteau/vrchat.py` directly: every upload/setup
operation takes `avatar_prefab`/`avatar_name`, there's no world
equivalent). `unity_jobs(operation="submit", job_type="build")` triggers
a generic Unity player build (`StandaloneWindows64` etc.), not a VRChat
SDK world publish — the VRChat SDK's own Build & Publish panel is a
different thing entirely and isn't wrapped.

**So this step is manual**: open the VRChat SDK panel inside the Unity
Editor and click Build & Publish yourself, after everything above has
been automated. If this gap matters enough to close, the natural fix is
adding a `publish_world` operation to unity3d-mcp's `vrchat` tool,
mirroring `upload_avatar` — that's a unity3d-mcp change, not something to
fake here.

### Step 6 — Back to vrchat-mcp's lane
Once the world is live, control and observe it with vrchat-mcp:
- `manage_world(operation="get_info", world_id=...)` — confirm it's up,
  pull metadata.
- `manage_osc` / `manage_input` — the same avatar/world-object OSC
  automation covered in `PLATFORM_ALTERNATIVES.md` (world triggers,
  environmental control, chatbox).

## Revised verdict vs. PLATFORM_ALTERNATIVES.md

That doc said VRChat has "no live external scene-graph API." More
precisely, after actually reading unity3d-mcp's source: the **scene
assembly** leg (create/transform objects, import assets, validate) *is*
now genuinely automatable via unity3d-mcp's Hands-In bridge — that's a
real capability, not aspirational. What's still missing, and still
structural rather than a temporary gap, is (a) Udon interactivity
authoring and (b) the VRChat SDK's world Build & Publish step. Neither
has an external API to hook into; both remain manual today. The
population/ecosystem analysis in `PLATFORM_ALTERNATIVES.md` is unaffected
by this — this doc only refines the automation-difficulty claim.

## Sources

Read directly from source, not documentation, per this project's usual
verify-before-writing standard:
- `unity3d-mcp/src/unity3d_mcp/tools/portmanteau/unity_bridge.py`
- `unity3d-mcp/src/unity3d_mcp/tools/portmanteau/unity_import.py`
- `unity3d-mcp/src/unity3d_mcp/tools/portmanteau/unity_validation.py`
- `unity3d-mcp/src/unity3d_mcp/tools/portmanteau/unity_jobs.py`
- `unity3d-mcp/src/unity3d_mcp/tools/portmanteau/worldlabs.py`
- `unity3d-mcp/src/unity3d_mcp/tools/portmanteau/platform.py`
- `unity3d-mcp/src/unity3d_mcp/tools/portmanteau/vrchat.py`
- `vrchat-mcp/src/vrchat_mcp/server.py`
- `mcp-central-docs/projects/resonite-living/PLATFORM_ALTERNATIVES.md`
