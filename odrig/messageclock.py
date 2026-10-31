"""Strict reading of bounded message-clock widget payloads."""

import struct

from . import errors, odrgx

HEAD = struct.Struct('<BBBBIHHIII')
RECORD = struct.Struct('<IBBHHH')
MASK_BYTES = 900
GLYPH_BYTES = 3968


def decode(data):
    header = odrgx.read_header(data)
    payload = memoryview(data)[odrgx.HEADER.size:]
    def reject(reason, detail):
        raise errors.Rejection(reason, detail)
    def take(at, size):
        if at + size > len(payload):
            reject(errors.TRUNCATED, 'message-clock payload ended early')
        return payload[at:at + size]
    if header.type != 3:
        reject(errors.UNKNOWN_TYPE, 'not a widget')
    if (header.width, header.height) != (60, 60):
        reject(errors.BAD_SETTINGS, 'message-clock canvas must be 60 x 60')
    widget, version, tab, count, loop, text_size, zero, masks, glyphs, total = HEAD.unpack(take(0, HEAD.size))
    if widget != 6:
        reject(errors.UNKNOWN_WIDGET, 'not a message-clock widget')
    if version != 1 or not 1 <= tab <= 7 or not 1 <= count <= 24 or zero or not 1 <= text_size <= 4096:
        reject(errors.BAD_SETTINGS, 'invalid message-clock header')
    wanted_masks = HEAD.size + RECORD.size * count + text_size
    wanted_glyphs = wanted_masks + count * MASK_BYTES
    if masks != wanted_masks or glyphs != wanted_glyphs:
        reject(errors.BAD_SETTINGS, 'invalid message-clock offsets')
    if total != wanted_glyphs + GLYPH_BYTES or total != header.payload_size or total > 32768:
        reject(errors.PAYLOAD_SIZE, 'invalid message-clock size')
    rows = []
    offset = elapsed = 0
    stops = freezes = 0
    for i in range(count):
        duration, flags, reserved, at, size, tail = RECORD.unpack(take(HEAD.size + i * RECORD.size, RECORD.size))
        if (reserved or tail or flags & ~31 or flags & 3 == 3 or
                flags & 3 and tab != 5 or flags & 4 and tab != 1 or
                flags & 24 and tab != 6 or not 1 <= size <= 256 or at != offset or
                duration != (2000 if flags & 1 else 6100)):
            reject(errors.BAD_SETTINGS, 'invalid message-clock caption')
        stops += bool(flags & 4)
        freezes += bool(flags & 8)
        if stops > 1 or freezes > 1:
            reject(errors.BAD_SETTINGS, 'duplicate stop boundary')
        rows.append(dict(duration=duration, flags=flags, offset=at, size=size))
        offset += size
        elapsed += duration
    if offset != text_size:
        reject(errors.BAD_SETTINGS, 'caption text lengths disagree')
    text_at = HEAD.size + RECORD.size * count
    for i, row in enumerate(rows):
        raw = take(text_at + row.pop('offset'), row.pop('size'))
        try:
            text = bytes(raw).decode('utf-8')
        except UnicodeDecodeError:
            reject(errors.BAD_TEXT, 'invalid caption UTF-8')
        if any(ord(c) < 32 or 127 <= ord(c) <= 159 for c in text):
            reject(errors.BAD_TEXT, 'control character in caption')
        row['text'] = text
        row['mask'] = bytes(take(masks + i * MASK_BYTES, MASK_BYTES))
    atlas = bytes(take(glyphs, GLYPH_BYTES))
    if len(payload) > total:
        reject(errors.TRAILING_BYTES, 'bytes follow message-clock')
    if loop != elapsed or header.loop_ms != loop:
        reject(errors.LOOP_MISMATCH, 'message-clock loop disagrees')
    return dict(widget='message-clock', width=60, height=60, tab=tab,
        loopMs=loop, messages=rows, glyphs=atlas)
