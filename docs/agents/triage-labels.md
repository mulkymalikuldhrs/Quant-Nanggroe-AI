# Triage Labels

The skills speak in terms of five canonical triage roles. This file maps those roles to the actual label strings used in this repo's issue tracker.

| Label in mattpocock/skills | Label in our tracker | Meaning                                  |
| -------------------------- | -------------------- | ---------------------------------------- |
| `needs-triage`             | `needs-triage`       | Maintainer needs to evaluate this issue  |
| `needs-info`               | `needs-info`         | Waiting on reporter for more information |
| `ready-for-agent`          | `ready-for-agent`    | Fully specified, ready for an AFK agent  |
| `ready-for-human`          | `ready-for-human`    | Requires human implementation            |
| `wontfix`                  | `wontfix`            | Will not be actioned                     |

When a skill mentions a role (e.g. "apply the AFK-ready triage label"), use the corresponding label string from this table.

Edit the right-hand column to match whatever vocabulary you actually use.

---

## Cross-tracker mapping

Because this repo uses GitHub + GitLab + Codeberg (per `issue-tracker.md`), the canonical labels need the same spelling everywhere. If you ever need a different label on one tracker, do it in `docs/agents/issue-tracker.md` and re-push the labels to every remote.

| Label | GitHub | GitLab | Codeberg | Local |
|-------|--------|--------|----------|-------|
| `needs-triage` | ✓ | ✓ | ✓ | `state: open` + `labels: [needs-triage]` |
| `needs-info` | ✓ | ✓ | ✓ | `labels: [needs-info]` |
| `ready-for-agent` | ✓ | ✓ | ✓ | `labels: [ready-for-agent]` |
| `ready-for-human` | ✓ | ✓ | ✓ | `labels: [ready-for-human]` |
| `wontfix` | ✓ | ✓ | ✓ | `state: closed` + `labels: [wontfix]` |

For local markdown, "wontfix" means the file ends with a `## Resolution` section explaining why and a `state: closed` line in the front-matter.
