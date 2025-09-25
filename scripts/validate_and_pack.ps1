# VRChat MCP DXT Validation and Packaging Script
# Validates and packages the MCP server for Claude Desktop Extensions

param(
    [switch]$ValidateOnly,
    [switch]$SkipValidation,
    [string]$OutputPath = "d:\dev\repos\claude-desktop-extensions",
    [switch]$Verbose
)

# PowerShell reliability rules (per MCP Production Checklist)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# Setup logging
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logFile = Join-Path $env:TEMP "dxt_pack_$timestamp.log"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $logMessage = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') [$Level] $logMessage"
    Write-Host $Message
    if ($Verbose) {
        Add-Content -Path $logFile -Value $logMessage
    }
}

function Test-Prerequisites {
    Write-Log "Checking prerequisites..."

    # Check if mcpb is available
    try {
        $null = Get-Command mcpb -ErrorAction Stop
        Write-Log "✅ mcpb command found"
    } catch {
        throw "mcpb command not found. Please install Claude Desktop Extensions CLI."
    }

    # Check if dxt_manifest.json exists
    if (-not (Test-Path "dxt_manifest.json")) {
        throw "dxt_manifest.json not found in current directory"
    }

    # Check if output directory exists
    if (-not (Test-Path $OutputPath)) {
        Write-Log "Creating output directory: $OutputPath"
        New-Item -ItemType Directory -Path $OutputPath -Force | Out-Null
    }

    Write-Log "✅ All prerequisites met"
}

function Invoke-DXTValidation {
    Write-Log "Running DXT validation..."

    try {
        $result = mcpb validate 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Log "✅ DXT validation passed"
            return $true
        } else {
            Write-Log "❌ DXT validation failed:" "ERROR"
            Write-Log $result "ERROR"
            return $false
        }
    } catch {
        Write-Log "❌ DXT validation error: $_" "ERROR"
        return $false
    }
}

function Invoke-DXTPackaging {
    param([string]$OutputDir)

    Write-Log "Running DXT packaging..."

    try {
        # Ensure output directory exists
        if (-not (Test-Path $OutputDir)) {
            New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
        }

        # Change to output directory for packaging
        Push-Location $OutputDir

        try {
            # Run mcpb pack (DO NOT use mcpb init or mcpb publish per checklist)
            $packResult = mcpb pack ..\dxt_manifest.json 2>&1

            if ($LASTEXITCODE -eq 0) {
                Write-Log "✅ DXT packaging completed successfully"
                Write-Log "Package created in: $OutputDir"

                # List created files
                $createdFiles = Get-ChildItem -Path $OutputDir -File | Select-Object -ExpandProperty Name
                if ($createdFiles) {
                    Write-Log "Created files:"
                    foreach ($file in $createdFiles) {
                        Write-Log "  - $file"
                    }
                }

                return $true
            } else {
                Write-Log "❌ DXT packaging failed:" "ERROR"
                Write-Log $packResult "ERROR"
                return $false
            }
        } finally {
            Pop-Location
        }
    } catch {
        Write-Log "❌ DXT packaging error: $_" "ERROR"
        return $false
    }
}

function Test-PackageInstallation {
    param([string]$PackagePath)

    Write-Log "Testing package installation..."

    try {
        # Check if package files exist
        $manifestPath = Join-Path $PackagePath "package.json"
        if (-not (Test-Path $manifestPath)) {
            Write-Log "❌ package.json not found in package directory" "ERROR"
            return $false
        }

        # Validate package.json structure
        $packageJson = Get-Content $manifestPath -Raw | ConvertFrom-Json

        if (-not $packageJson.name) {
            Write-Log "❌ Package missing name field" "ERROR"
            return $false
        }

        if (-not $packageJson.version) {
            Write-Log "❌ Package missing version field" "ERROR"
            return $false
        }

        Write-Log "✅ Package structure validated"
        Write-Log "Package name: $($packageJson.name)"
        Write-Log "Package version: $($packageJson.version)"

        return $true

    } catch {
        Write-Log "❌ Package validation error: $_" "ERROR"
        return $false
    }
}

# Main execution
try {
    Write-Log "=== VRChat MCP DXT Validation and Packaging ==="
    Write-Log "Timestamp: $timestamp"
    Write-Log "Output Path: $OutputPath"
    Write-Log ""

    # Test prerequisites
    Test-Prerequisites

    $validationPassed = $true
    if (-not $SkipValidation) {
        $validationPassed = Invoke-DXTValidation
    } else {
        Write-Log "⏭️  Skipping validation as requested"
    }

    if (-not $ValidateOnly -and $validationPassed) {
        $packagingPassed = Invoke-DXTPackaging -OutputDir $OutputPath

        if ($packagingPassed) {
            # Test the created package
            Test-PackageInstallation -PackagePath $OutputPath
        }
    } elseif ($ValidateOnly) {
        Write-Log "⏭️  Validation only mode - skipping packaging"
    }

    Write-Log ""
    Write-Log "=== Process Complete ==="

    if ($Verbose) {
        Write-Log "Log file: $logFile"
    }

    # Return appropriate exit code
    if ($ValidateOnly -and $validationPassed) {
        exit 0
    } elseif (-not $ValidateOnly -and $validationPassed -and $packagingPassed) {
        exit 0
    } else {
        exit 1
    }

} catch {
    Write-Log "FATAL ERROR: $_" "ERROR"
    Write-Log "Stack trace: $($_.ScriptStackTrace)" "ERROR"
    exit 1
}


