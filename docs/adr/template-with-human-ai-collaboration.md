# [ADR Title - Short description of decision]

**Date**: [YYYY-MM-DD]
**Iteration**: [Number]
**Status**: [Draft | Under Review | Accepted | Implemented]
**Deciders**: [Human name], [Model name]

---

## Quick Start (Delete this section after reading)

**Human**: Dump your thoughts in "Human Context" section → Save file → Tell model "I've dumped thoughts in [filepath], please chunk into ADRs"

**Model**: Read → Create ADRs → Add navigation codes (QST:, COD:, etc.) → Ask questions

**Human**: Fill in **ANS:** blocks → Save → Tell model "I've answered questions in [filepath]"

**Model**: Process answers → Fill "Model's Response" and "Decision Summary" sections

**Both**: Check validation boxes when you agree with Decision Summary

---

## How This Template Works

**The Workflow**:
1. **Human**: Dumps stream-of-consciousness thoughts to a file
2. **Human**: Tells model: *"I've dumped thoughts to [filepath], please chunk into ADRs"*
3. **Model**: Reads, identifies distinct threads, creates ADR for each using this template
4. **Model**: Seeds ADR with extract from dump, asks clarifying questions using navigation codes
5. **Human**: Answers questions in place (just fill in **ANS:** sections)
6. **Model**: Processes answers, fills out response and decision summary
7. **Both**: Iterate (increment iteration number, update sections)

**Navigation Codes** (for grep in large documents):
- `QST:` - Questions
- `ANS:` - Answers
- `COD:` - Code examples
- `API:` - API calls
- `FIL:` - Files to read
- `DOC:` - Documentation

**Key Commands**:
- Find unanswered: `grep -A 2 '^### QST:' | grep 'Status: unanswered'`
- Find all questions: `grep '^### QST:'`
- Find code examples: `grep '^### COD:'`

**Who Does What**:
- **Human**: Write naturally (stream-of-consciousness)
- **Model**: Add structure (navigation codes, formatting)
- **Human**: Answer questions (fill in **ANS:** blocks)
- **Both**: Validate decision summary at end of each iteration

---

## Human Context

**HUMAN: Your stream-of-consciousness dump here**

[Your thoughts, ideas, questions, context - no structure needed, brain dump everything]

**Agency Grant**: [What freedom does the model have?]

[e.g., "You have freedom to implement this however you think best" or "Come up with creative solutions" or "Use subagents if helpful"]

---

## Model's Interpretation

**MODEL: Break down what you understood from the dump**

### What I understand you're asking:

1. **[Task/Question 1]**
   - Context: [Why this matters based on your dump]
   - My interpretation: [What I think you want]

2. **[Task/Question 2]**
   - Context: [Why this matters]
   - My interpretation: [What I think you want]

[Continue as needed...]

**Confirmation**: Did I understand correctly? Please confirm or clarify before I proceed.

---

## Clarifying Questions

### QST: [Question text]
- Status: unanswered
- Why asking: [Context for why this matters]
- What helps: [yes/no | stream-of-consciousness | code example | api call | etc]

**ANS:** (by [name])
[Human fills this in]

---

### QST: [Another question]
- Status: unanswered
- Why asking: [Context]
- What helps: [Format needed]

**ANS:** (by [name])
[Human fills this in]

---

## Supporting Materials

**HUMAN: Add materials here using navigation codes below. MODEL: Use grep to find them.**

### COD: [example-name]
- Language: [python|javascript|bash|etc]
- Description: [What this code demonstrates]

```python
[Your code here]
```

---

### API: [call-name]
- Description: [What this API call shows]

**Request:**
```http
POST /api/endpoint
Content-Type: application/json

{"param": "value"}
```

**Response:**
```json
{"result": "data"}
```

---

### FIL: [files-to-read]
- Priority: [high|medium|optional]
- Why relevant: [Context]

Files:
- `/path/to/file1.py` - [What to look for]
- `/path/to/file2.md` - [Why this matters]

---

### DOC: [documentation-name]
- Source: [URL or file path]
- Why relevant: [Context]

[Paste relevant documentation or excerpt]

---

## Model's Response

**MODEL: Document your thinking, decisions, and next steps**

### Cognitive Approach
[How you chose to engage with this information]

- [e.g., "I chose to use a subagent because..."]
- [e.g., "I read code examples first to understand pattern..."]
- [e.g., "I used grep to find all QST: tags, then..."]

### Decisions Made
[When human granted you agency, document your choices]

#### Decision 1: [Title]
- **Why**: [Your reasoning]
- **Alternatives considered**: [What else you thought about]
- **Chosen approach**: [What you decided]

[Continue as needed...]

### Implementation Notes
[Technical details, code structure, architectural points]

### Action Items
[Concrete next steps you will take]

- [ ] Action item 1
- [ ] Action item 2

---

## Decision Summary (ADR Format)

**After each iteration, MODEL synthesizes conversation into formal decision record. BOTH validate.**

### Context and Problem Statement
[Synthesized from conversation above: What problem are we solving? Why does it matter?]

### Decision Drivers
[Key factors that influenced the decision]

- [Driver 1]
- [Driver 2]

### Options Considered

#### Option 1: [Name]
- **Pros**: [Why this could work]
- **Cons**: [Why this might not work]

#### Option 2: [Name]
- **Pros**: [Why this could work]
- **Cons**: [Why this might not work]

[Continue as needed...]

### Decision Outcome

**Chosen**: [Option name]

**Rationale**: [Why we chose this - synthesized from Q&A and discussion above]

### Consequences

**Positive**:
- [Good outcome 1]
- [Good outcome 2]

**Negative**:
- [Tradeoff 1]
- [Tradeoff 2]

### Validation

**Human validation**: [ ] Approved by [name] on [date]
**Model validation**: [ ] Confirmed by [model] on [date]

**Notes**: [Any final thoughts or caveats]

---

## Iteration History

### Iteration 1 ([Date])
- **Human**: [Summary of what human provided]
- **Model**: [Summary of what model did]
- **Outcome**: [What changed, what was decided]
- **Validation**: [Approved by both? Any concerns?]

### Iteration 2 ([Date])
- **Human**: [Updates or new information]
- **Model**: [Model's response]
- **Outcome**: [What changed]
- **Validation**: [Approved by both?]

[Continue as needed...]

---

## Related Decisions

- **Related ADRs**: [Links to other ADRs]
- **Supersedes**: [If this replaces another ADR]
- **Superseded by**: [If this is replaced by another ADR]
- **Related Docs**: [Links to SHARED-WORKING-PRACTICES.md, code files, etc.]

---

## Quick Reference: Markdown Patterns

**For future AI instances - exact patterns to follow**:

```markdown
### QST: [question]
- Status: unanswered|answered
- Why asking: [context]
- What helps: [format]

**ANS:** (by [name])
[answer]

---

### COD: [name]
- Language: [lang]
- Description: [desc]

\```[lang]
[code]
\```

---

### API: [name]
- Description: [desc]

**Request:**
\```http
[request]
\```

**Response:**
\```json
[response]
\```
```

**Hierarchy Rules**:
- `##` = Major sections
- `###` = Individual items (QST, COD, API, FIL, DOC)
- `**BOLD:**` = Sub-items within an item (ANS, Request, Response)
- `---` = Separator between items at same level
