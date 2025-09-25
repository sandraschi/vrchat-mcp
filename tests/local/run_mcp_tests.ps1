# VRChat MCP Local Test Runner
# PowerShell script to run MCP interface tests locally

param(
    [string]$PythonPath = "python",
    [string]$TestMode = "both",  # "mcp", "fastapi", or "both"
    [switch]$Verbose,
    [switch]$KeepLogs
)

# Configure PowerShell for reliability (per MCP Production Checklist)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# Set up logging
$logDir = "d:\dev\repos\temp"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logFile = Join-Path $logDir "mcp_test_run_$timestamp.log"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $logMessage = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') [$Level] $Message"
    Write-Host $logMessage
    Add-Content -Path $logFile -Value $logMessage
}

function Write-VerboseLog {
    param([string]$Message)
    if ($Verbose) {
        Write-Log $Message "DEBUG"
    }
}

function Test-Command {
    param([string]$Command)
    try {
        $null = Get-Command $Command -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

function Start-MCPServer {
    param([string]$Mode)

    Write-Log "Starting MCP server in $Mode mode..."

    if ($Mode -eq "mcp") {
        $serverArgs = @("-m", "vrchat_mcp.server")
    } elseif ($Mode -eq "fastapi") {
        $serverArgs = @("-m", "vrchat_mcp.cli", "--mode", "fastapi", "--host", "127.0.0.1", "--port", "8000")
    } else {
        throw "Invalid mode: $Mode"
    }

    try {
        $serverProcess = Start-Process -FilePath $PythonPath -ArgumentList $serverArgs -NoNewWindow -PassThru -RedirectStandardOutput (Join-Path $logDir "server_stdout_$timestamp.log") -RedirectStandardError (Join-Path $logDir "server_stderr_$timestamp.log")
        Write-VerboseLog "Server process started with PID: $($serverProcess.Id)"

        # Wait for server to initialize
        Start-Sleep -Seconds 3

        # Verify server is running
        if ($serverProcess.HasExited) {
            throw "Server process exited prematurely with code: $($serverProcess.ExitCode)"
        }

        return $serverProcess
    } catch {
        Write-Log "Failed to start MCP server: $_" "ERROR"
        throw
    }
}

function Stop-MCPServer {
    param([System.Diagnostics.Process]$ServerProcess)

    if ($ServerProcess -and -not $ServerProcess.HasExited) {
        Write-Log "Stopping MCP server (PID: $($ServerProcess.Id))..."

        try {
            # Try graceful shutdown first
            $ServerProcess | Stop-Process -Force
            $ServerProcess.WaitForExit(5000)

            if (-not $ServerProcess.HasExited) {
                Write-Log "Server did not respond to graceful shutdown, forcing termination..." "WARNING"
                $ServerProcess | Stop-Process -Force -ErrorAction SilentlyContinue
            }

            Write-Log "MCP server stopped successfully"
        } catch {
            Write-Log "Error stopping server: $_" "WARNING"
        }
    }
}

function Run-MCPTest {
    param([string]$TestScript, [string]$TestName)

    Write-Log "Running $TestName test..."

    $testStartTime = Get-Date

    try {
        $testProcess = Start-Process -FilePath $PythonPath -ArgumentList $TestScript -NoNewWindow -Wait -PassThru -RedirectStandardOutput (Join-Path $logDir "test_stdout_$TestName_$timestamp.log") -RedirectStandardError (Join-Path $logDir "test_stderr_$TestName_$timestamp.log")

        $testDuration = (Get-Date) - $testStartTime

        if ($testProcess.ExitCode -eq 0) {
            Write-Log "✅ $TestName test PASSED (Duration: $($testDuration.TotalSeconds.ToString('F2'))s)"
            return $true
        } else {
            Write-Log "❌ $TestName test FAILED (Exit code: $($testProcess.ExitCode), Duration: $($testDuration.TotalSeconds.ToString('F2'))s)" "ERROR"
            return $false
        }
    } catch {
        Write-Log "❌ $TestName test ERROR: $_" "ERROR"
        return $false
    }
}

function Test-Prerequisites {
    Write-Log "Checking prerequisites..."

    # Check Python
    if (-not (Test-Command $PythonPath)) {
        throw "Python executable not found: $PythonPath"
    }

    # Check Python version
    try {
        $pythonVersion = & $PythonPath --version 2>&1
        Write-VerboseLog "Python version: $pythonVersion"
    } catch {
        throw "Cannot determine Python version"
    }

    # Check if VRChat MCP is installed
    try {
        $null = & $PythonPath -c "import vrchat_mcp" 2>&1
        Write-VerboseLog "VRChat MCP module found"
    } catch {
        throw "VRChat MCP module not found. Please install it first."
    }

    # Check test files exist
    $mcpTestFile = "tests/local/test_mcp_interface.py"
    $fastApiTestFile = "tests/local/test_fastapi_interface.py"

    if ($TestMode -in @("mcp", "both") -and -not (Test-Path $mcpTestFile)) {
        throw "MCP test file not found: $mcpTestFile"
    }

    if ($TestMode -in @("fastapi", "both") -and -not (Test-Path $fastApiTestFile)) {
        throw "FastAPI test file not found: $fastApiTestFile"
    }

    Write-Log "✅ All prerequisites met"
}

function Send-TestReport {
    param([hashtable]$Results)

    $totalTests = $Results.Count
    $passedTests = ($Results.Values | Where-Object { $_ -eq $true }).Count
    $failedTests = $totalTests - $passedTests

    Write-Log "=== TEST RESULTS SUMMARY ==="
    Write-Log "Total tests run: $totalTests"
    Write-Log "Tests passed: $passedTests"
    Write-Log "Tests failed: $failedTests"
    Write-Log "Success rate: $(($passedTests / $totalTests * 100).ToString('F1'))%"

    if ($failedTests -eq 0) {
        Write-Log "🎉 ALL TESTS PASSED!" "SUCCESS"
        return 0
    } else {
        Write-Log "❌ SOME TESTS FAILED" "ERROR"
        Write-Log "Check the log files in $logDir for details"
        return 1
    }
}

# Main execution
try {
    Write-Log "=== VRChat MCP Local Test Runner Started ==="
    Write-Log "Test Mode: $TestMode"
    Write-Log "Python Path: $PythonPath"
    Write-Log "Log Directory: $logDir"
    Write-Log "Timestamp: $timestamp"

    # Test prerequisites
    Test-Prerequisites

    # Run tests
    $testResults = @{}
    $serverProcess = $null

    if ($TestMode -in @("mcp", "both")) {
        # Test MCP interface
        $testResults["MCP_Interface"] = Run-MCPTest "tests/local/test_mcp_interface.py" "MCP_Interface"
    }

    if ($TestMode -in @("fastapi", "both")) {
        # Test FastAPI interface
        $testResults["FastAPI_Interface"] = Run-MCPTest "tests/local/test_fastapi_interface.py" "FastAPI_Interface"
    }

    # Send final report
    $exitCode = Send-TestReport $testResults

    Write-Log "=== Test Run Complete ==="

    # Cleanup
    if (-not $KeepLogs) {
        Write-VerboseLog "Cleaning up log files..."
        try {
            Remove-Item (Join-Path $logDir "server_*_$timestamp.log") -ErrorAction SilentlyContinue
            Remove-Item (Join-Path $logDir "test_*_$timestamp.log") -ErrorAction SilentlyContinue
        } catch {
            Write-VerboseLog "Warning: Could not clean up some log files"
        }
    }

    exit $exitCode

} catch {
    Write-Log "FATAL ERROR: $_" "ERROR"
    Write-Log "Stack trace: $($_.ScriptStackTrace)" "ERROR"
    exit 1
}


