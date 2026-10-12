"""The standalone firmware's build: a PlatformIO project of its own in the work folder,
written from a template that names the repository and WLED's checkout."""

import pathlib

from . import Failure, paths

TEMPLATE = paths.FIRMWARE / "standalone" / "platformio.ini.in"
PROJECT_NAME = "platformio.ini"
REPOSITORY, CHECKOUT = "@REPO@", "@WLED@"


def project_text(root=paths.ROOT, wled=paths.WLED, template=TEMPLATE):
    """The project file: the template with the two paths filled in."""
    filled = pathlib.Path(template).read_text()
    for placeholder, folder in ((REPOSITORY, root), (CHECKOUT, wled)):
        folder = str(pathlib.Path(folder).resolve())
        if any(character.isspace() for character in folder):
            raise Failure("build-failed", f"the path {folder!r} has a space in it, which the entries of the build cannot carry")
        filled = filled.replace(placeholder, folder)
    return filled


def write_project(folder=paths.STANDALONE, root=paths.ROOT, wled=paths.WLED, template=TEMPLATE):
    """Writes the project file into the project's folder, unless it is there with this
    content. Returns the folder."""
    folder = paths.output(folder)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / PROJECT_NAME
    text = project_text(root, wled, template)
    if not path.is_file() or path.read_text() != text:
        path.write_text(text)
    return folder
