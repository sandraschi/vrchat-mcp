# Universal FastMCP Version Manager
# ================================
# Manages FastMCP versions across all MCP servers
# Can update to specific versions, check current versions, and fix common issues

param(
    [string]$TargetVersion = "",  # If empty, will just report current versions
    [switch]$DryRun = $false,
    [switch]$Verbose = $false,
    [string]$ReposPath = "D:\Dev\repos"  # Default path, can be overridden
)

$logFile = "C:\temp\fastmcp_manager_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

function Write-Log {
    param($Message, $Color = "White")
    $timestamp = Get-Date -Format "HH:mm:ss"
    $logMessage = "[$timestamp] $Message"
    Write-Host $logMessage -ForegroundColor $Color
    $logMessage | Out-File -FilePath $logFile -Append -Encoding UTF8
}

function Get-FastMCPInfo {
    param($ProjectPath)
    
    $filesToCheck = @(
        @{ Name = "pyproject.toml"; Type = "toml" },
        @{ Name = "requirements.txt"; Type = "text" },
        @{ Name = "Pipfile"; Type = "toml" }
    )
    
    foreach ($file in $filesToCheck) {
        $filePath = Join-Path $ProjectPath $file.Name
        if (Test-Path $filePath) {
            $content = Get-Content $filePath -Raw
            $version = $null
            $hasFastMCP = $false
            
            if ($file.Type -eq "toml") {
                # Check for FastMCP in TOML files
                if ($content -match 'fastmcp\s*[=<>~]+\s*["\'']?([0-9]+\.[0-9]+(\.[0-9]+)?)') {
                    $version = $matches[1]
                    $hasFastMCP = $true
                }
            } else {
                # Check for FastMCP in requirements.txt
                if ($content -match '^fastmcp([<>=~!]=?[^,]*|$)') {
                    $version = $matches[1].Trim()
                    $hasFastMCP = $true
                }
            }
            
            if ($hasFastMCP) {
                return @{
                    HasFastMCP = $true
                    ConfigFile = $file.Name
                    Version = $version
                    Content = $content
                    FilePath = $filePath
                }
            }
        }
    }
    
    return @{ HasFastMCP = $false }
}

function Update-FastMCPVersion {
    param($ProjectInfo, $NewVersion)
    
    $content = $ProjectInfo.Content
    $filePath = $ProjectInfo.FilePath
    $changed = $false
    
    # Handle different file types
    switch -Wildcard ($ProjectInfo.ConfigFile) {
        "*.toml" {
            # Update pyproject.toml or Pipfile
            $content = $content -replace '(fastmcp\s*[=<>~]+\s*["\'']?)([0-9]+\.[0-9]+(\.[0-9]+)?)', "`$1$NewVersion"
            $changed = $true
        }
        "*.txt" {
            # Update requirements.txt
            $content = $content -replace '^(fastmcp)([<>=~!]=?[^,]*|$)', "`$1>=$NewVersion"
            $changed = $true
        }
    }
    
    if ($changed) {
        if (-not $DryRun) {
            $content | Set-Content $filePath -Encoding UTF8
        }
        return $true
    }
    
    return $false
}

function Update-Dependencies {
    param($ProjectPath)
    
    Push-Location $ProjectPath
    $success = $false
    
    try {
        # Try uv first (faster)
        if (Get-Command "uv" -ErrorAction SilentlyContinue) {
            Write-Log "    🔄 Updating dependencies with uv..." -Color Cyan
            $output = uv pip install -e . 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Log "    ✅ UV update successful" -Color Green
                $success = $true
            }
        }
        
        # Fallback to pip
        if (-not $success -and (Get-Command "pip" -ErrorAction SilentlyContinue)) {
            Write-Log "    ⏳ Falling back to pip..." -Color Yellow
            $output = pip install -e . 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Log "    ✅ Pip update successful" -Color Green
                $success = $true
            }
        }
        
        if (-not $success) {
            Write-Log "    ❌ Failed to update dependencies" -Color Red
            if ($Verbose) {
                Write-Log "    Output: $output" -Color Gray
            }
        }
    }
    catch {
        Write-Log "    ❌ Error updating dependencies: $_" -Color Red
    }
    finally {
        Pop-Location
    }
    
    return $success
}

# Main execution
Write-Log "🚀 UNIVERSAL FASTMCP VERSION MANAGER" -Color Magenta
Write-Log "===================================" -Color Magenta
Write-Log "Repositories path: $ReposPath" -Color Cyan
Write-Log "Target version: $($if($TargetVersion) { $TargetVersion } else { "Check only" })" -Color Cyan
if ($DryRun) {
    Write-Log "🔍 DRY RUN MODE - No changes will be made" -Color Yellow
}
Write-Log "Log file: $logFile" -Color Gray
Write-Log ""

# Discover all MCP projects
Write-Log "🔍 Discovering MCP projects in $ReposPath..." -Color Cyan
$mcpDirs = Get-ChildItem -Path $ReposPath -Directory | 
    Where-Object { 
        $_.Name -match "mcp|vrchat" -or 
        (Test-Path (Join-Path $_.FullName "pyproject.toml")) -or
        (Test-Path (Join-Path $_.FullName "requirements.txt"))
    } |
    Sort-Object Name

Write-Log "Found $($mcpDirs.Count) potential MCP projects" -Color Green
Write-Log ""

$projectsWithFastMCP = 0
$projectsUpdated = 0
$projectsTotal = 0

foreach ($dir in $mcpDirs) {
    $projectPath = $dir.FullName
    $projectName = $dir.Name
    $projectsTotal++
    
    Write-Log "📁 Project: $projectName" -Color White
    
    $fastmcpInfo = Get-FastMCPInfo -ProjectPath $projectPath
    
    if ($fastmcpInfo.HasFastMCP) {
        $projectsWithFastMCP++
        $status = "  🔍 Found FastMCP v$($fastmcpInfo.Version) in $($fastmcpInfo.ConfigFile)"
        
        if ($TargetVersion -and ($fastmcpInfo.Version -ne $TargetVersion)) {
            $status += " → v$TargetVersion"
            Write-Log $status -Color Yellow
            
            if (-not $DryRun) {
                $updated = Update-FastMCPVersion -ProjectInfo $fastmcpInfo -NewVersion $TargetVersion
                if ($updated) {
                    Write-Log "  ✅ Updated to v$TargetVersion" -Color Green
                    $updateResult = Update-Dependencies -ProjectPath $projectPath
                    if ($updateResult) {
                        $projectsUpdated++
                    }
                }
            } else {
                Write-Log "  ✅ Would update to v$TargetVersion (DRY RUN)" -Color Yellow
                $projectsUpdated++
            }
        } else {
            Write-Log $status -Color Green
        }
    } else {
        Write-Log "  ℹ️ No FastMCP dependency found" -Color Gray
    }
    
    Write-Log ""
}

# Summary
Write-Log "===================================" -Color Magenta
Write-Log "📊 VERSION MANAGEMENT SUMMARY" -Color Magenta
Write-Log "===================================" -Color Magenta
Write-Log "📂 Projects scanned: $projectsTotal" -Color White
Write-Log "📦 Projects with FastMCP: $projectsWithFastMCP" -Color White

if ($TargetVersion) {
    Write-Log "🔄 Projects updated: $projectsUpdated" -Color Green
    if ($projectsUpdated -gt 0) {
        Write-Log "🎉 Successfully updated $projectsUpdated projects to FastMCP v$TargetVersion" -Color Green
    }
} else {
    Write-Log "ℹ️ No version specified, run with -TargetVersion x.y.z to update" -Color Yellow
}

Write-Log ""
Write-Log "📄 Full log saved to: $logFile" -Color Gray
Write-Log "===================================" -Color Magenta
