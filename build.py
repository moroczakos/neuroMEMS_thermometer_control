import os
import sys
import PyInstaller.__main__
from PyInstaller.utils.hooks import collect_submodules

# Ensure repo root is in sys.path
repo_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, repo_root)
os.chdir(repo_root)

# Automatically find all Python packages (folders with __init__.py)
packages = []
for root, dirs, files in os.walk(repo_root):
    if '__init__.py' in files:
        # Convert path to dotted package notation
        rel_path = os.path.relpath(root, repo_root)
        package_name = rel_path.replace(os.path.sep, '.')
        packages.append(package_name)

print(f"Detected packages: {packages}")

# Collect all submodules for every package
hidden_imports = []
for pkg in packages:
    hidden_imports += collect_submodules(pkg)

# Optional: sanity check
if 'apps.cycle_sequence_editor' not in hidden_imports:
    print("WARNING: apps.cycle_sequence_editor not detected — forcing inclusion")
    hidden_imports.append('apps.cycle_sequence_editor')

print(f"Total hidden imports detected: {len(hidden_imports)}")

# Run PyInstaller
PyInstaller.__main__.run([
    'main.py',
    '--name=main',
    '--debug', 'all',
    '--onedir',
    '--windowed',
    '--icon=icon.ico',
    '--exclude=PyQt5',
    '--paths=.',
    *[f'--hidden-import={m}' for m in hidden_imports],
    '--clean'
])
