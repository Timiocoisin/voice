import os
import glob

files = []
for f in glob.glob('**/*.py', recursive=True):
    if 'venv' not in f and '__pycache__' not in f:
        with open(f, 'r', encoding='utf-8') as file:
            lines = len(file.readlines())
            if lines > 300:
                files.append((f.replace('\\', '/'), lines))

files.sort(key=lambda x: x[1], reverse=True)
print('Files over 300 lines:')
print('=' * 60)
for path, lines in files:
    print(f'{lines:>5} lines  {path}')
