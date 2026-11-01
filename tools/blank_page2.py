# -*- coding: utf-8 -*-
"""Blank the HIDDEN SECOND PAGE of ui_font_cnx.bpr (ghost-character fix).

Background
----------
Each of the 3 font blocks in ui_font_cnx.bpr is 2,752,512 bytes:
  - main page : 2048x2048 DXT1  (2,097,152 B)  <- indexed by .dat, shown by most UI
  - page 2    : 2048x640  DXT1  (  655,360 B)  <- NOT indexed by .dat
The hidden second page holds a full small SIMPLIFIED font atlas. Some UI
(dialogs, dossier menu, subtitles, credits lists) render BOTH pages stacked.
In the original both pages are simplified so they overlap invisibly; once you
redraw the main page with traditional glyphs, the simplified page 2 shows up
as faint "ghost" characters behind the real text.

Fix: zero out page 2 of all 3 blocks (solid DXT1 black blocks). Verified
in-game: ghost characters disappear completely, no missing text anywhere,
because the page-2 path only produces the ghost overlay.

Usage:
  python blank_page2.py path/to/ui_font_cnx.bpr [--restore backup.bpr]
"""
import argparse
import shutil

BLK = 2752512          # bytes per font block
PAGE2_OFF = 2097152    # page-2 offset inside a block
PAGE2_LEN = 655360     # 2048x640 DXT1
BLACK8 = b'\x00' * 8   # DXT1 block: c0=c1=0, all indices 0 -> solid black


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('bpr', help='path to ui_font_cnx.bpr')
    ap.add_argument('--restore', metavar='BACKUP',
                    help='instead of blanking, restore this backup over the bpr')
    args = ap.parse_args()

    if args.restore:
        shutil.copyfile(args.restore, args.bpr)
        print('restored %s -> %s' % (args.restore, args.bpr))
        return

    with open(args.bpr, 'rb') as f:
        b = bytearray(f.read())
    assert len(b) >= 3 * BLK, 'file too small: %d bytes' % len(b)

    for bi in range(3):
        base = 0x9D + bi * BLK + PAGE2_OFF
        page = b[base:base + PAGE2_LEN]
        if page == BLACK8 * (PAGE2_LEN // 8):
            print('block %d: page 2 already blank' % bi)
            continue
        b[base:base + PAGE2_LEN] = BLACK8 * (PAGE2_LEN // 8)
        print('block %d: page 2 blanked (%d bytes at 0x%X)' % (bi, PAGE2_LEN, base))

    with open(args.bpr, 'wb') as f:
        f.write(bytes(b))
    print('written %s (%d bytes)' % (args.bpr, len(b)))


if __name__ == '__main__':
    main()
