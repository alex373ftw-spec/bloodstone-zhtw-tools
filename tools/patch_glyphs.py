# -*- coding: utf-8 -*-
"""Batch redraw ALL hanzi glyph cells in ui_font_cnx.bpr: simplified -> traditional.

- --pristine : pristine (simplified) .bpr, used as the base; the output is
               written to --bpr so the original stays untouched
- --map     : s2t_map.pkl produced by build_map2.py (context-aware majority)
              chars not in the corpus fall back to per-char OpenCC
- every real CJK record (36x32 cell, all 3 font blocks) whose traditional
  glyph differs gets its 9x8 DXT1 blocks rewritten.

.bpr layout (verified):
  - glyph data starts at 0x9D; 3 font blocks x 2752512 bytes
  - each font block = ONE DXT1 texture, 2048 x 2688 (512x672 blocks, 8B/block)
  - .dat UV mapping: cell x0 = round(u1*2048), cell y0 = round(v1*2048) + 8
  - CJK cell = 36x32 pixels = 9x8 DXT1 blocks (always 4-aligned)
"""
import argparse, pickle, struct
from collections import defaultdict

import numpy as np
import opencc
from PIL import Image, ImageFont, ImageDraw

HDR = 0x9D
BLK = 2752512
NB = 512

CELL_W, CELL_H = 36, 32
BLOCKS_X, BLOCKS_Y = 9, 8

INK_W, INK_H = 32, 29          # glyph ink box inside the cell


def is_cjk(u):
    return 0x4E00 <= u <= 0x9FFF


def render_glyph(ch, font_cache={}):
    """Render ch into 36x32 cell; ink box 32x29, top-aligned, centered x."""
    if ch in font_cache:
        return font_cache[ch]
    if 'font' not in font_cache:
        font_cache['font'] = ImageFont.truetype(font_cache['font_path'], 200)
    font = font_cache['font']
    tmp = Image.new('L', (800, 800), 0)
    d = ImageDraw.Draw(tmp)
    d.text((400, 400), ch, font=font, anchor='mm', fill=255)
    bbox = tmp.getbbox()
    gw, gh = bbox[2] - bbox[0], bbox[3] - bbox[1]
    scale = min(INK_W / gw, INK_H / gh)
    nw, nh = max(1, int(round(gw * scale))), max(1, int(round(gh * scale)))
    g = tmp.crop(bbox).resize((nw, nh), Image.LANCZOS)
    canvas = Image.new('L', (CELL_W, CELL_H), 0)
    canvas.paste(g, ((CELL_W - nw) // 2, 0))
    arr = np.array(canvas)
    font_cache[ch] = arr
    return arr


def quantize_blocks(cell):
    """36x32 lum -> 8x9 arrays of 16 indices (0=white,1=black,2=170,3=85)."""
    out = np.ones((BLOCKS_Y, BLOCKS_X, 16), np.uint8)
    for j in range(BLOCKS_Y):
        for i in range(BLOCKS_X):
            b = cell[j * 4:j * 4 + 4, i * 4:i * 4 + 4]
            idx = np.ones((4, 4), np.uint8)
            idx[(b >= 60) & (b < 140)] = 3
            idx[(b >= 140) & (b < 200)] = 2
            idx[b >= 200] = 0
            out[j, i] = idx.reshape(16)
    return out


def dxt1_block_bytes(idx16):
    bits = 0
    for i in range(16):
        bits |= int(idx16[i]) << (2 * i)
    return struct.pack('<HHI', 0xFFFF, 0x0000, bits)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--pristine', required=True, help='pristine simplified .bpr (base)')
    ap.add_argument('--dat', required=True, help='ui_font_cnx.dat UV index table')
    ap.add_argument('--bpr', required=True, help='output .bpr path (patched)')
    ap.add_argument('--map', default='s2t_map.pkl', help='s2t_map.pkl from build_map2.py')
    ap.add_argument('--font', default='C:/Windows/Fonts/msyhbd.ttc', help='TTF/TTC font for rendering')
    args = ap.parse_args()

    render_glyph.font_cache['font_path'] = args.font
    data = bytearray(open(args.pristine, 'rb').read())
    corpus = pickle.load(open(args.map, 'rb'))
    CC = opencc.OpenCC('s2twp')

    # ---- collect records from .dat ----
    d = open(args.dat, 'rb').read()
    ns = [(0x148, (0x1A3B4 - 0x148) // 28),
          (0x1A3B4, (0x34620 - 0x1A3B4) // 28),
          (0x34620, (len(d) - 0x34620) // 28)]
    jobs = []          # (block_idx, x0, y0, T)
    final_map = {}
    nredered = 0
    for bi, (st, n) in enumerate(ns):
        for i in range(n):
            cid, u1, v1, u2, v2, ox, w, h, oy = struct.unpack_from('<IffffHHHH', d, st + i * 28)
            if not is_cjk(cid) or (u1 == 0.0 and v1 == 0.0):
                continue
            S = chr(cid)
            if S in corpus:
                T = corpus[S]
            else:
                T = final_map.setdefault(S, CC.convert(S))
            if T == S or not is_cjk(ord(T)):
                continue
            x0 = round(u1 * 2048)
            y0 = round(v1 * 2048) + 8
            assert (w, h) == (36, 32) and x0 % 4 == 0 and y0 % 4 == 0, (S, w, h, x0, y0)
            jobs.append((bi, x0, y0, T, S))
            nredered += 1

    print('cells to redraw:', nredered, ' unique glyphs:', len(set(t for _, _, _, t, _ in jobs)))

    npatch = 0
    for bi, x0, y0, T, S in jobs:
        q = quantize_blocks(render_glyph(T))
        c0b, r0b = x0 // 4, y0 // 4
        base = HDR + bi * BLK
        for j in range(BLOCKS_Y):
            for i in range(BLOCKS_X):
                off = base + ((r0b + j) * NB + (c0b + i)) * 8
                data[off:off + 8] = dxt1_block_bytes(q[j, i])
                npatch += 1

    open(args.bpr, 'wb').write(bytes(data))
    print('written %s (%d bytes), DXT1 blocks written: %d' % (args.bpr, len(data), npatch))

    # save a preview strip of some redrawn cells
    sample_cells = []
    st, n = ns[0]
    for i in range(n):
        cid, u1, v1, u2, v2, ox, w, h, oy = struct.unpack_from('<IffffHHHH', d, st + i * 28)
        if not is_cjk(cid) or (u1 == 0.0 and v1 == 0.0):
            continue
        S = chr(cid)
        T = corpus.get(S) or final_map.get(S, S)
        if T != S:
            sample_cells.append((S, T, round(u1 * 2048), round(v1 * 2048) + 8))
            if len(sample_cells) >= 12:
                break
    tiles = []
    for S, T, x0, y0 in sample_cells:
        cell = np.zeros((32, 36), np.float32)
        for j in range(8):
            for i in range(9):
                off = HDR + ((y0 // 4 + j) * NB + (x0 // 4 + i)) * 8
                c0, c1 = struct.unpack_from('<HH', data, off)
                bits = struct.unpack_from('<I', data, off + 4)[0]
                pal = np.array([255.0, 0.0, 170.0, 85.0])
                idx = np.array([(bits >> (2 * k)) & 3 for k in range(16)]).reshape(4, 4)
                cell[j * 4:j * 4 + 4, i * 4:i * 4 + 4] = pal[idx]
        tiles.append(cell)
        tiles.append(np.full((32, 2), 128.0))
    comp = np.concatenate(tiles[:-1], axis=1)
    Image.fromarray(comp.astype(np.uint8)).resize((comp.shape[1] * 6, 32 * 6), Image.NEAREST).save('batch_preview.png')
    print('preview chars:', ' '.join(T for _, T, _, _ in sample_cells))


if __name__ == '__main__':
    main()
