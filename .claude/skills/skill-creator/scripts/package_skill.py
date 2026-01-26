#!/usr/bin/env python3
"""
Package a skill into a distributable .skill file.

Usage:
    python package_skill.py <path/to/skill-folder>
    python package_skill.py <path/to/skill-folder> ./dist
"""

import argparse
import os
import sys
import zipfile
from pathlib import Path
import re


def validate_skill(skill_path: Path) -> list[str]:
    """Validate skill structure and return list of errors."""
    errors = []

    # Check SKILL.md exists
    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        errors.append("Missing required file: SKILL.md")
        return errors

    # Read and validate SKILL.md
    content = skill_md.read_text()

    # Check for YAML frontmatter
    if not content.startswith("---"):
        errors.append("SKILL.md must start with YAML frontmatter (---)")
        return errors

    # Extract frontmatter
    parts = content.split("---", 2)
    if len(parts) < 3:
        errors.append("SKILL.md frontmatter not properly closed (missing second ---)")
        return errors

    frontmatter = parts[1].strip()

    # Check required fields
    if not re.search(r'^name:\s*\S', frontmatter, re.MULTILINE):
        errors.append("SKILL.md frontmatter missing required field: name")

    if not re.search(r'^description:\s*\S', frontmatter, re.MULTILINE):
        errors.append("SKILL.md frontmatter missing required field: description")

    # Check for forbidden files
    forbidden_files = [
        "README.md", "INSTALLATION_GUIDE.md", "QUICK_REFERENCE.md",
        "CHANGELOG.md", "LICENSE.md"
    ]
    for forbidden in forbidden_files:
        if (skill_path / forbidden).exists():
            errors.append(f"Skill should not contain: {forbidden}")

    # Check line count
    line_count = len(content.splitlines())
    if line_count > 500:
        errors.append(f"SKILL.md exceeds recommended 500 lines ({line_count} lines)")

    return errors


def package_skill(skill_path: Path, output_dir: Path) -> Path:
    """Package skill into a .skill file (zip format)."""

    skill_name = skill_path.name
    output_file = output_dir / f"{skill_name}.skill"

    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(skill_path):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]

            for file in files:
                # Skip hidden files
                if file.startswith('.'):
                    continue

                file_path = Path(root) / file
                arcname = file_path.relative_to(skill_path)
                zf.write(file_path, arcname)

    return output_file


def main():
    parser = argparse.ArgumentParser(
        description="Package a skill into a distributable .skill file"
    )
    parser.add_argument("skill_path", help="Path to the skill folder")
    parser.add_argument(
        "output_dir",
        nargs="?",
        default=".",
        help="Output directory (default: current directory)"
    )

    args = parser.parse_args()

    skill_path = Path(args.skill_path).resolve()
    output_dir = Path(args.output_dir).resolve()

    if not skill_path.is_dir():
        print(f"Error: {skill_path} is not a directory")
        sys.exit(1)

    # Validate
    print(f"Validating skill: {skill_path.name}")
    errors = validate_skill(skill_path)

    if errors:
        print("\n❌ Validation failed:")
        for error in errors:
            print(f"  • {error}")
        sys.exit(1)

    print("✓ Validation passed")

    # Package
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = package_skill(skill_path, output_dir)

    print(f"✓ Packaged skill: {output_file}")
    print(f"  Size: {output_file.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
