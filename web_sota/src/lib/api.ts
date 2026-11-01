// Backend base URL. Fleet launcher injects VITE_API_TARGET=http://127.0.0.1:<backendPort>.
// Fallback matches fleet-start.config.ps1 BackendPort 10712.
export const API_BASE =
  (import.meta as any)?.env?.VITE_API_TARGET || "http://127.0.0.1:10712";
