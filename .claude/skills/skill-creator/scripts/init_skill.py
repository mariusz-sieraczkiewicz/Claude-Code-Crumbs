#!/usr/bin/env python3
"""
Initialize a new skill with the standard directory structure.

Usage:
    python init_skill.py <skill-name> --path <output-directory>
    python init_skill.py my-awesome-skill --path ./skills
"""

import argparse
import os
from pathlib import Path


def create_skill_structure(skill_name: str, output_path: str) -> None:
    """Create the standard skill directory structure."""

    # Normalize skill name
    skill_name = skill_name.lower().replace(" ", "-").replace("_", "-")

    # Create base directory
    skill_dir = Path(output_path) / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    (skill_dir / "scripts").mkdir(exist_ok=True)
    (skill_dir / "references").mkdir(exist_ok=True)
    (skill_dir / "assets").mkdir(exist_ok=True)

    # Create SKILL.md template
    skill_md_content = f"""---
name: {skill_name}
description: |
  [Describe what this skill does and when it should be triggered.
  Include specific keywords, phrases, or contexts that should activate this skill.]
---

# {skill_name.replace("-", " ").title()}

## Overview

[Provide a brief overview of what this skill enables Claude to do.]

## When to Use

This skill should be used when:
- [Condition 1]
- [Condition 2]

## Instructions

[Provide clear, concise instructions for how Claude should use this skill.]

## Resources

### Scripts
- `scripts/example.py` - [Description]

### References
- `references/guide.md` - [Description]

### Assets
- `assets/` - [Description of any assets]

## Examples

### Example 1: [Title]
**User request:** "[Example user request]"
**Expected behavior:** [What Claude should do]
"""

    (skill_dir / "SKILL.md").write_text(skill_md_content)

    # Create example script
    example_script = '''#!/usr/bin/env python3
"""
Example script for the skill.
Replace this with actual functionality.
"""

def main():
    print("Hello from the skill script!")

if __name__ == "__main__":
    main()
'''
    (skill_dir / "scripts" / "example.py").write_text(example_script)

    # Create example reference
    example_reference = """# Reference Guide

This file contains reference documentation that Claude can load when needed.

## Section 1

[Add detailed information here]

## Section 2

[Add more information here]
"""
    (skill_dir / "references" / "guide.md").write_text(example_reference)

    # Create .gitkeep in assets
    (skill_dir / "assets" / ".gitkeep").write_text("")

    print(f"✓ Created skill structure at: {skill_dir}")
    print(f"  ├── SKILL.md")
    print(f"  ├── scripts/")
    print(f"  │   └── example.py")
    print(f"  ├── references/")
    print(f"  │   └── guide.md")
    print(f"  └── assets/")
    print(f"\nNext steps:")
    print(f"  1. Edit SKILL.md with your skill's instructions")
    print(f"  2. Add scripts to scripts/")
    print(f"  3. Add reference docs to references/")
    print(f"  4. Add assets to assets/")


def main():
    parser = argparse.ArgumentParser(
        description="Initialize a new skill with standard directory structure"
    )
    parser.add_argument("skill_name", help="Name of the skill (will be normalized)")
    parser.add_argument(
        "--path",
        default=".",
        help="Output directory (default: current directory)"
    )

    args = parser.parse_args()
    create_skill_structure(args.skill_name, args.path)


if __name__ == "__main__":
    main()
