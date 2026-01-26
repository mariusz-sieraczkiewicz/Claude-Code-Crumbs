# Workflow Design Patterns

## Sequential Workflows

Sequential workflows are step-by-step procedures that Claude follows in order.

### Pattern: Linear Steps

```markdown
## Workflow

1. **Step 1: Gather Information**
   - Ask user for X
   - Read file Y

2. **Step 2: Process**
   - Transform data using Z
   - Validate results

3. **Step 3: Output**
   - Generate report
   - Save to file
```

### Pattern: Conditional Steps

```markdown
## Workflow

1. **Analyze Input**
   - Determine input type

2. **Process Based on Type**
   - If type A: Use method X
   - If type B: Use method Y
   - Otherwise: Ask for clarification

3. **Finalize**
   - Apply common post-processing
```

## Decision Trees

Use decision trees when the workflow depends on multiple conditions.

```markdown
## Decision Process

```
Input received
├── Is it valid?
│   ├── Yes → Process normally
│   └── No → Request correction
├── Requires approval?
│   ├── Yes → Queue for review
│   └── No → Execute immediately
└── Has dependencies?
    ├── Yes → Resolve first
    └── No → Proceed
```
```

## Iterative Workflows

For tasks that require multiple passes or refinement.

```markdown
## Iterative Refinement

1. **Initial Pass**
   - Generate first draft
   - Quick validation

2. **Refinement Loop** (repeat until quality threshold met)
   - Review output
   - Identify issues
   - Apply corrections

3. **Final Validation**
   - Comprehensive check
   - User confirmation
```

## Parallel Workflows

When independent tasks can be done simultaneously.

```markdown
## Parallel Processing

Execute in parallel:
- [ ] Task A: Gather data from source 1
- [ ] Task B: Gather data from source 2
- [ ] Task C: Prepare output template

After all complete:
- Merge results
- Generate final output
```

## Error Handling Patterns

### Graceful Degradation

```markdown
## Error Handling

On error:
1. Log the error context
2. Attempt recovery:
   - Try alternative method
   - Use cached/default value
   - Ask user for guidance
3. If unrecoverable:
   - Explain what failed
   - Suggest manual steps
```

### Checkpoint Pattern

```markdown
## Checkpointed Workflow

1. **Checkpoint: Start**
   - Save initial state

2. **Phase 1: Data Collection**
   - Collect data
   - **Checkpoint: Data collected**

3. **Phase 2: Processing**
   - Process data
   - **Checkpoint: Processing complete**

4. **Phase 3: Output**
   - Generate output
   - **Checkpoint: Complete**

On failure: Resume from last checkpoint
```
