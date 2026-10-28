"""What a build needs and the repository does not hold: the Capacitor packages, a JDK,
the Android SDK's command-line tools and the SDK packages. Each is fetched once, by its
exact version, and checked."""

import hashlib
import json
import os
import platform
import shutil
import stat
import subprocess
import sys
import tarfile
import urllib.error
import urllib.request
import zipfile

from . import Failure, env, paths, setuplock

OLDEST_NODE = 22
PIECE = 1 << 20


def read(path=paths.TOOLCHAIN):
    return json.loads(path.read_text(encoding="utf-8"))


def system():
    """This system and processor, as `toolchain.json` names them."""
    machine = {"aarch64": "arm64", "amd64": "x86_64"}.get(platform.machine().lower(), platform.machine().lower())
    return f"{sys.platform}-{machine}"


def archive_of(listed, name, on=None):
    """What `toolchain.json` says of an archive for this system: its address, its size and
    its SHA-256."""
    on = system() if on is None else on
    if on not in listed[name]:
        raise Failure("unsupported-platform", f"{paths.TOOLCHAIN} has no {name} for {on}")
    return listed[name][on]


def _run(what, command, reason="setup-failed", **settings):
    try:
        done = subprocess.run(command, capture_output=True, text=True, **settings)
    except OSError as error:
        raise Failure(reason, f"{what}: {error.strerror or type(error).__name__}") from None
    if done.returncode != 0:
        raise Failure(reason, f"{what} ended with status {done.returncode}: {(done.stdout + done.stderr).strip()[-600:]}")
    return done


def node_version():
    """The major version of `node`, which has to be new enough for Capacitor's command line."""
    program = shutil.which("node")
    if program is None:
        raise Failure("node-missing", f"node is not on the path; Capacitor's command line needs Node.js {OLDEST_NODE} or later")
    said = _run("node --version", [program, "--version"], "node-missing").stdout.strip()
    try:
        major = int(said.lstrip("v").split(".")[0])
    except ValueError:
        raise Failure("node-missing", f"node --version said {said!r}") from None
    if major < OLDEST_NODE:
        raise Failure("node-missing", f"node is {said}; Capacitor's command line needs Node.js {OLDEST_NODE} or later")
    return major


def fetched(archive, folder=paths.DOWNLOADS, opener=urllib.request.urlopen):
    """The path of an archive in the folder of downloads, fetched now when it is not
    there. A file with another size or SHA-256 than the tracked one is removed and
    refused, whether it was just fetched or lay there."""
    folder.mkdir(parents=True, exist_ok=True)
    kept = folder / archive["url"].rsplit("/", 1)[1]
    if not kept.is_file():
        part = kept.with_name(kept.name + ".part")
        try:
            with opener(archive["url"]) as answer, open(part, "wb") as file:
                shutil.copyfileobj(answer, file, PIECE)
        except (OSError, urllib.error.URLError) as error:
            part.unlink(missing_ok=True)
            if hasattr(error, "close"):
                error.close()
            raise Failure("download-failed", f"{archive['url']}: {getattr(error, 'reason', None) or error}") from None
        os.replace(part, kept)
    digest = hashlib.sha256()
    with open(kept, "rb") as file:
        for piece in iter(lambda: file.read(PIECE), b""):
            digest.update(piece)
    size = kept.stat().st_size
    if size != archive["bytes"] or digest.hexdigest() != archive["sha256"]:
        kept.unlink()
        raise Failure("checksum-mismatch", f"{kept.name} has {size} bytes and the SHA-256 {digest.hexdigest()}; {paths.TOOLCHAIN.name} names {archive['bytes']} bytes and {archive['sha256']}")
    return kept


def java_home(folder=paths.JDK):
    """The home of the JDK in the work folder: the folder that holds `bin/java`. None when
    there is none."""
    for found in sorted(folder.glob("*/Contents/Home")) + sorted(folder.glob("*")):
        if (found / "bin" / "java").is_file():
            return found
    return None


def unpacked_jdk(archive, folder=paths.JDK):
    """Unpacks the JDK's archive into the work folder and gives its home."""
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    with tarfile.open(archive) as packed:
        packed.extractall(folder, filter="tar")
    home = java_home(folder)
    if home is None:
        raise Failure("setup-failed", f"{archive.name} holds no bin/java")
    return home


def unpacked_tools(archive, sdk=paths.SDK):
    """Unpacks the command-line tools so that `cmdline-tools/latest/bin/sdkmanager` is in
    the SDK's folder, with the executable bits the archive has."""
    latest = sdk / "cmdline-tools" / "latest"
    shutil.rmtree(sdk / "cmdline-tools", ignore_errors=True)
    unpacking = sdk / "cmdline-tools.part"
    shutil.rmtree(unpacking, ignore_errors=True)
    unpacking.mkdir(parents=True)
    with zipfile.ZipFile(archive) as packed:
        for member in packed.infolist():
            written = packed.extract(member, unpacking)
            mode = member.external_attr >> 16
            if mode and not member.is_dir():
                os.chmod(written, stat.S_IMODE(mode))
    inner = unpacking / "cmdline-tools"
    if not (inner / "bin" / "sdkmanager").is_file():
        shutil.rmtree(unpacking, ignore_errors=True)
        raise Failure("setup-failed", f"{archive.name} holds no cmdline-tools/bin/sdkmanager")
    latest.parent.mkdir(parents=True)
    os.replace(inner, latest)
    shutil.rmtree(unpacking, ignore_errors=True)
    return latest


def package_folder(name, sdk=paths.SDK):
    """The folder of the SDK that holds a package: `platforms;android-36` is in
    `platforms/android-36`."""
    return sdk.joinpath(*name.split(";"))


def sdk_packages(listed, home, sdk=paths.SDK, manager=paths.SDK_MANAGER):
    """Installs the SDK packages of `toolchain.json`. The tool is given one `y`, the answer
    to the one licence the packages are under; afterwards that licence and no other must
    be accepted, and every package must be there."""
    names = listed["sdk-packages"]
    if not all(package_folder(name, sdk).is_dir() for name in names):
        _run("sdkmanager", [str(manager), f"--sdk_root={sdk}", *names], input="y\n", env=env.child(home))
    accepted = sorted(path.name for path in (sdk / "licenses").glob("*")) if (sdk / "licenses").is_dir() else []
    if accepted != [listed["licence"]]:
        raise Failure("licence-refused", f"the SDK holds the accepted licences {accepted}; the build accepts {listed['licence']} and no other")
    missing = [name for name in names if not package_folder(name, sdk).is_dir()]
    if missing:
        raise Failure("licence-refused", f"sdkmanager did not install {', '.join(missing)}")


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _record(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def _write_record(path, members):
    """Writes members into a setup record, keeping the others it has."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(_record(path), **members), indent=2) + "\n", encoding="utf-8")


def setup(out=sys.stdout):
    """Puts everything a build needs into `app/node_modules/`, the work folder and the shared
    toolchains. A step whose result is there is skipped, and a setup waits for another one
    that runs from another checkout."""
    node_version()
    listed = read()
    with setuplock.held(paths.SETUP_LOCK, waiting=lambda: print(f"waiting for another setup, which holds {paths.SETUP_LOCK}", file=out)):
        return _setup(listed, out)


def _setup(listed, out):
    lock, toolchain = _sha256(paths.LOCK), _sha256(paths.TOOLCHAIN)
    paths.WORK.mkdir(parents=True, exist_ok=True)

    if _record(paths.SETUP_RECORD).get("package-lock") != lock or not paths.CAPACITOR.is_file():
        _run("npm ci", ["npm", "ci", "--prefix", str(paths.APP)], env=env.child())
    _write_record(paths.SETUP_RECORD, {"package-lock": lock})

    current = _record(paths.SHARED_RECORD).get("toolchain") == toolchain
    home = java_home()
    if not current or home is None:
        home = unpacked_jdk(fetched(archive_of(listed, "jdk")))
    print(_run("java -version", [str(home / "bin" / "java"), "-version"]).stderr.splitlines()[0], file=out)

    if not current or not paths.SDK_MANAGER.is_file():
        unpacked_tools(fetched(archive_of(listed, "command-line-tools")))
    sdk_packages(listed, home)

    _write_record(paths.SHARED_RECORD, {"toolchain": toolchain})
    return home
