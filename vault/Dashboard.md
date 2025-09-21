---
ai_summary: 'Topic: PAKE+ Knowledge Dashboard | ~538 words | contains code | includes
  lists'
automated_processing: true
confidence_score: 0.8
connections: []
created: '2024-08-22 11:30:00'
human_notes: Central dashboard for monitoring PAKE+ knowledge system
last_processed: '2025-08-22T22:05:10.618527'
modified: '2024-08-22 11:30:00'
pake_id: dashboard-main-001
source_uri: local://dashboard
status: verified
tags:
- dashboard
- overview
- system
type: dashboard
vector_dimensions: 128
verification_status: verified
---

# PAKE+ Knowledge Dashboard

## System Statistics

```dataview
TABLE WITHOUT ID
  "Metric" as "",
  "Value" as ""
FROM ""
WHERE file.name != "Dashboard"
FLATTEN [
  ["Total Notes", length(file.lists.outlinks)],
  ["High Confidence (≥0.8)", length(filter(file.lists, (x) => x.confidence_score >= 0.8))],
  ["Verified Notes", length(filter(file.lists, (x) => x.verification_status = "verified"))],
  ["Pending Verification", length(filter(file.lists, (x) => x.verification_status = "pending"))]
] AS stat
WHERE stat[1] != null
```

## Confidence Distribution

```dataview
TABLE 
  round(confidence_score, 1) as "Confidence Score",
  length(rows) as "Count"
FROM ""
WHERE confidence_score != null 
AND file.name != "Dashboard"
GROUP BY round(confidence_score, 1)
SORT confidence_score DESC
```

## Unverified Knowledge (Action Required)

```dataview
TABLE 
  file.link as "Note",
  confidence_score as "Confidence",
  dateformat(date(created), "MMM dd") as "Created",
  choice(length(ai_summary) > 50, substr(ai_summary, 0, 47) + "...", ai_summary) as "AI Summary"
FROM ""
WHERE verification_status = "pending"
AND file.name != "Dashboard"
SORT confidence_score ASC
LIMIT 10
```

## Recent High-Confidence Insights

```dataview
TABLE
  file.link as "Insight",
  confidence_score as "Score",
  dateformat(date(modified), "MMM dd HH:mm") as "Modified",
  choice(length(ai_summary) > 60, substr(ai_summary, 0, 57) + "...", ai_summary) as "Summary"
FROM ""
WHERE confidence_score >= 0.8
AND file.name != "Dashboard"
SORT date(modified) DESC
LIMIT 5
```

## Cross-Domain Connections

```dataview
LIST
FROM ""
WHERE length(connections) > 3
AND file.name != "Dashboard"
SORT length(connections) DESC
LIMIT 8
```

## Knowledge by Type

```dataview
TABLE
  type as "Type",
  length(rows) as "Count",
  round(average(rows.confidence_score), 2) as "Avg Confidence"
FROM ""
WHERE type != null
AND file.name != "Dashboard"
GROUP BY type
SORT length(rows) DESC
```

## Recent Activity

```dataview
TABLE
  file.link as "Note",
  type as "Type",
  dateformat(date(modified), "MMM dd HH:mm") as "Last Modified",
  choice(status = "draft", "🟡", choice(status = "verified", "🟢", choice(status = "archived", "🔴", "⚪"))) as "Status"
FROM ""
WHERE file.name != "Dashboard"
SORT date(modified) DESC
LIMIT 12
```

## Tags Cloud

```dataview
TABLE WITHOUT ID
  tags as "Popular Tags",
  length(rows) as "Usage Count"
FROM ""
WHERE tags != null AND tags != []
AND file.name != "Dashboard"
FLATTEN tags
GROUP BY tags
SORT length(rows) DESC
LIMIT 15
```

## Low Confidence Items (Review Needed)

```dataview
TABLE
  file.link as "Note",
  confidence_score as "Score",
  source_uri as "Source",
  dateformat(date(created), "MMM dd") as "Created"
FROM ""
WHERE confidence_score <= 0.4
AND verification_status != "rejected"
AND file.name != "Dashboard"
SORT confidence_score ASC
LIMIT 8
```

## Project Status Overview

```dataview
TABLE
  file.link as "Project",
  choice(contains(string(status), "active"), "🟢 Active", choice(contains(string(status), "completed"), "✅ Done", choice(contains(string(status), "paused"), "⏸️ Paused", "⚪ Other"))) as "Status",
  choice(project_priority = "high", "🔴 High", choice(project_priority = "medium", "🟡 Medium", choice(project_priority = "low", "🟢 Low", "⚪"))) as "Priority"
FROM ""
WHERE type = "project"
AND file.name != "Dashboard"
SORT project_priority ASC, status ASC
```

---

## Quick Actions

### Daily Review Checklist
- [ ] Review unverified knowledge items
- [ ] Update confidence scores for low-scoring items
- [ ] Check cross-references for new connections
- [ ] Process inbox items
- [ ] Update project statuses

### System Health
- **Last Dashboard Update**: `= this.modified`
- **Knowledge Base Size**: `= length(file.lists) - 1` notes
- **Average Confidence**: `= round(average(map(filter(file.lists, (x) => x.confidence_score != null), (x) => x.confidence_score)), 2)`

### Navigation
- [[00-Inbox/]] - New items to process
- [[02-Permanent/]] - Verified knowledge
- [[03-Projects/]] - Active projects
- [[_templates/]] - Note templates

---

*Dashboard auto-updates with new data. Refresh view or reopen to see latest metrics.*