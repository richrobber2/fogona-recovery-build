#!/usr/bin/env python3
"""Audit staged recovery contents; does not claim hardware/loader compatibility."""
from pathlib import Path, PurePosixPath
import json
import os
import re
import struct
import subprocess
import sys

root = Path(sys.argv[1]).resolve()
errors = []
critical_elf_paths = {'init', 'system/bin/recovery', 'system/bin/sh'}

# Resolve links using Android's root instead of the runner's /system or /init.
def rooted(path):
    pending = list(PurePosixPath(path).parts)
    current = []
    hops = 0
    while pending:
        part = pending.pop(0)
        if part in ('/', '.'):
            continue
        if part == '..':
            if not current:
                raise ValueError('Path escapes ramdisk')
            current.pop()
            continue
        candidate = root.joinpath(*current, part)
        if candidate.is_symlink():
            hops += 1
            if hops > 40:
                raise ValueError('Symlink loop')
            target = os.readlink(candidate)
            if target.startswith('/'):
                current = []
            pending = list(PurePosixPath(target).parts) + pending
        else:
            current.append(part)
    return root.joinpath(*current)

required = ['init', 'system/bin/recovery', 'system/bin/sh', 'system/bin/twrp',
            'system/bin/keystore2', 'system/bin/fscryptpolicyget',
            'system/bin/device-rescue.sh', 'system/etc/recovery.fstab',
            'system/etc/task_profiles.json']
if len(sys.argv) > 3:
    if sys.argv[3:] != ['--require-logging']:
        raise SystemExit('Unknown audit options')
    required += ['system/bin/logd', 'system/bin/logcat',
                 'system/bin/recovery-logsave.sh', 'init.recovery.logd.rc']
    critical_elf_paths.update({'system/bin/logd', 'system/bin/logcat'})
for name in required:
    path = rooted(name)
    if not path.is_file() or path.stat().st_size == 0:
        errors.append('Missing required ramdisk file: ' + name)
    elif name == 'init' or name.startswith('system/bin/'):
        if not path.stat().st_mode & 0o111:
            errors.append('Required executable lacks execute bits: ' + name)

elfs = []
libraries = set()
for parent, dirs, files in os.walk(root):
    for name in files:
        logical = (Path(parent) / name).relative_to(root).as_posix()
        try:
            path = rooted(logical)
            if not path.is_file():
                continue
            with path.open('rb') as stream:
                header = stream.read(20)
            if header[:4] != b'\x7fELF':
                if logical in critical_elf_paths:
                    errors.append('Critical program is not ELF: ' + logical)
                continue
            key = (header[4], struct.unpack('<H' if header[5] == 1 else '>H', header[18:20])[0])
            if key not in {(2, 183), (1, 40)}:
                errors.append(f'{logical}: unexpected ELF architecture {key}')
            if logical in critical_elf_paths and key != (2, 183):
                errors.append(f'{logical}: critical program must be ARM64')
            libraries.add((name, key))
            elfs.append((logical, path, key))
        except (OSError, ValueError) as exc:
            errors.append(f'{logical}: {exc}')
records = []
for logical, path, key in elfs:
    result = subprocess.run(['readelf', '-d', '-l', str(path)], text=True, capture_output=True, check=True)
    needed = re.findall(r'\(NEEDED\).*?\[(.*?)\]', result.stdout)
    interpreters = re.findall(r'Requesting program interpreter:\s*(.*?)\]', result.stdout)
    missing = [name for name in needed if (name, key) not in libraries]
    for interpreter in interpreters:
        if not rooted(interpreter).is_file():
            missing.append(interpreter)
    if missing:
        errors.append(f'{logical}: unresolved dependencies: {", ".join(missing)}')
    records.append({'path': logical, 'elf_class_machine': key, 'needed': needed, 'interpreters': interpreters, 'missing': missing})
report = {'scope': 'Staged files and ELF name/architecture closure only; Android linker namespaces, vendor HALs, AVB, boot, touch and decryption require further validation.', 'required': required, 'elfs': records, 'errors': errors}
Path(sys.argv[2]).write_text(json.dumps(report, indent=2) + '\n')
if errors:
    raise SystemExit('\n'.join(errors))
print(f'Ramdisk contains required tools; dependency-name/architecture closure passed for {len(elfs)} ELF entries.')
