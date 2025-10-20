import os
import sys
import PyInstaller.__main__
from PyInstaller.utils.hooks import collect_submodules

# -----------------------------------------------------------------------------
# Ensure repo root is on sys.path
# -----------------------------------------------------------------------------
repo_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, repo_root)
os.chdir(repo_root)

# -----------------------------------------------------------------------------
# Collect all submodules from key project packages
# -----------------------------------------------------------------------------
packages = [
    'apps',
    'base_classes',
    'controllers',
    'instruments',
    'models',
    'views',
    'utils'
]

hidden_imports = []
for pkg in packages:
    try:
        subs = collect_submodules(pkg)
        hidden_imports += subs
        print(f"Detected {len(subs)} submodules in {pkg}")
    except Exception as e:
        print(f"Failed to collect submodules for {pkg}: {e}")

print(f"\n Total hidden imports collected: {len(hidden_imports)}")

# -----------------------------------------------------------------------------
# Force-include any modules PyInstaller tends to miss
# -----------------------------------------------------------------------------
force_includes = [
    'apps.cycle_sequence_editor',
]

for m in force_includes:
    if m not in hidden_imports:
        hidden_imports.append(m)
        print(f"Forcing inclusion of {m}")
    else:
        print(f"Already detected: {m}")

# -----------------------------------------------------------------------------
# Run PyInstaller build
# -----------------------------------------------------------------------------
args = [
    'main.py',
    '--name=main',
    '--debug', 'all',
    '--onedir',
    '--windowed',
    '--icon=icon.ico',
    '--exclude=PyQt5',
    '--paths=.',
    *[f'--hidden-import={m}' for m in hidden_imports],
    '--add-data=apps/cycle_sequence_editor.py;apps',
    '--clean'
]

print("\nRunning PyInstaller with the following args:")
for a in args:
    print(" ", a)

PyInstaller.__main__.run(args)
