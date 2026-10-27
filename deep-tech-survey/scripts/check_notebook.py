#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""核对 notebook 是不是**完整执行过**的 —— 交付带输出的 ipynb 之前跑这个。

为什么需要它:notebook 的价值在于"分阶段看到真实结果"。一旦有格没输出、
或带着报错交付出去,读者第一反应是"这东西根本没跑通",整份材料的可信度一起塌。
而这件事从文件外观完全看不出来 —— json 里少一段 outputs 不会有任何提示。

检查项:
    1. 每个代码单元都有输出        —— 抓"这一格没执行"
    2. 没有 error 类型的输出       —— 抓"跑了但报错了还交出去"
    3. 有输出的单元里图的张数      —— 报数供人对照(不判定对错)
    4. 单元执行序号单调递增        —— 抓"东一格西一格乱跑出来的状态"

用法:
    python check_notebook.py demo/x.ipynb
    python check_notebook.py demo/x.ipynb --allow-empty setup,imports   # 允许空输出的单元关键词

退出码非 0 表示这个 notebook 不该交付。
"""
import argparse
import io
import json
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('notebook')
    ap.add_argument('--allow-empty', default='',
                    help='逗号分隔的关键词;源码里含这些词的单元允许没有输出')
    a = ap.parse_args()

    with io.open(a.notebook, encoding='utf-8', errors='replace') as f:
        nb = json.load(f)

    allow = [w.strip() for w in a.allow_empty.split(',') if w.strip()]
    cells = nb.get('cells', [])
    code = [c for c in cells if c.get('cell_type') == 'code']
    md = len(cells) - len(code)

    no_out, errs, figs, counts = [], [], 0, []
    for i, c in enumerate(code):
        src = ''.join(c.get('source', []))
        outs = c.get('outputs', [])
        if not outs and not any(w in src for w in allow):
            no_out.append((i, src.strip().split('\n')[0][:56]))
        for o in outs:
            if o.get('output_type') == 'error':
                errs.append((i, o.get('ename', '?'), (o.get('evalue') or '')[:60]))
            data = o.get('data', {})
            if 'image/svg+xml' in data or 'image/png' in data:
                figs += 1
        if c.get('execution_count') is not None:
            counts.append(c['execution_count'])

    ok_order = counts == sorted(counts)

    print('%s:%d 个单元(%d markdown / %d 代码),%d 张图'
          % (a.notebook, len(cells), md, len(code), figs))
    print('[%s]   每格都有输出        缺 %d 格' % ('ok' if not no_out else 'FAIL', len(no_out)))
    for i, head in no_out[:5]:
        print('       第 %d 个代码单元:%s' % (i, head))
    print('[%s]   没有报错格          %d 个' % ('ok' if not errs else 'FAIL', len(errs)))
    for i, name, val in errs[:5]:
        print('       第 %d 个代码单元:%s %s' % (i, name, val))
    print('[%s]   执行序号单调递增' % ('ok' if ok_order else 'FAIL'))

    print()
    if no_out or errs or not ok_order:
        print('这个 notebook 不是完整执行过的状态,重跑一遍再交付。')
        return 1
    print('notebook 完整执行过,可以交付。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
