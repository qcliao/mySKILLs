---
name: deep-tech-survey
description: Use when producing a deep technical write-up, report, or presentation that must be defensible — surveying papers then cross-checking against real source code, comparing several implementations of the same algorithm, drawing timing/occupancy/architecture diagrams, or annotating numerical precision. Also covers how to structure the material (per-section template: domain model → execution-flow diagram → code correspondence → 读法) and how to render it to md/HTML/PPT — heading hierarchy, auto-fit font sizing, text-clipping prediction, stale-artifact discipline. Triggers include "调研/survey 一下"、"结合代码看实现"、"对比几套实现"、"画个流水图/占用图/gantt"、"写份材料/技术报告"、"生成 HTML/PPT"、"文字被裁/没显示出来"、"标题不明显"、"这个图对吗"、"核实一下"、"deep dive", and any task where a claim will be written down and later defended in front of someone who knows the code. Complementary to [[ascend-davinci-architecture]] for NPU domain facts.
---

# 深度技术 survey:从论文到源码到可辩护的材料

这份 skill 的核心主张:**材料里每一条断言都要能追到一个已核实的事实。**
survey 的产出不是"一份文档",而是一组**可辩护的断言** —— 文档、HTML、PPT 都只是载体。
但载体决定断言能不能被读到:标题不显眼、文字被裁、产物没重新生成,写对了也等于没写。
形式上的经验见 `references/output-forms.md`。

## 何时用

要写下会被懂代码的人当面质疑的东西时。典型场景:技术材料、汇报、设计评审、
方案对比、给别人讲清一套实现。**不适用**于只需一个答案的查询式提问。

## 四步主循环

每一步的产出物不同,不能跳步 —— 跳过 ① 就没有可核对的先验,跳过 ② 会把论文的
省略当成事实。

### ① 论文 → 骨架 + 可引用坐标

论文给的是"应该长什么样"的**先验**和权威出处(章节号、图号),**不是实现细节**。
标了出处,后面才有东西可核对。允许发散、结合网上资料补背景。

### ② 源码 → 校正先验(校正本身就是产出)

拿源码逐条核对 ① 的先验。**论文与实现的差异比论文原文更有信息量** —— 它标出了
论文省略掉的工程约束。校正出的每一处都要写进材料,而不是悄悄改掉。

常见校正类型:函数实际的调用位置(fwd 还是 bwd)、真实的 kernel 数与插入顺序、
返回值个数、按硬件/版本分叉的常量、真实的同步原语名。

取数通道与可信度分级见 `references/evidence-grading.md`。

### ③ 多实现横向对照 → 定位设计自由度

同一件事找 N 套实现摆一起。**分歧处 = 设计自由度,一致处 = 硬约束。**
这是通用手法,不限某个领域。

对照表**按不变量排行**(领域概念、公式项、流程阶段),不按各家的变量名排 ——
不同实现的命名根本对不上,按名字排的表读者看不出差异。

### ④ 反推 → 把陈述变推导

已知的容量/带宽/规模约束能反解出材料里那些"神秘常量"的来源。
**把结论变成推导,比多给一个数字有用得多** —— 一旦读者能自己推一遍,
这条断言就不需要信任你。

反推也顺带暴露量级错误:算不出来的数,往往是原先某处单位或层级搞错了。

## 标准节模板:五个部件,顺序固定

内容对不对是上面四步的事;**部件齐不齐决定读者能不能读懂**。
讲清"某套实现怎么做某件事"的小节,一律按这个顺序摆:

```
① 一句话定位   这节解决什么 / 承接上一节的哪个问题
② 领域模型     公式、阶段表、不变量 —— 先立锚
③ 执行流图     流程图/时序图,节点标阶段编号 ①②③④
④ 代码对应     每阶段贴真实代码骨架,带真实行号
⑤ 读法         把图和代码翻译成论点
```

三条硬约束:

- **② 必须在 ④ 之前** —— 先给阶段编号,代码块才能用 `═══ ① … ═══` 挂回去;
  反过来读者得自己反推每段代码在算法里是哪一项
- **③④ 用同一套编号**,互相锚定
- **⑤ 不能省** —— 图和代码只呈现事实,论点必须显式写出来。这是最容易漏、
  最影响可读性的部件

展开(代码块的三类旁注、读法的三种写法、横向对比节的额外部件、全篇骨架)见
`references/document-skeleton.md`。

## 落笔前的 11 类自查

history 里所有被当面纠正的错误都收敛到这 11 类。**每次落笔前逐条过一遍**,
成本几分钟,漏掉一条就是一次返工。

| # | 类型 | 自查问题 |
|---|---|---|
| 1 | **层级归属错** | 这个数是"这一级本身"还是"切进下一级的粒度"?二者常差好几倍 |
| 2 | **资源无界** | 图/叙述里是否隐含 buffer、slot、队列无限?**画对的流水必须有 stall** |
| 3 | **依赖违背** | 每条并行边:这两块之间真的没有数据依赖吗? |
| 4 | **调用位置错** | 这个函数真的在我说的那条路径上吗?(fwd / bwd / 只在某分支) |
| 5 | **签名漂移** | 返回值个数、常量值,是否按版本或硬件分叉? |
| 6 | **陈旧产物** | 改完源文件后,**重新生成了吗**?生成时目标文件被锁了吗? |
| 7 | **自造缩写** | 我用的名字是源码里的,还是我自己编的? |
| 8 | **过度采信 agent 汇总** | agent 报的数值/层级,我亲自 Read 回源码核过吗? |
| 9 | **猜想当事实** | 这条是核实过的,还是我(或对方)的推测?推测必须标记 |
| 10 | **量级/单位错** | 按字节重算一遍对得上吗?图上标签是单份还是总量? |
| 11 | **配置静默失效** | 我设的那个开关,在当前 dtype/路径下真的生效吗? |

第 6 类在 history 里出现最多,而且是**元错误**:源文件改对了但没重新生成,
对方看到的还是旧产物,于是"同一个问题"被反复提出。见 `references/verification.md`。

## 三条贯穿全程的纪律

**双向核验。** 对方的质疑先默认成立、去核 —— history 里标注"(用户指出,属实)"
的居多。但反向也有:对方自述的结论核完是错的(那次是"两种形式不等价")。
**双向核验,不无条件采信任一方**;核出对方错了,照实写并给出证据。

**hedge 是纪律,不是含糊。** 核不到就不写、推断要标成推断、runtime 值不编造总数、
省略要显式标记。四种处理见 `references/evidence-grading.md`。

**治本不治标。** 同一类问题第二次出现时,改的应该是产生它的机制,不是躲开它的措辞。

## 细节参考

- `references/evidence-grading.md` — 证据分级、四种 hedge、骨架代码"删枝"手法、取数通道
- `references/diagram-as-claim.md` — 示意图的七条视觉断言检查表、mermaid vs 手写 SVG 分工
- `references/document-skeleton.md` — 标准节的五个部件、代码旁注约定、读法写法、全篇骨架
- `references/material-anchoring.md` — 按领域模型组织、降级≠删除、从困惑点找解释入口
- `references/verification.md` — 结构不变量计数、精度基线怎么选才可信、陈旧产物
- `references/output-forms.md` — md/HTML/PPT 三种载体的分工、标题层级、自适应字号与溢出预测
