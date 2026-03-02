import ast
import os
import sys

imports = set()
for root, dirs, files in os.walk('backend'):
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read(), filename=filepath)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for name in node.names:
                            imports.add(name.name.split('.')[0])
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            imports.add(node.module.split('.')[0])
            except Exception as e:
                pass

stdlib = set(sys.builtin_module_names) | {'os', 'sys', 'datetime', 'json', 're', 'logging', 'pathlib', 'typing', 'io', 'subprocess', 'time', 'uuid', 'collections', 'math', 'enum', 'traceback', 'importlib', 'hashlib', 'asyncio', 'contextlib'}
third_party = imports - stdlib - {'backend', 'frontend', 'data', 'tests'}

print("Found imports:", third_party)
