# Worked example:FlashKDA 的保序计算流

一份走完整流程的真实例子。素材是 **[MoonshotAI/FlashKDA](https://github.com/MoonshotAI/FlashKDA)**(CUTLASS/CuTe,SM90),选它是因为**公开可 clone** —— 下面每个行号你都能自己打开核对。

算子是 Kimi Delta Attention 的前向:通道级门控的 delta rule,chunk-wise 并行。数学形式见 [KDA 论文](https://arxiv.org/abs/2510.04800),这里只关心"代码按顺序算了什么"。

---

## 〇、先摘源码

`fwd_launch.cu` 的两次 launch 就是整份材料的骨架 —— 它同时给出了**执行顺序**和**跨 kernel 的全部数据通道**:

```cpp
// fwd_launch.cu:64-69 —— workspace 分成 6 个独立数组
BF16*  ws_kd  = ...;   // k_decayed
BF16*  ws_qd  = ...;   // q_decayed
BF16*  ws_kr  = ...;   // k_restored
float* ws_gt  = ...;   // g_total
BF16*  ws_inv = ...;   // INV
BF16*  ws_mqk = ...;   // Mqk

// :165  K1:grid(total_tiles, H) —— 每 chunk 独立,写这 6 个 workspace
kernel1<<<grid_k1, block_k1, smem_size_k1, stream>>>(
    tma_load_q, tma_load_k, tma_load_beta, tma_load_g, tma_load_dt_bias,
    tma_store_ws_kd, tma_store_ws_qd, tma_store_ws_kr,
    tma_store_ws_gt, tma_store_ws_inv, tma_store_ws_mqk, ..);

// :199  K2:grid(N, H) —— chunk 轴串行,把这 6 个读回来
kernel2<<<grid_k2, block_k2, smem_size_k2, stream>>>(
    tma_load_v, tma_load_beta2,
    tma_load_ws_kd, tma_load_ws_qd, tma_load_ws_kr,
    tma_load_ws_gt, tma_load_ws_inv, tma_load_ws_mqk,
    tma_load_initial_state, tma_store_final_state, tma_store_out, ..);
```

**这段参数表就是后面画图判断依赖的权威证据**:K1 存了哪 6 个、K2 读了哪 6 个,一一对应。比读函数体可靠 —— 函数体里 buffer 名会被局部变量遮掉,参数表不会。

> 这也印证了 SKILL 正文「第 0 层不可省」那条:如果只交付计算流,读者就看不到"6 个 workspace"这个事实,而它恰恰解释了后面 ⑥ 那条跨过两段的边。

---

## 一、定口径

| 项 | 取值 | 证据 |
|---|---|---|
| `D`(head dim) | 128 | `flash_kda.cpp:107` `TORCH_CHECK(D == 128, ...)` |
| `CHUNK` | 16 | `flash_kda.cpp:10` |
| Q/K/V/G/Beta/Out | BF16 | `flash_kda.cpp:46-51` 六条 `TORCH_CHECK` |
| `A_log` / `dt_bias` | FP32 | `flash_kda.cpp:79,81` |
| 方向 | 前向 | 仓库只有 fwd |

口径里的每一项都带断言行号 —— 这是"证据"的含义:不是我认为它是 128,是代码拒绝其它值。

---

## 二、抓语句:grep 起手式的实际产出

按 SKILL 正文的 CUDA/CUTLASS 起手式 grep:

```bash
grep -nE 'gemm\(|mma_|__expf|expf\(|rsqrtf|__shfl|ex2_approx|sigmoid|bf16_to_f32|BF16\(|FP16\(' \
     csrc/smxx/fwd_kernel1.cuh csrc/smxx/fwd_kernel2.cuh csrc/smxx/utils.cuh
```

1400 行的两个 kernel,**产生数值的语句只有 20 来条**。其余全是 TMA 描述符构造、CuTe layout 代数、pipeline 握手、下标反解 —— 都不进这条线。

被排除的典型:`cute::copy(...)`(搬运)、`local_tile(...)`(视图)、`SM75_U32x1_MOVM_T::copy`(寄存器内转置,不改数值)、`producer_acquire/consumer_wait`(同步)。

> ⚠️ `MOVM_T` 是个边界案例:它是"转置",按判据不改数值 → 排除。但它在这个 kernel 里是关键优化(免掉 U 的 smem 往返),所以**它属于流水图那份材料**,不属于这条线。这正是 SKILL 说的"搬运和同步是另一份材料"。

---

## 三、按执行顺序排

K1、K2 是两次 launch,天然全序。K2 内部是 warp-specialized(LOAD / MMA / STORE,`fwd_kernel2.cuh:190-196`),按 SKILL 第三节的办法**压成一条全序**:计算全在 MMA warp 的 Phase 1→6 里,LOAD/STORE 只搬运 —— 于是直接取 MMA warp 的 Phase 顺序,同步语句删掉。

---

## 四、每行三件事(节选)

完整的 12 段见下面「产出」。这里摘三段,示范三种不同的注释类型。

**(a) 普通的一步 —— 公式 + 精度 + 行号:**

```cpp
g_total(tid) = ex2_approx_ftz_f32(x);       // [f32] γᶜ = 2^{Σ logα}              :337
```

**(b) 带"↑ 为什么"的一步 —— 解释读者看不出来的设计:**

```cpp
r_ki = k * inv_cumsum;                      // [bf16] K̄ = K⊙γ^{-i}                :448
r_kr = k * inv_cumsum * BF16(reg_gt);       // [bf16] γᶜK̄:把 γᶜ 预乘进去          :449
//   ↑ 「1/γ 必须成对出现」的落地:γ^{-i} 只与 γ^j (j>i) 相乘,乘积恒 ≤1 不溢出
//   ↑ γᶜ 预乘进 k_restored ⇒ K2 的状态更新里第二项不必再乘门(见 ⑫)
```

第二条"↑"是**跨段的因果**:这里多乘一个数,是为了让 500 行之外的另一段少乘一个数。不写出来,读者在 ⑫ 处会疑惑"门去哪了"。

**(c) MMA 的三段式精度 —— 同一发 GEMM、两个出口格式:**

```cpp
mma_..._bf16bf16fp16_1warp(k_decayed, k_inv, L_fp16, ..);
                       // [bf16·bf16→f32→fp16] L = K̃K̄ᵀ,出口降 FP16   :465→utils:174
mma_..._bf16bf16bf16_1warp(q_decayed, k_inv, Mqk, ..);
                       // [bf16·bf16→f32→bf16] Mqk = Q̃K̄ᵀ,出口降 BF16  :467→utils:152
//   ↑ 同一个 MMA atom,差别只在 cooperative_gemm 最后那个 sC_store_op lambda。
//     L 喂下游的 FP16 Neumann、Mqk 过 TMA 喂 K2 的 BF16 MMA
//     ⇒「存什么格式」是被下游消费者的输入格式倒推的,不是精度考量
```

这就是 SKILL 说"MMA 必须写成三段"的原因:两行的累加器都是 FP32,但落盘一个 FP16 一个 BF16。只标 `[bf16→bf16]` 会把这个差异抹掉。

**精度记号在这个 kernel 上的实际分布**(全部从模板实参读出,不是推的):

| 记号 | 出现在 | 出处 |
|---|---|---|
| `[bf16·bf16→f32→bf16]` | K2 的 5 发 GEMM,全部 | atom `SM80_16x8x16_F32BF16BF16F32_TN`;降档在 `fwd_kernel2.cuh:570,591,618,644` |
| `[fp16·fp16→fp16]` | 只有求逆 | `SM80_16x8x16_F16F16F16F16_TN`,`utils.cuh:200` |
| `[bf16→f32 FMA→bf16]` | 只有状态递推 | 升 `fwd_kernel2.cuh:714-715`,存回 `:82` |

**(d) 漏掉第三段会直接读错依赖 —— 这是我在这份材料上真犯过的错。** 第一版把 ⑩ 写成:

```cpp
gemm(thr_mma, tCrA_k, tCrB_u_tmp, u_acc[i]);   // [bf16·bf16→f32] U = T·diag(β)(V−K̃S)  :616
```

只标了两段,停在 FP32。读者(以及我自己)于是以为 U 是以 FP32 传给下游的。实际下一行就降回去了:

```cpp
cute::transform(u_acc[i], u_bf16[i], [](float x){ return BF16(x); });
                       // [f32→bf16] U 立刻降 BF16,FP32 累加器当场丢弃            :618
//   ↑ 这是【硬约束不是取舍】:U 后面要当 MMA 的 B 操作数,atom 是 F32BF16BF16F32,
//     B 必须 BF16 —— FP32 累加器根本喂不进去。下游 :641 和 :694 拿到的都是 BF16
```

**查法**:把降档语句也 grep 一遍(`grep -nE 'return BF16\(x\)|return FP16\(x\)'`),数量应该和 GEMM 发数对得上;对不上就是有发漏标了第三段。这个 kernel grep 出来正好 4 处,而 MMA warp 里有 4 发需要接力的 GEMM。

由此得到一条只有把三段都标出来才看得见的结论:**FP32 只活在单发 GEMM 的累加器里,发与发之间一律 BF16**,从没跨过任何一条指令边界。

---

## 五、分段

12 段:K1 八段(①归一化 ②门+cumsum ③γᶜ ④四个待乘量 ⑤L ⑥Mqk ⑦掩码 ⑧求逆),K2 四段(⑨双GEMM ⑩U ⑪两项相加 ⑫状态递推)。

⑨ 拆成 ⑨a/⑨b 是因为**下游不同**:⑨a 的 $\tilde KS$ 进 ⑩,⑨b 的 $\tilde QS$ 进 ⑪。合成一个节点就看不出这是两条独立的路 —— 这与 SKILL 正文"下游不同必须分节点"是同一条判据。

---

## 六、画图:三处踩坑与修法

**(a) 无入边的 subgraph 被排错位。** 第一版渲出来 5319×2857(宽扁),K2 整个被 dagre 甩到 K1 **左边**。原因:K2 的入口节点 `s_acc` 没有任何入边(状态来自 `initial_state`,不来自 K1)。

修法是补一条**虚线控制边**,既修布局又如实标出语义:

```
A8 -.->|"K1 整个 launch 结束后 K2 才启动<br/>只有执行序,S 不来自 K1"| S0
```

修完 3410×3554(纵向)。**这条边是"控制"不是"数据",所以必须虚线** —— 画成实线就等于骗读者说 S 是 K1 算的。

**(b) `<` 被吃掉。** 节点里写 `Mqk: i&lt;j 清零` —— 即使已经转义,经 markdown → mermaid 两道解码后仍被当成 HTML 标签,整行渲染成 `Mqk: i—`。改写成不含 `<` 的等价表述:`Mqk: 只保留 i≥j(含对角)`。

**(c) 渲染完必须读回。** 上面两个问题**都只有看图才能发现** —— 脚本报告"rendered 1, failed 0",两次都是。

**边的分类**(这个例子里三种边都有):

| 线型 | 含义 | 本例中 |
|---|---|---|
| 细实线 | kernel 内数据依赖 | label 写 SMEM/寄存器变量原名 |
| 粗实线 `==>` | 跨 kernel 依赖(走 GM) | 6 条,label 写 `ws_kd`/`ws_qd`/… 正好对应 6 个 workspace |
| 虚线 | 不传数据 | 2 条:跨 chunk 状态回边、K1⇢K2 执行序边 |

**fan-out 不是链**:⑨a、⑨b、⑫ 三段都读**同一个未更新的 `s_acc`**,是从一个源拉出的三条边。画成 `⑨a→⑨b→⑫` 会凭空捏造出不存在的串行。判据就是 SKILL 说的:回源码看三者的入参是不是同一个变量 —— 是(`s_acc`,`fwd_kernel2.cuh:537,546` / `676`)。

---

## 七、验收:这个例子的三句"一眼看出什么"

1. **蓝橙交替只有 3 次,且全在 K1 内**;K2 的 ⑨–⑫ 全橙,一次不回蓝。对比异构架构(计算单元分离、必须经共享存储交货)的同类算子 —— 那里每次交货都是一次降精度。**同构 SM 上没有这个税,所以 FlashKDA 的降精度点全是主动选的**,不是被硬件逼的。
2. **⑫ 是全仓唯一升到 FP32 做的 FMA**:state 存 BF16(`fwd_kernel2.cuh:82`),递推那一步升 FP32 算完再存回 BF16(`:714-715`)。"存储降档"和"计算降档"是两件事 —— 但注意它同样没让 FP32 跨过指令边界,见四(d)。
3. **`ws_mqk` 那条粗线跨过了 ⑦⑧**:Mqk 在 ⑥ 算完、到 ⑪ 才用,中间两段与它无关。这解释了为什么要落 **6 个** workspace 而非 3 个 —— 算得早、用得晚的量,跨 kernel 必须落地。

第 1 条是这张图**唯一没法从代码直接读出来的结论**,也是画图的净收益。

**公式覆盖表**(参考公式 ↔ 段号)是完整性的唯一证据,10 条公式全部对上了段号,无遗漏、无孤段。

**未覆盖**:反向(仓库只有 fwd);`StateFP32=true` 分支的 SMEM 内 BF16↔FP32 转换(`utils.cuh:322-380`,只在出入口各一次,不进主流);varlen 下 `cu_seqlens` 线性扫反解(`fwd_kernel1.cuh:155-168`,下标计算不产生数值);`TMA_DISABLE_ALL` 调试分支未读。
