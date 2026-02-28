---
name: ai-product-guidelines
description: 产品中集成 AI 功能的设计与实现指南。涵盖多 API 适配、设置项设计、多模态处理、语言本地化、用量展示、交互设计、动效反馈等方面的最佳实践。适用于需要接入 LLM API 的桌面/Web 应用开发。
---

# AI 产品功能集成指南

为应用产品集成 AI（LLM）功能时的设计原则与实现规范，从实际踩坑经验中提炼。覆盖后端协议适配、前端交互体验、视觉反馈设计三大维度。

---

## 1. 多 API 格式适配

### 1.1 协议抽象

不要假设只有一种 API 格式。至少支持 **OpenAI** 和 **Anthropic** 两种主流协议：

| 维度 | OpenAI 格式 | Anthropic 格式 |
|------|------------|---------------|
| URL 后缀 | `/chat/completions` | `/v1/messages` |
| 认证头 | `Authorization: Bearer <key>` | `x-api-key: <key>` + `anthropic-version` |
| System 消息 | `role: "system"` 作为消息 | 顶层 `system` 字段 |
| 流式格式 | `data: {"choices":[...]}` | `event: content_block_delta` + `data: {...}` |
| 工具调用 | `tool_calls` 数组 + `role: "tool"` 回复 | `type: "tool_use"` 内容块 + `role: "user"` 带 `tool_result` |
| 停止原因 | `finish_reason: "tool_calls"` | `stop_reason: "tool_use"` |

### 1.2 不要假设兼容性

许多 API 声称"兼容 OpenAI 格式"，但实际有差异：

- **不要盲目发送 `max_tokens`**：某些 OpenAI 兼容 API（如智谱）会对无效的 `max_tokens` 值返回 400 错误。对 OpenAI 格式，建议不发送此字段，让 API 自行决定。
- **不要假设多模态支持**：即使 API 兼容 OpenAI 格式，不代表支持 Vision（`image_url` 类型的 content block）。发送不支持的内容类型会导致参数错误。
- **参数白名单**：只发送目标 API 确实支持的参数，避免未知参数导致报错。

---

## 2. 设置项设计

### 2.1 拆分语义不同的参数

不要用一个字段承载多种含义。例如：

- **`contextWindow`（上下文窗口）**：用于压缩/截断历史消息的阈值，影响发送给 API 的 token 上限。典型值：128K-200K。
- **`maxTokens`（最大输出）**：API 单次回复的最大 token 数，影响回复长度。典型值：4096-8192。

这两个值数量级差异巨大，合并为一个字段会导致混乱和 bug。

### 2.2 默认值与占位符

- 提供合理的默认值，让用户开箱即用。
- UI 上用 **placeholder** 展示默认值（浅色），而非将默认值填入输入框。用户一眼就能区分"我自定义了"和"这是默认值"。
- 输入框为空时使用默认值，不要用 `0` 或空字符串作为"使用默认值"的信号传给 API。
- 后端读取设置时做 fallback：`settings.value || defaultValue`。

```tsx
// 好：placeholder 展示默认值，输入框本身为空
<Input value={value || ''} placeholder="204800" />

// 差：把默认值直接填入，用户无法区分"自定义"和"默认"
<Input value={value || 204800} />
```

### 2.3 设置迁移

当设置结构变更时（如拆分字段），必须处理旧配置的迁移：

```typescript
// 检测旧格式并迁移
const needsMigration = !settings.newField && settings.oldField > threshold
const newValue = needsMigration ? settings.oldField : (settings.newField || default)
```

不做迁移会导致老用户升级后功能异常。

### 2.4 可选高级设置

- 将不常用的设置（如视觉模型、上下文窗口、最大输出）归为高级选项。
- 用清晰的标签和占位文字说明用途，如 `"可选，如 glm-4v-flash"`。
- 相关设置项可以用 grid 布局并排，节省空间，例如 Context Window 和 Max Tokens 放同一行。

---

## 3. 多模态（图片/视觉）处理

### 3.1 分离视觉模型

不是所有模型都支持图片输入。正确做法：

- 提供独立的 **Vision Model** 设置项（可选）。
- 未配置时，不注入图片——即使笔记/内容中包含图片引用。
- 已配置时，仅在需要识图的请求中切换到视觉模型。

### 3.2 图片仅首轮注入

在多轮工具调用循环中，图片只在第一轮请求中注入：

```
第 0 轮: [system] + [images] + [chat] → 用 visionModel
第 1 轮: [system] + [chat] + [tool_results] → 用主 model
第 2 轮: [system] + [chat] + [tool_results] → 用主 model
```

关键实现：图片消息存在独立数组（`imageMessages`），不要混入 `workingMessages`，仅在 `iteration === 0` 时拼接进请求。

原因：
- 避免每轮都发送大量 base64 数据，浪费 token 和带宽。
- 后续轮次是工具调用结果处理，不需要重复看图。
- 视觉模型通常更贵或能力不同，应最小化使用范围。

### 3.3 图片格式差异

| API 格式 | 图片内容块格式 |
|---------|-------------|
| OpenAI | `{ type: "image_url", image_url: { url: "data:image/png;base64,..." } }` |
| Anthropic | `{ type: "image", source: { type: "base64", media_type: "image/png", data: "..." } }` |

---

## 4. 语言与本地化

### 4.1 AI 输出语言跟随系统设置

仅翻译 UI 文案是不够的。AI 的回复语言也必须与系统语言一致：

- 在 system prompt 中注入语言指令：`"IMPORTANT: You MUST respond entirely in Chinese (简体中文)."`
- 按语言维护指令模板，通过 `i18n.language` 动态选择。
- **所有入口**（聊天、预设、头脑风暴、内联操作、内联聊天）都要注入语言指令，一个都不能遗漏。

### 4.2 Prompt 与 UI 文案分离

- Prompt 模板放在独立的配置文件（如 `aiPrompts.json`），不与 i18n 翻译混在一起。
- Prompt 本身用英文编写（LLM 对英文 prompt 理解最好），通过语言指令控制输出语言。
- UI 标签（"总结"、"翻译"等按钮文字）走正常 i18n 体系。

### 4.3 语言指令模板结构

```json
{
  "chat": {
    "langInstructions": {
      "zh": "IMPORTANT: You MUST respond entirely in Chinese (简体中文).",
      "en": "IMPORTANT: You MUST respond entirely in English."
    }
  }
}
```

每种 AI 功能入口复用同一套语言指令，保持一致性。

---

## 5. 流式响应的视觉反馈设计

### 5.1 阶段状态机

AI 响应过程分为多个阶段，每个阶段需要不同的视觉反馈：

```
idle → thinking → writing → idle
idle → thinking → tool_calling → thinking → writing → idle
```

状态机由事件驱动：
- 收到首个 chunk → `thinking` → `writing`
- 收到 tool_start 事件 → `tool_calling`
- 收到 done 事件 → `idle`

### 5.2 动态状态指示器（核心 UX）

**不要只用一个静态的"加载中..."**。为每个阶段准备一组有趣的词语搭配独特图标，轮播展示：

```typescript
// 思考阶段：每 2 秒轮换一条，配不同图标
thinking: [
  { text: "Thinking...",     icon: Brain },
  { text: "Reasoning...",    icon: Zap },
  { text: "Pondering...",    icon: Eye },
  { text: "Analyzing...",    icon: Lightbulb },
  { text: "Considering...",  icon: Sparkles }
]

// 写作阶段
writing: [
  { text: "Writing...",      icon: Pencil },
  { text: "Composing...",    icon: FileText },
  { text: "Drafting...",     icon: Type },
  { text: "Generating...",   icon: Wand2 },
  { text: "Creating...",     icon: Palette }
]

// 工具调用阶段
tool_calling: [
  { text: "Searching notes...",   icon: Search },
  { text: "Reading notes...",     icon: BookOpen },
  { text: "Exploring...",         icon: Compass },
  { text: "Investigating...",     icon: Microscope },
  { text: "Gathering info...",    icon: FolderSearch }
]
```

设计要点：
- **轮播间隔 2 秒**，配合 200ms 淡入淡出过渡，不要太快（焦虑）也不要太慢（无聊）。
- **图标 + 文字同步切换**，用 `animate-pulse` 让图标有呼吸感。
- **阶段切换时重置到第一条**，给用户清晰的状态变化感知。
- 词语要有**趣味性和多样性**，让等待过程不枯燥，避免千篇一律的"加载中"。
- 所有词语走 i18n，中文也要选用生动有趣的表达。

### 5.3 淡入淡出过渡

```tsx
// 图标和文字同时淡出 → 切换内容 → 同时淡入
const [fading, setFading] = useState(false)

useEffect(() => {
  const timer = setInterval(() => {
    setFading(true)                    // 开始淡出
    setTimeout(() => {
      setEntryIndex(prev => (prev + 1) % entries.length)  // 切换内容
      setFading(false)                 // 开始淡入
    }, 200)                            // 淡出持续 200ms
  }, 2000)                             // 每 2 秒轮换
}, [phase])

<Icon className={cn('animate-pulse transition-opacity duration-200',
  fading ? 'opacity-0' : 'opacity-100'
)} />
<span className={cn('transition-opacity duration-200',
  fading ? 'opacity-0' : 'opacity-100'
)}>{label}</span>
```

### 5.4 流式打字光标

在 AI 回复正在生成时，末尾显示一个闪烁的光标块，模拟打字效果：

```tsx
{isStreaming && (
  <span className="inline-block w-1.5 h-4 bg-foreground/60 animate-pulse ml-0.5 align-text-bottom" />
)}
```

- 宽度 `w-1.5`，高度与文字对齐 `align-text-bottom`。
- 半透明 `bg-foreground/60` + `animate-pulse` 产生呼吸闪烁。
- 流式结束后自动消失。

---

## 6. Token 用量展示

### 6.1 完成状态横幅

流式结束后，展示一条紧凑的状态行：

```
✓ Done · Input: 1,234 · Output: 567
```

- 绿色对勾 `✓` 表示完成。
- 数字用 `toLocaleString()` 格式化（千分位）。
- 字体小一号（`text-xs`），颜色用 `text-muted-foreground`，不抢内容视线。

### 6.2 不要自动隐藏

- **永远不要 `setTimeout` 自动隐藏用量信息**。用户需要时间查看，5 秒太短。
- 正确做法：用量横幅保持显示，直到用户发起下一次请求时自然替换。
- 发起新请求时先 `setShowUsageBanner(false)`，清除上一次的用量。

---

## 7. 预设操作与快捷按钮

### 7.1 预设按钮设计

为常用 AI 操作提供一键触发的预设按钮，降低使用门槛：

```
[📖 Summarize] [🌐 Translate] [✏️ Rewrite] [→ Continue] [✨ Explain] [💡 Brainstorm]
```

设计要点：
- 每个预设配一个**语义化图标**（BookOpen、Languages、PenLine、ArrowRight、Sparkles、Lightbulb）。
- 按钮用 `variant="outline"` + 小尺寸（`h-6 px-2 text-xs`），不喧宾夺主。
- 排列用 `flex flex-wrap gap-1`，窄屏自动换行。
- 流式进行中或未配置 API key 时 `disabled`。

### 7.2 预设消息的紧凑展示

用户点击预设后，不要在聊天区显示完整的 prompt 文本。改用**紧凑徽章**：

```tsx
// 预设消息展示为圆角胶囊标签
<div className="inline-flex items-center gap-1.5 rounded-full px-3 py-1
  bg-primary/15 text-primary text-xs font-medium border border-primary/20">
  <BookOpen className="h-3 w-3" />
  <span>Summarize</span>
</div>
```

对比效果：
- 好：`[📖 Summarize]` ← 一个小标签
- 差：`"Please summarize the current note concisely."` ← 一大段 prompt 文本

### 7.3 内联操作面板

选中文本后的内联 AI 操作（Ctrl+J），设计为居中弹出的面板：

- 顶部显示选中文本预览（`line-clamp-3` 限制高度）。
- 操作按钮用 `grid grid-cols-2` 网格布局。
- 结果区域带滚动，底部提供"替换选中"和"插入到下方"两个操作。
- 自定义指令输入框按需展开，支持 Enter 提交。

---

## 8. 工具调用的可视化

### 8.1 实时工具状态

AI 调用工具时，在聊天区实时展示每个工具的执行状态：

```tsx
// 执行中：旋转加载图标
<Loader2 className="h-3 w-3 animate-spin" />
<span>Searching notes: "machine learning"</span>

// 已完成：对勾图标
<Check className="h-3 w-3" />
<span>Reading note: research.md</span>
```

- 用 `text-xs text-muted-foreground` 保持低调。
- 展示工具名称的同时，显示关键参数（搜索关键词、文件名等），让用户知道 AI 在做什么。
- 多个工具调用垂直排列（`space-y-1`）。

### 8.2 工具名称本地化

工具内部名称（`search_notes`）不应直接展示给用户，通过 i18n 映射为友好名称：

```json
{
  "ai": {
    "tool_search_notes": "Searching notes",
    "tool_read_note": "Reading note",
    "tool_list_notes": "Listing notes"
  }
}
```

---

## 9. 聊天面板布局

### 9.1 可调位置

AI 聊天面板支持两种位置，用户可切换：

- **右侧面板**（`border-l`）：适合宽屏，与编辑器并排。
- **底部面板**（`border-t`）：适合竖屏或窄屏。
- 用 `PanelRight` / `PanelBottom` 图标按钮切换，带 tooltip 提示。

### 9.2 面板组件结构

```
┌──────── Header ────────┐  h-10, 标题 + 操作按钮（清除/切换位置/关闭）
├──────── Messages ──────┤  flex-1, ScrollArea, 自动滚动到底
├──────── Presets ────────┤  预设按钮行
├──────── Separator ─────┤
└──────── Input ─────────┘  textarea + 发送/停止按钮
```

### 9.3 自动滚动

每当消息列表或流式内容变化时，自动滚动到底部：

```typescript
useEffect(() => {
  if (scrollRef.current) {
    scrollRef.current.scrollTop = scrollRef.current.scrollHeight
  }
}, [messages, streamingContent])
```

### 9.4 未配置状态

API key 未配置时，聊天区显示友好的引导提示，而非空白：

```
API key not configured
Configure in Settings (Ctrl+,)
```

居中显示，用 `text-muted-foreground`，告知用户如何操作。

---

## 10. 附件与上下文引用

### 10.1 引用文本附件

支持用户将代码片段或文本选区"引用"到 AI 聊天（如 Ctrl+Shift+L）：

- 在输入框上方显示附件标签：`[📎 file.ts:10-25] [×]`
- 标签用 `rounded-md bg-muted text-xs border` 样式。
- 每个标签可单独移除（X 按钮）。
- 发送消息时将附件内容注入 system message，发送后自动清除。

### 10.2 笔记上下文注入

当前打开的笔记内容自动作为上下文：

- 通过 system prompt 注入，格式为 `---\n{content}\n---`。
- 明确指示 AI **不要主动总结笔记内容**，除非用户要求。
- 图片引用由后端从 system 消息中提取并处理。

---

## 11. 工具调用（Function Calling / Tool Use）

### 11.1 格式差异

工具定义和调用结果的格式在两种协议间完全不同：

```typescript
// OpenAI 工具定义
{ type: "function", function: { name, description, parameters: jsonSchema } }

// Anthropic 工具定义
{ name, description, input_schema: jsonSchema }
```

### 11.2 工具结果回传

```typescript
// OpenAI: role: "tool"
{ role: "tool", tool_call_id: id, content: result }

// Anthropic: role: "user" + tool_result block
{ role: "user", content: [{ type: "tool_result", tool_use_id: id, content: result }] }
```

### 11.3 迭代控制

- 设置最大迭代次数（如 10 次），防止无限循环。
- 每轮检查 abort 信号，支持用户中途停止。
- 工具执行结果过长时截断（如 200 字符 + `...`），避免上下文爆炸。
- 向用户展示工具执行的简要摘要，而非完整结果。

---

## 12. 消息渲染

### 12.1 用户消息

- 右对齐，主色背景（`bg-primary text-primary-foreground`）。
- 圆角气泡（`rounded-lg`），最大宽度 85%。
- 支持 `whitespace-pre-wrap` 保留换行。

### 12.2 AI 回复消息

- 左对齐，灰色背景（`bg-muted`）。
- 内容使用 Markdown 渲染（支持代码高亮、表格、数学公式等）。
- 非流式状态下，底部显示"插入到笔记"按钮，带分隔线。
- 流式状态下，末尾显示闪烁光标。

### 12.3 错误消息

- 仍以 assistant 消息展示，内容前缀 `Error: `。
- 不使用特殊样式（红色等），保持聊天流的一致性。

---

## 13. 错误处理与调试

### 13.1 API 错误诊断

遇到 API 错误时，优先检查：

1. **参数兼容性**：是否发送了目标 API 不支持的参数（如 `max_tokens`、`image_url`）。
2. **内容格式**：消息内容是否包含不支持的类型（如对非视觉模型发送图片）。
3. **认证方式**：Header 格式是否与 API 协议匹配。

### 13.2 调试手段

- 在发送请求前打印完整的 request body（开发阶段）。
- 日志中标注迭代轮次、使用的模型、是否包含图片，便于定位问题。
- 生产环境移除或降级敏感信息的日志。

### 13.3 空响应处理

当流式结束但没有收到任何内容时，不要静默失败：

```typescript
if (!content) {
  addMessage({
    role: 'assistant',
    content: 'No response received. Check the terminal logs for details.'
  })
}
```

---

## 14. 中止与状态恢复

### 14.1 用户中止

- 提供明显的停止按钮（红色 `variant="destructive"`，配 ■ 图标）。
- 中止后，已接收的部分内容仍保存为消息，不丢弃。
- 立即重置所有状态：`isStreaming`、`currentRequestId`、`streamingPhase`、`toolCalls`。

### 14.2 发送按钮状态切换

流式进行中，发送按钮自动变为停止按钮：

```tsx
{isStreaming ? (
  <Button variant="destructive" onClick={handleStop}>
    <Square /> Stop
  </Button>
) : (
  <Button onClick={handleSend}>
    <Send /> Send
  </Button>
)}
```

---

## 15. 检查清单

新增 AI 功能时，逐项检查：

**后端 / API**
- [ ] API 格式是否正确处理（OpenAI vs Anthropic）
- [ ] 是否避免了不兼容参数（如 OpenAI 格式不发 max_tokens）
- [ ] 多模态内容是否只在配置了视觉模型时发送
- [ ] 图片是否仅首轮注入，后续迭代不携带
- [ ] SSE 解析是否区分两种格式
- [ ] 工具调用循环是否有上限（如 10 次）和中断机制

**前端 / 交互**
- [ ] AI 输出语言是否跟随系统语言（所有入口）
- [ ] 设置项是否有合理默认值和 placeholder 展示
- [ ] 设置迁移是否处理旧配置格式
- [ ] 是否有阶段性动态状态指示器（thinking/writing/tool_calling）
- [ ] 状态文字和图标是否有趣味性和多样性
- [ ] 是否有 2 秒轮播 + 淡入淡出过渡
- [ ] 流式打字光标是否正确显示/隐藏
- [ ] Token 用量是否持久展示（不自动隐藏）
- [ ] 预设操作是否用紧凑标签展示（非原始 prompt）
- [ ] 工具调用是否有实时状态展示（旋转/对勾）
- [ ] 中止后部分内容是否保留
- [ ] 空响应是否有兜底提示
