---
pake_id: "{{UUID}}"
created: "{{date:YYYY-MM-DD HH:mm:ss}}"
modified: "{{date:YYYY-MM-DD HH:mm:ss}}"
type: "daily"
status: "active"
confidence_score: 1.0
verification_status: "verified"
source_uri: "local://daily"
tags: ["daily"]
connections: []
ai_summary: ""
human_notes: ""
---

# {{date:YYYY-MM-DD}} - Daily Note

## 🎯 Today's Focus
- [ ]
- [ ]
- [ ]

## 📝 Meeting Notes

## 💡 Key Insights

## 🔗 Knowledge Captured
```dataview
LIST
FROM ""
WHERE created = "{{date:YYYY-MM-DD}}"
AND type != "daily"
SORT confidence_score DESC
```

## ✅ Completed Tasks
- [x]

## 🔄 For Tomorrow
- [ ]
- [ ]

## 📊 Confidence Score Distribution
```dataview
TABLE confidence_score as "Score", length(rows) as "Count"
FROM ""
WHERE created = "{{date:YYYY-MM-DD}}"
GROUP BY confidence_score
SORT confidence_score DESC
```
