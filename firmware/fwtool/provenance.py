"""Source, host and toolchain identity beside a completed firmware image."""
import hashlib
import json
import os
import pathlib
import platform

from . import Failure, env, host, paths, process, toolchain, wled

GROUPS = ('core', 'firmware/usermod', 'firmware/usb_host_msc', 'firmware/newer', 'firmware/standalone', 'firmware/patches')
SOURCE_ENDINGS = {'.c', '.cpp', '.h', '.json', '.in', '.patch'}
IGNORED = {'build', '.pio', 'node_modules', '__pycache__', '.git'}


def digest(path):
    made = hashlib.sha256()
    with pathlib.Path(path).open('rb') as file:
        for block in iter(lambda:file.read(1 << 20),b''): made.update(block)
    return made.hexdigest()


def source_inputs(root=paths.ROOT):
    root = pathlib.Path(root)
    found = set()
    for group in GROUPS:
        directory = root.joinpath(*group.split('/'))
        for file in directory.rglob('*'):
            relative = file.relative_to(root)
            if file.is_file() and not (set(relative.parts) & IGNORED) and file.suffix in SOURCE_ENDINGS:
                found.add(file)
    for name in ('platformio_override.ini.in', 'requirements.txt', 'requirements-newer.txt'):
        file = root / 'firmware' / name
        if file.is_file(): found.add(file)
    hashes = {file.relative_to(root).as_posix():digest(file) for file in sorted(found)}
    total = hashlib.sha256()
    for name,value in hashes.items():
        total.update(name.encode('utf-8') + b'\0' + bytes.fromhex(value))
    return dict(sha256=total.hexdigest(),files=hashes)


def git_identity(root=paths.ROOT):
    def git(*args):
        result = process.run(['git','-C',str(root),*args],capture_output=True,text=True)
        if result.returncode:
            raise Failure('build-failed',f'cannot record source identity: {result.stderr.strip()[-300:]}')
        return result.stdout.strip()
    return dict(commit=git('rev-parse','HEAD'),trackedDirty=bool(git('status','--porcelain','--untracked-files=no')))


def package_identities(pio_root):
    found = []
    for category,filename in (('platforms','platform.json'),('packages','package.json')):
        parent = pathlib.Path(pio_root) / category
        for file in sorted(parent.glob('*/'+filename)):
            data = json.loads(file.read_text(encoding='utf-8'))
            found.append(dict(category=category,name=data.get('name',file.parent.name),
                              version=data.get('version'),manifestSha256=digest(file)))
    return found


def versions(newer):
    python = paths.NEWER_PYTHON if newer else paths.PYTHON
    venv = paths.NEWER_VENV if newer else paths.VENV
    def first(name, command):
        return toolchain._run(name,command,newer=newer).strip().splitlines()[0]
    return dict(python=first('Python',[python,'--version']),
                platformio=first('PlatformIO',[python,'-m','platformio','--version']),
                node=first('Node',[host.program(venv,'node'),'--version']),
                npm=first('npm',[host.program(venv,'npm'),'--version']))


def record(kind, environment, image, newer, root=paths.ROOT, pio_root=None):
    image = pathlib.Path(image)
    system, machine = host.supported()
    return dict(version=1,source=git_identity(root),host=dict(system=system,architecture=machine,os=platform.platform()),
                kind=kind,environment=environment,wled=dict(tag=wled.TAG,commit=wled.COMMIT),
                tools=versions(newer),packages=package_identities(pio_root or (paths.NEWER_PIO_CORE if newer else paths.PIO_CORE)),
                inputs=source_inputs(root),image=dict(file=image.name,bytes=image.stat().st_size,sha256=digest(image)),
                comparison='Source/configuration identity and image properties are compared; compiler paths, timestamps and ELF/application metadata can change binary bytes across hosts.')


def beside(image):
    image = pathlib.Path(image)
    return image.with_name(image.name+'.build.json')


def write(kind, environment, image, newer):
    target = paths.output(beside(image))
    data = record(kind,environment,image,newer)
    partial = paths.output(target.with_name(target.name+'.part'))
    try:
        partial.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
        os.replace(partial,target)
    finally:
        partial.unlink(missing_ok=True)
    return target
