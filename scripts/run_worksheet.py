#!/usr/bin/env python3
"""Portable entry point: reuse compatible dependencies; bootstrap an isolated venv if needed."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parents[1]
# Probe runs inside the candidate interpreter: its installed packages are what matter.
PROBE = r'''
import importlib.metadata as m, json
try:
    import reportlab.pdfgen.canvas, pypdf
    versions = {n: m.version(n) for n in ('reportlab', 'pypdf')}
    def release(s):
        import re
        parts = s.split('.')
        return tuple(int(re.match(r'\d+', p).group()) for p in parts[:2])
    ok = (4, 2) <= release(versions['reportlab']) < (5, 0) and (5, 0) <= release(versions['pypdf']) < (7, 0)
    print(json.dumps({'ok': ok, 'versions': versions}))
except Exception as e:
    print(json.dumps({'ok': False, 'reason': str(e)}))
'''


def check_runtime(python):
    if not Path(python).is_file():
        return {'ok': False, 'reason': 'interpreter missing'}
    p = subprocess.run([str(python), '-I', '-c', PROBE], capture_output=True, text=True)
    try:
        result = json.loads(p.stdout)
        if p.returncode:
            result['ok'] = False
        return result
    except (ValueError, TypeError):
        return {'ok': False, 'reason': p.stderr.strip() or 'dependency probe failed'}


def cache_environment(cache_dir=None):
    base = Path(cache_dir) if cache_dir else Path(os.environ.get(
        'PINYIN_WORKSHEET_CACHE', str(Path.home()/'.cache'/'pinyin-worksheet')))
    digest = hashlib.sha256((ROOT/'requirements.txt').read_bytes()).hexdigest()[:12]
    return base / f'{sys.implementation.cache_tag}-{sys.platform}-{digest}'


def environment_python(env):
    return env / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def choose_runtime(cache_dir=None, install=True):
    current = check_runtime(sys.executable)
    if current['ok']:
        return Path(sys.executable), 'current', current
    env = cache_environment(cache_dir)
    python = environment_python(env)
    cached = check_runtime(python)
    if cached['ok']:
        return python, 'cached', cached
    if not install:
        raise RuntimeError('缺少兼容依赖；运行本入口生成PDF时会首次安装到独立缓存环境。')
    print('首次准备依赖：创建独立环境并安装 requirements.txt；不修改全局 Python。', file=sys.stderr)
    env.parent.mkdir(parents=True, exist_ok=True)
    if not python.is_file():
        venv.EnvBuilder(with_pip=True).create(env)
    subprocess.run([str(python), '-m', 'pip', 'install', '--disable-pip-version-check',
                    '-r', str(ROOT/'requirements.txt')], check=True, stdout=sys.stderr)
    installed = check_runtime(python)
    if not installed['ok']:
        raise RuntimeError(f'依赖安装后仍不可用：{installed}；请检查Python环境，不自动循环重试。')
    return python, 'installed', installed


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, add_help=False)
    parser.add_argument('--check', action='store_true', help='只检查依赖，不安装或生成')
    parser.add_argument('--cache-dir', help='独立环境缓存根目录（默认用户缓存目录）')
    args, build_args = parser.parse_known_args(argv)
    if sys.version_info < (3, 10):
        print('需要 Python 3.10 或更新版本。', file=sys.stderr)
        return 2
    # Help and missing/nonexistent input must never trigger a network install.
    if not args.check and (not build_args or '-h' in build_args or '--help' in build_args):
        print('用法：python3 scripts/run_worksheet.py -i words.txt -o worksheet.pdf\n'
              '首次缺依赖时自动装入独立环境，以后复用；--check 只检查；--cache-dir 自定缓存。\n'
              '其他参数同 build_worksheet.py（--title / --py-pt / --report / --summary）。')
        return 0 if build_args else 2
    if not args.check:
        has_input = any(a in ('-i', '--input') or a.startswith('--input=') for a in build_args)
        if not has_input:
            print('缺少 -i/--input；尚未检查或安装依赖。', file=sys.stderr)
            return 2
        source = next((a.split('=', 1)[1] for a in build_args if a.startswith('--input=')), None)
        if source is None:
            pos = next(i for i,a in enumerate(build_args) if a in ('-i', '--input'))
            source = build_args[pos+1] if pos+1 < len(build_args) else ''
        if not Path(source).is_file():
            print('输入词表不存在；尚未检查或安装依赖。', file=sys.stderr)
            return 2
    try:
        python, mode, detail = choose_runtime(args.cache_dir, install=not args.check)
        if args.check:
            print(json.dumps({'runtime': mode, **detail}, ensure_ascii=False))
            return 0
        print(f'依赖环境：{mode}（兼容版本已复用，无需重复安装）' if mode != 'installed'
              else '依赖环境：首次安装完成', file=sys.stderr)
        if '--summary' not in build_args:
            build_args.append('--summary')
        return subprocess.run([str(python), str(ROOT/'scripts/build_worksheet.py'), *build_args]).returncode
    except (RuntimeError, OSError, subprocess.CalledProcessError) as e:
        print(f'环境准备失败：{e}\n首次安装需要联网；离线时请事先在所选Python中安装 requirements.txt。', file=sys.stderr)
        return 2

if __name__ == '__main__':
    sys.exit(main())
