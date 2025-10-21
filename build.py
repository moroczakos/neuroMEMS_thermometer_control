import os
import sys
import PyInstaller.__main__
from PyInstaller.utils.hooks import collect_submodules

repo_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, repo_root)
os.chdir(repo_root)

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
    '--clean'
]

print("\nRunning PyInstaller with the following args:")
for a in args:
    print(" ", a)

PyInstaller.__main__.run(args)
