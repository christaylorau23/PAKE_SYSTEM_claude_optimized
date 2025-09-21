---
ai_summary: 'Topic: PAKE+ Analytics Dashboard | ~700 words | contains code | includes
  lists'
automated_processing: true
confidence_score: 0.85
connections:
- dashboard-main-001
created: '2024-08-22 11:35:00'
human_notes: Deep analytics and trend analysis for the knowledge system
last_processed: '2025-08-22T22:05:10.658661'
modified: '2024-08-22 11:35:00'
pake_id: dashboard-analytics-001
source_uri: local://analytics
status: verified
tags:
- analytics
- dashboard
- metrics
- system
type: dashboard
vector_dimensions: 128
verification_status: verified
---

# PAKE+ Analytics Dashboard

## Knowledge Growth Trends

```dataview
TABLE WITHOUT ID
  dateformat(date(created), "yyyy-MM") as "Month",
  length(rows) as "Notes Created"
FROM ""
WHERE created != null
AND file.name != "Analytics-Dashboard"
GROUP BY dateformat(date(created), "yyyy-MM")
SORT dateformat(date(created), "yyyy-MM") DESC
LIMIT 12
```

## Confidence Score Evolution

```dataview
TABLE WITHOUT ID
  choice(confidence_score >= 0.9, "Excellent (0.9-1.0)", 
    choice(confidence_score >= 0.8, "High (0.8-0.9)", 
      choice(confidence_score >= 0.6, "Good (0.6-0.8)", 
        choice(confidence_score >= 0.4, "Fair (0.4-0.6)", "Poor (0-0.4)")))) as "Confidence Range",
  length(rows) as "Count",
  round((length(rows) / 1.0), 1) + "%" as "Percentage"
FROM ""
WHERE confidence_score != null
AND file.name != "Analytics-Dashboard"
GROUP BY choice(confidence_score >= 0.9, "Excellent (0.9-1.0)", 
    choice(confidence_score >= 0.8, "High (0.8-0.9)", 
      choice(confidence_score >= 0.6, "Good (0.6-0.8)", 
        choice(confidence_score >= 0.4, "Fair (0.4-0.6)", "Poor (0-0.4)"))))
SORT length(rows) DESC
```

## Source URI Analysis

```dataview
TABLE
  choice(contains(source_uri, "local"), "📝 Local", 
    choice(contains(source_uri, "http"), "🌐 Web", 
      choice(contains(source_uri, "email"), "📧 Email", 
        choice(contains(source_uri, "rss"), "📰 RSS", "❓ Other")))) as "Source Type",
  length(rows) as "Count",
  round(average(rows.confidence_score), 2) as "Avg Confidence"
FROM ""
WHERE source_uri != null AND source_uri != ""
AND file.name != "Analytics-Dashboard"
GROUP BY choice(contains(source_uri, "local"), "📝 Local", 
    choice(contains(source_uri, "http"), "🌐 Web", 
      choice(contains(source_uri, "email"), "📧 Email", 
        choice(contains(source_uri, "rss"), "📰 RSS", "❓ Other"))))
SORT length(rows) DESC
```

## Connection Network Analysis

```dataview
TABLE
  file.link as "Node",
  length(connections) as "Connection Count",
  confidence_score as "Confidence",
  type as "Type"
FROM ""
WHERE length(connections) > 0
AND file.name != "Analytics-Dashboard"
SORT length(connections) DESC
LIMIT 15
```

## Processing Pipeline Performance

```dataview
TABLE WITHOUT ID
  verification_status as "Verification Status",
  length(rows) as "Count",
  round((length(rows) / 1.0), 1) + "%" as "Percentage",
  round(average(rows.confidence_score), 2) as "Avg Confidence"
FROM ""
WHERE verification_status != null
AND file.name != "Analytics-Dashboard"
GROUP BY verification_status
SORT length(rows) DESC
```

## Content Quality Metrics

```dataview
TABLE
  file.link as "Note",
  length(file.size) as "Content Length",
  confidence_score as "Quality Score",
  length(connections) as "Connections",
  dateformat(date(modified), "MMM dd") as "Last Updated"
FROM ""
WHERE file.name != "Analytics-Dashboard"
AND length(file.size) > 1000
SORT confidence_score DESC, length(connections) DESC
LIMIT 10
```

## Tag Usage Statistics

```dataview
TABLE WITHOUT ID
  tags as "Tag",
  length(rows) as "Usage Count",
  round(average(rows.confidence_score), 2) as "Avg Confidence",
  min(rows.created) as "First Used"
FROM ""
WHERE tags != null AND tags != []
AND file.name != "Analytics-Dashboard"
FLATTEN tags
GROUP BY tags
SORT length(rows) DESC
LIMIT 20
```

## Weekly Activity Pattern

```dataview
TABLE WITHOUT ID
  dateformat(date(created), "EEEE") as "Day of Week",
  length(rows) as "Notes Created"
FROM ""
WHERE created != null
AND file.name != "Analytics-Dashboard"
AND date(created) >= date(today) - dur(30 days)
GROUP BY dateformat(date(created), "EEEE")
SORT length(rows) DESC
```

## Knowledge Decay Analysis (Outdated Content)

```dataview
TABLE
  file.link as "Note",
  dateformat(date(modified), "MMM dd, yyyy") as "Last Modified",
  round((date(today) - date(modified)).days, 0) as "Days Stale",
  confidence_score as "Confidence",
  verification_status as "Status"
FROM ""
WHERE date(modified) < date(today) - dur(90 days)
AND file.name != "Analytics-Dashboard"
AND verification_status != "archived"
SORT date(modified) ASC
LIMIT 15
```

## Cross-Reference Health

```dataview
TABLE
  file.link as "Note",
  length(connections) as "Declared Connections",
  length(file.outlinks) as "Actual Links",
  choice(length(connections) = length(file.outlinks), "✅ Sync", "⚠️ Mismatch") as "Status"
FROM ""
WHERE (length(connections) > 0 OR length(file.outlinks) > 0)
AND file.name != "Analytics-Dashboard"
SORT abs(length(connections) - length(file.outlinks)) DESC
LIMIT 10
```

---

## System Performance Indicators

### Knowledge Velocity
- **Notes This Week**: `= length(filter(file.lists, (x) => date(x.created) >= date(today) - dur(7 days))) - 1`
- **Average Daily Notes**: `= round((length(file.lists) - 1) / 30, 1)` (last 30 days estimate)

### Quality Metrics  
- **High Confidence Ratio**: `= round((length(filter(file.lists, (x) => x.confidence_score >= 0.8)) / length(file.lists)) * 100, 1)`%
- **Verification Rate**: `= round((length(filter(file.lists, (x) => x.verification_status = "verified")) / length(file.lists)) * 100, 1)`%

### Network Health
- **Average Connections**: `= round(average(map(file.lists, (x) => length(x.connections))), 1)`
- **Well-Connected Notes**: `= length(filter(file.lists, (x) => length(x.connections) >= 3))`

### Data Sources
- **Primary Source Types**: Local, Web, Email, RSS, Manual
- **Most Reliable Source**: `= "Local (Manual Entry)"`

---

## Recommended Actions

```dataview
TABLE WITHOUT ID
  "Priority" as "",
  "Action Item" as "",
  "Target" as ""
WHERE file.name = "Analytics-Dashboard"
FLATTEN [
  ["🔴 High", "Review stale content (>90 days old)", "15 notes"],
  ["🟡 Medium", "Improve low-confidence items", "Items <0.4"],
  ["🟢 Low", "Add cross-references", "Isolated notes"],
  ["🔵 Info", "Archive completed projects", "Completed items"]
] AS priority_action
WHERE priority_action[0] != null
```

---

*Analytics refresh automatically. For real-time metrics, reopen this dashboard.*