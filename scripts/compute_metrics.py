from __future__ import annotations
import os, re

src_path='src/yamlr'
total_files=0
code_lines=0
blank=0
comment=0
files_with_all=0
for root, dirs, files in os.walk(src_path):
    dirs[:] = [d for d in dirs if d not in ('__pycache__','.git','test','.dist','.build')]
    for file in files:
        if not file.endswith('.py'): continue
        total_files+=1
        filepath=os.path.join(root,file)
        has_all=False
        with open(filepath,'r',encoding='utf-8') as f:
            for line in f:
                stripped=line.strip()
                if not stripped:
                    blank+=1
                elif stripped.startswith('#'):
                    comment+=1
                else:
                    code_lines+=1
                if not has_all and re.match(r"__all__\s*=\s*\[", stripped):
                    has_all=True
        if has_all:
            files_with_all+=1

output = (
    f"Files: {total_files}\n"
    f"Code lines: {code_lines}\n"
    f"Blank: {blank}\n"
    f"Comment: {comment}\n"
    f"Code-to-comment ratio: {code_lines/comment:.2f if comment else 'NA'}\n"
    f"Files with __all__: {files_with_all}\n"
)
print(output)
# additional stats
all_count = 0
for root, dirs, files in os.walk(src_path):
    dirs[:] = [d for d in dirs if d not in ('__pycache__','.git','test','.dist','.build')]
    for file in files:
        if file.endswith('.py'):
            path = os.path.join(root,file)
            with open(path,'r',encoding='utf-8') as f:
                if any('__all__' in line for line in f):
                    all_count += 1
print(f"Total modules referencing __all__: {all_count}\n")
all_output = f"Total modules referencing __all__: {all_count}\n"
with open('metrics_output.txt','a',encoding='utf-8') as out:
    out.write(all_output)

# count docstrings starting with Why:
why_count = 0
total_docs = 0
for root, dirs, files in os.walk(src_path):
    dirs[:] = [d for d in dirs if d not in ('__pycache__','.git','test','.dist','.build')]
    for file in files:
        if file.endswith('.py'):
            path=os.path.join(root,file)
            with open(path,'r',encoding='utf-8') as f:
                try:
                    tree = ast.parse(f.read())
                except Exception:
                    continue
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Module)):
                        doc = ast.get_docstring(node)
                        if doc:
                            total_docs += 1
                            if doc.strip().startswith('Why:'):
                                why_count += 1
why_output = f"Total docstrings: {total_docs}, docs starting with Why: {why_count}\n"
print(why_output)
with open('metrics_output.txt','a',encoding='utf-8') as out:
    out.write(why_output)



