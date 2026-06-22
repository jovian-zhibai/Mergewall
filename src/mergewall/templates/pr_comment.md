## 🛡️ Mergewall Governance Report

**Decision: {{ decision }}** | Risk Score: {{ score }}/100

{% if findings %}
### Findings

{% for finding in findings %}
#### {{ finding.level_emoji }} [{{ finding.level }}] {{ finding.category }}
- **File:** `{{ finding.file }}`{% if finding.line %} (line {{ finding.line }}){% endif %}
- **Issue:** {{ finding.description }}
{% if finding.suggestion %}
- **Fix:** {{ finding.suggestion }}
{% endif %}

{% endfor %}
{% endif %}

### What to do
{% if decision == "BLOCK" %}
🔴 Fix the issues above and push again. Mergewall will re-evaluate automatically.
{% elif decision == "REQUIRE_APPROVAL" %}
🟡 Request approval from **{{ required_approvers }}** to proceed.
{% elif decision == "WARN" %}
⚠️ Review the findings above and use your judgment before merging.
{% else %}
✅ No blocking issues — safe to merge.
{% endif %}

---
*Powered by [Mergewall](https://github.com/jovian-zhibai/Mergewall)*
