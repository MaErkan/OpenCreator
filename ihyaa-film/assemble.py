"""Join ten rendered scenes and verify a complete silent 1080p output."""
import json, pathlib, subprocess, sys
root = pathlib.Path(sys.argv[1]).resolve()
clips = []
for scene in range(1, 11):
    matches = list(root.rglob(f'scene-{scene:02}.mp4'))
    if len(matches) != 1:
        raise RuntimeError(f'Expected one video for scene {scene}, found {len(matches)}')
    clip = matches[0]
    info = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(clip)]))
    assert all(s['codec_type'] != 'audio' for s in info['streams']), f'Unexpected audio: {clip}'
    video = next(s for s in info['streams'] if s['codec_type'] == 'video')
    assert (video['width'], video['height']) == (1920, 1080)
    assert float(info['format']['duration']) > 0
    clips.append(clip)
listing = root / 'scenes.txt'
listing.write_text(''.join(f"file '{p.as_posix()}'\n" for p in clips))
output = root / 'ihyaa-film-silent-fullhd.mp4'
subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', str(listing), '-c', 'copy', '-an', '-movflags', '+faststart', str(output)], check=True)
info = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(output)]))
assert not any(s['codec_type'] == 'audio' for s in info['streams'])
(root / 'verification.json').write_text(json.dumps(info, indent=2))
print(output)
