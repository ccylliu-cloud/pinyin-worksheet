#!/usr/bin/env python3
"""One deterministic bundled-font coverage check; no browser or screenshots."""
import hashlib
import json
from build_worksheet import register_fonts, ROOT
from reportlab.pdfbase import pdfmetrics


def check():
    register_fonts()
    f = pdfmetrics.getFont('Pinyin').face
    required = 'abcdefghijklmnopqrstuvwxyzüɑāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ'
    missing = [c for c in required if not f.charToGlyph.get(ord(c))]
    if missing:
        raise ValueError(f'拼音字体缺字：{missing}')
    if f.charToGlyph[ord('a')] == f.charToGlyph[ord('ɑ')]:
        raise ValueError('ɑ 与 a 指向同一字形')
    return {'coverage':'PASS','alpha_distinct_glyph':True,
            'font_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in (ROOT/'assets/fonts').glob('*.ttf')}}

if __name__=='__main__':
    print(json.dumps(check(),ensure_ascii=False,indent=2))
