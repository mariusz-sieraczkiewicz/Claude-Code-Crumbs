# The board

The GitHub Project board is the only place the human sees what the factory is doing. They do not
open issues, do not read comments, and do not watch any agent. So the board has to answer one
question at a glance: **what is happening right now, on each task?**

A single "In Progress" column cannot answer it — a task sits there for two hours and the human
cannot tell writing code from waiting on a review from being stuck. So the `Status` field carries
the phases a lane passes through, in order.

Read this file when you move a card or check the board against reality.

## The columns

| Column | What it means | Who moves the card into it |
| --- | --- | --- |
| **Todo** | Not started. No lane on it. | the planner, when a lane it was counting on turns out to be dead |
| **Planning** | A lane has started: reading the issue, writing its plan, opening the draft pull request. | the planner, at dispatch |
| **Implementing** | Writing the change and getting the checks green. | the lane, once its plan is posted |
| **Reviewing** | The diff is being read and the application driven — both at once — or the lane is acting on what they found. | the lane, before it launches them |
| **Testing** | The reviewer has finished and a tester is still driving the running application in a browser. | the lane, when the reviewer lands first |
| **Blocked** | Waiting on an answer from the human, or on a merge conflict the lane could not resolve. | whoever hits the wall: the lane, or the supervisor when it sends a conflicting pull request back |
| **Ready** | Checks green, diff read, screen driven. Waiting to be merged. | the lane, when it marks the pull request ready |
| **Last done** | The ten most recently merged. | the supervisor, at the merge |
| **Done archive** | Everything merged before those ten. | the supervisor, at the merge |

**Blocked sits before Ready deliberately.** The columns read left to right as a pipeline, so the
last thing before finished work should be the queue the human acts on. A stuck task belongs earlier,
where it reads as work that has not got out yet rather than work waiting to land.

**Blocked is not "a person is doing it by hand".** An issue labelled `hands-off` that no lane is
working belongs in Todo. Blocked means something is waiting on an answer or on an unresolved
conflict; a human working a task themselves is neither.

## Which column is correct

Exactly this, and it is what the drift check compares against:

- Every issue labelled `in-flight` sits in one of **Planning, Implementing, Reviewing, Testing,
  Blocked or Ready**.
- Nothing else sits in those columns.
- Everything else open sits in **Todo**.

## The lane moves its own card, before it enters the phase

Never after finishing it. A phase change is invisible from outside until it is over — a review that
started five minutes ago has written nothing anywhere — so a board built from what has been posted
always shows the step before the one being taken. One line before each step costs nothing and is the
difference between a board that reports and a board that reflects.

The exception is a lane that died mid-phase: it leaves a card claiming a phase nobody is in. The
planner's cycle and the supervisor's round both correct that. The board and the labels are written
separately, so they drift; the board is the copy the human reads, so it is the one that must be
right.

## Moving a card

Look the ids up rather than remembering them. Option ids change whenever the columns are edited, and
a stale id fails silently by writing the wrong phase.

```bash
phase() {                      # phase <issue-number> <column-name>
  local proj="<project-node-id>"
  local q=$(gh api graphql -f query="{node(id:\"$proj\"){... on ProjectV2{
      field(name:\"Status\"){... on ProjectV2SingleSelectField{id options{id name}}}
      items(first:100){nodes{id content{... on Issue{number}}}}}}}")
  local field=$(echo "$q" | jq -r '.data.node.field.id')
  local opt=$(echo "$q" | jq -r --arg n "$2" '.data.node.field.options[]|select(.name==$n)|.id')
  local item=$(echo "$q" | jq -r --argjson n "$1" '.data.node.items.nodes[]|select(.content.number==$n)|.id')
  gh api graphql -f query='mutation($p:ID!,$i:ID!,$f:ID!,$o:String!){
      updateProjectV2ItemFieldValue(input:{projectId:$p,itemId:$i,fieldId:$f,
        value:{singleSelectOptionId:$o}}){projectV2Item{id}}}' \
    -f p="$proj" -f i="$item" -f f="$field" -f o="$opt"
}
```

## The two done columns

The factory outruns the human. A night of lanes buries yesterday's merges under a wall of cards, and
a column of eighty is a column nobody opens — which costs the human the one thing finished work
still owes them: knowing what changed while they were away.

So **Last done holds exactly ten, newest first**, and everything older moves to Done archive.
Nothing is deleted; the archive is kept, it is simply not the thing you read.

Trimming is part of merging, not a chore of its own. After moving a card into Last done, move the
eleventh-newest out. One card in, one card out:

```bash
gh api graphql -f query='{node(id:"<project-node-id>"){... on ProjectV2{items(first:100){nodes{
    id content{... on Issue{number closedAt}}
    fieldValueByName(name:"Status"){... on ProjectV2ItemFieldSingleSelectValue{name}}}}}}}' \
  --jq '[.data.node.items.nodes[]|select(.fieldValueByName.name=="Last done")]
        | sort_by(.content.closedAt) | reverse | .[10:] | .[] | .content.number'
```

Whatever that prints goes to Done archive. It prints nothing until there are eleven, so running it
after every merge is safe.

**Newest at the top, or the column is worthless.** A column has no automatic sort — cards sit in the
order they were added, so a fresh merge lands wherever it happens to land, and a human catching up
would have to check every timestamp to find the newest. The same merge that moves a card into Last
done also lifts it to the top:

```bash
gh api graphql -f query='mutation($p:ID!,$i:ID!){
    updateProjectV2ItemPosition(input:{projectId:$p,itemId:$i}){clientMutationId}}' \
  -f p="<project-node-id>" -f i="<item-id>"
```

Omitting `afterId` means the top; passing it puts the card straight after that one.

## Two traps

- **`gh project item-list --owner <org>` returns nothing when the project belongs to a user** rather
  than an organisation. Check who owns it before blaming the query.
- **Editing the columns with `updateProjectV2Field` replaces the whole option list.** Pass every
  option you want to keep, with its existing id, or the ones you leave out are deleted and their
  cards go blank.
