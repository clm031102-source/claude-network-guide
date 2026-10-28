"""Check imports, attribution, portable source inventory and main documentation links."""
from pathlib import Path
import hashlib
import importlib.util
import json
import re
import shlex
import sys
from urllib.parse import unquote, urlsplit
from zipfile import ZipFile
import xml.etree.ElementTree as ET

root=Path(__file__).resolve().parents[1]
issues=[]
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'cp':'http://schemas.openxmlformats.org/package/2006/metadata/core-properties'}
W='{'+NS['w']+'}'


def text_blocks(markdown):
    """Return complete text fences, preserving every character inside them."""
    return re.findall(r'^```text[ \t]*\n(.*?)\n```[ \t]*(?=\n|$)',markdown,re.M|re.S)


def paragraph_text(paragraph):
    return ''.join(node.text or '' if node.tag==W+'t' else '\t' if node.tag==W+'tab' else '\n'
                   for node in paragraph.iter() if node.tag in (W+'t',W+'tab',W+'br',W+'cr'))


def field_codes(element):
    """Read each complex field separately, including fields split across runs."""
    stack=[]
    codes=[]
    for node in element.iter():
        if node.tag==W+'fldSimple':
            codes.append(node.get(W+'instr',''))
        elif node.tag==W+'fldChar':
            kind=node.get(W+'fldCharType')
            if kind=='begin':stack.append([])
            elif kind=='end' and stack:codes.append(''.join(stack.pop()))
        elif node.tag==W+'instrText':
            if stack:stack[-1].append(node.text or '')
            else:codes.append(node.text or '')
    codes.extend(''.join(parts) for parts in stack)
    return codes


def field_tokens(code):
    try:
        return [token[1:-1] if len(token)>1 and token[0]==token[-1]=='"' else token
                for token in shlex.split(code,posix=False)]
    except ValueError:
        return []


def hyperlink_parts(code):
    """Return the external URL and/or internal bookmark from a HYPERLINK."""
    tokens=field_tokens(code)
    if not tokens or tokens[0].upper()!='HYPERLINK':return None
    external=[]
    anchor=None
    index=1
    while index<len(tokens):
        token=tokens[index]
        if token.lower() in ('\\l','\\o','\\t'):
            if index+1>=len(tokens):raise ValueError('Hyperlink switch has no value')
            if token.lower()=='\\l':anchor=tokens[index+1]
            index+=2
        elif token.lower() in ('\\m','\\n','\\h'):
            index+=1
        elif token.startswith('\\'):
            raise ValueError('Unknown hyperlink switch or local network path')
        else:
            external.append(token)
            index+=1
    if len(external)>1 or not (external or anchor):raise ValueError('Malformed hyperlink field')
    return external[0] if external else None,anchor


def check_web_target(target,context):
    """A web URL is allowed; repository URLs must point to existing files."""
    parsed=urlsplit(target)
    if (parsed.scheme not in ('https','http','mailto') or
            (parsed.scheme in ('https','http') and not parsed.netloc) or
            any(ord(char)<32 for char in target)):
        issues.append(context+' contains a non-web or malformed external reference')
        return
    prefixes=(
        'https://github.com/clm031102-source/claude-network-guide/blob/main/',
        'https://github.com/clm031102-source/claude-network-guide/raw/refs/heads/main/',
        'https://raw.githubusercontent.com/clm031102-source/claude-network-guide/main/',
    )
    without_fragment=target.split('#',1)[0].split('?',1)[0]
    for prefix in prefixes:
        if without_fragment.startswith(prefix):
            candidate=(root/unquote(without_fragment[len(prefix):])).resolve()
            if not candidate.is_relative_to(root) or not candidate.exists():
                issues.append(context+' contains a broken repository reference: '+target)


def check_word(archive,prompt,source):
    document=ET.fromstring(archive.read('word/document.xml'))
    styles=ET.fromstring(archive.read('word/styles.xml'))
    style_names={style.get(W+'styleId'):style.find('w:name',NS).get(W+'val','').casefold()
                 for style in styles.findall('w:style',NS) if style.find('w:name',NS) is not None}
    body=document.find('w:body',NS)
    if body is None:
        issues.append('Word guide has no document body')
        return
    paragraphs=list(body.iter(W+'p'))
    def style_name(paragraph):
        style=paragraph.find('w:pPr/w:pStyle',NS)
        return style_names.get(style.get(W+'val'),'') if style is not None else ''

    # This stamp was created when the Word body was built, not when hashes were
    # refreshed. It also covers referenced image contents, unlike the MD hash.
    try:
        spec=importlib.util.spec_from_file_location('guide_builder_check',root/'scripts/build-guide.py')
        builder=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        expected_stamp='claude-network-guide-build-v1:'+builder.build_fingerprint()
        properties=ET.fromstring(archive.read('docProps/core.xml'))
        stamp=properties.findtext('cp:keywords',default='',namespaces=NS)
        if stamp!=expected_stamp:
            issues.append('Word build fingerprint differs from current source, prompt or images; rebuild the Word guide')
    except (OSError,ValueError,AttributeError,KeyError,ET.ParseError) as error:
        issues.append('Cannot verify Word build fingerprint: '+type(error).__name__)

    prompt_paragraphs=[paragraph_text(p) for p in paragraphs if style_name(p)=='agent prompt']
    actual_prompt='\n'.join(text for text in prompt_paragraphs if text.strip())
    expected_prompt='\n'.join(line for line in prompt.splitlines() if line.strip())
    if actual_prompt!=expected_prompt:
        issues.append('Word Agent Prompt paragraphs differ from the complete canonical prompt')

    source_titles=re.findall(r'^##[ \t]+(.+)$',source,re.M)
    expected_titles=[re.sub(r'[：:；;，,。！？!?（）()·—/、“”‘’]',' ',title) for title in source_titles]
    normalized=lambda text:re.sub(r'\s+','',text)
    headings=[p for p in paragraphs if style_name(p)=='heading 1']
    if [normalized(paragraph_text(p)) for p in headings]!=[normalized(title) for title in expected_titles]:
        issues.append('Word chapter headings differ from the Markdown guide')

    bookmark_paragraphs={node.get(W+'name'):p for p in paragraphs for node in p.iter(W+'bookmarkStart')}
    bookmarks={node.get(W+'name') for node in document.iter(W+'bookmarkStart')}
    toc=[p for p in paragraphs if re.fullmatch(r'toc\s+[1-9]\d*',style_name(p)) and paragraph_text(p).strip()]
    if len(expected_titles)!=12 or len(toc)!=12:
        issues.append(f'Word TOC needs 12 cached chapter entries; found {len(toc)} entries and {len(expected_titles)} source chapters')
    if not any(re.match(r'^\s*TOC\b',code,re.I) for code in field_codes(body)):
        issues.append('Word guide is missing its TOC field')
    toc_pages=[]
    toc_targets=[]
    for index,paragraph in enumerate(toc):
        codes=field_codes(paragraph)
        targets=[]
        for code in codes:
            try:
                parts=hyperlink_parts(code)
                if parts and not parts[0] and parts[1]:targets.append(parts[1])
            except ValueError:
                pass  # The global link check below reports malformed fields.
        targets.extend(link.get(W+'anchor') for link in paragraph.iter(W+'hyperlink') if link.get(W+'anchor'))
        references=[]
        for code in codes:
            tokens=field_tokens(code)
            if len(tokens)>=2 and tokens[0].upper()=='PAGEREF':references.append(tokens[1])
        target=targets[0] if len(set(targets))==1 else None
        if not target or set(references)!={target} or target not in bookmarks:
            issues.append(f'Word TOC entry {index+1} lacks a valid matching internal HYPERLINK, PAGEREF or bookmark')
        else:
            toc_targets.append(target)
            destination=bookmark_paragraphs.get(target)
            expected=expected_titles[index] if index<len(expected_titles) else ''
            if destination is None or style_name(destination)!='heading 1' or normalized(paragraph_text(destination))!=normalized(expected):
                issues.append(f'Word TOC entry {index+1} points to the wrong chapter')
        texts=[node.text or '' for node in paragraph.iter(W+'t')]
        if not texts or not re.fullmatch(r'[1-9]\d*',texts[-1].strip()):
            issues.append(f'Word TOC entry {index+1} has no cached page number')
        else:
            toc_pages.append(int(texts[-1].strip()))
            label=''.join(texts[:-1])
            if index>=len(expected_titles) or normalized(label)!=normalized(expected_titles[index]):
                issues.append(f'Word TOC entry {index+1} has stale or incorrect cached text')
    if len(toc_targets)!=len(set(toc_targets)):
        issues.append('Word TOC repeats a chapter bookmark')
    if toc_pages!=sorted(toc_pages):
        issues.append('Word TOC cached page numbers are out of order')

    relationships=ET.fromstring(archive.read('word/_rels/document.xml.rels'))
    for relationship in relationships:
        if relationship.get('TargetMode')=='External':
            check_web_target(relationship.get('Target',''),'Word relationship')
    for code in field_codes(body):
        try:
            parts=hyperlink_parts(code)
            if parts is None:continue
            external,anchor=parts
            if external:check_web_target(external,'Word HYPERLINK field')
            elif anchor not in bookmarks:issues.append('Word hyperlink points to a missing internal bookmark')
        except ValueError:
            issues.append('Word contains a malformed or unsupported HYPERLINK field')

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
    links=re.findall(r'\[[^\]]*\]\(([^)]+)\)',text)
    links+=re.findall(r'^\[[^\]]+\]:\s*(\S+)',text,re.M)
    for link in links:
        link=link.split('#')[0].split(' "')[0]
        link=unquote(link)
        for prefix in ['https://github.com/clm031102-source/claude-network-guide/blob/main/',
                       'https://github.com/clm031102-source/claude-network-guide/raw/refs/heads/main/',
                       'https://raw.githubusercontent.com/clm031102-source/claude-network-guide/main/']:
            if link.startswith(prefix):
                candidate=root/link[len(prefix):]
                if not candidate.exists():issues.append(f'Broken repository link in {file.relative_to(root)}: {link}')
        if not link or ':' in link or link.startswith('/'):continue
        if not (file.parent/link).exists():issues.append(f'Broken link in {file.relative_to(root)}: {link}')
guide_version=root/'docs/guide-version.json'
if (root/'docs/beginner-guide.md').exists():
    if not guide_version.exists():issues.append('Missing linked guide version manifest')
    else:
        version=json.loads(guide_version.read_text(encoding='utf-8'))
        required_hashes={version['source'],version['prompt'],version['word']}
        if not required_hashes.issubset(version['sha256']):
            issues.append('Guide manifest does not cover source, prompt and Word hashes')
        for name,digest in version['sha256'].items():
            path=root/name
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
                issues.append('Guide source or download changed without rebuild/finalize: '+name)
        prompt=(root/version['prompt']).read_text(encoding='utf-8').rstrip('\n')
        source=(root/version['source']).read_text(encoding='utf-8')
        begin='<!-- AGENT_PROMPT_START -->'
        end='<!-- AGENT_PROMPT_END -->'
        if source.count(begin)!=1 or source.count(end)!=1 or source.index(begin)>source.index(end):
            issues.append('Guide must contain one ordered pair of agent prompt markers')
        else:
            region=source.split(begin,1)[1].split(end,1)[0]
            blocks=text_blocks(region)
            if len(blocks)!=1 or blocks[0]!=prompt:
                issues.append('Guide marked agent prompt differs from the exact canonical prompt')
        handoff=(root/'docs/agent-handoff.md').read_text(encoding='utf-8')
        blocks=text_blocks(handoff)
        if not blocks or blocks[0]!=prompt:
            issues.append('Agent handoff first text block differs from the exact canonical prompt')
        word=root/version['word']
        if word.exists():
            with ZipFile(word) as archive:
                check_word(archive,prompt,source)
        else:
            issues.append('Missing Word guide download')
for name in ['app/core.py','app/server.py','app/web/index.html','app/web/app.js','app/web/style.css','LICENSE','SECURITY.md','启动检测.cmd','start.sh']:
    if not (root/name).is_file():issues.append('Missing required file: '+name)
if issues:
    print('\n'.join(issues));sys.exit(1)
print(f'PASS: source inventory ({sum(len(s["files"]) for s in manifest["sources"])} files), licenses, module checksums, application files, document links, exact agent prompts, Word build fingerprint and cached TOC')
