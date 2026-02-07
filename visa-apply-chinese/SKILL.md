---
name: visa-apply-chinese
description: 中国公民申请其他国家旅游签证的完整指导。包含申请流程、材料准备、常见问题解答。适用于中国护照持有者申请旅游签证时的所有场景，如准备申请材料、填写申请表、预约签证中心、面签准备等。
---

# 中国公民旅游签证申请指南

## 概述

本技能为中国公民申请其他国家旅游签证提供全面指导，包括申请流程、材料准备、常见问题解答。适用于所有中国护照持有者申请旅游签证的场景。

## 核心功能

- 提供不同国家旅游签证的申请流程
- 详细的材料准备清单
- 申请表填写指导
- 预约签证中心指南
- 面签准备建议
- 常见问题解答

## 使用场景

当用户需要：
- 了解某个国家的旅游签证要求
- 准备签证申请材料
- 填写签证申请表
- 预约签证中心
- 准备签证面试
- 解决签证申请过程中的问题

## 参考资源

- `references/requirements.md` - 主要国家旅游签证要求
- `references/checklist.md` - 签证申请材料清单
- `assets/templates/` - 签证申请表模板
- `assets/sample/` - 材料准备样例

## 工作流程

1. **确定目的地**：选择要前往的国家
2. **了解要求**：查看该国家的签证要求和流程
3. **准备材料**：根据清单准备所需文件
4. **填写申请表**：完成在线或纸质申请表
5. **预约面签**：预约签证中心或使领馆
6. **参加面试**：准备并参加签证面试
7. **等待结果**：跟踪申请状态
8. **领取签证**：获取签证并准备出行

---

## 快速开始

### 1. 查看签证要求

```python
# 示例：获取美国旅游签证要求
from references.requirements import get_country_requirements

usa_requirements = get_country_requirements('usa')
print(usa_requirements)
```

### 2. 准备申请材料

```python
# 示例：生成材料清单
from references.checklist import generate_checklist

checklist = generate_checklist('usa', purpose='tourism')
print(checklist)
```

### 3. 填写申请表

使用 `assets/templates/` 目录下的申请表模板，或通过官方网站在线填写。

## 常见问题

### Q: 旅游签证需要提前多久申请？

A: 建议提前至少2-3个月开始准备，具体时间取决于目的地国家的处理速度。

### Q: 银行对账单需要多长时间的？

A: 大多数国家要求提供最近3-6个月的银行对账单。

### Q: 没有在职证明怎么办？

A: 可以提供其他收入证明，如银行流水、资产证明等。

---

## 支持的国家

当前支持的主要旅游目的地国家：
- 美国 (USA)
- 英国 (UK)
- 申根国家 (Schengen)
- 日本 (Japan)
- 韩国 (South Korea)
- 澳大利亚 (Australia)
- 加拿大 (Canada)
- 新加坡 (Singapore)
- 马来西亚 (Malaysia)
- 泰国 (Thailand)

如需其他国家的信息，请联系我们或访问该国驻华使领馆官网。
