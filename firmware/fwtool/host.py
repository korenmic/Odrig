"""Host identities and executable layouts for isolated firmware toolchains."""
import pathlib
import platform
import sys

from . import Failure

SUPPORTED = {('win32', 'x86_64'), ('darwin', 'arm64'), ('darwin', 'x86_64'),
             ('linux', 'x86_64'), ('linux', 'arm64')}


def identity(system=None, machine=None):
    system = sys.platform if system is None else system
    machine = platform.machine() if machine is None else machine
    machine = {'amd64': 'x86_64', 'aarch64': 'arm64'}.get(machine.lower(), machine.lower())
    return system, machine


def supported(system=None, machine=None):
    found = identity(system, machine)
    if found not in SUPPORTED:
        raise Failure('unsupported-platform', f'no pinned firmware toolchain for {found[0]}-{found[1]}')
    return found


def tool_root(shared, system=None, machine=None):
    system, machine = identity(system, machine)
    shared = pathlib.Path(shared)
    return shared if system == 'darwin' else shared / 'hosts' / f'{system}-{machine}'


def scripts(venv, system=None):
    system = sys.platform if system is None else system
    return pathlib.Path(venv) / ('Scripts' if system == 'win32' else 'bin')


def program(venv, name, system=None):
    system = sys.platform if system is None else system
    return scripts(venv, system) / (name + ('.exe' if system == 'win32' else ''))


def config_path(folder):
    """A complete INI path; individual compiler arguments are quoted by the template."""
    value = pathlib.Path(folder).resolve().as_posix()
    if any(c in value for c in ('\r','\n','\0','"')):
        raise Failure('build-failed', 'a build path contains a character not representable in its configuration')
    return value
