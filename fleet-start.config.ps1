# Per-repo fleet start config for vrchat-mcp
@{
    Name         = 'vrchat-mcp'
    BackendPort  = 10712
    FrontendPort = 11252
    HealthPath   = '/health'
    WebRoot      = 'web_sota'
    Backend = @{
        Kind          = 'uvicorn'
        UvicornTarget = 'web_sota.backend.server:app'
        Env           = @{ WEB_PORT = '10712' }
    }
    Frontend = @{
        Kind           = 'vite-npm'
        PackageManager = 'npm'
        PortEnvVar     = 'VITE_PORT'
        ApiTargetEnv   = 'VITE_API_TARGET'
    }
}