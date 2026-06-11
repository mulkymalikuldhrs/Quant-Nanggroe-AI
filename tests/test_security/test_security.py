"""Tests for security module."""
import pytest
from ai_multicolony.security.analyzer import SecurityAnalyzer
from ai_multicolony.security.audit import AuditTrail
from ai_multicolony.security.permissions import PermissionEngine, RoleDef

class TestSecurityAnalyzer:
    def test_create(self): assert SecurityAnalyzer() is not None
    def test_analyze_code(self):
        s = SecurityAnalyzer()
        results = s.analyze_code("password = \'hardcoded123\'")
        assert isinstance(results, (list, dict))
    def test_detect_secrets(self):
        s = SecurityAnalyzer()
        results = s.detect_secrets("aws_access_key = \'AKIAIOSFODNN7EXAMPLE\'")
        assert isinstance(results, (list, dict))
    def test_calculate_score(self):
        s = SecurityAnalyzer()
        score = s.calculate_score([])
        assert isinstance(score, (int, float))
    def test_generate_report(self):
        s = SecurityAnalyzer()
        report = s.generate_report([])
        assert isinstance(report, (dict, str))

class TestAuditTrail:
    def test_create(self): assert AuditTrail() is not None
    def test_record(self):
        a = AuditTrail()
        entry = a.record(agent_id="a1", tool_name="shell", action="execute")
        assert entry is not None
    def test_get_entries(self):
        a = AuditTrail()
        a.record(agent_id="a1", tool_name="shell", action="execute")
        entries = a.get_entries(agent_id="a1")
        assert len(entries) >= 1

class TestPermissionEngine:
    def test_create(self): assert PermissionEngine() is not None
    def test_check_access(self):
        p = PermissionEngine()
        result = p.check_access(agent_id="a1", tool_name="browser.navigate")
        assert result is not None
    def test_define_role(self):
        p = PermissionEngine()
        role = RoleDef(name="viewer", permissions=["read"], autonomy_level=0)
        p.define_role(role)
        assert p.get_role("viewer") is not None
