# [Short title of ADR or feedback document]

**Date**: [YYYY-MM-DD]
**Iteration**: [Number - increment each time this document is updated]
**Status**: [Draft | Under Review | Accepted | Implemented]
**Type**: [ADR | Feedback | Collaboration Pattern | Meta-Discussion]
**Deciders**: [Human name], [Model name and version]

---

## THE WORKFLOW: How This Template Works

**The Full Pattern**:

### Initial Stream-of-Consciousness Dump
1. **Human**: Writes a big stream-of-consciousness dump (all topics, unstructured)
2. **Human**: Tells model: *"I've dumped thoughts to [filepath], please chunk into ADRs"*

### Model Chunks Into ADRs
3. **Model**: Reads the dump
4. **Model**: Identifies distinct threads/topics
5. **Model**: Creates separate ADR for each thread (using this template)
6. **Model**: Seeds each ADR with relevant extract from human's dump
7. **Model**: Asks clarifying question or for supporting materials using precise XML tags (see below)

### Iterative Refinement Per ADR
8. **Human**: Adds supporting materials to relevant ADRs using XML tags
9. **Model**: Processes materials, fills out response sections
10. **Both**: Iterate on each ADR separately (increment iteration number)

**Why this works**:
- ✅ Human dumps everything at once (neurodivergent-friendly, context-rich)
- ✅ Model organizes into digestible threads (architectural clarity)
- ✅ Each ADR becomes focused discussion of one topic
- ✅ Stream-of-consciousness preserved in version control (not lost in conversation)
- ✅ Model has agency to engage strategically (may use subagents)
- ✅ Shared artifacts persist across context windows

**KEY PRINCIPLE**: **Commit all discussion immediately to an ADR or AIDR!!**

---

## INSTRUCTIONS FOR HUMAN COLLABORATOR

**How to fill out this template**:

1. **Fill out "Human Prompt" section** below with your stream-of-consciousness thoughts
2. **Grant agency explicitly** - tell the model what freedom they have
3. **Add supporting materials** in the designated sections (code, files, etc.)
4. **Save this document** and tell the model: "I've added feedback to [filepath], please read and respond"
5. **The model will fill out the "Model's Response" section** and may ask you questions

**Key patterns**:
- Use `--------------------` dividers to separate sections (model can choose when to read)
- Use XML tags like `<code_example>` on their own lines for easy parsing/grepping
- Put iteration number in header so we track evolution
- Don't paste huge content in conversation - put it here instead

---

## Human Prompt: High-Level Context

**INSTRUCTIONS FOR HUMAN**: Write your stream-of-consciousness thoughts here. No need for structure - brain dump ideas, connections, questions, intuitions. This is where context-rich, neurodivergent working style shines.

[Your thoughts here]

**Agency Grant**:
**INSTRUCTIONS FOR HUMAN**: Explicitly state what freedom the model has. Examples:
- "You have freedom to implement this however you think best"
- "Come up with your own creative solutions"
- "Use subagents if helpful"
- "Your call on the technical approach"

[Your agency grant here]

---

## Model's Interpretation: Breaking Down the Prompt

**INSTRUCTIONS FOR MODEL**: Parse the human's stream-of-consciousness prompt into structured questions/tasks you understand. This helps confirm alignment.

### What I understand you're asking:

1. **[Task/Question 1]**
   - Context: [Why this matters based on prompt]
   - My interpretation: [What I think you want]

2. **[Task/Question 2]**
   - Context: [Why this matters]
   - My interpretation: [What I think you want]

[Continue as needed...]

### Confirmation Check:
**INSTRUCTIONS FOR MODEL**: Ask the human to validate your interpretation before proceeding.

Did I understand correctly? Please confirm or clarify before I proceed.

--------------------
## Supporting Materials: Code Examples
--------------------

**INSTRUCTIONS FOR HUMAN**: Add supporting materials here using precise XML tags (start tags on their own line for easy grepping). The model can choose when to read these deeply.

**XML Tag Vocabulary** (use these specific tags):

### For Supporting Materials:

<code-example name="descriptive-name">
Description: [What this code demonstrates]
Language: [python|javascript|bash|etc]

```python
[Your code here]
```
</code-example>

<api-call name="descriptive-name">
Description: [What this API call shows]

**Request**:
```http
POST /api/endpoint
Content-Type: application/json

{"param": "value"}
```

**Response**:
```json
{"result": "data"}
```
</api-call>

<documentation source="url-or-file">
Description: [What this documents]

[Paste relevant documentation or excerpt]
</documentation>

<url source="https://example.com">
Description: [Why this URL is relevant]
Context: [What to look for at this URL]
</url>

### For Questions & Answers:

<model-question id="unique-id">
  <question>
    [Model's clarifying question]
  </question>

  <answer status="unanswered|answered" human="name">
    [Human's answer - can reference other tags like <files_to_read> or <code-example>]
  </answer>
</model-question>

**INSTRUCTIONS FOR MODEL**: Use `grep` to navigate:
- `grep '<code-example'` - Find all code examples
- `grep '<api-call'` - Find all API call specs
- `grep '<documentation'` - Find all documentation references
- `grep '<url'` - Find all URL references
- `grep '<answer status="unanswered"'` - Find unanswered questions
- `grep '<answer status="answered"'` - Find answered questions

--------------------
## Supporting Materials: Files to Reference
--------------------

**INSTRUCTIONS FOR HUMAN**: List files the model should read. Provide context for why each file matters.

<files_to_read priority="high">
- `/path/to/file1.py` - [Why this file is relevant, what to look for]
- `/path/to/file2.md` - [What to look for]
</files_to_read>

<files_to_read priority="optional">
- `/path/to/optional.json` - [Context for why this might be useful]
</files_to_read>

**INSTRUCTIONS FOR MODEL**: Read high-priority files first. Use optional files for additional context if needed.

--------------------
## Supporting Materials: Related Discussions
--------------------

[Links to other ADRs, conversations, or documents that provide context]

- Related ADR: [ADR-XXXX](./XXXX-filename.md)
- Previous conversation: [Link or description]
- External resource: [URL]

---

## Model's Response

**INSTRUCTIONS FOR MODEL**: This is YOUR section. Document your thinking, choices, and actions here.

### Cognitive Approach
**INSTRUCTIONS FOR MODEL**: Explain how you engaged with this information.

- Example: "I chose to use a subagent to process the 261KB file because..."
- Example: "I read the code examples first to understand the pattern, then..."
- Example: "I used grep to find all `<code_example>` tags, then read selectively"

[Your approach here]

### Decisions Made
**INSTRUCTIONS FOR MODEL**: When the human granted you agency, document your choices explicitly.

#### Decision 1: [Title]
**Why**: [Your reasoning]
**Alternatives considered**: [What else you thought about]
**Chosen approach**: [What you decided to do]

[Continue as needed...]

### Action Items
**INSTRUCTIONS FOR MODEL**: List concrete next steps you will take or are requesting.

- [ ] Action item 1
- [ ] Action item 2

### Reflections
**INSTRUCTIONS FOR MODEL**: Optional - your thoughts on the collaboration process itself.

[Your reflections here]

---

## Clarifying Questions (Model ↔ Human)

**INSTRUCTIONS FOR MODEL**: Ask clarifying questions using `<model-question>` tags. Each question gets a unique ID for easy navigation.

**INSTRUCTIONS FOR HUMAN**: Answer by filling in the `<answer>` tag. You can reference files, add materials, or give stream-of-consciousness responses.

**Navigation for Model**:
- Find unanswered questions: `grep '<answer status="unanswered"'`
- Find answered questions: `grep '<answer status="answered"'`
- Find specific question: `grep '<model-question id="q1"'`

### Questions:

<model-question id="q1">
  <question>
    [Your question here]

    **Why I'm asking**: [Context]
    **What would help**:
    - [ ] Simple yes/no
    - [ ] Stream-of-consciousness thoughts
    - [ ] Reference to `<files_to_read>`
    - [ ] New `<code-example>` or `<api-call>` in supporting materials
    - [ ] Other: [specify]
  </question>

  <answer status="unanswered" human="">
    [HUMAN: Fill this in when you answer. Change status to "answered" and add your name to human attribute]

    [You can reference: see <files_to_read priority="high"> above, or I'll add <code-example name="..."> below]
  </answer>
</model-question>

<model-question id="q2">
  <question>
    [Your question here]
  </question>

  <answer status="unanswered" human="">
    [HUMAN: Your answer here]
  </answer>
</model-question>

**INSTRUCTIONS FOR HUMAN**: After answering questions:
1. Change `status="unanswered"` to `status="answered"`
2. Add your name to `human` attribute: `human="Jérémie"`
3. Increment iteration number in header
4. Tell model: "I've answered questions in [filepath]"

---

## Iteration History

[Track how this document evolved through conversation]

### Iteration 1 ([Date])
**Human**: [Summary of user input]
**Claude**: [Summary of Claude's response]
**Outcome**: [What changed]

### Iteration 2 ([Date])
[Continue as needed...]

---

## Implementation Notes

[Technical details, code snippets, or architectural decisions that emerged from the collaboration]

---

## Success Criteria

[How we'll know this ADR/decision was successful]

- [ ] Criterion 1
- [ ] Criterion 2

---

## Meta: What Made This Collaboration Work

[Optional reflection on the collaboration process itself - what patterns worked well]

**Human working style that helped**:
- [Example: Stream-of-consciousness context provided rich understanding]

**AI capabilities that were useful**:
- [Example: Subagent processing for large files]

**Patterns to repeat**:
- [Example: Divider-separated examples for agency in engagement]

---

## Related Documents

- **Related ADRs**: [Links]
- **Related Feedback**: [Links]
- **Related Code**: [File paths]
