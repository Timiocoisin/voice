files = {
    'gui/main_window.py': 0,
    'gui/components/chat_bubble.py': 0,
    'gui/components/sections.py': 0,
    'gui/handlers/dialog_handlers.py': 0,
    'gui/handlers/avatar_handlers.py': 0,
}
for path in files:
    with open(path, 'r', encoding='utf-8') as f:
        files[path] = len(f.readlines())
        
print('代码拆分统计：')
print('=' * 60)
print(f'main_window.py:           {files["gui/main_window.py"]:>5} 行 (原 2827 行，减少 {2827-files["gui/main_window.py"]} 行)')
print()
print('新建模块：')
print(f'  chat_bubble.py:         {files["gui/components/chat_bubble.py"]:>5} 行')
print(f'  sections.py:            {files["gui/components/sections.py"]:>5} 行')
print(f'  dialog_handlers.py:     {files["gui/handlers/dialog_handlers.py"]:>5} 行')
print(f'  avatar_handlers.py:     {files["gui/handlers/avatar_handlers.py"]:>5} 行')
print()
new_files_total = sum(files[k] for k in files if k != 'gui/main_window.py')
print(f'新模块总计：              {new_files_total:>5} 行')
print(f'重构效率：减少重复约 {622 - new_files_total} 行')
