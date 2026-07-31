#!/usr/bin/env python3
"""
SKILL AUTO-GEN — MetaClaw-inspired pattern extraction
Conversations → patterns → reusable skills. No GPU needed.
"""

import os
import re
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("SkillAutogen")

SKILLS_DIR = Path.home() / ".hermes" / "skills"
HISTORY_DB = Path.home() / ".hermes" / "state.db"

@dataclass
class Pattern:
    name: str
    description: str
    trigger_phrases: List[str]
    steps: List[str]
    frequency: int = 0
    last_seen: str = ""
    success_count: int = 0

@dataclass
class ConversationSession:
    session_id: str
    title: str
    messages: List[Dict[str, str]]
    tools_used: List[str]
    outcome: str
    timestamp: str

class PatternExtractor:
    """Extract reusable patterns from conversation history"""

    TRIGGER_PATTERNS = [
        # Tool usage patterns
        (r"search_files.*?pattern=['\"](.+?)['\"]", "file_search: {0}"),
        (r"terminal.*?command=['\"](.+?)['\"]", "terminal_cmd: {0}"),
        (r"read_file.*?path=['\"](.+?)['\"]", "read_file: {0}"),
        (r"write_file.*?path=['\"](.+?)['\"]", "write_file: {0}"),
        (r"patch.*?path=['\"](.+?)['\"]", "patch_file: {0}"),
        # Task patterns
        (r"skill_view.*?name=['\"](.+?)['\"]", "load_skill: {0}"),
        (r"skill_manage.*?action=['\"](.+?)['\"]", "skill_action: {0}"),
        (r"delegate_task.*?goal=['\"](.+?)['\"]", "delegation: {0}"),
        (r"cronjob.*?action=['\"](.+?)['\"]", "cron_action: {0}"),
        # Problem patterns
        (r"(bug|error|fail|fix|broken|crash|issue).*?(?:in|at|on)\s+(\S+)", "debug: {1}"),
        (r"(refactor|cleanup|optimize|improve)\s+(\S+)", "improve: {1}"),
        (r"(deploy|release|ship|launch)\s+(\S+)", "deploy: {1}"),
        # Architecture patterns
        (r"(MCP|plugin|skill|tool|agent)\s+(add|install|configure|setup)", "hermes_config: {0}"),
        # Research patterns
        (r"(research|investigate|find|discover|explore)\s+(.+)", "research: {1}"),
    ]

    def __init__(self):
        self.patterns: Dict[str, Pattern] = {}

    def extract_from_session(self, session: ConversationSession) -> List[Pattern]:
        """Extract all patterns from a single conversation session"""
        found = []
        for msg in session.messages:
            text = msg.get("content", "")
            for regex, template in self.TRIGGER_PATTERNS:
                match = re.search(regex, text, re.IGNORECASE)
                if match:
                    pattern_name = template.format(*match.groups())
                    if pattern_name not in self.patterns:
                        self.patterns[pattern_name] = Pattern(
                            name=pattern_name,
                            description=f"Auto-detected pattern: {pattern_name}",
                            trigger_phrases=[match.group(0)],
                            steps=[f"Execute: {pattern_name}"],
                            frequency=1,
                            last_seen=session.timestamp,
                        )
                        found.append(self.patterns[pattern_name])
                    else:
                        self.patterns[pattern_name].frequency += 1
                        self.patterns[pattern_name].last_seen = session.timestamp
                        # Add trigger phrase if different
                        if match.group(0) not in self.patterns[pattern_name].trigger_phrases:
                            self.patterns[pattern_name].trigger_phrases.append(match.group(0))
        return found

    def get_recurring_patterns(self, min_frequency: int = 3) -> List[Pattern]:
        """Get patterns that appear frequently enough to be reusable skills"""
        return [p for p in self.patterns.values() if p.frequency >= min_frequency]

    def get_new_skills_candidates(self) -> List[Pattern]:
        """Get patterns that qualify as new skills (frequency >= 3, not yet a skill)"""
        existing_skills = self._list_existing_skills()
        candidates = []
        for p in self.get_recurring_patterns(min_frequency=3):
            if p.name not in existing_skills:
                candidates.append(p)
        return candidates

    def _list_existing_skills(self) -> set:
        """List all existing skills in ~/.hermes/skills/"""
        existing = set()
        if SKILLS_DIR.exists():
            for f in SKILLS_DIR.rglob("*.md"):
                stem = f.stem
                existing.add(stem)
        return existing


class SkillGenerator:
    """Generate SKILL.md files from extracted patterns"""

    SKILL_TEMPLATE = """---
name: {name}
description: {description}
version: 1.0.0
author: hermes-autogen
tags: {tags}
auto_generated: true
generated_at: {timestamp}
---

# {name}

{description}

## Trigger
{trigger_condition}

## Steps
{steps}

## Verification
{verification}

## Notes
Auto-generated from conversation patterns. Review before use.
"""

    def __init__(self, skills_dir: Path = SKILLS_DIR):
        self.skills_dir = skills_dir

    def generate_skill(self, pattern: Pattern) -> Path:
        """Generate a SKILL.md file from a pattern"""
        name = pattern.name.replace(":", "_").replace(" ", "_")
        if len(name) > 64:
            name = name[:64]

        # Generate trigger condition from trigger phrases
        trigger = " or ".join(f'"{p}"' for p in pattern.trigger_phrases[:3])

        # Generate steps from pattern name
        steps = f"1. Identify when {pattern.name} is needed\n2. Execute the pattern\n3. Verify the result"

        # Generate verification
        verification = f"Run the pattern for {pattern.name} and confirm it produces expected output."

        # Tags from pattern name
        tags_list = pattern.name.split(":")
        tags = ", ".join(t.strip() for t in tags_list)

        content = self.SKILL_TEMPLATE.format(
            name=name,
            description=pattern.description,
            trigger_condition=trigger,
            steps=steps,
            verification=verification,
            tags=tags,
            timestamp=datetime.now().isoformat(),
        )

        skill_file = self.skills_dir / f"{name}.md"
        skill_file.parent.mkdir(parents=True, exist_ok=True)
        skill_file.write_text(content)
        log.info(f"Generated skill: {skill_file}")
        return skill_file


class ConversationAnalyzer:
    """Main orchestrator: analyze conversations and create skills"""

    def __init__(self):
        self.extractor = PatternExtractor()
        self.generator = SkillGenerator()

    def analyze_recent_sessions(self, days: int = 30) -> Dict[str, Any]:
        """Analyze recent conversation sessions and generate skills"""
        cutoff = datetime.now() - timedelta(days=days)

        # Load sessions from Hermes state.db
        sessions = self._load_sessions(cutoff)

        # Extract patterns
        all_patterns = []
        for session in sessions:
            patterns = self.extractor.extract_from_session(session)
            all_patterns.extend(patterns)

        # Get new skill candidates
        candidates = self.extractor.get_new_skills_candidates()

        # Generate skills
        generated = []
        for candidate in candidates:
            try:
                skill_path = self.generator.generate_skill(candidate)
                generated.append(str(skill_path))
            except Exception as e:
                log.warning(f"Failed to generate skill for {candidate.name}: {e}")

        return {
            "sessions_analyzed": len(sessions),
            "patterns_found": len(all_patterns),
            "candidates_identified": len(candidates),
            "skills_generated": len(generated),
            "generated_paths": generated,
            "top_patterns": [
                {"name": p.name, "frequency": p.frequency}
                for p in sorted(self.extractor.patterns.values(), key=lambda x: x.frequency, reverse=True)[:10]
            ],
        }

    def _load_sessions(self, cutoff: datetime) -> List[ConversationSession]:
        """Load conversation sessions from Hermes state.db"""
        import sqlite3

        sessions = []
        try:
            conn = sqlite3.connect(str(HISTORY_DB))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Try to get sessions from the messages table
            cursor.execute("""
                SELECT DISTINCT session_id, title FROM messages
                WHERE timestamp > ?
                ORDER BY timestamp DESC
            """, (cutoff.isoformat(),))

            rows = cursor.fetchall()
            for row in rows:
                session_id = row["session_id"]
                title = row.get("title", "Unknown")

                # Get messages for this session
                cursor2 = conn.cursor()
                cursor2.execute("""
                    SELECT role, content, timestamp FROM messages
                    WHERE session_id = ?
                    ORDER BY timestamp ASC
                    LIMIT 100
                """, (session_id,))

                messages = []
                tools = []
                for msg in cursor2.fetchall():
                    messages.append({
                        "role": msg["role"],
                        "content": msg["content"] or "",
                        "timestamp": msg["timestamp"],
                    })
                    # Track tool usage
                    if msg["role"] == "assistant" and msg["content"]:
                        # Extract tool calls from content
                        tool_match = re.findall(r'"(tool|function)["\s:]+(\w+)', msg["content"])
                        tools.extend(t[1] for t in tool_match)

                sessions.append(ConversationSession(
                    session_id=session_id,
                    title=title,
                    messages=messages,
                    tools=list(set(tools)),
                    outcome="completed",
                    timestamp=cutoff.isoformat(),
                ))

            conn.close()
        except Exception as e:
            log.warning(f"Could not load sessions from state.db: {e}")
            # Fallback: try to find session files
            sessions = self._load_sessions_from_files(cutoff)

        return sessions

    def _load_sessions_from_files(self, cutoff: datetime) -> List[ConversationSession]:
        """Fallback: load sessions from JSONL files"""
        sessions = []
        hermes_sessions = Path.home() / ".hermes" / "sessions"
        if hermes_sessions.exists():
            for f in hermes_sessions.glob("*.jsonl"):
                try:
                    with open(f) as fh:
                        content = fh.read()
                        # Simple extraction — would need proper JSONL parsing
                        pass
                except Exception:
                    pass
        return sessions


def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="MetaClaw-inspired skill auto-generator for Hermes")
    parser.add_argument("--days", type=int, default=30, help="Days of history to analyze")
    parser.add_argument("--min-freq", type=int, default=3, help="Minimum frequency for skill candidate")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be generated without creating files")
    parser.add_argument("--list-patterns", action="store_true", help="List all extracted patterns")
    parser.add_argument("--generate", action="store_true", help="Generate skills for candidates")

    args = parser.parse_args()

    analyzer = ConversationAnalyzer()

    if args.list_patterns:
        analyzer.analyze_recent_sessions(days=args.days)
        patterns = sorted(analyzer.extractor.patterns.values(), key=lambda x: x.frequency, reverse=True)
        print(f"\n{'─' * 60}")
        print(f"PATTERNS FOUND ({len(patterns)})")
        print(f"{'─' * 60}")
        for p in patterns:
            print(f"  [{p.frequency:3d}] {p.name}")
            for tp in p.trigger_phrases[:3]:
                print(f"        → {tp}")
        return

    if args.dry_run:
        analyzer.analyze_recent_sessions(days=args.days)
        candidates = analyzer.extractor.get_new_skills_candidates()
        print(f"\n{'─' * 60}")
        print(f"DRY RUN — {len(candidates)} skills would be generated")
        print(f"{'─' * 60}")
        for c in candidates:
            print(f"  → {c.name} (freq={c.frequency})")
            print(f"    Triggers: {', '.join(c.trigger_phrases[:3])}")
        return

    if args.generate:
        result = analyzer.analyze_recent_sessions(days=args.days)
        print(f"\n{'═' * 60}")
        print(f"SKILL AUTO-GEN RESULTS")
        print(f"{'═' * 60}")
        print(f"  Sessions analyzed:     {result['sessions_analyzed']}")
        print(f"  Patterns found:        {result['patterns_found']}")
        print(f"  Candidates identified: {result['candidates_identified']}")
        print(f"  Skills generated:      {result['skills_generated']}")
        print(f"{'─' * 60}")
        for path in result["generated_paths"]:
            print(f"  ✓ {path}")
        print(f"{'═' * 60}")
        return

    # Default: run full analysis
    result = analyzer.analyze_recent_sessions(days=args.days)
    print(f"\nSkill Autogen: {result['skills_generated']} skills from {result['sessions_analyzed']} sessions")


if __name__ == "__main__":
    main()