"""Import audited public upstream checkouts without their Git history or local files."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

SOURCES = {
    'switcher': 'https://github.com/YOURSJEYO/claude-switcher',
    'vps': 'https://github.com/nevertoday/xiaoxiaodong-vps',
}
PROJECT = 'clm031102-source/claude-network-guide'
URL = f'https://github.com/{PROJECT}'

def rebrand(text: str, module: str) -> str:
    if module == 'vps':
        text = re.sub(r'https://vps\.xiaoxiaodong\.ai((?:/[^\s<>"\)\]}]*)?)', lambda m: URL + '/tree/main/modules/vps/site/src/pages' + (m.group(1) or '/'), text)
        text = text.replace('https://nevertoday.github.io/xiaoxiaodong-vps/', URL + '/tree/main/modules/vps/site/src/pages/')
        text = text.replace('https://github.com/nevertoday/xiaoxiaodong-vps/blob/main/', URL+'/blob/main/modules/vps/')
        text = text.replace('https://github.com/nevertoday/xiaoxiaodong-vps', URL)
        text = text.replace('nevertoday/xiaoxiaodong-vps', PROJECT)
        text = text.replace('xiaoxiaodong-vps', 'claude-network-guide')
        for old in ['小小东 VPS', '小小东VPS', '小小东的 VPS', '小小东的服务器', '小小东']:
            text = text.replace(old, 'Claude 网络指南')
        text = text.replace('Xiaoxiaodong VPS','Claude Network Guide').replace('xiaoxiaodong VPS','Claude Network Guide')
        # Invitations belong to the upstream author; our documentation uses ordinary vendor links.
        text = re.sub(r'https://bandwagonhost\.com/aff\.php\?[^\s<>"\)\]]+', 'https://bandwagonhost.com/', text)
        text = re.sub(r'https://(?:www\.)?dmit\.io/aff\.php\?[^\s<>"\)\]]+', 'https://www.dmit.io/', text)
    else:
        text = text.replace('https://raw.githubusercontent.com/YOURSJEYO/claude-switcher/main/', f'https://raw.githubusercontent.com/{PROJECT}/main/modules/switcher/')
        text = text.replace('https://github.com/YOURSJEYO/claude-switcher/blob/main/', URL+'/blob/main/modules/switcher/')
        text = text.replace('YOURSJEYO/claude-switcher',PROJECT)
        text = text.replace('Claude 切换器','Claude 网络指南 账号工具').replace('Claude切换器','Claude网络指南账号工具')
        text = text.replace('cd claude-switcher', 'cd claude-network-guide/modules/switcher')
        text = text.replace('claude-switcher-main/', 'claude-network-guide-main/modules/switcher/')
    return text

def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument('source_root', type=Path)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    if (root/'UPSTREAM.json').exists() or (root/'modules').exists():
        parser.error('Initial import only: existing adapted modules must not be overwritten. Use a fresh staging directory for upstream updates.')
    records=[]
    for module,url in SOURCES.items():
        source=args.source_root/module
        revision=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
        paths=subprocess.check_output(['git','-C',str(source),'ls-files','-z']).decode('utf-8').split('\0')
        inventory=[]
        for name in filter(None,paths):
            raw=subprocess.check_output(['git','-C',str(source),'show',f'{revision}:{name}'])
            destname=name.replace('skills/xiaoxiaodong-vps/','skills/claude-network-guide/')
            # Upstream agent-install prompts are reference material, not repo-wide instructions.
            if destname=='AGENTS.md':destname='docs/agent-install-reference.md'
            target=root/'modules'/module/destname
            target.parent.mkdir(parents=True,exist_ok=True)
            transformed=raw
            if not target.name.upper().startswith('LICENSE') and not name.startswith('site/public/xxd/'):
                try:transformed=rebrand(raw.decode('utf-8'),module).encode('utf-8')
                except UnicodeDecodeError:pass
            target.write_bytes(transformed)
            inventory.append({'source_path':name,'path':target.relative_to(root).as_posix(),'source_sha256':hashlib.sha256(raw).hexdigest()})
        records.append({'module':module,'repository':url,'commit':revision,'license':'MIT','files':inventory})
    (root/'UPSTREAM.json').write_text(json.dumps({'sources':records},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({r['module']:{'commit':r['commit'],'files':len(r['files'])} for r in records},indent=2))

if __name__=='__main__':main()
