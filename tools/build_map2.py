# -*- coding: utf-8 -*-
"""Build S->T (simplified->traditional) mapping from the .loc corpus.

Context-aware majority voting via difflib alignment, then output:
  - s2t_map.pkl : full S->T mapping (majority vote per char)
  - redraw.pkl  : chars that actually need glyph redraw (S != T and the
                  simplified glyph has a real cell in font block 0)
"""
import argparse, os, pickle, struct
from collections import Counter, defaultdict
from difflib import SequenceMatcher

import opencc

from s2t_loc import runs_of, is_cjk, ratio

CC = opencc.OpenCC('s2twp')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--loc', required=True, help='directory containing .loc files')
    ap.add_argument('--dat', required=True, help='ui_font_cnx.dat (UV index table)')
    ap.add_argument('--out', default='.', help='output directory for pkl files')
    args = ap.parse_args()

    cnt = Counter()
    corpus_chars = Counter()
    nruns = 0
    for fn in sorted(os.listdir(args.loc)):
        if not fn.endswith('.loc'):
            continue
        data = open(os.path.join(args.loc, fn), 'rb').read()
        for s, e, txt in runs_of(data):
            if any(0x3400 <= ord(c) <= 0x4DBF or 0xE000 <= ord(c) <= 0xF8FF for c in txt):
                continue
            r, nk = ratio(txt)
            if not ((nk >= 4 and r >= 0.70) or (nk >= 2 and r >= 1.0)):
                continue
            nruns += 1
            t = CC.convert(txt)
            sm = SequenceMatcher(None, txt, t, autojunk=False)
            for tag, i1, i2, j1, j2 in sm.get_opcodes():
                if tag == 'replace' and (i2 - i1) == (j2 - j1):
                    for a, b in zip(txt[i1:i2], t[j1:j2]):
                        if is_cjk(ord(a)) and is_cjk(ord(b)):
                            cnt[(a, b)] += 1
                            corpus_chars[a] += 1
                elif tag == 'equal':
                    for a, b in zip(txt[i1:i2], t[j1:j2]):
                        if is_cjk(ord(a)):
                            cnt[(a, b)] += 1
                            corpus_chars[a] += 1

    print('strong runs:', nruns, ' distinct S:', len(corpus_chars))

    multi = defaultdict(Counter)
    for (a, b), n in cnt.items():
        multi[a][b] += n
    amb = {a: m for a, m in multi.items() if len(m) > 1}
    print('ambiguous:', len(amb))
    for a, m in sorted(amb.items(), key=lambda kv: -sum(kv[1].values()))[:25]:
        tot = sum(m.values())
        print('  %s -> %s' % (a, ' | '.join('%s %d(%.0f%%)' % (b, n, n * 100.0 / tot) for b, n in m.most_common())))

    # final mapping: majority vote, target must be CJK
    mapping = {}
    for a, m in multi.items():
        for b, n in m.most_common():
            if is_cjk(ord(b)):
                mapping[a] = b
                break
    pickle.dump(mapping, open(os.path.join(args.out, 's2t_map.pkl'), 'wb'))
    print('mapping entries:', len(mapping))

    # ---- .dat coverage ----
    d = open(args.dat, 'rb').read()
    starts = [0x148, 0x1A3B4, 0x34620]
    ns = [(0x148, (0x1A3B4 - 0x148) // 28),
          (0x1A3B4, (0x34620 - 0x1A3B4) // 28),
          (0x34620, (len(d) - 0x34620) // 28)]
    sec0 = {}
    st, n = ns[0]
    for i in range(n):
        cid, u1, v1, u2, v2, ox, w, h, oy = struct.unpack_from('<IffffHHHH', d, st + i * 28)
        if is_cjk(cid) and not (u1 == 0.0 and v1 == 0.0):
            sec0[cid] = (u1, v1)
    need = set(corpus_chars)
    print('corpus S with real cell:', len(need & set(sec0)), '/', len(need))
    miss = sorted(need - set(sec0))
    print('missing from font:', len(miss), miss[:30])
    chg = {a: b for a, b in mapping.items() if a != b and a in sec0}
    print('chars to redraw (S!=T, has cell):', len(chg))
    pickle.dump(chg, open(os.path.join(args.out, 'redraw.pkl'), 'wb'))


if __name__ == '__main__':
    main()
