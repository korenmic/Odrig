"""Builds the catalog vectors in tests/vectors/catalog. Run by hand, from the repository
root:

    python -m tests.converter.build_catalog_vectors

Each folder holds the files of one storage's catalog; `cases.json` says what a reader must
find in it: the state, what is wrong with a damaged or incompatible one, and the entries of
one that is ok, as `[name, bytes, crc32, width, height, total_ms, type]`. The outcomes are
written here by hand, never by a reader. The core's tests and the PC library's read the
same folders. tests/vectors/index holds the same for a drive's catalog of version 2 with
its index; an `ok` case gives its files in the walk's order too, as `[id, name]`.
"""

import json
import pathlib
import shutil

from odrig import catalog

VECTORS = pathlib.Path(__file__).resolve().parents[1] / "vectors" / "catalog"

# Entries of the valid catalogs: plain names, a name with capitals and spaces, the longest
# name, and numbers at their largest.
LONGEST = "l" * 95 + ".odrg"
ENTRIES = [
    catalog.Entry("sunrise.odrg", 52340, 0x1A2B3C4D, 60, 60, 12000),
    catalog.Entry("moon.odrg", 1612, 0x00000001, 60, 60, 4000),
    catalog.Entry("Fire Swirl 2.ODRG", 734002, 0xFFFFFFFF, 60, 60, 61000),
    catalog.Entry(LONGEST, 4294967295, 0x0BADF00D, 65535, 65535, 18446744073709551615),
    catalog.Entry("a.odrg", 0, 0, 1, 1, 0),
]
MANY = [catalog.Entry(f"clip-{number:03d}.odrg", 1000 + number, number * 7919, 60, 60, 1000 * number) for number in range(40)]
# Entries of a card with sub-folders: paths of one, two and three folders, a folder with a
# space in its name, one of digits alone, and a loose file.
FOLDERS = [
    catalog.Entry("loose.odrg", 2048, 0x0000BEEF, 60, 60, 3000),
    catalog.Entry("night/comet.odrg", 4096, 0x00C0FFEE, 60, 60, 8000),
    catalog.Entry("night/deep/x.odrg", 512, 0x0DEADBEE, 60, 60, 1500),
    catalog.Entry("night/deep/deeper/y.odrgx", 777, 0x0ABCDEF0, 60, 60, 2000, "text"),
    catalog.Entry("a b/c.odrg", 1024, 0x00001234, 60, 60, 4000),
    catalog.Entry("2026/day.odrg", 3333, 0x0000CAFE, 60, 60, 6000),
]


def files_of(entries, generation=1):
    """The files of a catalog of these entries, page by page in their order."""
    pages = [b""] * catalog.PAGES
    for entry in entries:
        pages[catalog.page_of(entry.name)] += entry.line()
    counts = tuple(page.count(b"\n") for page in pages)
    crcs = tuple(catalog.crc(page) if page else 0 for page in pages)
    made = {catalog.page_name(number): page for number, page in enumerate(pages) if page}
    made[catalog.MARKER] = catalog.Marker(generation, counts, crcs).text()
    return made


def remarked(files, page_number, page):
    """The files with one page replaced and the marker made to agree with it again."""
    files = dict(files)
    files[catalog.page_name(page_number)] = page
    marker = catalog.parse_marker(files[catalog.MARKER])
    counts = list(marker.counts)
    crcs = list(marker.crcs)
    # Its lines, the last one too when it has no line feed.
    counts[page_number] = page.count(b"\n") + (1 if page and not page.endswith(b"\n") else 0)
    crcs[page_number] = catalog.crc(page)
    files[catalog.MARKER] = catalog.Marker(marker.generation, tuple(counts), tuple(crcs)).text()
    return files


def resealed(marker_bytes):
    """A marker whose closing CRC-32 is made right again after its lines were changed."""
    body = marker_bytes[: catalog.MARKER_SIZE - 13]
    return body + f"crc {catalog.crc(body):08x}\n".encode("ascii")


def listed(entries):
    """The entries as a reader gives them: page by page, in the order of their lines."""
    ordered = sorted(enumerate(entries), key=lambda pair: (catalog.page_of(pair[1].name), pair[0]))
    return [[entry.name, entry.bytes, entry.crc, entry.width, entry.height, entry.total_ms, entry.type] for _, entry in ordered]


def cases():
    valid = files_of(ENTRIES, generation=0x2A)
    many = files_of(MANY, generation=0xFFFFFFFF)
    page = catalog.page_of("sunrise.odrg")
    other = (page + 1) % catalog.PAGES
    sunrise_page = valid[catalog.page_name(page)]
    made = {}

    made["ok-empty"] = (files_of([]), {"state": "ok", "generation": 1, "entries": []})
    made["ok-entries"] = (valid, {"state": "ok", "generation": 0x2A, "entries": listed(ENTRIES)})
    made["ok-many-pages"] = (many, {"state": "ok", "generation": 0xFFFFFFFF, "entries": listed(MANY)})
    made["none"] = ({"sunrise.odrg": b"not read"}, {"state": "none"})

    marker = valid[catalog.MARKER]
    made["damaged-marker-short"] = ({**valid, catalog.MARKER: marker[:-1]}, {"state": "damaged", "detail": "marker"})
    made["damaged-marker-long"] = ({**valid, catalog.MARKER: marker + b"\n"}, {"state": "damaged", "detail": "marker"})
    flipped = bytearray(marker)
    flipped[60] ^= 1
    made["damaged-marker-crc"] = ({**valid, catalog.MARKER: bytes(flipped)}, {"state": "damaged", "detail": "marker"})
    made["damaged-marker-line"] = ({**valid, catalog.MARKER: resealed(marker.replace(b"page 03 ", b"page 3  ", 1))}, {"state": "damaged", "detail": "marker"})
    made["damaged-marker-generation"] = ({**valid, catalog.MARKER: resealed(marker.replace(b"generation 0000002a", b"generation 00000000"))}, {"state": "damaged", "detail": "marker"})
    empty_crc = resealed(files_of([])[catalog.MARKER].replace(b"page 07 0000 00000000", b"page 07 0000 00000001"))
    made["damaged-marker-empty-page-crc"] = ({catalog.MARKER: empty_crc}, {"state": "damaged", "detail": "marker"})
    made["incompatible-format"] = ({**valid, catalog.MARKER: resealed(marker.replace(b"odrig-catalog 1 ", b"odrig-catalog 2 "))}, {"state": "incompatible"})
    made["incompatible-check"] = ({**valid, catalog.MARKER: resealed(marker.replace(b" check 1 ", b" check 2 "))}, {"state": "incompatible"})

    missing = dict(valid)
    del missing[catalog.page_name(page)]
    made["damaged-page-missing"] = (missing, {"state": "damaged", "detail": "page"})
    made["damaged-page-crc"] = ({**valid, catalog.page_name(page): sunrise_page.replace(b"52340", b"52341")}, {"state": "damaged", "detail": "page"})
    made["damaged-page-unended"] = (remarked(valid, page, sunrise_page[:-1]), {"state": "damaged", "detail": "page"})
    made["damaged-line-form"] = (remarked(valid, page, sunrise_page.replace(b" frames ", b" frame ")), {"state": "damaged", "detail": "line"})
    made["damaged-line-zero-width"] = (remarked(valid, page, sunrise_page.replace(b" 60 60 ", b" 0 60 ")), {"state": "damaged", "detail": "line"})
    made["damaged-line-size"] = (remarked(valid, page, sunrise_page.replace(b" 52340 ", b" 4294967296 ")), {"state": "damaged", "detail": "line"})
    made["damaged-line-name"] = (remarked(valid, page, sunrise_page.replace(b"sunrise.odrg", b"sun?rise.odrg")), {"state": "damaged", "detail": "line"})
    wrong = remarked(valid, other, valid.get(catalog.page_name(other), b"") + sunrise_page)
    made["damaged-line-wrong-page"] = (wrong, {"state": "damaged", "detail": "line"})
    made["damaged-line-twice"] = (remarked(valid, page, sunrise_page + sunrise_page), {"state": "damaged", "detail": "line"})

    record = catalog.do_text(0x2B, 1 << page, [("move", catalog.PART, "sunrise.odrg")])
    made["interrupted"] = ({**valid, catalog.DO: record}, {"state": "damaged", "detail": "interrupted"})
    made["torn-commit-record"] = ({**valid, catalog.DO: record[:-2]}, {"state": "ok", "generation": 0x2A, "entries": listed(ENTRIES)})

    folders = files_of(FOLDERS, generation=3)
    made["ok-folders"] = (folders, {"state": "ok", "generation": 3, "entries": listed(FOLDERS)})
    comet_page = catalog.page_of("night/comet.odrg")
    comet_lines = folders[catalog.page_name(comet_page)]
    made["damaged-line-path-empty-part"] = (remarked(folders, comet_page, comet_lines.replace(b"night/comet.odrg", b"night//comet.odrg")), {"state": "damaged", "detail": "line"})
    made["damaged-line-path-dot"] = (remarked(folders, comet_page, comet_lines.replace(b"night/comet.odrg", b".night/comet.odrg")), {"state": "damaged", "detail": "line"})
    made["damaged-line-path-deep"] = (remarked(folders, comet_page, comet_lines.replace(b"night/comet.odrg", b"a/b/c/d/comet.odrg")), {"state": "damaged", "detail": "line"})
    return made


def drive_files_of(entries, generation=1):
    """The files of a drive's catalog of these entries, of version 2, with its index: the
    pages, the folders' files, the table and the map, and the marker."""
    made = files_of(entries, generation)
    pages = catalog.parse_marker(made.pop(catalog.MARKER))
    index = catalog.build_index(sorted(entries, key=lambda entry: catalog.listing_key(entry.name)))
    for ordinal, folder in enumerate(index.folders):
        text = index.folder_text(ordinal)
        if text:
            made[catalog.folder_file(folder.id)] = text
    made[catalog.FOLDERS] = index.table_text()
    if index.map_text():
        made[catalog.IDS] = index.map_text()
    folders, ids = index.counts()
    made[catalog.MARKER] = catalog.Marker(generation, pages.counts, pages.crcs, folders, ids).text()
    return made


def remade(files, name, data):
    """A drive's files with one folder's file replaced, its CRC-32 put into the table and
    the table's into the marker, so that only what the rows say is wrong."""
    files = dict(files)
    old = files[name]
    files[name] = data
    files[catalog.FOLDERS] = files[catalog.FOLDERS].replace(f"{catalog.crc(old):08x}".encode(), f"{catalog.crc(data):08x}".encode())
    marker = catalog.parse_marker(files[catalog.MARKER], drive=True)
    folders = (marker.folders[0], catalog.crc(files[catalog.FOLDERS]))
    files[catalog.MARKER] = catalog.Marker(marker.generation, marker.counts, marker.crcs, folders, marker.ids).text()
    return files


def walked(entries):
    """The files of a drive's index in the walk's order, each `[id, name]`."""
    index = catalog.build_index(sorted(entries, key=lambda entry: catalog.listing_key(entry.name)))
    return [[file_id, entry.name] for folder in index.folders for file_id, entry in folder.rows]


def index_cases():
    """The cases of a drive's catalog with its index, read by a drive's readers."""
    valid = drive_files_of(FOLDERS, generation=3)
    made = {}
    made["ok-index"] = (valid, {"state": "ok", "generation": 3, "entries": listed(FOLDERS), "walk": walked(FOLDERS)})
    made["ok-index-empty"] = (drive_files_of([]), {"state": "ok", "generation": 1, "entries": [], "walk": []})
    made["incompatible-version-1"] = (files_of(FOLDERS, generation=3), {"state": "incompatible"})
    without = dict(valid)
    del without[catalog.FOLDERS]
    made["damaged-index-table-missing"] = (without, {"state": "damaged", "detail": "page"})
    night = catalog.folder_file(catalog.build_index(sorted(FOLDERS, key=lambda entry: catalog.listing_key(entry.name))).folders[3].id)
    made["damaged-index-folder-crc"] = ({**valid, night: valid[night].replace(b"night/comet", b"night/comex")}, {"state": "damaged", "detail": "page"})
    made["damaged-index-map-crc"] = ({**valid, catalog.IDS: valid[catalog.IDS].replace(b"60001 f 0 0", b"60001 f 0 1")}, {"state": "damaged", "detail": "page"})
    made["damaged-index-row-form"] = (remade(valid, night, valid[night].replace(b" f ", b" g ", 1)), {"state": "damaged", "detail": "line"})
    made["damaged-index-row-disagrees"] = (remade(valid, night, valid[night].replace(b"night/comet.odrg", b"night/comex.odrg")), {"state": "damaged", "detail": "line"})
    return made


def write_cases(folder_of_cases, made):
    if folder_of_cases.exists():
        shutil.rmtree(folder_of_cases)
    folder_of_cases.mkdir(parents=True)
    expected = {}
    for name, (files, outcome) in made.items():
        folder = folder_of_cases / name
        folder.mkdir()
        for file, data in files.items():
            (folder / file).write_bytes(data)
        expected[name] = outcome
    (folder_of_cases / "cases.json").write_bytes((json.dumps(expected, indent=1, sort_keys=True) + "\n").encode("ascii"))


INDEX_VECTORS = VECTORS.parent / "index"


def build():
    write_cases(VECTORS, cases())
    write_cases(INDEX_VECTORS, index_cases())


if __name__ == "__main__":
    build()
