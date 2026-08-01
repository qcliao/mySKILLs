# 各框架怎么读:找什么、在哪找

同一个问题("stage 怎么划的、什么在并行、精度怎么走")在五种框架里看不同的东西。

## Triton(如 FLA)

**最好读的一种,适合当参考实现先看。**

| 要回答的 | 看哪 |
|---|---|
| 几个 kernel | Python 侧的 `..._fwd` 函数,一路读下来就是调用链 |
| 并行维度 | `grid = (...)` 或 `@triton.jit` 上方的 launch 代码 |
| 串行维度 | kernel 内的 `for` —— **不在 grid 里的就是串行的** |
| tiling | `BLOCK_*` / `BT` / `BC` / `BV` 常量,以及 `tl.arange` 的形状 |
| 精度 | `tl.dot(..., allow_tf32=)`、`.to(tl.float32)`、accumulator 的初始 dtype |
| 中间量放哪 | 有没有 `.new_empty(...)` → 落 HBM;否则全在寄存器 |

**关键信号:`k.new_empty(B, NT, HV, K, V)` 这类分配。** 它意味着"每个块的状态
都要落 HBM",是 stage 拆分的铁证,也是显存代价的来源(算一下有多少 MB)。

**autotune 的配置列表**告诉你作者认为哪些参数重要。

## CUDA / CUTLASS(如 FlashAttention 3/4)

**最难读,但流水信息最丰富。** 重点是 warp specialization 与异步。

| 要回答的 | 看哪 |
|---|---|
| 角色分工 | `*_warp_ids = (...)` 常量,以及按 `warp_idx` 分派的主体 |
| 有几个 buffer slot | `*_stage` 常量;常常是**拿容量倒算的**,附近有注释 |
| 阻塞点 | `producer_acquire` / `consumer_wait` —— 这就是 stall 的位置 |
| 释放点 | `consumer_release` / `producer_commit` —— 决定下一笔搬运何时能发 |
| 同步 | `alloc_barrier` / named barrier,barrier 名字通常自带语义 |
| 精度 | MMA 的 `ElementA/B/Accumulator` 模板参数 |

**画流水图前必须做的两件事**:
1. 数出 slot 数(或从容量倒算)
2. 找到所有 release 点,记下源码行号

否则画出来一定是"无限 buffer"的假流水。

**源码注释常常直接说出设计意图**(如 "2 WGs having different code" = ping-pong)。
搜注释比读代码快。

## TileLang(如 FlashQLA)

介于 Triton 与 CUDA 之间:有 `T.gemm` 这种高层原语,但也能手写 warp 专门化。

| 要回答的 | 看哪 |
|---|---|
| 调用链 | Python 侧 `__init__.py` 的导出与编排 |
| 精度 | 显式的 `qkva_dtype` / `accum_dtype` 变量 |
| 门控/缩放在哪 | 看函数签名收不收那个参数 —— **签名不含 `g` 就说明门不在这一步** |
| 分治结构 | 求逆这类常写成级联(16 → 32 → 64),找块合并的公式 |

**签名是强证据。** 某个 kernel 的签名不含门参数,就能断定它用的是原始输入、
门被推迟到后面 —— 这类结论不用读实现体就能下。

## AscendC / CANN(NPU)

硬件事实(各级 buffer 容量、单元分工、同步代价)以手册和实测为准,
本节只说源码读法 —— 别把读法里的示例数字当成硬件参数。

| 要回答的 | 看哪 |
|---|---|
| stage 划分 | `SyncAll()` / `CROSS_CORE_SYNC` —— **每次全核同步就是一个 stage 边界** |
| 每 stage 干什么 | `if (stage == N)` 或按 block_idx 分派的分支 |
| tiling 三级 | Single(核间)→ L1 → L0(Base),三个数不同,别混 |
| buffer 复用 | `TBuf` 的 `Get<T>()` 调用点;同一块在不同 stage 装不同东西是常态 |
| ping-pong | 申请 `32K*2` 配一个 flag 在两半间跳,不是两个 `TBuf` |
| 精度 | `Mmad` 的输入输出类型、`Cast` 调用、累加器位宽 |

**Cube/Vector 分离是一切的根源**:一个 stage = 一段连续的 Cube 计算或
一段连续的 Vector 计算,交界处必须同步。**同步很贵,所以 stage 数就是设计的核心权衡。**

**注意区分模板路径与手写路径。** 同一个算子的不同数据布局/量化模式可能一个走模板
(`Matmul<...>`)、一个手写 `Mmad` 循环。别引了 A 路径的代码去讲 B 路径的设计。

## PyTorch 参考实现 / naive 版

**先读它。** 它是 ① 计算流的最直接对应,也是精度验证的基线来源
—— 但注意基线要**同精度**(见 SKILL.md ④)。

递归/循环版最能看清依赖关系;chunk/并行版是它的恒等变形。
**两者数学等价**,不要把低精度下的既定误差当成变形引入的 bug。

## 取源码的通道

**本地代码树优先** —— 手上有就直接读,别去网上找同一份(版本可能不同)。

WebFetch 被 GitHub 拦时:

```bash
# 单文件原文
curl -sL https://raw.githubusercontent.com/<owner>/<repo>/<branch>/<path>
# 整仓文件树,先看结构再决定拉哪些
curl -sL "https://api.github.com/repos/<owner>/<repo>/git/trees/<branch>?recursive=1"
```

raw 端点会间歇 reset,重试 2-3 次。

## 论文与官方图

时序类结论优先找**官方图**再自己画:很多 kernel 的论文/博客里有权威流水图
(FA3 的 ping-pong 图、AMLA 的 preload 图)。找到就连出处链接,
让读者能自己比对。

**别拿上一代的图当这一代用** —— 架构换代时流水结构会变(如寄存器里的累加器
换成 SMEM、warp 组数变化)。
