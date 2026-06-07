set windows-shell := ["pwsh.exe", "-NoLogo", "-Command"]

# ── Dashboard ─────────────────────────────────────────────────────────────────

# Open the interactive recipe dashboard in the browser
default:
    @just --list

# ── Quality ───────────────────────────────────────────────────────────────────

# Execute Ruff SOTA v14.1 linting audit
lint:
    Set-Location '{{justfile_directory()}}'
    uv run ruff check .
    Set-Location '{{justfile_directory()}}\web_sota'
    npx @biomejs/biome ci .

# Execute Ruff SOTA v14.1 fix and premium formatting
fix:
    Set-Location '{{justfile_directory()}}'
    uv run ruff check . --fix --unsafe-fixes
    uv run ruff format .
    Set-Location '{{justfile_directory()}}\web_sota'
    npx @biomejs/biome check --write .

# ── Execution ─────────────────────────────────────────────────────────────────

# Launch the SOTA VRChat Control Plane (Backend + Frontend)
up:
    Set-Location '{{justfile_directory()}}'
    Start-Process pwsh -ArgumentList "-NoExit -Command `"uv run python -m vrchat_mcp.server`""
    Set-Location 'web_sota'
    npm run dev

# Launch the VRChat Control Plane (Backend only)
server:
    Set-Location '{{justfile_directory()}}'
    uv run python -m vrchat_mcp.server

# ── Hardening ─────────────────────────────────────────────────────────────────

# Execute Bandit industrial security audit
check-sec:
    Set-Location '{{justfile_directory()}}'
    uv run bandit -r src/

# Execute industrialized dependency audit
audit-deps:
    Set-Location '{{justfile_directory()}}'
    uv run safety check
# ── Distribution ──────────────────────────────────────────────────────────────

# Build and pack the industrialized .mcpb bundle
pack:
    Set-Location '{{justfile_directory()}}'
    npx mcpb build
    npx mcpb pack . dist/vrchat-mcp.mcpb

