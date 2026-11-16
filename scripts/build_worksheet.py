#!/usr/bin/env python3
"""V2: validate Agent-supplied readings, then draw A4 vector worksheets with ReportLab."""
import argparse
import json
import math
from pathlib import Path
import re
import sys
import tempfile
import os
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from pypdf import PdfReader
from pinyin_alpha import normalize, split_tone, validate_syllable, fix_pinyin, has_tone

ROOT = Path(__file__).resolve().parents[1]
BOX = 15.0
GAP = 4.0
ROW_H = 24.2
HEADER_H = 9.0
MAX_W = 189.0
ROWS_PER_PAGE = 11


def register_fonts():
    for name, filename in [('Pinyin', 'DejaVuSans.ttf'), ('Chinese', 'NotoSansSC-Regular.ttf')]:
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(ROOT / 'assets/fonts' / filename)))


def is_hanzi(ch):
    n = ord(ch)
    return (0x3400 <= n <= 0x4dbf or 0x4e00 <= n <= 0x9fff or
            0x20000 <= n <= 0x323af or 0xf900 <= n <= 0xfaff)


def parse_line(line):
    line = line.strip().lstrip('\ufeff')
    if not line or line.startswith('#'):
        return None
    parts = re.split(r'\s*[|,，\t]\s*|\s+', line, maxsplit=1)
    if len(parts) != 2 or not all(parts):
        raise ValueError('每行必须含词语及拼音，不能省略或跳过')
    return tuple(parts)


def load_words(path):
    path = Path(path)
    pairs = []
    if path.suffix.lower() == '.json':
        data = json.loads(path.read_text(encoding='utf-8-sig'))
        if isinstance(data, dict) and 'words' in data:
            data = data['words']
        if isinstance(data, dict):
            pairs = list(data.items())
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and set(item) >= {'word', 'pinyin'}:
                    pairs.append((item['word'], item['pinyin']))
                elif isinstance(item, str):
                    pair = parse_line(item)
                    if pair is None:
                        raise ValueError('JSON 数组不能含空记录')
                    pairs.append(pair)
                else:
                    raise ValueError('JSON 记录必须为字符串或含 word/pinyin 的对象')
        else:
            raise ValueError('JSON 顶层必须为对象或数组')
    else:
        for num, line in enumerate(path.read_text(encoding='utf-8-sig').splitlines(), 1):
            try:
                pair = parse_line(line)
            except ValueError as e:
                raise ValueError(f'第 {num} 行：{e}') from e
            if pair:
                pairs.append(pair)
    if not pairs:
        raise ValueError('没有词语')
    words, warnings = [], []
    for i, (word, pinyin) in enumerate(pairs, 1):
        if not isinstance(word, str) or not isinstance(pinyin, str):
            raise ValueError(f'第 {i} 项：word 和 pinyin 必须为字符串')
        word = word.strip()
        if not word or not all(is_hanzi(ch) for ch in word):
            raise ValueError(f'第 {i} 项：词语必须由汉字组成（不接受数字或标点）')
        syls = [normalize(s) for s in pinyin.split()]
        if len(syls) != len(word):
            raise ValueError(f'{word}：音节数 {len(syls)} 与字数 {len(word)} 不符')
        for s in syls:
            issues = validate_syllable(s)
            if issues:
                raise ValueError(f'{word} / {s}：' + '；'.join(issues))
            if not has_tone(s):
                warnings.append(f'{word} / {s}：无声调，请 Agent 确认是轻声')
        words.append((word, syls))
    return words, warnings


def layout(words):
    rows, current, width = [], [], 0
    for i, (word, _) in enumerate(words):
        w = len(word) * BOX
        if w > MAX_W:
            raise ValueError(f'{word}：词组宽 {w}mm 超出 {MAX_W}mm，不能拆词或缩格')
        if current and width + GAP + w > MAX_W:
            rows.append(current)
            current, width = [], 0
        if current:
            width += GAP
        current.append(i)
        width += w
    if current:
        rows.append(current)
    return rows


def glyph_text(s):
    # Precomposed accents for e/i/o/u/ü; alpha tone is placed as an explicit vector.
    return fix_pinyin(s)


def syllable_width(s, size):
    return sum(pdfmetrics.stringWidth(c, 'Pinyin', size) for c in glyph_text(s)
               if c not in '\u0304\u0301\u030c\u0300')


def draw_syllable(c, s, center, baseline, size):
    text = glyph_text(s)
    x = center - syllable_width(s, size)/2
    c.setFont('Pinyin', size)
    for ch in text:
        if ch in '\u0304\u0301\u030c\u0300':
            # Alpha is the only uncomposed accented vowel. ReportLab does not
            # perform mark shaping here, so construct the tone above its center.
            mid = previous_x + previous_width/2
            y, half, rise = baseline + size*.66, size*.17, size*.11
            c.setLineWidth(size*.045)
            if ch == '\u0304':
                c.line(mid-half,y+rise/2,mid+half,y+rise/2)
            elif ch == '\u0301':
                c.line(mid-half,y,mid+half,y+rise)
            elif ch == '\u0300':
                c.line(mid-half,y+rise,mid+half,y)
            else:
                p = c.beginPath()
                p.moveTo(mid-half,y+rise)
                p.lineTo(mid,y)
                p.lineTo(mid+half,y+rise)
                c.drawPath(p)
            continue
        previous_x = x
        previous_width = pdfmetrics.stringWidth(ch, 'Pinyin', size)
        c.drawString(x,baseline,ch)
        x += previous_width


def draw_grid(c, x, y, count):
    b = BOX*mm
    c.setStrokeColorRGB(.63,.63,.63)
    c.setLineWidth(.35)
    c.setDash(1.2,1.5)
    c.line(x,y+b/2,x+count*b,y+b/2)
    for j in range(count):
        c.line(x+(j+.5)*b,y,x+(j+.5)*b,y+b)
    c.setDash()
    c.setStrokeColorRGB(.1,.1,.1)
    c.setLineWidth(.6)
    c.rect(x,y,count*b,b)
    for j in range(1,count):
        c.line(x+j*b,y,x+j*b,y+b)


def build(input_path, output, title='看拼音写词语', py_pt=13):
    if not math.isfinite(py_pt) or not 8 <= py_pt <= 16:
        raise ValueError('拼音字号必须为 8 至 16pt 的有限数字')
    words, warnings = load_words(input_path)
    rows = layout(words)
    register_fonts()
    chinese = pdfmetrics.getFont('Chinese').face.charToGlyph
    if not title or pdfmetrics.stringWidth(title, 'Chinese', 14) > 120*mm or any(ord(ch) not in chinese for ch in title):
        raise ValueError('标题过长或包含中文字体未覆盖的字符')
    for word, syllables in words:
        for s in syllables:
            if syllable_width(s,py_pt) > (BOX-.5)*mm:
                raise ValueError(f'{word} / {s}：实际字宽超过 14.5mm，请减小 --py-pt')
    pages = [rows[i:i+ROWS_PER_PAGE] for i in range(0,len(rows),ROWS_PER_PAGE)]
    out = Path(output).resolve()
    if out == Path(input_path).resolve():
        raise ValueError('输出文件不能覆盖输入词表')
    out.parent.mkdir(parents=True,exist_ok=True)
    # Validate first, then write atomically. Failed runs preserve existing PDFs.
    fd, tmp = tempfile.mkstemp(suffix='.pdf',dir=out.parent)
    os.close(fd)
    try:
        c = canvas.Canvas(tmp,pagesize=A4,pageCompression=1,invariant=1)
        c.setTitle(title)
        c.setAuthor('pinyin-worksheet V2.1')
        for page_num, page_rows in enumerate(pages,1):
            c.setFillColorRGB(0,0,0)
            c.setFont('Chinese',14)
            c.drawString(10*mm,279*mm,title)
            c.setFont('Chinese',9)
            c.drawRightString(200*mm,279*mm,'姓名：________  日期：________')
            for r, row in enumerate(page_rows):
                y = (297-12-HEADER_H-7-BOX-r*ROW_H)*mm
                x = 10*mm
                for idx in row:
                    word, syllables = words[idx]
                    draw_grid(c,x,y,len(word))
                    for j,s in enumerate(syllables):
                        draw_syllable(c,s,x+(j+.5)*BOX*mm,y+(BOX+2)*mm,py_pt)
                    x += (len(word)*BOX+GAP)*mm
            c.setFont('Pinyin',8)
            c.drawRightString(200*mm,5*mm,f'{page_num} / {len(pages)}')
            c.showPage()
        c.save()
        pdf = PdfReader(tmp)
        if len(pdf.pages) != len(pages):
            raise ValueError('生成页数与排版计划不符')
        for p in pdf.pages:
            if abs(float(p.mediabox.width)-A4[0]) > .01 or abs(float(p.mediabox.height)-A4[1]) > .01:
                raise ValueError('生成纸张不是 A4')
        os.replace(tmp,out)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    report = dict(version='2.1.0',engine='ReportLab',words=len(words),
                  syllables=sum(len(s) for _,s in words),rows=len(rows),pages=len(pages),
                  box_mm=BOX,rows_per_page=[len(p) for p in pages],
                  groups_per_row=[len(r) for r in rows],
                  page_content_heights_mm=[HEADER_H+len(p)*ROW_H-2.2 for p in pages],
                  alpha_count=sum(glyph_text(s).count('ɑ') for _,ss in words for s in ss),
                  ordinary_a_remaining=sum(glyph_text(s).count('a') for _,ss in words for s in ss),
                  warnings=warnings,output=str(out))
    return report


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('-i','--input',required=True)
    ap.add_argument('-o','--output',default='worksheet.pdf')
    ap.add_argument('--title',default='看拼音写词语')
    ap.add_argument('--py-pt',type=float,default=13)
    ap.add_argument('--report',help='可选 JSON 检查报告路径')
    ap.add_argument('--summary',action='store_true',help='终端仅显示摘要；完整数据写 --report')
    args=ap.parse_args()
    if args.report and Path(args.report).resolve() in (Path(args.input).resolve(),Path(args.output).resolve()):
        ap.error('报告路径不能覆盖输入或 PDF')
    try:
        result=build(args.input,args.output,args.title,args.py_pt)
        if args.report:
            Path(args.report).parent.mkdir(parents=True,exist_ok=True)
            Path(args.report).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        if args.summary:
            print(f"完成：{result['words']}词 / {result['syllables']}格 / {result['pages']}页；A4 / 15mm；普通a残留{result['ordinary_a_remaining']}")
            for warning in result['warnings']:
                print('注意：'+warning)
            print('PDF：'+result['output'])
        else:
            print(json.dumps(result,ensure_ascii=False,indent=2))
    except (ValueError,OSError,KeyError,TypeError) as e:
        print(f'错误：{e}',file=sys.stderr)
        return 2
    return 0

if __name__=='__main__':
    sys.exit(main())
