#!/usr/bin/env python3
"""Unicode normalization and structural checks, never a word pronunciation dictionary."""
import re
import unicodedata as ud
TONES = {'\u0304': 1, '\u0301': 2, '\u030c': 3, '\u0300': 4}
VOWELS = 'aeiouü'


def normalize(s):
    return ud.normalize('NFC', s.replace('ɑ', 'a'))


def split_tone(s):
    """Return NFC unaccented letters, tone number, accented letter index."""
    chars, tone, index = [], 0, -1
    for ch in ud.normalize('NFD', normalize(s)):
        if ch in TONES:
            tone, index = TONES[ch], len(chars) - 1
        elif ch == '\u0308' and chars and chars[-1] == 'u':
            chars[-1] = 'ü'
        else:
            chars.append(ch)
    return ''.join(chars), tone, index


def tone_index(base):
    for v in 'aoe':
        if v in base:
            return base.index(v)
    return max((i for i, c in enumerate(base) if c in 'iuü'), default=-1)


def validate_syllable(s):
    s = normalize(s)
    decomposed = ud.normalize('NFD', s)
    if not s:
        return ['空音节']
    if any(c not in 'abcdefghijklmnopqrstuvwxyzüāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ' for c in s):
        return ['非法字符或组合标记（只接受小写带调拼音，不接受数字调、v、u:）']
    base, tone, idx = split_tone(s)
    issues = []
    if 'v' in base or not re.fullmatch('[a-zü]+', base):
        issues.append('非法拼音字母')
    if not any(c in VOWELS for c in base):
        issues.append('没有韵母；本练习不支持音节化 m/n')
    if sum(decomposed.count(t) for t in TONES) > 1:
        issues.append('一个音节存在多个声调')
    if tone and idx != tone_index(base):
        issues.append('声调标记位置错误')
    if 'ü' in base and not re.fullmatch('[nl]ü(?:e|n)?', base):
        issues.append('ü 拼写错误（j/q/x/y 后应写 u）')
    # This is a structural check, not an exhaustive inventory of valid syllables.
    return issues


def fix_pinyin(s):
    return ''.join({'a':'ɑ', 'ā':'ɑ\u0304', 'á':'ɑ\u0301',
                    'ǎ':'ɑ\u030c', 'à':'ɑ\u0300'}.get(c,c) for c in normalize(s))


def has_tone(s):
    return split_tone(s)[1] != 0
