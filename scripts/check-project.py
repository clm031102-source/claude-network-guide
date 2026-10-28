"""Check imports, attribution, portable source inventory and main documentation links."""
from pathlib import Path
import hashlib
import json
import re
import sys

root=Path(__file__).resolve().parents[1]
issues=[]
manifest=json.loads((root/'UPSTREAM.json').read_text(encoding='utf-8'))
for source in manifest['sources']:
    if not (root/'modules'/source['module']/'LICENSE').is_file():
        issues.append('Missing upstream license: '+source['module'])
    for item in source['files']:
        if not (root/item['path']).is_file():issues.append('Missing imported file: '+item['path'])
        elif item['source_path'] == 'LICENSE' and hashlib.sha256((root/item['path']).read_bytes()).hexdigest() != item['source_sha256']:
            issues.append('Upstream license changed: '+item['path'])
checksum_file=root/'modules/switcher/SHA256SUMS'
for line in checksum_file.read_text(encoding='utf-8').splitlines():
    if not line.strip():continue
    digest,name=line.split(None,1)
    path=checksum_file.parent/name.lstrip('*')
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
        issues.append('Module checksum mismatch: '+name)
docs=[root/'README.md',root/'NOTICE.md',*(root/'docs').glob('*.md')]
for file in docs:
    if not file.exists():issues.append('Missing document: '+str(file));continue
    text=file.read_text(encoding='utf-8')
    for link in re.findall(r'\[[^\]]*\]\(([^)]+)\)',text):
        link=link.split('#')[0].split(' "')[0]
        if not link or ':' in link or link.startswith('/'):continue
        if not (file.parent/link).exists():issues.append(f'Broken link in {file.relative_to(root)}: {link}')
for name in ['app/core.py','app/server.py','app/web/index.html','app/web/app.js','app/web/style.css','LICENSE','SECURITY.md','启动检测.cmd','start.sh']:
    if not (root/name).is_file():issues.append('Missing required file: '+name)
if issues:
    print('\n'.join(issues));sys.exit(1)
print(f'PASS: source inventory ({sum(len(s["files"]) for s in manifest["sources"])} files), original licenses, module checksums, application files and main document links')
