#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""编号一致性:同一个圈号在全文里只能指同一件事。

为什么需要它:段号的唯一用途是让读者在图、代码块、正文、notebook 之间跳转。
一旦同一个符号在两处指不同的东西,索引就失效 —— 而且**每一处单独看都自洽**,
只有把全文的编号并排列出来才会暴露。实测中一份材料同时存在两套编号
(计算流 ①–⑫ 与逐步讲解 ①–⑯),⑧ 一处指"损失"、一处指"语言模型前向",
写的时候完全没察觉。

做法:把每个圈号后面紧跟的那个短标签收集起来。一个圈号绑定了两个以上不同标签,
就是候选冲突 —— 输出成一张表由人判定(同一件事的不同说法不算冲突,
但**你会被迫为每个编号选定一个说法**,这本身就是要的纪律)。

用法:
    python check_numbering.py 材料.md
    python check_numbering.py 材料.md 另一份.md demo/x.ipynb   # 多份一起查,跨文件也要一致
    python check_numbering.py 材料.md --max-label 12           # 标签取多长(默认 10 字)

退出码非 0 表示有圈号绑定了多个标签。
"""
import argparse
import io
import json
import os
import re
import sys
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

CIRCLED = '①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳'
# 编号后紧跟的标签:允许中英数与少量符号,遇到标点/括号/竖线就停
LABEL_RE = r'[ \t]*([A-Za-z0-9一-鿿_.·\-]{2,%d})'


def load(path):
    if path.endswith('.ipynb'):
        nb = json.load(io.open(path, encoding='utf-8', errors='replace'))
        return '\n'.join(''.join(c.get('source', [])) for c in nb.get('cells', []))
    return io.open(path, encoding='utf-8', errors='replace').read()


def fragments(line):
    """把一行拆成"**定义处**"的片段。只认三种位置:

    1. 小节标题(`#### ⑧ 损失`)
    2. 表格单元格(`| ⑧ 损失 | … |`)
    3. 代码块里的分隔注释(`# ═══ ⑧ 损失 ═══`)

    **正文段落与引用块里的枚举不算定义** —— 读法里的"① … ② …"是列举,不是段号;
    "见 ⑫ 那条边"是提及,不是定义。不做这层过滤,输出全是噪声(实测第一版正是如此)。
    """
    t = line.strip()
    if t.startswith('|'):                                  # 表格行:每个单元格各看一次
        return [c.strip() for c in t.strip('|').split('|')]
    m = re.match(r'^#{1,6}\s+(.*)$', t)                     # markdown 标题
    if m:
        return [m.group(1).strip()]
    m = re.match(r'^(?:#|//)\s*[═=─-]*\s*(.*)$', t)         # 代码块里的注释
    if m:
        return [m.group(1).strip()]
    return []


def norm(label):
    """归一化:去掉尾部的助词与标点,便于把"损失"与"损失:"看成同一个。"""
    return label.strip().rstrip(':,。、)]』」')


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('sources', nargs='+', help='材料文件,可给多份(md / ipynb)')
    ap.add_argument('--max-label', type=int, default=10, help='标签取多长(默认 10 字)')
    ap.add_argument('--quiet', action='store_true', help='只报冲突')
    a = ap.parse_args()

    # (作用域, 圈号) → 标签 → [出处];作用域 = 最近的一个 h2/h3 标题
    bind = defaultdict(lambda: defaultdict(list))
    pat = re.compile('^([%s])%s' % (CIRCLED, LABEL_RE % a.max_label))
    for src in a.sources:
        scope = '(文件开头)'
        for i, line in enumerate(load(src).split('\n'), 1):
            h = re.match(r'^(#{2,3})\s+(.*)$', line.strip())
            if h:
                scope = h.group(2).strip()[:26]
            for frag in fragments(line):
                m = pat.match(frag)
                if not m:
                    continue
                num, label = m.group(1), norm(m.group(2))
                if label:
                    bind[(scope, num)][label].append('%s:%d' % (os.path.basename(src), i))

    # 机械可判的那半:同一作用域内一个编号绑定了多个标签 —— 硬失败
    hard = {k: v for k, v in bind.items() if len(v) > 1}

    # 需要人判的那半:同一个编号在多个作用域里指不同的东西 —— 可能是合法的多命名空间
    per_num = defaultdict(list)
    for (scope, num), labs in bind.items():
        for lab in labs:
            per_num[num].append((scope, lab))
    cross = {n: v for n, v in per_num.items()
             if len({lab for _, lab in v}) > 1}

    if not a.quiet and cross:
        print('跨作用域的编号(**请确认这是几个不同的命名空间,而不是几套指同一件事的编号**):')
        print('%-4s %-30s %s' % ('编号', '所在小节', '它在那里指什么'))
        print('-' * 78)
        for num in CIRCLED:
            for scope, lab in sorted(per_num.get(num, [])):
                print('%-4s %-30s %s' % (num, scope, lab))
        print()

    if hard:
        print('同一小节内编号冲突(%d 处,必须改):' % len(hard))
        for (scope, num), labs in hard.items():
            print('  %s 在「%s」里同时指:' % (num, scope))
            for lab, where in sorted(labs.items(), key=lambda kv: -len(kv[1])):
                print('     %-22s %s' % (lab, ', '.join(where[:4])))
        print('\n**一个编号在一个作用域内只能指一件事。**')
        print('若两套编号指的是同一个对象(比如都在编号"一次训练步"),')
        print('把"关于主干的观察"移出段号,另用 A/B/C。')
        return 1
    print('同一小节内没有编号冲突。**跨小节的那张表需要人确认命名空间是有意分开的。**')
    return 0


if __name__ == '__main__':
    sys.exit(main())
