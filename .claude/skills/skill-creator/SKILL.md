---
name: skill-creator
description: Guide for creating effective skills. This skill should be used when users want to create a new skill (or update an existing skill) that extends Claude's capabilities with specialized knowledge, workflows, or tool integrations.
---

# Skill Creator

## About Skills

Skills are modular, self-contained packages that extend Claude's capabilities by providing:
- **Specialized workflows**: Multi-step procedures for specific domains
- **Tool integrations**: Instructions for working with specific file formats or APIs
- **Domain expertise**: Company-specific knowledge, schemas, business logic
- **Bundled resources**: Scripts, references, and assets for complex tasks

## Core Principles

### Concise is Key
- The context window is a shared resource
- Assume Claude is already very smart—only add context Claude doesn't have
- Prefer concise examples over verbose explanations

### Set Appropriate Degrees of Freedom
- **High freedom** (text-based instructions): Multiple approaches valid, context-dependent decisions
- **Medium freedom** (pseudocode/scripts with parameters): Preferred pattern exists, some variation acceptable
- **Low freedom** (specific scripts, few parameters): Operations fragile, consistency critical

## Anatomy of a Skill

```
skill-name/
├── SKILL.md (required)
│   ├── YAML frontmatter metadata (required)
│   │   ├── name: (required)
│   │   └── description: (required)
│   └── Markdown instructions (required)
└── Bundled Resources (optional)
    ├── scripts/ - Executable code (Python/Bash/etc.)
    ├── references/ - Documentation to load into context as needed
    └── assets/ - Files used in output (templates, icons, fonts, etc.)
```

## SKILL.md Structure

### Frontmatter (YAML)
- `name`: Skill name (lowercase, hyphens for spaces)
- `description`: Critical for triggering—include what the skill does and specific triggers/contexts

### Body (Markdown)
- Instructions and guidance for using the skill and bundled resources

## Bundled Resources

### Scripts (scripts/)
- Executable code for tasks requiring deterministic reliability
- Use when same code is repeatedly rewritten
- Example: `scripts/rotate_pdf.py`

### References (references/)
- Documentation to be loaded into context as needed
- Examples: `references/finance.md`, `references/api_docs.md`
- Keep in separate files to avoid duplication with SKILL.md
- Include grep search patterns for large files (>10k words)

### Assets (assets/)
- Files used in output, not loaded into context
- Examples: `assets/logo.png`, `assets/template.pptx`

## What NOT to Include
- README.md, INSTALLATION_GUIDE.md, QUICK_REFERENCE.md, CHANGELOG.md
- Any auxiliary documentation
- Skills should only contain information needed for Claude to do the job

## Progressive Disclosure Design

Three-level loading system:
1. **Metadata** (name + description) - Always in context (~100 words)
2. **SKILL.md body** - When skill triggers (<5k words)
3. **Bundled resources** - As needed by Claude (unlimited)

Key patterns:
- Keep SKILL.md body under 500 lines
- High-level guide with references to detailed content
- Avoid deeply nested references—keep one level deep
- Include table of contents for files longer than 100 lines

## Skill Creation Process

### Step 1: Understanding with Concrete Examples
- Gather real or generated examples of skill usage
- Understand functionality the skill should support
- Ask: "What would users say that should trigger this skill?"

### Step 2: Planning Reusable Skill Contents
- Analyze each concrete example
- Identify reusable resources (scripts, references, assets)

### Step 3: Initialize the Skill
Run `scripts/init_skill.py <skill-name> --path <output-directory>` to create:
- Skill directory structure
- SKILL.md template with frontmatter
- Example resource directories

### Step 4: Edit the Skill
1. See `references/workflows.md` for design patterns
2. Implement scripts/, references/, assets/ files
3. Test all scripts by running them
4. Update SKILL.md with clear frontmatter and instructions
5. Use imperative/infinitive form throughout

### Step 5: Package the Skill
Run `scripts/package_skill.py <path/to/skill-folder>` to:
- Validate skill structure
- Create distributable .skill file

### Step 6: Iterate
- Use skill on real tasks
- Notice struggles or inefficiencies
- Update and repackage
