import os
import sys
import PyInstaller.__main__
from PyInstaller.utils.hooks import collect_submodules

repo_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, repo_root)
os.chdir(repo_root)

# Collect all submodules from key project packages
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

# Run PyInstaller build
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
    '--clean'
]

print("\nRunning PyInstaller with the following args:")
for a in args:
    print(" ", a)

PyInstaller.__main__.run(args)
