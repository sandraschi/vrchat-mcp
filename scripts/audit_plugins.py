#!/usr/bin/env python3
"""
Audit VRChat MCP plugins for compliance with documentation standards.

This script checks all plugins for proper docstrings, @tool decorator usage,
and other coding standards.
"""

import ast
import importlib.util
import inspect
import os
import sys
from typing import Any

# Define the plugins directory
PLUGINS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "vrchat_mcp", "plugins")

# Define the standards that plugins should follow
REQUIRED_TOOL_METADATA = ["name", "description", "category", "args", "returns", "requires_auth", "rate_limit"]


class PluginAudit:
    """Class to audit a single plugin file."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self.plugin_name = os.path.splitext(self.filename)[0]
        self.issues: list[tuple[str, str]] = []
        self.tools: list[dict[str, Any]] = []
        self.event_listeners: list[dict[str, str]] = []
        self.ast_tree = None

    def load_module(self) -> bool:
        """Load the plugin module using importlib."""
        try:
            spec = importlib.util.spec_from_file_location(f"vrchat_mcp.plugins.{self.plugin_name}", self.filepath)
            if spec is None or spec.loader is None:
                self.issues.append(("error", "Failed to create module spec"))
                return False

            module = importlib.util.module_from_spec(spec)
            sys.modules[f"vrchat_mcp.plugins.{self.plugin_name}"] = module
            spec.loader.exec_module(module)
            self.module = module
            return True
        except Exception as e:
            self.issues.append(("error", f"Failed to import module: {e!s}"))
            return False

    def parse_ast(self) -> None:
        """Parse the file with AST to find tool and event listener decorators."""
        try:
            with open(self.filepath, encoding="utf-8") as f:
                content = f.read()
            self.ast_tree = ast.parse(content, filename=self.filename)
        except Exception as e:
            self.issues.append(("error", f"Failed to parse AST: {e!s}"))

    def check_plugin_class(self) -> None:
        """Check if the plugin class is properly defined."""
        # Find the plugin class (should be named {PluginName}Plugin)
        plugin_class = None
        for name, obj in inspect.getmembers(self.module, inspect.isclass):
            if (
                name.endswith("Plugin")
                and name != "Plugin"
                and hasattr(obj, "__module__")
                and obj.__module__ == self.module.__name__
            ):
                plugin_class = obj
                break

        if plugin_class is None:
            self.issues.append(("error", "No plugin class found (should be named {Name}Plugin)"))
            return

        # Check required methods
        required_methods = ["name"]
        for method in required_methods:
            if not hasattr(plugin_class, method):
                self.issues.append(("error", f"Missing required method: {method}"))

        return plugin_class

    def check_tools(self, plugin_class: type) -> None:
        """Check all tools in the plugin class."""
        for name, method in inspect.getmembers(plugin_class, inspect.isfunction):
            if name.startswith("_"):
                continue

            if hasattr(method, "_is_tool"):
                self.audit_tool(name, method)

            # Also check for @event_listener
            if hasattr(method, "_event_listeners"):
                self.event_listeners.extend(
                    [
                        {"name": name, "event_type": listener.get("event_type", "unknown")}
                        for listener in method._event_listeners
                    ]
                )

    def audit_tool(self, name: str, method: Any) -> None:
        """Audit a single tool method."""
        metadata = getattr(method, "_tool_metadata", {})

        # Check for required metadata
        missing_metadata = [m for m in REQUIRED_TOOL_METADATA if m not in metadata]
        if missing_metadata:
            self.issues.append(
                ("warning", f"Tool '{name}' is missing required metadata: {', '.join(missing_metadata)}")
            )

        # Check docstring
        doc = inspect.getdoc(method)
        if not doc:
            self.issues.append(("warning", f"Tool '{name}' is missing a docstring"))
        else:
            # Check for Args and Returns sections
            if "Args:" not in doc:
                self.issues.append(("warning", f"Tool '{name}' docstring is missing 'Args:' section"))
            if "Returns:" not in doc:
                self.issues.append(("warning", f"Tool '{name}' docstring is missing 'Returns:' section"))

        # Store tool info
        self.tools.append(
            {
                "name": name,
                "metadata": metadata,
                "has_docstring": bool(doc),
                "has_args_section": bool(doc and "Args:" in doc),
                "has_returns_section": bool(doc and "Returns:" in doc),
            }
        )

    def run_audit(self) -> dict[str, Any]:
        """Run the complete audit."""
        self.parse_ast()

        if not self.load_module():
            return self.get_report()

        plugin_class = self.check_plugin_class()
        if plugin_class is not None:
            self.check_tools(plugin_class)

        return self.get_report()

    def get_report(self) -> dict[str, Any]:
        """Generate a report of the audit findings."""
        return {
            "plugin": self.plugin_name,
            "file": self.filename,
            "issues": self.issues,
            "tools_found": len(self.tools),
            "event_listeners_found": len(self.event_listeners),
            "tools": self.tools,
            "event_listeners": self.event_listeners,
        }


def print_report(report: dict[str, Any]) -> None:
    """Print a formatted audit report."""
    print(f"\n{'=' * 80}")
    print(f"AUDIT REPORT: {report['plugin']} ({report['file']})")
    print(f"{'=' * 80}")

    # Print summary
    print("\n📊 SUMMARY")
    print(f"- Tools found: {report['tools_found']}")
    print(f"- Event listeners found: {report['event_listeners_found']}")
    print(f"- Issues found: {len(report['issues'])}")

    # Print tools
    if report["tools"]:
        print("\n🔧 TOOLS")
        for tool in report["tools"]:
            status = []
            if tool["has_docstring"]:
                status.append("📝")
            else:
                status.append("❌")

            if tool["has_args_section"]:
                status.append("📋")
            else:
                status.append("❌")

            if tool["has_returns_section"]:
                status.append("🔄")
            else:
                status.append("❌")

            print(f"  {' '.join(status)} {tool['name']}")

    # Print event listeners
    if report["event_listeners"]:
        print("\n🎯 EVENT LISTENERS")
        for listener in report["event_listeners"]:
            print(f"  - {listener['name']} (event: {listener['event_type']})")

    # Print issues
    if report["issues"]:
        print("\n⚠️  ISSUES")
        for severity, message in report["issues"]:
            print(f"  {severity.upper()}: {message}")

    print(f"\n✅ Audit complete for {report['plugin']}")
    print(f"{'=' * 80}\n")


def main():
    """Main function to run the plugin audit."""
    print(f"🔍 Auditing plugins in: {PLUGINS_DIR}\n")

    # Find all plugin files
    plugin_files = []
    for filename in os.listdir(PLUGINS_DIR):
        if filename.endswith(".py") and not filename.startswith("__") and not filename.startswith("."):
            plugin_files.append(os.path.join(PLUGINS_DIR, filename))

    if not plugin_files:
        print("❌ No plugin files found!")
        return 1

    # Audit each plugin
    all_issues = 0
    for plugin_file in sorted(plugin_files):
        audit = PluginAudit(plugin_file)
        report = audit.run_audit()
        all_issues += len(report["issues"])
        print_report(report)

    # Print final summary
    print(f"\n{'=' * 80}")
    print("AUDIT COMPLETE")
    print(f"{'=' * 80}")
    print(f"Total plugins audited: {len(plugin_files)}")
    print(f"Total issues found: {all_issues}")
    print(f"{'=' * 80}\n")

    return 0 if all_issues == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
