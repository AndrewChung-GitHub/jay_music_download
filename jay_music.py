import os
import re

import requests

GIST_OWNER = 'lvyueyang'
GIST_ID = 'cb11eaafbe69fc7ba63c38f9ff40e0d9'
GIST_FILE = 'jay-music.json'
GIST_REVISION = '43dc5d6193faca67908865c543a978d65ae8880c'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_DIR = os.path.join(BASE_DIR, 'jay_music')

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0'})


def gist_raw_url(revision=None):
    url = f'https://gist.githubusercontent.com/{GIST_OWNER}/{GIST_ID}/raw'
    if revision:
        url += f'/{revision}'
    return f'{url}/{GIST_FILE}'


def load_songs():
    for url in (gist_raw_url(GIST_REVISION), gist_raw_url()):
        try:
            resp = session.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except (requests.RequestException, ValueError) as exc:
            print(f'读取失败: {url}\n  {exc}')
            continue

        songs = data.get('list') or []
        songs = [s for s in songs if s.get('songInfo', {}).get('flac')]
        print(f'{url}\n  共 {len(data.get("list") or [])} 首, 其中有 flac 直链 {len(songs)} 首')
        if songs:
            return songs
        print('  这个版本里没有 flac 字段, 换下一个数据源...')
    return []


def safe_filename(name):
    name = re.sub(r'[\\/:*?"<>|\r\n\t]', '_', name).strip().rstrip('.')
    return name or 'unknown'


def download_file(url, path):
    tmp = path + '.part'
    with session.get(url, stream=True, timeout=60) as resp:
        resp.raise_for_status()
        with open(tmp, 'wb') as fp:
            for chunk in resp.iter_content(chunk_size=256 * 1024):
                if chunk:
                    fp.write(chunk)
    os.replace(tmp, path)


def main(limit=None):
    songs = load_songs()
    if not songs:
        print('没有可下载的曲目, 数据源可能已失效。')
        return 1

    os.makedirs(SAVE_DIR, exist_ok=True)
    used_names = {}
    ok = skipped = failed = 0

    for index, music in enumerate(songs, 1):
        if limit and ok >= limit:
            break

        base = safe_filename(music.get('name', ''))
        used_names[base] = used_names.get(base, 0) + 1
        if used_names[base] > 1:
            base = f'{base}_{used_names[base]}'
        path = os.path.join(SAVE_DIR, f'{base}-周杰伦.flac')

        if os.path.exists(path) and os.path.getsize(path) > 0:
            skipped += 1
            print(f'[{index}/{len(songs)}] 已存在, 跳过: {base}')
            continue

        try:
            download_file(music['songInfo']['flac'], path)
            ok += 1
            print(f'[{index}/{len(songs)}] 完成: {base}')
        except requests.RequestException as exc:
            failed += 1
            print(f'[{index}/{len(songs)}] 失败: {base} -> {exc}')

    print(f'\n完成 {ok} 首, 跳过 {skipped} 首, 失败 {failed} 首。目录: {SAVE_DIR}')
    return 0 if failed == 0 else 2


if __name__ == '__main__':
    raise SystemExit(main())
