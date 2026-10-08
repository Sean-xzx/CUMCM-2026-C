"""Check live documentation links, bilingual examples and entry-point help."""
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
FILES=[ROOT/'README.md',ROOT/'README.zh-CN.md',*(ROOT/'docs').glob('*.md')]
errors=[]
for path in FILES:
    text=path.read_text(encoding='utf-8')
    for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',text):
        target=target.split('#',1)[0].strip('<>')
        if not target or re.match(r'^[a-z]+://',target):continue
        if not (path.parent/target).exists():errors.append(f'{path.relative_to(ROOT)}: missing {target}')
en=(ROOT/'README.md').read_text(encoding='utf-8')
zh=(ROOT/'README.zh-CN.md').read_text(encoding='utf-8')
blocks=lambda text:re.findall(r'```(?:powershell|json|text)\n(.*?)```',text,re.S)
en_blocks,zh_blocks=blocks(en),blocks(zh)
# The architecture tree is translated; all commands, input layout and demo output
# must stay identical. The tree is the last text block, so omit it from this check.
if en_blocks[:-1]!=zh_blocks[:-1]:errors.append('Bilingual commands/output/resource layout differ')
for expected in ['3.12.14','1e-4','A0=0.6, ALO=0.7, AHI=0.9','13,854,618.279093','--select-q3']:
    if expected not in en or expected not in zh:errors.append('Bilingual expected value missing: '+expected)
for cmd in [[],['demo','--help'],['reproduce','--help'],['check-resources','--help'],['verify','--help']]:
    # Root invocation uses --help to avoid the intentional missing-subcommand error.
    result=subprocess.run([sys.executable,str(ROOT/'scripts/run.py'),*(cmd or ['--help'])],capture_output=True,text=True,encoding='utf-8')
    if result.returncode:errors.append('CLI help failed: '+repr(cmd))
if errors:raise SystemExit('\n'.join(errors))
print('Documentation links, bilingual commands/values and CLI help passed.')
