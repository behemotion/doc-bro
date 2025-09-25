#!/usr/bin/env python3
"""Fix all broken model_config instances in the codebase."""

import os
import re
from pathlib import Path

def fix_model_config_in_file(file_path):
    """Fix broken model_config in a single file."""
    with open(file_path, 'r') as f:
        content = f.read()

    # Check if file has model_config
    if 'model_config = ConfigDict(' not in content:
        return False

    # Pattern to find broken model_config blocks
    pattern = r'(\s*)model_config = ConfigDict\((.*?)\n\1\)'

    def fix_config(match):
        indent = match.group(1)
        body = match.group(2)

        # Clean up the body
        lines = body.split('\n')
        params = []

        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            # Fix common patterns
            if '=' in line:
                # Clean up parameter lines
                line = line.rstrip(',').rstrip(')')
                if 'json_encoders' in line:
                    params.append(f'{indent}    json_encoders={{')
                elif 'datetime:' in line or 'UUID:' in line or 'Path:' in line:
                    params.append(f'{indent}        {line},')
                elif '}' in line and 'json_encoders' in '\n'.join(params[-3:]):
                    params.append(f'{indent}    }}')
                else:
                    # Regular parameter
                    key_val = line.split('=', 1)
                    if len(key_val) == 2:
                        key = key_val[0].strip()
                        val = key_val[1].strip()
                        params.append(f'{indent}    {key}={val},')

        if params and params[-1].endswith(','):
            params[-1] = params[-1][:-1]  # Remove trailing comma

        result = f'{indent}model_config = ConfigDict(\n'
        result += '\n'.join(params)
        result += f'\n{indent})'

        return result

    # Apply fixes
    new_content = re.sub(pattern, fix_config, content, flags=re.DOTALL)

    # Additional fix for completely broken patterns
    if 'use_enum_values = True,        json_encoders = {' in new_content:
        new_content = new_content.replace(
            'use_enum_values = True,        json_encoders = {',
            'use_enum_values=True,\n        json_encoders={'
        )

    if new_content != content:
        with open(file_path, 'w') as f:
            f.write(new_content)
        return True

    return False

# Find all Python files with potential issues
for root, dirs, files in os.walk('src'):
    for file in files:
        if file.endswith('.py'):
            file_path = os.path.join(root, file)
            try:
                # Try to compile the file
                with open(file_path) as f:
                    compile(f.read(), file_path, 'exec')
            except SyntaxError as e:
                print(f"Fixing syntax error in {file_path}:{e.lineno}")
                if fix_model_config_in_file(file_path):
                    print(f"  ✓ Fixed {file_path}")
                else:
                    # Try manual fix for specific patterns
                    with open(file_path, 'r') as f:
                        lines = f.readlines()

                    fixed = False
                    for i, line in enumerate(lines):
                        if 'model_config = ConfigDict(' in line:
                            # Find the end of this block
                            j = i + 1
                            while j < len(lines) and not lines[j].strip().startswith(')'):
                                j += 1

                            # Reconstruct the block
                            if j < len(lines):
                                lines[i] = '    model_config = ConfigDict(\n'
                                lines[i+1:j] = ['        use_enum_values=True\n']
                                lines[j] = '    )\n'
                                fixed = True
                                break

                    if fixed:
                        with open(file_path, 'w') as f:
                            f.writelines(lines)
                        print(f"  ✓ Manually fixed {file_path}")

print("\nDone! Testing import...")
try:
    import src.cli.main
    print("✓ Import successful!")
except Exception as e:
    print(f"✗ Import failed: {e}")