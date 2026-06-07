#!/usr/bin/env python3
"""
Run the plugin audit and generate a report.

This script runs the plugin audit and generates a detailed report of any
issues found in the plugins.
"""

import json
import os
import sys
from typing import Any

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.audit_plugins import PLUGINS_DIR, PluginAudit


def generate_report(report: dict[str, Any], output_file: str | None = None) -> str:
    """Generate a report from the audit results.

    Args:
        report: The audit report to format
        output_file: Optional path to write the report to

    Returns:
        The formatted report as a string
    """
    lines = []

    # Header
    lines.append("=" * 80)
    lines.append(f"PLUGIN AUDIT REPORT: {report['plugin']}")
    lines.append("=" * 80)
    lines.append(f"File: {report['file']}")
    lines.append(f"Tools found: {len(report['tools'])}")
    lines.append(f"Event listeners found: {len(report['event_listeners'])}")
    lines.append(f"Issues found: {len(report['issues'])}")
    lines.append("")

    # Tools section
    if report["tools"]:
        lines.append("TOOLS:")
        lines.append("-" * 40)
        for tool in report["tools"]:
            lines.append(f"  {tool['name']}")
            lines.append(f"    Description: {tool.get('description', 'No description')}")
            lines.append(f"    Category: {tool.get('category', 'Uncategorized')}")

            # Check for missing metadata
            missing_meta = [m for m in ["description", "category", "args", "returns"] if m not in tool or not tool[m]]
            if missing_meta:
                lines.append(f"    WARNING: Missing metadata: {', '.join(missing_meta)}")

            # Check docstring
            if not tool.get("docstring"):
                lines.append("    WARNING: Missing docstring")
            else:
                if "Args:" not in tool["docstring"]:
                    lines.append("    WARNING: Docstring missing 'Args:' section")
                if "Returns:" not in tool["docstring"] and not tool["name"].startswith("on_"):
                    lines.append("    WARNING: Docstring missing 'Returns:' section")

            lines.append("")

    # Event listeners section
    if report["event_listeners"]:
        lines.append("EVENT LISTENERS:")
        lines.append("-" * 40)
        for listener in report["event_listeners"]:
            lines.append(f"  {listener['name']} (event: {listener['event_type']})")
            if not listener.get("docstring"):
                lines.append("    WARNING: Missing docstring")
            lines.append("")

    # Issues section
    if report["issues"]:
        lines.append("ISSUES:")
        lines.append("-" * 40)
        for severity, message in report["issues"]:
            lines.append(f"  {severity.upper()}: {message}")

    # Summary
    lines.append("")
    lines.append("SUMMARY:")
    lines.append("-" * 40)
    lines.append(f"Total tools: {len(report['tools'])}")
    lines.append(f"Total event listeners: {len(report['event_listeners'])}")
    lines.append(f"Total issues: {len(report['issues'])}")

    # Write to file if specified
    report_str = "\n".join(lines)
    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report_str)

    return report_str


def main():
    """Run the plugin audit and generate a report."""
    # Find all Python files in the plugins directory
    plugin_files = []
    for filename in os.listdir(PLUGINS_DIR):
        if filename.endswith(".py") and not filename.startswith("__"):
            plugin_files.append(os.path.join(PLUGINS_DIR, filename))

    if not plugin_files:
        print("No plugin files found!")
        return 1

    # Run the audit on each plugin
    all_reports = []
    for plugin_file in sorted(plugin_files):
        print(f"Auditing {os.path.basename(plugin_file)}...")
        audit = PluginAudit(plugin_file)
        report = audit.run_audit()
        all_reports.append(report)

    # Generate individual reports
    for report in all_reports:
        report_file = os.path.join(os.path.dirname(PLUGINS_DIR), "reports", f"audit_{report['plugin']}.txt")
        os.makedirs(os.path.dirname(report_file), exist_ok=True)
        generate_report(report, report_file)

    # Generate a summary report
    summary = {
        "total_plugins": len(all_reports),
        "total_tools": sum(len(r["tools"]) for r in all_reports),
        "total_event_listeners": sum(len(r["event_listeners"]) for r in all_reports),
        "total_issues": sum(len(r["issues"]) for r in all_reports),
        "plugins": [
            {
                "name": r["plugin"],
                "file": r["file"],
                "tools": len(r["tools"]),
                "event_listeners": len(r["event_listeners"]),
                "issues": len(r["issues"]),
            }
            for r in all_reports
        ],
    }

    # Write summary to JSON
    summary_file = os.path.join(os.path.dirname(PLUGINS_DIR), "reports", "audit_summary.json")
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    # Print summary
    print("\n" + "=" * 80)
    print("AUDIT SUMMARY")
    print("=" * 80)
    print(f"Plugins audited: {summary['total_plugins']}")
    print(f"Total tools: {summary['total_tools']}")
    print(f"Total event listeners: {summary['total_event_listeners']}")
    print(f"Total issues found: {summary['total_issues']}")
    print("\nDetailed reports have been saved to the 'reports' directory.")

    return 0 if summary["total_issues"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
