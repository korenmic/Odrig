"""The network's name and password: a settings file read and checked, and WLED's two
settings files edited in a storage image."""

import copy
import json

from littlefs.errors import LittleFSError

from . import Failure, paths, settingsfile, storage

# WLED's stored settings: the name is in the first, the password in the second.
CONFIG = "/cfg.json"
SECRETS = "/wsec.json"
ACCESS_POINT = "ap"

MEMBERS = ("name", "password")
NAME_CHARACTERS = (1, 32)
PASSWORD_CHARACTERS = (8, 63)
# Printable ASCII: with it a character is a byte, which is what the radio counts.
PRINTABLE = (0x20, 0x7E)


class Settings:
    """A name and a password. Its text form does not show the password."""

    def __init__(self, name, password):
        self.name = name
        self.password = password

    def __eq__(self, other):
        return isinstance(other, Settings) and (self.name, self.password) == (other.name, other.password)

    def __hash__(self):
        return hash((self.name, self.password))

    def __repr__(self):
        return f"Settings(name={self.name!r}, password=<hidden>)"


def _checked(value, limits, reason, what, of):
    """A value with a number of printable ASCII characters inside the limits."""
    low, high = limits
    if not low <= len(value) <= high:
        raise Failure(reason, f"the {what} has {len(value)} characters; {of} has {low} to {high}")
    if any(not PRINTABLE[0] <= ord(character) <= PRINTABLE[1] for character in value):
        raise Failure(reason, f"the {what} has a character that is not printable ASCII")
    return value


def read(path=paths.WIFI_SETTINGS):
    """The settings of a settings file, checked. No detail of a refusal quotes the file."""
    value = settingsfile.value_of(path, "wifi-settings-missing", "wifi-settings-malformed")
    if not isinstance(value, dict) or sorted(value) != sorted(MEMBERS) or not all(isinstance(value[member], str) for member in MEMBERS):
        raise Failure("wifi-settings-malformed", f"{path} is not an object with exactly the strings name and password")
    name = _checked(value["name"], NAME_CHARACTERS, "wifi-name-invalid", "name", "a network name")
    password = _checked(value["password"], PASSWORD_CHARACTERS, "wifi-password-invalid", "password", "a Wi-Fi password")
    return Settings(name, password)


def _not_json(name):
    raise ValueError(name)


def _object(files, path):
    """The object one of WLED's settings files holds. An absent file counts as empty."""
    if path not in files:
        return {}
    try:
        value = json.loads(files[path].decode("utf-8"), parse_constant=_not_json)
    except (UnicodeDecodeError, ValueError, RecursionError):
        raise Failure("wled-settings-malformed", f"{path} in the board's storage is not JSON") from None
    if not isinstance(value, dict):
        raise Failure("wled-settings-malformed", f"{path} in the board's storage is not a JSON object")
    if ACCESS_POINT in value and not isinstance(value[ACCESS_POINT], dict):
        raise Failure("wled-settings-malformed", f"{ACCESS_POINT} in {path} in the board's storage is not an object")
    return value


def _text(value):
    """A value as WLED writes its settings files: JSON without spaces."""
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


def _without_the_settings(value):
    """A settings object without what the tool sets, as text, so that the order of the
    members counts. An access point left empty by this counts as absent."""
    left = copy.deepcopy(value)
    if isinstance(left.get(ACCESS_POINT), dict):
        for member in ("ssid", "pskl", "psk"):
            left[ACCESS_POINT].pop(member, None)
        if not left[ACCESS_POINT]:
            del left[ACCESS_POINT]
    return _text(left)


def _set(config, secrets, settings):
    """The two objects with the name and the password in them."""
    config, secrets = copy.deepcopy(config), copy.deepcopy(secrets)
    access = config.setdefault(ACCESS_POINT, {})
    access["ssid"] = settings.name
    access["pskl"] = len(settings.password)
    access.pop("psk", None)
    secrets.setdefault(ACCESS_POINT, {})["psk"] = settings.password
    return config, secrets


def _holds(config, secrets, settings):
    access, secret = config.get(ACCESS_POINT, {}), secrets.get(ACCESS_POINT, {})
    return (access.get("ssid") == settings.name and access.get("pskl") == len(settings.password) and type(access.get("pskl")) is int
            and "psk" not in access and secret.get("psk") == settings.password)


def _other_files(files):
    return {path: content for path, content in files.items() if path not in (CONFIG, SECRETS)}


def apply(image, settings):
    """A storage image with the name and the password in WLED's stored settings, and
    everything else as it was. The result is checked before it is returned. An image that
    holds the settings already is returned as it is."""
    system = storage.mount(image)
    before = storage.files_in(system)
    old = {path: _object(before, path) for path in (CONFIG, SECRETS)}
    new = dict(zip((CONFIG, SECRETS), _set(old[CONFIG], old[SECRETS], settings)))
    changed = [path for path in (CONFIG, SECRETS) if _text(new[path]) != _text(old[path])]
    if not changed:
        return image
    try:
        for path in changed:
            with system.open(path, "wb") as file:
                file.write(_text(new[path]).encode("utf-8"))
        system.unmount()
    except LittleFSError as error:
        if error.code == storage.NO_SPACE:
            raise Failure("no-space", "WLED's stored settings do not fit into storage") from None
        raise Failure("verify-failed", f"the file system refused WLED's stored settings: {error}") from None
    made = bytes(system.context.buffer)
    if storage.geometry(made) != storage.geometry(image):
        raise Failure("verify-failed", "the file system changed its version or its size")
    after = storage.files_in(storage.mount(made))
    difference = storage.differing(_other_files(after), _other_files(before))
    if difference:
        raise Failure("verify-failed", f"a file other than WLED's stored settings changed in the new image: {difference}")
    if not holds(made, settings):
        raise Failure("verify-failed", f"{CONFIG} and {SECRETS} in the new image do not hold the settings")
    for path in (CONFIG, SECRETS):
        if _without_the_settings(_object(after, path)) != _without_the_settings(old[path]):
            raise Failure("verify-failed", f"{path} in the new image differs in more than the name and the password")
    return made


def holds(image, settings):
    """Whether WLED's stored settings in a storage image are these settings."""
    files = storage.files_in(storage.mount(image))
    try:
        return _holds(_object(files, CONFIG), _object(files, SECRETS), settings)
    except Failure:
        return False


def name_in(image):
    """The name in WLED's stored settings of a storage image, or None."""
    try:
        name = _object(storage.files_in(storage.mount(image)), CONFIG).get(ACCESS_POINT, {}).get("ssid")
    except Failure:
        return None
    return name if isinstance(name, str) else None
