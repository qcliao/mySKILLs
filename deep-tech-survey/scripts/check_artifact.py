#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""核对生成产物是否与源文件同步 —— 报告"完成"之前跑这个。

为什么需要它:材料的读者看的是产物(HTML/PDF/PPT),不是源文件。改完源文件却没
重新生成,读者就还在看旧内容,而你以为已经改好了。这个失败模式很难自查,因为
"我改对了"的感觉和"读者看到了"之间没有任何提示会告警。

用法:
    python check_artifact.py 材料.md 材料.html
    python check_artifact.py 材料.md 材料.html --expect "新措辞" --gone "旧措辞"

检查项:
    1. 产物 mtime 必须新于源文件           —— 抓"忘了重新生成"
    2. --expect 的串必须在两边都命中       —— 抓"生成了但没生效"
    3. --gone   的串必须在两边都消失       —— 抓"新旧内容并存"

退出码非 0 表示不同步,不要在这种状态下报告完成。
"""
import argparse
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def read(path):
    with io.open(path, encoding='utf-8', errors='replace') as f:
        return f.read()


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('source', help='源文件,如 材料.md')
    ap.add_argument('artifact', help='生成产物,如 材料.html')
    ap.add_argument('--expect', action='append', default=[],
                    help='本次新增的串,两边都应命中(可重复)')
    ap.add_argument('--gone', action='append', default=[],
                    help='本次删除的串,两边都应为 0(可重复)')
    a = ap.parse_args()

    problems = []

    for p in (a.source, a.artifact):
        if not os.path.exists(p):
            print('缺文件: %s' % p)
            return 2

    # 1. mtime
    ts, ta = os.path.getmtime(a.source), os.path.getmtime(a.artifact)
    if ta < ts:
        problems.append('产物比源文件旧 %.0f 秒 —— 大概没重新生成' % (ts - ta))
        print('[FAIL] mtime  产物落后 %.0f 秒' % (ts - ta))
    else:
        print('[ok]   mtime  产物新于源文件 %.0f 秒' % (ta - ts))

    src, art = read(a.source), read(a.artifact)

    # 2. 新串两边都要有
    for s in a.expect:
        cs, ca = src.count(s), art.count(s)
        if cs and ca:
            print('[ok]   新串   %-28s src=%d art=%d' % (s[:28], cs, ca))
        else:
            problems.append('新串 %r 未同时出现(src=%d art=%d)' % (s[:40], cs, ca))
            print('[FAIL] 新串   %-28s src=%d art=%d' % (s[:28], cs, ca))

    # 3. 旧串两边都要没
    for s in a.gone:
        cs, ca = src.count(s), art.count(s)
        if cs or ca:
            problems.append('旧串 %r 仍存在(src=%d art=%d)' % (s[:40], cs, ca))
            print('[FAIL] 旧串   %-28s src=%d art=%d  应为 0/0' % (s[:28], cs, ca))
        else:
            print('[ok]   旧串   %-28s 两边均已清除' % s[:28])

    print()
    if problems:
        print('不同步(%d 项):' % len(problems))
        for p in problems:
            print('  - ' + p)
        print('\n先重新生成,再报告完成。')
        return 1
    print('产物与源文件一致。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
