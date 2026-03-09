#!/usr/bin/env python3
"""
MCP Knowledge Base Server - Interactive Setup Script

This script helps you configure the MCP Knowledge Base Server for use with
multiple AI tools: Claude Desktop, Claude Code, Cursor, and OpenCode.

Usage:
    python setup.py              # Interactive setup
    python setup.py --dry-run    # Preview what would be configured
"""

import os
import sys
import json
import argparse
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any


@dataclass
class SetupConfig:
    """Configuration for the setup process."""

    mcp_server_path: Path
    personal_kb_path: Path
    work_kb_path: Optional[Path]
    file_extensions: List[str]
    max_file_size_mb: int
    tools: Dict[str, bool]


class SetupWizard:
    """Interactive setup wizard for MCP Knowledge Base Server."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.config: Optional[SetupConfig] = None
        self.os_type = self._detect_os()

    def _detect_os(self) -> str:
        """Detect the operating system."""
        if sys.platform == "darwin":
            return "macos"
        elif sys.platform == "win32":
            return "windows"
        else:
            return "linux"

    def _get_home_dir(self) -> Path:
        """Get the user's home directory."""
        return Path.home()

    def _ask_question(self, prompt: str, default: str = "", required: bool = False) -> str:
        """Ask the user a question and return their answer."""
        if default:
            full_prompt = f"{prompt} [{default}]: "
        else:
            full_prompt = f"{prompt}: "

        while True:
            answer = input(full_prompt).strip()
            if answer:
                return answer
            elif default:
                return default
            elif not required:
                return ""
            else:
                print("  This field is required. Please provide a value.")

    def _ask_yes_no(self, prompt: str, default: bool = True) -> bool:
        """Ask a yes/no question."""
        default_str = "Y/n" if default else "y/N"
        answer = input(f"{prompt} [{default_str}]: ").strip().lower()

        if not answer:
            return default
        return answer.startswith("y")

    def _ask_multiple_choice(self, prompt: str, options: List[str]) -> List[str]:
        """Ask user to select multiple options."""
        print(f"\n{prompt}")
        print("Select all that apply (comma-separated numbers, or 'all'):")

        for i, option in enumerate(options, 1):
            print(f"  [{i}] {option}")

        answer = input("\nYour selection: ").strip().lower()

        if answer == "all":
            return options

        selected = []
        try:
            for num in answer.split(","):
                idx = int(num.strip()) - 1
                if 0 <= idx < len(options):
                    selected.append(options[idx])
        except ValueError:
            print("  Invalid selection. Please use comma-separated numbers.")
            return self._ask_multiple_choice(prompt, options)

        return selected

    def run(self) -> SetupConfig:
        """Run the interactive setup wizard."""
        print("=" * 70)
        print("MCP Knowledge Base Server - Setup Wizard")
        print("=" * 70)
        print()
        print("This wizard will help you configure the MCP Knowledge Base Server")
        print("for use with your favorite AI tools.")
        print()

        if self.dry_run:
            print("[DRY RUN MODE - No files will be modified]")
            print()

        # Step 1: MCP Server Location
        print("Step 1: MCP Server Location")
        print("-" * 70)
        current_dir = Path.cwd()
        server_path_input = self._ask_question(
            "Where is the MCP server located?", str(current_dir / "mcp_kb_server.py")
        )
        server_path = Path(server_path_input).expanduser().resolve()

        if not server_path.exists():
            print(f"\n  Warning: File not found at {server_path}")
            if not self._ask_yes_no("Continue anyway?", default=False):
                sys.exit(1)

        # Step 2: Knowledge Base Paths
        print("\n\nStep 2: Knowledge Base Configuration")
        print("-" * 70)
        print("You can set up one or two knowledge bases:")
        print("  - Personal: For personal projects, learning notes, hobbies")
        print("  - Work: For professional work, company projects")
        print()

        personal_kb = self._ask_question(
            "Personal knowledge base path?", str(self._get_home_dir() / "knowledge-base")
        )
        personal_kb_path = Path(personal_kb).expanduser().resolve()

        use_work_kb = self._ask_yes_no("\nSet up a separate work knowledge base?", default=False)

        work_kb_path = None
        if use_work_kb:
            work_kb = self._ask_question(
                "Work knowledge base path?", str(self._get_home_dir() / "knowledge-base-work")
            )
            work_kb_path = Path(work_kb).expanduser().resolve()

        # Step 3: File Settings
        print("\n\nStep 3: File Settings")
        print("-" * 70)

        extensions_input = self._ask_question("File extensions to index?", ".md,.json")
        extensions = [ext.strip() for ext in extensions_input.split(",")]

        max_size = self._ask_question("Maximum file size (MB)?", "10")

        # Step 4: AI Tools Selection
        print("\n\nStep 4: AI Tools Configuration")
        print("-" * 70)
        print("Which AI tools do you want to configure?")
        print()

        tools = {
            "claude_desktop": self._ask_yes_no("Configure for Claude Desktop?", default=True),
            "claude_code": self._ask_yes_no("Configure for Claude Code?", default=False),
            "cursor": self._ask_yes_no("Configure for Cursor?", default=False),
            "opencode": self._ask_yes_no("Configure for OpenCode?", default=False),
        }

        # Create config
        self.config = SetupConfig(
            mcp_server_path=server_path,
            personal_kb_path=personal_kb_path,
            work_kb_path=work_kb_path,
            file_extensions=extensions,
            max_file_size_mb=int(max_size),
            tools=tools,
        )

        return self.config

    def preview(self) -> None:
        """Preview the configuration without making changes."""
        if not self.config:
            print("No configuration to preview. Run setup first.")
            return

        print("\n" + "=" * 70)
        print("Configuration Preview")
        print("=" * 70)
        print()
        print(f"MCP Server Path:     {self.config.mcp_server_path}")
        print(f"Personal KB Path:    {self.config.personal_kb_path}")
        print(f"Work KB Path:        {self.config.work_kb_path or 'Not configured'}")
        print(f"File Extensions:     {', '.join(self.config.file_extensions)}")
        print(f"Max File Size:       {self.config.max_file_size_mb} MB")
        print()
        print("AI Tools to Configure:")
        for tool, enabled in self.config.tools.items():
            status = "✓" if enabled else "✗"
            print(f"  [{status}] {tool.replace('_', ' ').title()}")
        print()

    def apply(self) -> None:
        """Apply the configuration by creating all necessary files."""
        if not self.config:
            print("No configuration to apply. Run setup first.")
            return

        if self.dry_run:
            print("[DRY RUN - No files modified]")
            return

        print("\n" + "=" * 70)
        print("Applying Configuration")
        print("=" * 70)
        print()

        # Create knowledge base directories
        self._create_kb_directories()

        # Generate configs for each tool
        if self.config.tools["claude_desktop"]:
            self._setup_claude_desktop()

        if self.config.tools["claude_code"]:
            self._setup_claude_code()

        if self.config.tools["cursor"]:
            self._setup_cursor()

        if self.config.tools["opencode"]:
            self._setup_opencode()

        print()
        print("=" * 70)
        print("Setup Complete!")
        print("=" * 70)
        print()
        print("Summary:")
        print(f"  ✓ Knowledge base directories created")
        print(f"  ✓ Configuration files generated for enabled tools")
        print()
        print("Next steps:")
        print("  1. Review the generated configuration files")
        print("  2. Install the MCP server dependencies: pip install -r requirements.txt")
        print("  3. Restart your AI tool to load the new configuration")
        print()

    def _create_kb_directories(self) -> None:
        """Create knowledge base directories."""
        print("Creating knowledge base directories...")

        # Create personal KB structure
        personal_kb = self.config.personal_kb_path
        (personal_kb / "docs").mkdir(parents=True, exist_ok=True)
        (personal_kb / "knowledge").mkdir(parents=True, exist_ok=True)
        (personal_kb / "config").mkdir(parents=True, exist_ok=True)

        print(f"  ✓ {personal_kb}")

        # Create work KB if configured
        if self.config.work_kb_path:
            work_kb = self.config.work_kb_path
            (work_kb / "docs").mkdir(parents=True, exist_ok=True)
            (work_kb / "knowledge").mkdir(parents=True, exist_ok=True)
            (work_kb / "config").mkdir(parents=True, exist_ok=True)
            print(f"  ✓ {work_kb}")

    def _get_kb_paths_string(self, kb_path: Path) -> str:
        """Get the knowledge base paths string for a given KB."""
        docs_path = kb_path / "docs"
        knowledge_path = kb_path / "knowledge"
        config_path = kb_path / "config"
        return f"{knowledge_path},{docs_path},{config_path}"

    def _setup_claude_desktop(self) -> None:
        """Configure for Claude Desktop."""
        print("\nConfiguring Claude Desktop...")

        # Claude Desktop config location
        if self.os_type == "macos":
            config_dir = self._get_home_dir() / "Library" / "Application Support" / "Claude"
        elif self.os_type == "windows":
            config_dir = Path(os.environ.get("APPDATA", "")) / "Claude"
        else:
            config_dir = self._get_home_dir() / ".config" / "Claude"

        config_file = config_dir / "claude_desktop_config.json"

        # Create config directory if it doesn't exist
        config_dir.mkdir(parents=True, exist_ok=True)

        # Build MCP servers config
        mcp_servers = {
            "personal-kb": {
                "command": "python",
                "args": [str(self.config.mcp_server_path)],
                "env": {
                    "KB_PATHS": self._get_kb_paths_string(self.config.personal_kb_path),
                    "KB_EXTENSIONS": ",".join(self.config.file_extensions),
                    "KB_MAX_SIZE_MB": str(self.config.max_file_size_mb),
                },
            }
        }

        # Add work KB if configured
        if self.config.work_kb_path:
            mcp_servers["work-kb"] = {
                "command": "python",
                "args": [str(self.config.mcp_server_path)],
                "env": {
                    "KB_PATHS": self._get_kb_paths_string(self.config.work_kb_path),
                    "KB_EXTENSIONS": ",".join(self.config.file_extensions),
                    "KB_MAX_SIZE_MB": str(self.config.max_file_size_mb),
                },
            }

        config = {"mcpServers": mcp_servers}

        # Backup existing config
        if config_file.exists():
            backup_file = config_file.with_suffix(".json.backup")
            with open(config_file, "r") as f:
                existing = json.load(f)
            with open(backup_file, "w") as f:
                json.dump(existing, f, indent=2)
            print(f"  ✓ Backed up existing config to {backup_file}")

        # Write config
        with open(config_file, "w") as f:
            json.dump(config, f, indent=2)

        print(f"  ✓ Config written to: {config_file}")
        print(f"  ✓ Configured MCP servers: {', '.join(mcp_servers.keys())}")

    def _setup_claude_code(self) -> None:
        """Configure for Claude Code."""
        print("\nConfiguring Claude Code...")
        print("  Note: Claude Code uses project-specific configuration.")
        print("  To use with Claude Code, add this to your project's .claude/ directory")
        print("  or set the MCP_CONFIG_PATH environment variable.")

        # Create example config in current directory
        config_file = Path.cwd() / "claude-code-mcp.json"

        mcp_servers = {
            "personal-kb": {
                "command": "python",
                "args": [str(self.config.mcp_server_path)],
                "env": {
                    "KB_PATHS": self._get_kb_paths_string(self.config.personal_kb_path),
                    "KB_EXTENSIONS": ",".join(self.config.file_extensions),
                    "KB_MAX_SIZE_MB": str(self.config.max_file_size_mb),
                },
            }
        }

        if self.config.work_kb_path:
            mcp_servers["work-kb"] = {
                "command": "python",
                "args": [str(self.config.mcp_server_path)],
                "env": {
                    "KB_PATHS": self._get_kb_paths_string(self.config.work_kb_path),
                    "KB_EXTENSIONS": ",".join(self.config.file_extensions),
                    "KB_MAX_SIZE_MB": str(self.config.max_file_size_mb),
                },
            }

        config = {"mcpServers": mcp_servers}

        with open(config_file, "w") as f:
            json.dump(config, f, indent=2)

        print(f"  ✓ Example config created: {config_file}")
        print("  ✓ Copy this file to your project's .claude/mcp.json")

    def _setup_cursor(self) -> None:
        """Configure for Cursor."""
        print("\nConfiguring Cursor...")

        # Cursor config location
        if self.os_type == "macos":
            config_dir = self._get_home_dir() / "Library" / "Application Support" / "Cursor"
        elif self.os_type == "windows":
            config_dir = Path(os.environ.get("APPDATA", "")) / "Cursor"
        else:
            config_dir = self._get_home_dir() / ".config" / "Cursor"

        # Cursor uses .cursor/mcp.json in the workspace
        print("  Note: Cursor uses workspace-specific MCP configuration.")
        print("  Creating example configuration file...")

        config_file = Path.cwd() / ".cursor" / "mcp.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)

        mcp_servers = {
            "personal-kb": {
                "command": "python",
                "args": [str(self.config.mcp_server_path)],
                "env": {
                    "KB_PATHS": self._get_kb_paths_string(self.config.personal_kb_path),
                    "KB_EXTENSIONS": ",".join(self.config.file_extensions),
                    "KB_MAX_SIZE_MB": str(self.config.max_file_size_mb),
                },
            }
        }

        if self.config.work_kb_path:
            mcp_servers["work-kb"] = {
                "command": "python",
                "args": [str(self.config.mcp_server_path)],
                "env": {
                    "KB_PATHS": self._get_kb_paths_string(self.config.work_kb_path),
                    "KB_EXTENSIONS": ",".join(self.config.file_extensions),
                    "KB_MAX_SIZE_MB": str(self.config.max_file_size_mb),
                },
            }

        config = {"mcpServers": mcp_servers}

        with open(config_file, "w") as f:
            json.dump(config, f, indent=2)

        print(f"  ✓ Config created: {config_file}")
        print("  ✓ Copy the .cursor directory to your project root")

    def _setup_opencode(self) -> None:
        """Configure for OpenCode."""
        print("\nConfiguring OpenCode...")

        # OpenCode config location
        config_dir = self._get_home_dir() / ".config" / "opencode"
        config_file = config_dir / "opencode.json"

        # Create config directory if it doesn't exist
        config_dir.mkdir(parents=True, exist_ok=True)

        # Build MCP config
        mcp_config = {
            "personal-kb": {
                "type": "local",
                "command": ["python", str(self.config.mcp_server_path)],
                "enabled": True,
                "environment": {
                    "KB_PATHS": self._get_kb_paths_string(self.config.personal_kb_path),
                    "KB_EXTENSIONS": ",".join(self.config.file_extensions),
                    "KB_MAX_SIZE_MB": str(self.config.max_file_size_mb),
                },
            }
        }

        if self.config.work_kb_path:
            mcp_config["work-kb"] = {
                "type": "local",
                "command": ["python", str(self.config.mcp_server_path)],
                "enabled": True,
                "environment": {
                    "KB_PATHS": self._get_kb_paths_string(self.config.work_kb_path),
                    "KB_EXTENSIONS": ",".join(self.config.file_extensions),
                    "KB_MAX_SIZE_MB": str(self.config.max_file_size_mb),
                },
            }

        config = {"$schema": "https://opencode.ai/config.json", "mcp": mcp_config}

        # Backup existing config
        if config_file.exists():
            backup_file = config_file.with_suffix(".json.backup")
            with open(config_file, "r") as f:
                existing = json.load(f)
            with open(backup_file, "w") as f:
                json.dump(existing, f, indent=2)
            print(f"  ✓ Backed up existing config to {backup_file}")

        # Write config
        with open(config_file, "w") as f:
            json.dump(config, f, indent=2)

        print(f"  ✓ Config written to: {config_file}")
        print(f"  ✓ Configured MCP servers: {', '.join(mcp_config.keys())}")


def main():
    parser = argparse.ArgumentParser(description="Setup wizard for MCP Knowledge Base Server")
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview configuration without making changes"
    )

    args = parser.parse_args()

    wizard = SetupWizard(dry_run=args.dry_run)

    # Run interactive setup
    wizard.run()

    # Preview configuration
    wizard.preview()

    # Confirm and apply
    if not args.dry_run:
        if wizard._ask_yes_no("\nApply this configuration?", default=True):
            wizard.apply()
        else:
            print("\nSetup cancelled. No changes were made.")
            sys.exit(0)
    else:
        print("\n[DRY RUN COMPLETE - No files were modified]")
        print("Run without --dry-run to apply the configuration.")


if __name__ == "__main__":
    main()
