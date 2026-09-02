#!/bin/bash
echo "=== hardcoded secrets scan ==="
grep -rni "password" quant_nanggroe/ --include="*.py" 2>/dev/null | grep -v "self.password\|password=\|password: \|no password\|password is\|password)\|password_\|password " | head -20
echo "=== env var usage ==="
grep -rni "os.environ.get.*MT5\|getenv.*MT5\|environ.*MT5" quant_nanggroe/ --include="*.py" 2>/dev/null | head -20
echo "=== config files with secrets ==="
grep -rni "password\|secret\|api_key\|token" config/ --include="*.yaml" --include="*.yml" --include="*.json" --include="*.toml" 2>/dev/null | head -20
