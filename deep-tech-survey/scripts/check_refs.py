#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把材料里每一条 "文件:行号" 引用回源打印,供人工比对 —— 抓行号漂移。

为什么需要它:数值写错了,内行一眼看出"这个数不对";**行号写错了没有任何症状** ——
文字通顺、格式正确、看起来完全可信,只有读者真去点开那一行才发现对不上。
实测中一份 130 多条引用的材料,自认为逐条核过,仍有 4 条偏移 1-3 行;
换了代码树版本之后,又有 2 条"行号仍然存在、但指向了别的代码"。

脚本能判定:文件存在、行号不越界、区间端点合法、短名引用有唯一候选。
脚本判定不了:该行内容是否支撑正文 —— 所以它的主要输出是一张
"引用 → 该行真实内容"的并排表,由人扫一遍。130 条约两分钟。

约定:**每个文件在正文里至少出现一次完整路径**(相对代码树根),
之后才允许用短名(如 `train.py:308`)引用 —— 短名靠这条规则解析。

用法:
    python check_refs.py 材料.md --root /path/to/repo
    python check_refs.py 材料.md --root core=/path/to/A --root ext=/path/to/B
    python check_refs.py 材料.md --root /path/to/repo --quiet   # 只报问题,不打印并排表

多代码树时可给前缀绑定:`--root <前缀>=<路径>`,材料里以该前缀开头的引用只在该树解析;
不带前缀的 `--root` 是兜底树,按给出顺序尝试。

退出码非 0 表示有引用指向不存在的文件、越界的行号,或短名无法唯一解析。
"""
import argparse
import io
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 形如 `path/to/file.py:123`、`file.py:123-145`,反引号可有可无。
# 扩展名列表按需增补 —— 只认代码与文档,避免把版本号之类的东西当引用。
EXTS = r'py|md|rst|c|cc|cpp|h|hpp|cu|cuh|ts|tsx|js|go|rs|java|sh|yaml|yml|toml|txt'
# 一条引用可以带多组行号:`file.py:12,33`、`file.py:12-20,33-40`、`file.py:583,:735`。
# **逗号续写这一种最容易漏检** —— 只校验第一组,后面几组就成了没人核过的数字。
REF_RE = re.compile(
    r'`?([A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:%s))`?:'
    r'(\d+(?:-\d+)?(?:\s*,\s*:?\d+(?:-\d+)?)*)' % EXTS)
RANGE_RE = re.compile(r':?(\d+)(?:-(\d+))?$')


def parse_roots(values):
    """--root 参数 → [(前缀 or None, 绝对路径)]"""
    roots = []
    for v in values:
        if '=' in v and not os.path.exists(v):
            prefix, path = v.split('=', 1)
        else:
            prefix, path = None, v
        path = os.path.abspath(path)
        if not os.path.isdir(path):
            print('不是目录: %s' % path)
            sys.exit(2)
        roots.append((prefix, path))
    return roots


def resolve(relpath, roots):
    """按前缀绑定 → 兜底树的顺序解析。返回 (绝对路径, 树名) 或 (None, None)。"""
    for prefix, root in roots:
        if prefix is not None and relpath.startswith(prefix):
            sub = relpath[len(prefix):].lstrip('/') if relpath != prefix else relpath
            for cand in (os.path.join(root, sub), os.path.join(root, relpath)):
                if os.path.exists(cand):
                    return cand, os.path.basename(root)
    for prefix, root in roots:
        if prefix is None:
            cand = os.path.join(root, relpath)
            if os.path.exists(cand):
                return cand, os.path.basename(root)
    return None, None


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('source', help='材料源文件(md)')
    ap.add_argument('--root', action='append', default=[], required=True,
                    help='代码树根,可重复;支持 <前缀>=<路径> 绑定')
    ap.add_argument('--quiet', action='store_true', help='只报问题,不打印并排表')
    a = ap.parse_args()

    roots = parse_roots(a.root)
    with io.open(a.source, encoding='utf-8', errors='replace') as f:
        md = f.read()

    refs = []
    for m in REF_RE.finditer(md):
        rel = m.group(1)
        for part in m.group(2).split(','):
            rm = RANGE_RE.match(part.strip())
            if not rm:
                continue
            first = int(rm.group(1))
            refs.append((rel, first, int(rm.group(2)) if rm.group(2) else first))

    if not refs:
        print('材料里没有 "文件:行号" 形式的引用 —— 确认这是有意为之。')
        return 0

    # 第一遍:能靠前缀/兜底直接定位的,建立 basename → 全路径索引,供短名引用解析。
    index = {}
    for rel, _a, _b in refs:
        path, _ = resolve(rel, roots)
        if path is not None:
            index.setdefault(os.path.basename(rel), set()).add(path)

    seen, bad, ok_n, cache = set(), [], 0, {}
    for rel, s_line, e_line in refs:
        if (rel, s_line, e_line) in seen:
            continue
        seen.add((rel, s_line, e_line))

        path, _root = resolve(rel, roots)
        if path is None:
            cands = index.get(os.path.basename(rel), set())
            if len(cands) == 1:
                path = next(iter(cands))
            elif len(cands) > 1:
                bad.append('%s:%d —— 短名有 %d 个候选,正文里应写全路径:%s'
                           % (rel, s_line, len(cands), sorted(cands)))
                continue
            else:
                bad.append('%s:%d —— 无法解析(正文里没有该文件的完整路径引用,'
                           '或代码树根给错)' % (rel, s_line))
                continue

        if path not in cache:
            with io.open(path, encoding='utf-8', errors='replace') as f:
                cache[path] = f.read().split('\n')
        lines = cache[path]
        if s_line < 1 or e_line > len(lines) or s_line > e_line:
            bad.append('%s:%d-%d —— 越界或区间倒置(该文件共 %d 行)'
                       % (rel, s_line, e_line, len(lines)))
            continue

        ok_n += 1
        if not a.quiet:
            txt = lines[s_line - 1].strip()
            if len(txt) > 90:
                txt = txt[:87] + '...'
            span = '%d' % s_line if s_line == e_line else '%d-%d' % (s_line, e_line)
            print('  %-56s %-9s %s' % (rel, span, txt))

    print()
    print('可解析引用 %d 条,涉及 %d 个文件。' % (ok_n, len(cache)))
    if bad:
        print('\n有问题的引用(%d 条):' % len(bad))
        for x in bad:
            print('  - ' + x)
        return 1
    print('文件与行号均存在。**该行内容是否支撑正文,脚本判定不了 —— 扫一遍上面那张表。**')
    return 0


if __name__ == '__main__':
    sys.exit(main())
