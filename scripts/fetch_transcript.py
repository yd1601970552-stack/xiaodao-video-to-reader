"""python fetch_transcript.py URL --output source.json [--proxy http://host:port]"""
import argparse
import json
import re
import time
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from urllib.request import build_opener, ProxyHandler, Request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('url')
    parser.add_argument('--output', required=True)
    parser.add_argument('--proxy')
    args = parser.parse_args()
    url = urlparse(args.url)
    if url.hostname in ('youtu.be', 'www.youtu.be'):
        vid = url.path.strip('/')
    elif url.hostname in ('youtube.com', 'www.youtube.com', 'm.youtube.com') and url.path == '/watch':
        vid = parse_qs(url.query).get('v', [''])[0]
    else:
        parser.error('请提供 YouTube watch 链接或 youtu.be 单视频链接')
    if not re.fullmatch(r'[A-Za-z0-9_-]{11}', vid):
        parser.error('视频 ID 无效')
    output = Path(args.output)
    if output.exists():
        parser.error('输出已存在，请使用新路径')
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api.proxies import GenericProxyConfig
    kwargs = {}
    if args.proxy:
        kwargs['proxy_config'] = GenericProxyConfig(http_url=args.proxy, https_url=args.proxy)
    api = YouTubeTranscriptApi(**kwargs)
    for attempt in range(3):
        try:
            tracks = [t for t in api.list(vid) if t.language_code.startswith('en')]
            tracks.sort(key=lambda t: (t.is_generated, t.language_code != 'en'))
            if not tracks:
                raise SystemExit('没有可获取的英文字幕；停止，不生成稿件')
            track = tracks[0]
            transcript = track.fetch()
            break
        except Exception as error:
            if attempt == 2:
                raise SystemExit('字幕获取失败：' + type(error).__name__ + '；检查网络或字幕可用性')
            time.sleep(3 * (attempt + 1))
    result = {'video_id': vid, 'url': 'https://www.youtube.com/watch?v=' + vid,
              'language': track.language_code, 'generated': track.is_generated,
              'segments': [{'id': i + 1, 'start': s.start, 'duration': s.duration, 'text': s.text}
                           for i, s in enumerate(transcript)]}
    try:
        handler = ProxyHandler({'http': args.proxy, 'https': args.proxy}) if args.proxy else ProxyHandler()
        opener = build_opener(handler)
        metadata_url = 'https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=' + vid + '&format=json'
        with opener.open(Request(metadata_url, headers={'User-Agent': 'podcast-to-bilingual-html/0.1'}), timeout=15) as response:
            metadata = json.load(response)
        result['original_title'] = metadata.get('title', '')
        result['author'] = metadata.get('author_name', '')
    except Exception:
        result['metadata_status'] = 'unavailable: Agent must verify original title from public video information'
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as file:
        json.dump(result, file, ensure_ascii=False, indent=2)
    print(f'完成：{len(result["segments"])} 段字幕；{output}')


if __name__ == '__main__':
    main()
