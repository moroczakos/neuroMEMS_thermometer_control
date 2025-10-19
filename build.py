import PyInstaller.__main__
from PyInstaller.utils.hooks import collect_submodules

# List all your project packages
packages = ['apps', 'base_classes', 'controllers', 'instruments', 'models', 'views', 'utils']

# Collect all submodules automatically
hidden_imports = []
for pkg in packages:
    hidden_imports += collect_submodules(pkg)

print(f"Hidden imports: {len(hidden_imports)} modules detected.")

# Run PyInstaller
PyInstaller.__main__.run([
    'main.py',
    '--onedir',
    '--windowed',
    '--icon=icon.ico',
    '--exclude=PyQt5',
    *[f'--hidden-import={m}' for m in hidden_imports],
    '--name=main',
    '--clean'
])
