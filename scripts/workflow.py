"""Agent 入口：prepare URL；deliver episode.json source.json [--output-dir DIR]。"""
import argparse
import ctypes
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def reader_home(override=None):
    if override:
        return Path(override)
    return Path(os.environ.get('LOCALAPPDATA', str(Path.home() / '.local/share'))) / 'Xiaodao' / 'HTMLReader'


def reader_status(home):
    state_path = home / 'install-state.json'
    state = json.loads(state_path.read_text(encoding='utf-8')) if state_path.exists() else {}
    target = home / 'index.html'
    installed = target.exists()
    return {'installed': installed, 'declined': state.get('declined', False),
            'reader': str(target) if installed else None,
            'shortcut': state.get('shortcut'),
            'shortcut_exists': bool(state.get('shortcut') and Path(state['shortcut']).exists()),
            'update_available': installed and hashlib.sha256(target.read_bytes()).hexdigest() !=
            hashlib.sha256((ROOT / 'assets/reader/index.html').read_bytes()).hexdigest()}


def install_reader(home, desk, confirmed):
    if not confirmed:
        raise RuntimeError('必须先取得用户安装确认，再传入 --confirmed')
    if os.name != 'nt':
        raise RuntimeError('桌面快捷方式安装目前仅支持 Windows；其他系统可直接打开内置阅读器')
    home.mkdir(parents=True, exist_ok=True)
    target = home / 'index.html'
    new = (ROOT / 'assets/reader/index.html').read_bytes()
    if target.exists() and target.read_bytes() != new:
        backup = home / ('reader-backup-' + hashlib.sha256(target.read_bytes()).hexdigest()[:12] + '.html')
        if not backup.exists():
            shutil.copy2(target, backup)
    # 固定阅读器路径，避免更新版本后因 file:// 地址变化而分离批注存储。
    if not target.exists() or target.read_bytes() != new:
        target.write_bytes(new)
    shutil.copy2(ROOT / 'assets/reader-icon.ico', home / 'reader-icon.ico')
    desk.mkdir(parents=True, exist_ok=True)
    shortcut = desk / '阅·批注.lnk'
    n = 2
    while shortcut.exists():
        # 只复用本安装器登记的入口，保留用户原有同名快捷方式。
        state_path = home / 'install-state.json'
        state = json.loads(state_path.read_text(encoding='utf-8')) if state_path.exists() else {}
        if state.get('shortcut') == str(shortcut):
            break
        shortcut = desk / f'阅·批注_{n}.lnk'
        n += 1
    ps = "$w=New-Object -ComObject WScript.Shell;$s=$w.CreateShortcut($env:READER_SHORTCUT);$s.TargetPath=$env:READER_TARGET;$s.IconLocation=$env:READER_ICON;$s.Description='HTML 阅读与批注';$s.Save()"
    env = os.environ.copy()
    env.update(READER_SHORTCUT=str(shortcut.resolve()), READER_TARGET=str(target.resolve()),
               READER_ICON=str((home / 'reader-icon.ico').resolve()))
    subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', ps], env=env, check=True, capture_output=True)
    (home / 'install-state.json').write_text(json.dumps({'declined': False, 'shortcut': str(shortcut)}, ensure_ascii=False), encoding='utf-8')
    return {'reader': str(target), 'shortcut': str(shortcut)}


def desktop():
    if os.name == 'nt':
        buf = ctypes.create_unicode_buffer(32768)
        if ctypes.windll.shell32.SHGetFolderPathW(None, 0x10, None, 0, buf) != 0:
            raise RuntimeError('无法识别桌面，请指定 --output-dir')
        return Path(buf.value)
    return Path.home() / 'Desktop'


def exclusive(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as f:
        f.write(content)


def render(episode, source):
    if not episode.get('title') or not episode.get('original_title'):
        raise ValueError('必须提供中文 title 和英文 original_title')
    if not re.search(r'[\u3400-\u9fff]', episode['title']):
        raise ValueError('主标题必须翻译为中文')
    if episode['url'] != source['url'] or not re.fullmatch(r'https://www\.youtube\.com/watch\?v=[\w-]{11}', source['url']):
        raise ValueError('来源网址无效或不一致')
    if not source.get('segments') or not episode.get('sections'):
        raise ValueError('来源或章节为空')
    cursor = 0
    sections = []
    esc = html.escape
    for i, section in enumerate(episode['sections'], 1):
        if not section.get('title') or not section.get('paragraphs'):
            raise ValueError('章节为空')
        paragraphs = []
        for p in section['paragraphs']:
            if not p.get('zh', '').strip() or not p.get('source_ids'):
                raise ValueError('译文或来源 ID 缺失')
            refs = source['segments'][cursor:cursor + len(p['source_ids'])]
            if [s['id'] for s in refs] != p['source_ids']:
                raise ValueError('来源遗漏、重复或乱序')
            cursor += len(refs)
            if p['en'] != ' '.join(s['text'] for s in refs):
                raise ValueError('英文与来源字幕不一致')
            seconds = int(refs[0]['start'])
            stamp = f'{seconds // 60}:{seconds % 60:02d}'
            ad = ' class="ad"' if p.get('ad') else ''
            tag = ' · 广告' if p.get('ad') else ''
            paragraphs.append(f'<article{ad}><div class="who">{esc(p.get("speaker") or "说话人未确认")} · {stamp}{tag}</div><p class="zh">{esc(p["zh"])}</p><p class="en" lang="en">{esc(p["en"])}</p></article>')
        sections.append(f'<section id="s{i}"><h2>{i:02d} {esc(section["title"])}</h2>' + '\n'.join(paragraphs) + '</section>')
    if cursor != len(source['segments']):
        raise ValueError('字幕未完整覆盖')
    values = {'TITLE': esc(episode['title']), 'ORIGINAL_TITLE': esc(episode['original_title']),
              'URL': esc(source['url']), 'BODY': '\n'.join(sections),
              'TOC': ''.join(f'<a href="#s{i}">{esc(s["title"])}</a>' for i, s in enumerate(episode['sections'], 1)),
              'NOTES': esc('；'.join(episode.get('notes', [])))}
    template = (ROOT / 'assets/template.html').read_text(encoding='utf-8')
    result = re.sub(r'\{\{(TITLE|ORIGINAL_TITLE|URL|BODY|TOC|NOTES)\}\}', lambda m: values[m[1]], template)
    return result, cursor


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    prepare = sub.add_parser('prepare')
    prepare.add_argument('url')
    prepare.add_argument('--proxy')
    prepare.add_argument('--work-dir')
    prepare.add_argument('--install-deps', action='store_true')
    deliver = sub.add_parser('deliver')
    deliver.add_argument('episode')
    deliver.add_argument('source')
    deliver.add_argument('--output-dir')
    deliver.add_argument('--desktop-dir', help=argparse.SUPPRESS)
    status = sub.add_parser('reader-status')
    status.add_argument('--install-dir', help=argparse.SUPPRESS)
    installer = sub.add_parser('install-reader')
    installer.add_argument('--confirmed', action='store_true')
    installer.add_argument('--install-dir', help=argparse.SUPPRESS)
    installer.add_argument('--desktop-dir', help=argparse.SUPPRESS)
    decline = sub.add_parser('decline-reader')
    decline.add_argument('--install-dir', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.action == 'reader-status':
        print(json.dumps(reader_status(reader_home(args.install_dir)), ensure_ascii=False))
    elif args.action == 'install-reader':
        print(json.dumps(install_reader(reader_home(args.install_dir), Path(args.desktop_dir) if args.desktop_dir else desktop(), args.confirmed), ensure_ascii=False))
    elif args.action == 'decline-reader':
        home = reader_home(args.install_dir)
        home.mkdir(parents=True, exist_ok=True)
        (home / 'install-state.json').write_text('{"declined":true}', encoding='utf-8')
        print('已记录暂不安装，不再重复提示；用户可随时要求安装。')
    elif args.action == 'prepare':
        work = Path(args.work_dir) if args.work_dir else ROOT / 'work' / hashlib.sha256(args.url.encode()).hexdigest()[:12]
        source = work / 'source.json'
        if source.exists():
            cached = json.loads(source.read_text(encoding='utf-8'))
            if not cached.get('segments'):
                raise RuntimeError('缓存为空，请指定新的 --work-dir')
            print(json.dumps({'source': str(source), 'cached': True}, ensure_ascii=False))
            return
        env = ROOT / '.venv'
        python = env / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        if not python.exists():
            if not args.install_deps:
                raise RuntimeError('缺少独立运行环境，授权后使用 --install-deps')
            subprocess.run([sys.executable, '-m', 'venv', str(env)], check=True)
        check = subprocess.run([str(python), '-c', 'import youtube_transcript_api'], capture_output=True)
        if check.returncode:
            if not args.install_deps:
                raise RuntimeError('缺少字幕依赖，授权后使用 --install-deps')
            subprocess.run([str(python), '-m', 'pip', 'install', '-r', str(ROOT / 'requirements.txt')], check=True)
        command = [str(python), str(ROOT / 'scripts/fetch_transcript.py'), args.url, '--output', str(source)]
        if args.proxy:
            command += ['--proxy', args.proxy]
        subprocess.run(command, check=True)
        print(json.dumps({'source': str(source), 'work_dir': str(work)}, ensure_ascii=False))
    else:
        episode = json.loads(Path(args.episode).read_text(encoding='utf-8'))
        source = json.loads(Path(args.source).read_text(encoding='utf-8'))
        content, count = render(episode, source)
        desk = Path(args.desktop_dir) if args.desktop_dir else desktop()
        folder = Path(args.output_dir) if args.output_dir else desk
        folder.mkdir(parents=True, exist_ok=True)
        basename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', episode['title']).strip(' .')[:70] or '双语阅读稿'
        if basename.upper() in ('CON', 'PRN', 'AUX', 'NUL') or re.fullmatch(r'(COM|LPT)[1-9]', basename.upper()):
            basename = '_' + basename
        output = folder / (basename + '_中英对照.html')
        number = 2
        while output.exists():
            output = folder / f'{basename}_中英对照_{number}.html'
            number += 1
        exclusive(output, content)
        print(json.dumps({'html': str(output), 'reader': reader_status(reader_home())['reader'], 'segments': count,
                          'verification': '字幕完整覆盖、英文一致；语义准确性须由 Agent 审校'}, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'失败：{error}', file=sys.stderr)
        sys.exit(1)
