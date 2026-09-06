set windows-shell := ["powershell.exe", "-NoProfile", "-Command"]

# --- Dashboard ---

# Open the interactive recipe dashboard in the browser
default:
    @just --list


# Synchronize deps, pre-commit hooks, and web frontend
bootstrap:
    uv sync --extra dev --group dev
    uv run pre-commit install
    Set-Location web_sota; npm ci; if ($LASTEXITCODE -ne 0) { npm install }
    Write-Host "Pre-commit hooks installed." -ForegroundColor Green
# --- Quality ---

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

# --- Execution ---

# Launch the SOTA VRChat Control Plane (Backend + Frontend)
up:
    Set-Location '{{justfile_directory()}}'
    Start-Process pwsh -ArgumentList "-NoExit -Command `"uv run python -m vrchat_mcp.server`""
    Set-Location 'web_sota'; npm run dev

# Launch the VRChat Control Plane (Backend only)
server:
    Set-Location '{{justfile_directory()}}'
    uv run python -m vrchat_mcp.server

# --- Hardening ---

# Execute Bandit industrial security audit
check-sec:
    Set-Location '{{justfile_directory()}}'
    uv run bandit -r src/

# Execute industrialized dependency audit
audit-deps:
    Set-Location '{{justfile_directory()}}'
    uv run safety check
# --- Distribution ---

# Pack the industrialized .mcpb bundle
# `mcpb build` was never a real subcommand (mcpb --help: init/validate/clean/pack/unpack/
# sign/verify/info/unsign) - removed 2026-09-03. It silently failed every run
# ("error: unknown command 'build'") and `pack` ran anyway on the unbuilt tree, which is how
# the .mcpbignore gaps went unnoticed long enough to ship a 47.6MB bundle including
# web_sota/node_modules/.
pack:
    Set-Location '{{justfile_directory()}}'
    npx mcpb pack . dist/vrchat-mcp.mcpb


# Bootstrap: install dev deps + pre-commit hook

# Run CUA-NSIS smoke test (install -> launch -> nav walk -> uninstall)
cua-nsis-test:
    powershell.exe -NoProfile -File "{{justfile_directory()}}\scripts\just\cua-nsis-test.ps1"

# Run CUA webapp test (pre-Tauri: start.ps1 stack + nav walk in browser)
cua-webapp-test:
    powershell.exe -NoProfile -File "{{justfile_directory()}}\scripts\just\cua-webapp-test.ps1"