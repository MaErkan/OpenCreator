"""Prepare the supplied Remotion film and approved Higgsfield assets."""
import argparse, hashlib, json, os, pathlib, re, subprocess, urllib.request, zipfile
BASE = pathlib.Path(__file__).resolve().parent

def download(url, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=180) as src, path.open('wb') as out:
        while chunk := src.read(1024 * 1024):
            out.write(chunk)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=pathlib.Path)
    parser.add_argument('--output', type=pathlib.Path, default=BASE / 'project')
    parser.add_argument('--skip-media', action='store_true')
    args = parser.parse_args()
    manifest = json.loads((BASE / 'assets.json').read_text())
    archive = args.source or BASE / 'source.zip'
    if not args.source:
        source_url = os.environ.get('IHYAA_SOURCE_URL')
        if not source_url:
            raise RuntimeError('Supply --source or configure IHYAA_SOURCE_URL privately in Actions secrets')
        download(source_url, archive)
    if not args.skip_media:
        media_urls = json.loads(os.environ.get('IHYAA_MEDIA_URLS', '{}'))
        missing = [shot['shot_id'] for shot in manifest['shots'] if shot['shot_id'] not in media_urls]
        if missing:
            raise RuntimeError('Configure IHYAA_MEDIA_URLS privately for all six approved clips')
    if hashlib.sha256(archive.read_bytes()).hexdigest() != manifest['source_sha256']:
        raise RuntimeError('Source archive hash mismatch')
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        for item in z.infolist():
            if not (root / item.filename).resolve().is_relative_to(root):
                raise RuntimeError('Unsafe archive member')
        z.extractall(root)
    config = root / 'src/config.ts'
    text = config.read_text().replace('subtitles: true,', 'subtitles: false,').replace('music: true,', 'music: false,')
    config.write_text(text)
    assets = root / 'src/data/assets.ts'
    overrides = {s['shot_id']: {'video': 'shots/' + s['shot_id'] + '.mp4'} for s in manifest['shots']}
    text = assets.read_text()
    old = 'export const SHOT_ASSETS: Record<string, ShotAsset> = {};'
    assert text.count(old) == 1
    assets.write_text(text.replace(old, 'export const SHOT_ASSETS: Record<string, ShotAsset> = ' + json.dumps(overrides, indent=2) + ';'))
    # SFX and optional voice tracks are disabled at component level as well as --muted export.
    view = root / 'src/components/ShotView.tsx'
    text = view.read_text()
    text, count = re.subn(r'      \{/\* الصوت \*/\}.*?(?=      <AbsoluteFill style=\{\{ background: "#000")', '', text, flags=re.S)
    assert count == 1
    view.write_text(text)
    if not args.skip_media:
        for shot in manifest['shots']:
            path = root / 'public/shots' / (shot['shot_id'] + '.mp4')
            raw = path.with_suffix('.source.mp4')
            download(media_urls[shot['shot_id']], raw)
            subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(raw), '-map', '0:v:0', '-an', '-c:v', 'copy', str(path)], check=True)
            raw.unlink()
    (root / 'silent-props.json').write_text(json.dumps({'music': False, 'subtitles': False, 'closeUpMode': 'portrait'}))
    print('Prepared 84-shot film with 6 approved Higgsfield clips and silent export settings:', root)

if __name__ == '__main__':
    main()
