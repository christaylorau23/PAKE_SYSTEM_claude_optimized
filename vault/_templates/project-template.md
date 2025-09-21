---
pake_id: "{{UUID}}"
created: "{{date:YYYY-MM-DD HH:mm:ss}}"
modified: "{{date:YYYY-MM-DD HH:mm:ss}}"
type: "project"
status: "{{value:planning|active|paused|completed|archived}}"
confidence_score: 0.8
verification_status: "verified"
source_uri: "local://project"
tags: ["project"]
connections: []
ai_summary: ""
human_notes: ""
project_priority: "{{value:low|medium|high|critical}}"
estimated_completion: ""
actual_completion: ""
---

# {{title}}

## Project Overview

## Goals & Objectives
- [ ] 
- [ ] 
- [ ] 

## Key Milestones
- [ ] **Milestone 1**: 
- [ ] **Milestone 2**: 
- [ ] **Milestone 3**: 

## Resources Required

## Success Metrics

## Risks & Mitigation

## Progress Log

## Related Notes
```dataview
LIST
FROM ""
WHERE contains(connections, this.pake_id)
SORT file.mtime DESC
```