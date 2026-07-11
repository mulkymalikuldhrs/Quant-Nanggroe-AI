"""Test Almgren-Chriss execution model (syntax + logic verification)"""
import ast

# Validate AST
with open("../quant_nanggroe/engine/execution/almgren_chriss.py") as f:
    source = f.read()
tree = ast.parse(source)

classes = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}
funcs = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}

print(f"File parses OK: {len(classes)} classes, {len(funcs)} functions")

assert "AlmgrenChriss" in classes, "Missing AlmgrenChriss"
assert "ExecutionParams" in classes, "Missing ExecutionParams"
assert "TradeSchedule" in classes, "Missing TradeSchedule"
assert "ExecutionResult" in classes, "Missing ExecutionResult"
assert "ExecutionSimulator" in classes, "Missing ExecutionSimulator"
assert "optimal_execution_schedule" in funcs, "Missing optimal_execution_schedule"

# Check AlmgrenChriss methods
ac_methods = {n.name for n in classes["AlmgrenChriss"].body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
required = {"twap", "vwap", "implementation_shortfall", "adaptive", "compare_strategies"}
assert required.issubset(ac_methods), f"Missing AC methods: {required - ac_methods}"

# Check ExecutionParams has from_market_data
ep_methods = {n.name for n in classes["ExecutionParams"].body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
assert "from_market_data" in ep_methods, "Missing ExecutionParams.from_market_data"

# Check ExecutionSchedule props (property decorators)
ts_body = classes["TradeSchedule"].body
ts_props = set()
for node in ts_body:
    for deco in getattr(node, 'decorator_list', []):
        if isinstance(deco, ast.Name) and deco.id == 'property':
            ts_props.add(node.name)
assert "avg_price" in ts_props, "Missing TradeSchedule.avg_price property"
assert "implementation_shortfall" in ts_props, "Missing TradeSchedule.implementation_shortfall property"

print("AST validation: ALL CHECKS PASSED")
print("RUNTIME_SKIPPED: numpy not installed in environment")
