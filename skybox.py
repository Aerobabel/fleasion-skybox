"""Portable Crossroads skybox profile and byte-level verification."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import ssl
import struct
import sys
import urllib.parse
import urllib.request
import zlib

ROOT = Path(__file__).resolve().parent
NAME = 'Crossroads-Diagnostic-Sky'
IDS = {'Bk': 1013852, 'Dn': 1013853, 'Lf': 1013851,
       'Rt': 1013849, 'Ft': 1013850, 'Up': 1013854}
COLORS = {'Bk': (235, 60, 180), 'Dn': (180, 80, 240),
          'Lf': (40, 210, 210), 'Rt': (240, 150, 35),
          'Ft': (80, 210, 80), 'Up': (60, 120, 240)}

def digest(data):
    return hashlib.sha256(data).hexdigest()

def texture(face):
    """Deterministic 256px RGB calibration grid; no external image dependency."""
    def chunk(kind, data):
        return (struct.pack('>I', len(data)) + kind + data
                + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff))
    rows = bytearray()
    color = COLORS[face]
    for y in range(256):
        rows.append(0)
        for x in range(256):
            factor = 1 if ((x // 32 + y // 32) % 2) else .55
            rows.extend(int(c * factor) for c in color)
    return (b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', struct.pack('>IIBBBBB', 256, 256, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(rows, 9)) + chunk(b'IEND', b''))

def profile():
    return {'replacement_rules': [
        {'name': 'Crossroads Skybox' + face, 'replace_ids': [asset],
         'mode': 'local', 'local_path': f'/{NAME}/{face}.png', 'enabled': True}
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

def verify(directory):
    for relative, expected in files().items():
        path = directory / relative
        if not path.is_file() or digest(path.read_bytes()) != digest(expected):
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
    verify(destination)
    owned = {destination / name for name in files()}
    if set((destination / NAME).rglob('*')) != {p for p in owned if p.suffix == '.png'}:
        raise ValueError('Asset folder contains additional files; refusing to remove it.')
    for path in owned:
        path.unlink()
    (destination / NAME).rmdir()

def check_installed(home):
    hashes = verify(home / 'configs')
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
