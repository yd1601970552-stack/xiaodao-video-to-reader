"""构建可安装 ZIP，仅纳入公开资源。"""
import hashlib
import json
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parent.parent
manifest = json.loads((root / 'vendor-manifest.json').read_text(encoding='utf-8'))
for item in manifest:
    actual = hashlib.sha256((root / item['local']).read_bytes()).hexdigest()
    if actual != item['sha256']:
        raise SystemExit('第三方文件校验失败：' + item['local'])
allowed = ['SKILL.md', 'README.md', 'LICENSE', 'THIRD_PARTY_NOTICES.md',
           'VALIDATION.md', 'RELEASE_NOTES.md', 'vendor-manifest.json', 'requirements.txt', '.gitignore']
files = [root / name for name in allowed]
for folder in ['assets', 'vendor', 'references', 'scripts', 'examples']:
    files.extend(p for p in (root / folder).rglob('*') if p.is_file()
                 and '__pycache__' not in p.parts and '.bak-' not in p.name)
dest = root.parent / 'xiaodao-video-to-reader-v0.1.1.zip'
with zipfile.ZipFile(dest, 'w', zipfile.ZIP_DEFLATED) as archive:
    for file in files:
        archive.write(file, str(Path('xiaodao-video-to-reader') / file.relative_to(root)))
print(f'PASS：{len(manifest)} 个上游文件校验一致；{len(files)} 个发布文件；{dest}')
