# Working Protocol

## Accepted Collaboration Contract

- The agent may explore, investigate, reason, and run bounded experiments
  without requesting permission.
- Source or durable project mutation begins only after product design, HLD, and
  an implementation-ready plan are complete and Sir explicitly says to start.
  Task-packet maintenance is exempt.
- Each conversation round carries one bounded decision, or one small coherent
  batch whose cognitive load is comparable to one decision.
- Every round reports the previous result before advancing to the next question.
- Sir's statements are proposals and evidence, not automatic authority; the
  agent must independently evaluate them and may disagree with reasons.
- The agent owns proposing coherent solutions. Sir reviews and steers those
  proposals; the agent must not outsource design work as a series of tiny
  questions.
- Decisions, evidence, open questions, and plan revisions remain synchronized
  in this packet.
- The agent stops only for meaningful review, a material decision, missing
  information that changes the design, or a mutation gate.

## Current Mode

This chronological protocol is retained as accepted collaboration history.
Current state, authority and gates now live in `active/00-state.md`; the task
dashboard is `packet.md`. No source implementation is currently authorized.

## Repository Boundary

This packet lives in `ext-reg` only as the active cross-repository control
surface for the current task. It does not transfer setup ownership to the
Registry. Expected implementation owners are primarily `client-web` and
`core-py`; stable cross-unit product or technical truth may later be promoted to
the shared InKCre docs through its normal ownership workflow.
