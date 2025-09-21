# 🔍 PAKE Daily Review Queue

*Last Updated: {{date:YYYY-MM-DD HH:mm}}*

## 📊 Quick Stats

```dataview
TABLE WITHOUT ID
  "**" + key + "**" as Metric,
  value as Count
FROM "vault"
WHERE file.name != this.file.name
FLATTEN {
  "Total Notes": length(filter(file.etags, (t) => t = "#pake")),
  "Quarantined": length(filter(file.etags, (t) => t = "#status/quarantined")),
  "Pending Review": length(filter(file.etags, (t) => t = "#verification/pending")),
  "Low Confidence": length(filter(file.etags, (t) => contains(t, "confidence/low")))
} as stats
FLATTEN object(stats) as pair
FLATTEN pair.key as key, pair.value as value
```

---

## 🚨 Priority Review Queue

### Items Flagged for Immediate Review

```dataview
TABLE 
  file.frontmatter.pake_id as "PAKE ID",
  file.frontmatter.confidence_score as "Confidence",
  file.frontmatter.type as "Type",
  file.frontmatter.created as "Created",
  file.frontmatter.verification_status as "Status"
FROM "vault"
WHERE (
  file.frontmatter.status = "Quarantined" OR
  file.frontmatter.confidence_score < 0.75 OR
  file.frontmatter.verification_status = "pending"
)
AND file.frontmatter.pake_id
SORT file.frontmatter.confidence_score ASC, file.ctime DESC
LIMIT 20
```

---

## 📝 Notes Requiring Review by Category

### Low Confidence SourceNotes (< 0.5)
*These notes may contain unreliable information that needs verification*

```dataview
TABLE 
  file.frontmatter.source_uri as "Source",
  file.frontmatter.confidence_score as "Confidence",
  file.frontmatter.tags as "Tags",
  file.frontmatter.created as "Created"
FROM "vault"
WHERE file.frontmatter.type = "SourceNote" 
  AND file.frontmatter.confidence_score < 0.5
  AND file.frontmatter.verification_status != "rejected"
SORT file.frontmatter.confidence_score ASC
LIMIT 15
```

### Unverified InsightNotes
*Synthesized insights waiting for human validation*

```dataview
TABLE 
  split(file.frontmatter.source_uri, ":")[1] as "Source Notes",
  file.frontmatter.confidence_score as "Confidence", 
  file.frontmatter.tags as "Tags",
  file.frontmatter.created as "Created"
FROM "vault"
WHERE file.frontmatter.type = "InsightNote"
  AND file.frontmatter.verification_status = "pending"
SORT file.frontmatter.created DESC
LIMIT 10
```

### Processing Errors & Exceptions
*Notes that encountered issues during ingestion or synthesis*

```dataview
TABLE 
  file.frontmatter.pake_id as "PAKE ID",
  file.frontmatter.type as "Type",
  file.frontmatter.human_notes as "Error Details",
  file.frontmatter.modified as "Last Modified"
FROM "vault"
WHERE contains(file.frontmatter.human_notes, "ERROR") OR
  contains(file.frontmatter.human_notes, "FAILED") OR
  file.frontmatter.status = "error"
SORT file.frontmatter.modified DESC
LIMIT 10
```

---

## 📈 Quality Metrics Dashboard

### Confidence Score Distribution

```dataview
TABLE WITHOUT ID
  confidence_range as "Confidence Range",
  count as "Count",
  round((count / total) * 100, 1) + "%" as "Percentage"
FROM "vault"
WHERE file.frontmatter.confidence_score
FLATTEN {
  excellent: length(filter(file.frontmatter, (f) => f.confidence_score >= 0.9)),
  high: length(filter(file.frontmatter, (f) => f.confidence_score >= 0.7 AND f.confidence_score < 0.9)),
  medium: length(filter(file.frontmatter, (f) => f.confidence_score >= 0.5 AND f.confidence_score < 0.7)),
  low: length(filter(file.frontmatter, (f) => f.confidence_score >= 0.3 AND f.confidence_score < 0.5)),
  poor: length(filter(file.frontmatter, (f) => f.confidence_score < 0.3))
} as ranges
FLATTEN length(file.frontmatter) as total
FLATTEN ranges.excellent as excellent, ranges.high as high, ranges.medium as medium, ranges.low as low, ranges.poor as poor
FLATTEN [
  ["Excellent (0.9-1.0)", excellent],
  ["High (0.7-0.9)", high], 
  ["Medium (0.5-0.7)", medium],
  ["Low (0.3-0.5)", low],
  ["Poor (0.0-0.3)", poor]
] as pairs
FLATTEN pairs[0] as confidence_range, pairs[1] as count
WHERE count > 0
SORT count DESC
```

### Verification Status Overview

```dataview
TABLE WITHOUT ID
  verification_status as "Verification Status",
  count as "Count"
FROM "vault"
WHERE file.frontmatter.verification_status
GROUP BY file.frontmatter.verification_status as verification_status
FLATTEN length(rows) as count
SORT count DESC
```

---

## 🔄 Recent Activity Summary

### Recently Created Notes (Last 7 Days)

```dataview
TABLE 
  file.frontmatter.type as "Type",
  file.frontmatter.confidence_score as "Confidence",
  file.frontmatter.tags as "Tags",
  file.frontmatter.created as "Created"
FROM "vault"
WHERE file.frontmatter.created >= date(today) - dur(7 days)
  AND file.frontmatter.pake_id
SORT file.frontmatter.created DESC
LIMIT 15
```

### Recently Modified Notes (Last 24 Hours)

```dataview
TABLE 
  file.frontmatter.type as "Type",
  file.frontmatter.verification_status as "Status",
  file.frontmatter.modified as "Modified"
FROM "vault"
WHERE file.frontmatter.modified >= date(today) - dur(1 days)
  AND file.frontmatter.pake_id
SORT file.frontmatter.modified DESC
LIMIT 10
```

---

## ⚡ Quick Actions

### Review Workflow Checklist

For each note in the priority queue:

- [ ] **Read the full content** - Does it make sense and provide value?
- [ ] **Verify the source** - Is the source_uri accurate and authoritative?
- [ ] **Check confidence score** - Does it match your assessment?
- [ ] **Review tags** - Are they specific and discoverable?
- [ ] **Validate connections** - Are related notes properly linked?
- [ ] **Update status**: 
  - ✅ `verified` - Accurate and valuable
  - ❌ `rejected` - Inaccurate or not valuable  
  - 🔄 `refined` - Edited and improved
- [ ] **Add human notes** - Document any changes or observations

### Batch Actions

```markdown
<!-- Quick templates for common review actions -->

## Approve Note Template
**Action**: Update frontmatter
```yaml
verification_status: verified
status: refined
human_notes: "Reviewed {{date:YYYY-MM-DD}} - Content verified and valuable"
```

## Quarantine Note Template  
**Action**: Update frontmatter
```yaml
verification_status: rejected
status: quarantined
human_notes: "Quarantined {{date:YYYY-MM-DD}} - [Reason for quarantine]"
```

## Request Revision Template
**Action**: Update frontmatter
```yaml  
verification_status: pending
human_notes: "Needs revision: [Specific feedback] - {{date:YYYY-MM-DD}}"
```
```

---

## 🎯 Focus Areas for Today

### Suggested Review Priorities

1. **High Impact, Low Confidence**: Notes with important topics but low confidence scores
2. **Recent Synthesis**: New InsightNotes that combine multiple sources
3. **Error Resolution**: Any notes flagged with processing errors
4. **Batch Processing**: Groups of related notes from the same ingestion session

### Learning Opportunities

Look for patterns in:
- **Common confidence issues** - What causes low scores?
- **Source quality patterns** - Which sources consistently provide value?
- **Tagging effectiveness** - Are notes discoverable with current tags?
- **Synthesis quality** - Do InsightNotes provide genuine new value?

---

## 📚 Review History & Learning

### Improvement Tracking

*Document lessons learned from reviews to improve future AI agent performance*

#### Common Issues Identified:
- [ ] Source extraction problems
- [ ] Inconsistent confidence scoring  
- [ ] Poor tag selection
- [ ] Missing connections between related notes
- [ ] Synthesis that doesn't add value beyond sources

#### Agent Instruction Updates Needed:
- [ ] Refine confidence scoring criteria
- [ ] Improve source quality assessment
- [ ] Enhance tagging strategies
- [ ] Strengthen synthesis requirements

---

*💡 **Tip**: Use the search and filter capabilities in your PKM tool to create custom views of this data. The goal is efficient human oversight that continuously improves the AI agents' performance.*