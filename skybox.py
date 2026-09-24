"""Portable Crossroads MIRA skybox profile and byte-level verification."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import ssl
import sys
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parent
NAME = 'Crossroads-Mira-Sky'
ARTWORK_REVISION = 'ade9b7cebea074bf6e68fa8cfe3417eb556ef621'
CDN_BASE = (f'https://raw.githubusercontent.com/Aerobabel/fleasion-skybox/'
            f'{ARTWORK_REVISION}/bundle/{NAME}')
IDS = {'Bk': 12221870, 'Dn': 12221876, 'Lf': 12221895,
       'Rt': 12221908, 'Ft': 12221889, 'Up': 12221917}
TEXTURE_SHA256 = {
    'Bk': '570f3086a5cd1120fc82ece896bda589e91452459f561b2bb565144d50c529e6',
    'Dn': '80ace0e89d6efb5ba7bb8aea13bf8fccbc3ff690dba025a8a1e648d660f469a2',
    'Lf': '8a6b653be2f8c8f557fbbc0ecebce2b5fb69b15b4e20603f802d83ee39928628',
    'Rt': '42c0c83a3d3fd09df252be1b99960e2aa076312d84b9919bc8b18db25c0dcf59',
    'Ft': 'c652c553bddb7123bf681af9230e1d5c0a3fd03b890ce2270d34772a075b284a',
    'Up': '6d55796fb8b3578e5d7faa7f181fcfa4491e1a7e6695f455187424dc0fc840be',
}

def digest(data):
    return hashlib.sha256(data).hexdigest()

def texture(face):
    """Read an authored face and verify it against the committed digest."""
    data = (ROOT / 'bundle' / NAME / f'{face}.png').read_bytes()
    if digest(data) != TEXTURE_SHA256[face]:
        raise ValueError(f'Bundled sky texture was modified: {face}.png')
    return data

def profile(mode='cdn'):
    if mode not in ('cdn', 'local'):
        raise ValueError(f'Unknown profile mode: {mode}')
    return {'replacement_rules': [
        {'name': 'Crossroads Skybox' + face, 'replace_ids': [asset],
         'mode': mode, 'enabled': True,
         **({'cdn_url': f'{CDN_BASE}/{face}.png'} if mode == 'cdn'
            else {'local_path': f'/{NAME}/{face}.png'})}
        for face, asset in IDS.items()]}

def files():
    result = {f'{NAME}/{f}.png': texture(f) for f in IDS}
    result[f'{NAME}.json'] = (json.dumps(profile(), indent=2) + '\n').encode()
    return result

def default_home():
    if sys.platform == 'win32':
        return Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local')) / 'FleasionNT'
    if sys.platform == 'darwin':
        return Path.home() / 'Library/Application Support/FleasionNT'
    return Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'Fleasion'

def build(destination):
    for relative, data in files().items():
        path = destination / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

def verify(directory, allow_legacy_local=False):
    for relative, expected in files().items():
        path = directory / relative
        if not path.is_file():
            raise ValueError(f'Missing or modified file: {relative}')
        actual = path.read_bytes()
        # Git's core.autocrlf converts the checked-out profile on Windows.
        # The PNGs still require an exact byte match.
        if relative.endswith('.json'):
            actual = actual.replace(b'\r\n', b'\n')
            if allow_legacy_local:
                # Keep verification/removal working for the already-tested local install.
                legacy = profile('local')
                if json.loads(actual) == legacy:
                    continue
        if digest(actual) != digest(expected):
            raise ValueError(f'Missing or modified file: {relative}')
    return {f: digest(texture(f)) for f in IDS}

def install(home):
    """Write only this profile. Refuse collisions; activate through Fleasion UI."""
    if not (home / 'settings.json').is_file():
        raise ValueError('Fleasion settings not found. Launch Fleasion once, then close it.')
    destination = home / 'configs'
    targets = [destination / f'{NAME}.json', destination / NAME]
    if any(p.exists() for p in targets):
        raise ValueError('Profile already exists. Verify it or uninstall it first; nothing overwritten.')
    build(destination)
    verify(destination)

def uninstall(home):
    destination = home / 'configs'
    verify(destination, allow_legacy_local=True)
    owned = {destination / name for name in files()}
    if set((destination / NAME).rglob('*')) != {p for p in owned if p.suffix == '.png'}:
        raise ValueError('Asset folder contains additional files; refusing to remove it.')
    for path in owned:
        path.unlink()
    (destination / NAME).rmdir()

def check_installed(home):
    hashes = verify(home / 'configs', allow_legacy_local=True)
    settings = json.loads((home / 'settings.json').read_text(encoding='utf-8-sig'))
    if NAME not in settings.get('enabled_configs', []):
        raise ValueError('Files are intact, but profile is not enabled in Fleasion Dashboard.')
    return hashes

def probe(home, ca, port):
    """Request public assets through Fleasion; require exact replacement bytes."""
    check_installed(home)
    context = ssl.create_default_context(cafile=str(ca))
    # Explicit set_proxy avoids environment NO_PROXY rules silently skipping Fleasion.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}),
                                        urllib.request.HTTPSHandler(context=context))
    def request(url, data=None):
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != 'https' or not (parsed.hostname == 'assetdelivery.roblox.com'
                or (parsed.hostname or '').endswith('.rbxcdn.com')):
            raise ValueError('Unexpected asset response host; refusing request.')
        req = urllib.request.Request(url, data=data, headers={
            'Content-Type': 'application/json', 'User-Agent': 'Roblox/WinInet'})
        req.set_proxy(f'127.0.0.1:{port}', 'http')
        with opener.open(req, timeout=30) as response:
            return response.read(16 * 1024 * 1024 + 1)
    results = {}
    for face, asset in IDS.items():
        body = json.dumps([{'requestId': face, 'assetId': asset}]).encode()
        entries = json.loads(request('https://assetdelivery.roblox.com/v1/assets/batch', body))
        if not isinstance(entries, list) or len(entries) != 1:
            raise ValueError(f'Unexpected batch response for {asset}')
        entry = entries[0]
        locations = entry.get('locations', [])
        location = locations[0].get('location') if locations else entry.get('location')
        if not location:
            raise ValueError(f'Asset {asset} unavailable: {entry.get("errors", "no location")}')
        received = request(location)
        if digest(received) != digest(texture(face)):
            raise ValueError(f'Asset {asset}: proxy did not return expected replacement bytes.')
        results[face] = {'asset_id': asset, 'sha256': digest(received), 'status': 'PASS'}
    return results

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['build', 'verify', 'install', 'uninstall', 'installed', 'probe'])
    parser.add_argument('--home', type=Path, default=default_home(), help='Fleasion data directory')
    parser.add_argument('--bundle', type=Path, default=ROOT / 'bundle', help='Portable configs directory')
    parser.add_argument('--ca', type=Path, help='Fleasion CA certificate PEM for TLS validation')
    parser.add_argument('--port', type=int, default=58443)
    args = parser.parse_args()
    try:
        if args.command == 'build':
            build(args.bundle)
            print('Built portable profile:', args.bundle)
        elif args.command == 'verify':
            print(json.dumps({'bundle': 'PASS', 'sha256': verify(args.bundle),
                              'live_game': 'NOT_TESTED'}, indent=2))
        elif args.command == 'install':
            verify(args.bundle)
            install(args.home)
            print(f'Installed. Enable {NAME} in Fleasion Dashboard; clear Roblox cache there.')
        elif args.command == 'uninstall':
            uninstall(args.home)
            print('Removed profile and its textures. Restart Fleasion.')
        elif args.command == 'installed':
            print(json.dumps({'installation': 'PASS', 'sha256': check_installed(args.home)}, indent=2))
        else:
            if args.ca is None or not 1 <= args.port <= 65535:
                raise ValueError('probe requires --ca PATH and a valid local proxy port.')
            print(json.dumps({'proxy': probe(args.home, args.ca, args.port),
                              'live_game_visual': 'NOT_TESTED'}, indent=2))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        return 1
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
