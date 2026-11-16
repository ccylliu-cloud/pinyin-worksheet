#!/usr/bin/env python3
"""Executable behavioral regression; outputs PDFs and a machine-readable report."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from pypdf import PdfReader
from pypdf.generic import ContentStream
from reportlab.lib.units import mm
from build_worksheet import build, load_words, ROOT
from pinyin_alpha import fix_pinyin, validate_syllable
from check_glyph import check


def inspect_pdf(path, expected_words, expected_pages, expected_cells):
    reader=PdfReader(path)
    assert len(reader.pages)==expected_pages
    rectangles=[]
    embedded=0
    extracted=''
    for page in reader.pages:
        assert abs(float(page.mediabox.width)/mm-210)<.001
        assert abs(float(page.mediabox.height)/mm-297)<.001
        extracted += page.extract_text()
        for args,op in ContentStream(page.get_contents(),reader).operations:
            if op==b're':
                x,y,w,h=map(float,args)
                assert abs(h/mm-15)<.001
                assert abs(w/mm/15-round(w/mm/15))<.001
                assert x/mm>=9.99 and (x+w)/mm<=200.01
                assert y/mm>=9.99 and (y+h)/mm<=276.01
                rectangles.append((w/mm,h/mm))
        for font in page['/Resources']['/Font'].get_object().values():
            font=font.get_object()
            if '/FontDescriptor' in font and '/FontFile2' in font['/FontDescriptor']:
                embedded+=1
    assert len(rectangles)==expected_words
    assert round(sum(w/15 for w,h in rectangles))==expected_cells
    assert embedded>=2
    assert 'ɑ' in extracted
    # No ordinary 'a' in worksheet content, title or page labels.
    assert 'a' not in extracted
    return {'pages':len(reader.pages),'grids':len(rectangles),'cells':expected_cells,
            'a4':True,'all_boxes_15mm':True,'fonts_embedded':True,'bounds':True}


def run(out):
    out.mkdir(parents=True,exist_ok=True)
    results=[]
    def case(name, fn):
        try:
            detail=fn()
            results.append({'name':name,'status':'PASS','detail':detail})
        except Exception as e:
            results.append({'name':name,'status':'FAIL','detail':str(e) or type(e).__name__})
    case('bundled-font-coverage',check)
    baseline=ROOT/'assets/words-sample.txt'
    words,_=load_words(baseline)
    lines=[f'{w} {" ".join(ss)}' for w,ss in words]
    extended=out/'words-104.txt'
    extended.write_text('\n'.join(lines*2)+'\n',encoding='utf-8')
    for count,source,pages in [(52,baseline,1),(104,extended,2)]:
        def sample(count=count,source=source,pages=pages):
            pdf=out/f'sample-{count}.pdf'
            report=build(source,pdf)
            assert report['words']==count
            assert report['pages']==pages
            assert report['ordinary_a_remaining']==0
            assert report['alpha_count']==38*(count//52)
            assert not report['warnings']
            assert all(h<=275 for h in report['page_content_heights_mm'])
            report['pdf_checks']=inspect_pdf(pdf,count,pages, sum(len(w) for w,_ in words)*(count//52))
            (out/f'sample-{count}-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            return report
        case(f'{count}-words-pagination-and-pdf-geometry',sample)
    with tempfile.TemporaryDirectory() as tmp:
        tmp=Path(tmp)
        invalid={
            'missing-pinyin':'麻雀', 'count-mismatch':'麻雀 má',
            'tone-digit':'麻雀 ma2 què','uppercase':'麻雀 Má què',
            'v-spelling':'女 nǚv', 'u-colon':'女 nu:',
            'wrong-tone-position':'对 dùi','iu-position':'流 líu',
            'multiple-tones':'麻 mǎá','no-vowel':'字 z',
            'bad-mark':'麻 a\u0302','punctuation':'麻雀！ má què',
            'empty':'# comment only', 'nonhanzi':'A ā',
            'overwide-word':'一'*13+' '+' '.join(['yī']*13),
            'overwide-syllable':'麻 '+'m'*25+'ā',
            'bad-umlaut':'去 qü',
        }
        for name,content in invalid.items():
            def reject(name=name,content=content):
                src=tmp/'bad.txt'; dest=tmp/'sentinel.pdf'
                src.write_text(content,encoding='utf-8')
                sentinel=b'existing PDF must remain unchanged'
                dest.write_bytes(sentinel)
                p=subprocess.run([sys.executable,str(ROOT/'scripts/build_worksheet.py'),'-i',str(src),'-o',str(dest)],capture_output=True,text=True)
                assert p.returncode==2,(p.returncode,p.stderr)
                assert dest.read_bytes()==sentinel
                dest.unlink()
                p=subprocess.run([sys.executable,str(ROOT/'scripts/build_worksheet.py'),'-i',str(src),'-o',str(dest)],capture_output=True,text=True)
                assert p.returncode==2 and not dest.exists()
                return {'exit_code':2,'no_partial_pdf':True,'existing_pdf_preserved':True}
            case('reject-'+name,reject)
        valid={
            'nfd':'麻雀 ma\u0301 què',
            'alpha-input':'麻雀 mɑ\u0301 què',
            'neutral-tone':'孩子 hái zi',
            'umlaut':'女 nǚ',
            'all-alpha-tones':'啊啊啊啊 ā á ǎ à',
            'separator-pipe':'麻雀|má què',
            'separator-comma':'麻雀,má què',
            'separator-tab':'麻雀\tmá què',
        }
        for name,content in valid.items():
            def accept(name=name,content=content):
                src=tmp/'ok.txt'; src.write_text(content,encoding='utf-8')
                report=build(src,tmp/'ok.pdf')
                if name=='neutral-tone':
                    assert len(report['warnings'])==1
                else:
                    assert not report['warnings']
                return {'pages':report['pages'],'warnings':report['warnings']}
            case('accept-'+name,accept)
        schemas=[{'麻雀':'má què'},[{'word':'麻雀','pinyin':'má què'}],
                 {'words':[{'word':'麻雀','pinyin':'má què'}]},['麻雀 má què']]
        for i,data in enumerate(schemas):
            def schema(data=data):
                src=tmp/'ok.json'; src.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
                assert build(src,tmp/'ok.pdf')['words']==1
                return True
            case(f'json-schema-{i+1}',schema)
        for data in [[{'word':'麻雀'}],['麻雀'],[],{'words':42},[{'word':12,'pinyin':'má'}]]:
            def bad_json(data=data):
                src=tmp/'bad.json'; src.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
                try: build(src,tmp/'bad.pdf')
                except (ValueError,TypeError,KeyError): return True
                raise AssertionError('accepted invalid JSON')
            case(f'reject-json-{len(results)}',bad_json)
        def size_guard():
            for size in [float('nan'),float('inf'),-1,100]:
                try: build(baseline,tmp/'bad.pdf',py_pt=size)
                except ValueError: continue
                raise AssertionError(size)
            return True
        case('invalid-font-size',size_guard)
        def normalize_guard():
            assert fix_pinyin('ma\u0301')=='mɑ\u0301'
            assert not validate_syllable('lüè')
            assert validate_syllable('lǜe')
            assert not validate_syllable('guī')
            return True
        case('normalization-and-tone-target',normalize_guard)
        def output_guard():
            src=tmp/'preserve.txt'; src.write_text('麻雀 má què',encoding='utf-8')
            before=src.read_bytes()
            try: build(src,src)
            except ValueError: pass
            else: raise AssertionError('overwrote input')
            assert src.read_bytes()==before
            return True
        case('output-cannot-overwrite-input',output_guard)
    report={'total':len(results),'passed':sum(r['status']=='PASS' for r in results),'results':results}
    report['failed']=report['total']-report['passed']
    (out/'test-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return report['failed']

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--output-dir',default=str(ROOT/'tests/output'))
    sys.exit(bool(run(Path(p.parse_args().output_dir))))
