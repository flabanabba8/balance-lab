"""Compare two tunings using an isolated copy of the user's real simulation source."""
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import signal
import time
import shutil
import subprocess
import tempfile
import tomllib

PRIVATE = {'.ssh', '.gnupg', '.aws', '.azure', '.codex', '.docker', '.kube', '.pki', '.config', '.hermes'}


def chosen(value, directory=False):
    p = Path(value).expanduser()
    if not p.is_absolute() or p.is_symlink() or any(x in PRIVATE for x in p.parts):
        raise ValueError('Choose an absolute non-symlink path outside private configuration')
    p = p.resolve(strict=True)
    if any(x in PRIVATE for x in p.parts) or (not p.is_dir() if directory else not p.is_file()):
        raise ValueError('Selected source is not accessible')
    return p


def read_config(value):
    path = chosen(value)
    if path.suffix.lower() != '.ron' or path.stat().st_size > 1024 * 1024:
        raise ValueError('Select a RON tuning file no larger than 1 MiB')
    return path.read_bytes()


def copied_source(project, destination):
    sim = project / 'crates' / 'sim'
    manifest, lock = project / 'Cargo.toml', project / 'Cargo.lock'
    if not sim.is_dir() or not manifest.is_file() or not lock.is_file():
        raise ValueError('Expected a Packet Storm workspace with a simulation crate and Cargo.lock')
    if any(p.is_symlink() for p in (sim, manifest, lock)):
        raise ValueError('Symlinked project components are unsupported')
    files = []
    for root, dirs, names in os.walk(sim, followlinks=False):
        for name in dirs + names:
            if name in PRIVATE or name == '.git': raise ValueError('Private configuration and Git entries are unsupported')
            path = Path(root) / name
            if path.is_symlink(): raise ValueError('Symlinks in the simulation crate are unsupported')
        for name in names:
            path = Path(root) / name
            if not path.is_file(): raise ValueError('Special files are unsupported')
            files.append(path)
    if len(files) > 1000 or sum(p.stat().st_size for p in files) > 20 * 1024**2:
        raise ValueError('Simulation source exceeds copy limits')
    inputs = [manifest, lock, *sorted(files)]
    if any(p.stat().st_size > 8 * 1024**2 for p in inputs): raise ValueError('Source file exceeds copy limit')
    before = {p.relative_to(project).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    raw = manifest.read_text(encoding='utf-8')
    data = tomllib.loads(raw)
    if 'crates/sim' not in data.get('workspace', {}).get('members', []):
        raise ValueError('Selected workspace does not contain the expected simulation crate')
    start = re.search(r'^\[workspace\]\s*$', raw, re.M)
    if not start: raise ValueError('Workspace manifest is unsupported')
    stop = re.search(r'^\[', raw[start.end():], re.M)
    end = start.end() + stop.start() if stop else len(raw)
    section = raw[start.start():end]
    section, count = re.subn(r'^members\s*=.*$', 'members = ["crates/sim"]', section, count=1, flags=re.M)
    if count != 1: raise ValueError('Workspace member declaration is unsupported')
    section = re.sub(r'^default-members\s*=.*$', 'default-members = ["crates/sim"]', section, count=1, flags=re.M)
    (destination / 'Cargo.toml').write_text(raw[:start.start()] + section + raw[end:], encoding='utf-8')
    shutil.copyfile(lock, destination / 'Cargo.lock')
    shutil.copytree(sim, destination / 'crates' / 'sim')
    current_files = [p for p in sim.rglob('*') if p.is_file()]
    after = {p.relative_to(project).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in [manifest, lock, *sorted(current_files)]}
    copied = {key: hashlib.sha256((destination/key).read_bytes()).hexdigest() for key in before if key != 'Cargo.toml'}
    if before != after or any(before[key] != value for key, value in copied.items()):
        raise ValueError('Simulation source changed while copying')
    return hashlib.sha256(json.dumps(before, sort_keys=True).encode()).hexdigest()


def run_owned(command, cwd, env, timeout, capture=False):
    process = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE if capture else subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.monotonic() + timeout
    try:
        output = b''
        if capture:
            chunks, size = [], 0
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0 or not selector.select(remaining):
                        raise subprocess.TimeoutExpired(command, timeout)
                    chunk = os.read(process.stdout.fileno(), 4096)
                    if not chunk: break
                    size += len(chunk)
                    if size > 16384: raise RuntimeError('Simulation response exceeded its limit')
                    chunks.append(chunk)
            output = b''.join(chunks)
        if process.wait(timeout=max(.1, deadline - time.monotonic())):
            raise RuntimeError('Simulation build or run failed')
        return output
    finally:
        if process.poll() is None:
            try: os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            process.wait()
        if process.stdout is not None: process.stdout.close()


def packet_storm(project_path, baseline_tuning, candidate_tuning, seed, trials, max_seconds):
    if type(seed) is not int or not 1 <= seed <= 2**63-100 or type(trials) is not int or not 1 <= trials <= 10 or type(max_seconds) is not int or not 1 <= max_seconds <= 120:
        raise ValueError('Use a positive seed, 1–10 trials and a 1–120 second simulation cap')
    project = chosen(project_path, directory=True)
    baseline, candidate = read_config(baseline_tuning), read_config(candidate_tuning)
    cargo = shutil.which('cargo') or str(Path.home() / '.cargo' / 'bin' / 'cargo')
    if not Path(cargo).is_file(): raise ValueError('Cargo is required to build the local simulation bridge')
    with tempfile.TemporaryDirectory(prefix='balance-lab-', dir='/tmp') as temporary:
        sandbox = Path(temporary)
        source_hash = copied_source(project, sandbox)
        bridge = Path(__file__).with_name('packet_storm_bridge.rs')
        (sandbox/'crates'/'sim'/'examples').mkdir(exist_ok=True)
        shutil.copyfile(bridge, sandbox/'crates'/'sim'/'examples'/'hermes_balance.rs')
        (sandbox/'baseline.ron').write_bytes(baseline)
        (sandbox/'candidate.ron').write_bytes(candidate)
        env = {k: os.environ[k] for k in ('HOME','CARGO_HOME','RUSTUP_HOME','RUSTUP_TOOLCHAIN','LANG') if k in os.environ}
        env['PATH'] = str(Path(cargo).parent) + os.pathsep + os.defpath
        env['CARGO_TARGET_DIR'] = str(sandbox/'target')
        deadline = time.monotonic() + 55
        def remaining():
            value = deadline - time.monotonic()
            if value <= 0: raise RuntimeError('Simulation exceeded its time limit')
            return value
        try:
            run_owned([cargo, 'build', '--offline', '--release', '--jobs', '1', '-p', 'packet_storm_sim', '--example', 'hermes_balance'],
                      sandbox, env, remaining())
            program = sandbox/'target'/'release'/'examples'/'hermes_balance'
            results = []
            for name in ('baseline','candidate'):
                output = run_owned([str(program), str(sandbox/(name+'.ron')), str(seed), str(trials), str(max_seconds)],
                                   sandbox, env, remaining(), capture=True)
                rows = []
                for line in output.decode('ascii').splitlines():
                    parts = line.split(',')
                    if len(parts) != 5: raise RuntimeError('Simulation returned malformed results')
                    rows.append({'seed': int(parts[0]), 'elapsed': float(parts[1]), 'level': int(parts[2]), 'breaches': int(parts[3]), 'collateral': int(parts[4])})
                if [x['seed'] for x in rows] != list(range(seed, seed+trials)): raise RuntimeError('Simulation returned an incomplete seed set')
                results.append(rows)
        except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
            raise RuntimeError('Simulation build or run failed; no project files were intentionally modified') from exc
    return {'simulation_source_sha256': source_hash, 'baseline_sha256': hashlib.sha256(baseline).hexdigest(),
            'candidate_sha256': hashlib.sha256(candidate).hexdigest(), 'baseline': results[0], 'candidate': results[1],
            'paired_elapsed_difference': [b['elapsed'] - a['elapsed'] for a,b in zip(*results)],
            'notice': 'Runs an isolated source copy offline via Cargo. The bot stands still and chooses the first offered card; this is not a human playtest. Cargo build scripts are trusted code, not a network sandbox.'}
