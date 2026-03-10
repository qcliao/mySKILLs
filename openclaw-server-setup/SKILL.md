---
name: openclaw-server-setup
description: 在新服务器上安装和配置 OpenClaw。当用户要求"在新服务器装 OpenClaw"、"配置远程服务器的 OpenClaw"、"部署 OpenClaw 到服务器"时触发。支持 SSH 密钥配置、Node.js 安装、OpenClaw 安装、配置文件复制、Gateway 服务启动。
---

# OpenClaw 服务器部署

在新服务器上快速部署 OpenClaw 的完整流程。

## 前置条件

- 目标服务器的 SSH 访问权限（用户名 + 密码 或 密钥）
- 本地已运行 OpenClaw（用于复制配置）

## 部署流程

### 1. 测试 SSH 连接

```bash
ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no <user>@<host> "echo '连接成功' && hostname"
```

如果认证失败，需要配置 SSH 密钥。

### 2. 配置 SSH 密钥（如需要）

**检查本地是否有密钥**：
```bash
ls -la ~/.ssh/
```

**生成新密钥（如果没有）**：
```bash
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N "" -C "openclaw@$(hostname)"
```

**将公钥添加到目标服务器**：
```bash
# 本地显示公钥
cat ~/.ssh/id_ed25519.pub

# 在目标服务器上执行
echo "<公钥内容>" >> ~/.ssh/authorized_keys
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
```

### 3. 安装 Node.js

**检查是否已安装**：
```bash
ssh <user>@<host> "node --version && npm --version"
```

**安装 Node.js 22.x（Ubuntu/Debian）**：
```bash
ssh <user>@<host> "curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - && sudo apt-get install -y nodejs"
```

### 4. 安装 OpenClaw

```bash
ssh <user>@<host> "sudo npm install -g openclaw"
```

**验证安装**：
```bash
ssh <user>@<host> "openclaw --version"
```

### 5. 复制配置文件

**创建目录结构**：
```bash
ssh <user>@<host> "mkdir -p ~/.openclaw/agents/main/agent"
```

**复制配置文件**：
```bash
# 主配置文件
scp ~/.openclaw/openclaw.json <user>@<host>:~/.openclaw/openclaw.json

# API 认证配置
scp ~/.openclaw/agents/main/agent/auth-profiles.json <user>@<host>:~/.openclaw/agents/main/agent/auth-profiles.json
```

**修复路径和插件**（如果原配置有问题）：
```bash
# 修改 workspace 路径
ssh <user>@<host> "sed -i 's|/root/.openclaw/workspace|/home/<user>/.openclaw/workspace|g' ~/.openclaw/openclaw.json"

# 创建 workspace 目录
ssh <user>@<host> "mkdir -p ~/.openclaw/workspace"

# 移除不存在的插件（可选）
ssh <user>@<host> "sed -i 's|\"dingtalk-connector\",||g; s|\"qqbot\",||g; s|\"wecom\"||g' ~/.openclaw/openclaw.json"
```

### 6. 复制 Workspace（可选）

如果有备份文件：
```bash
scp <backup-file>.tar.gz <user>@<host>:~/
ssh <user>@<host> "rm -rf ~/.openclaw/workspace && tar -xzf ~/$(basename <backup-file>.tar.gz) -C ~/.openclaw/"
```

或直接复制目录：
```bash
scp -r ~/.openclaw/workspace <user>@<host>:~/.openclaw/
```

### 7. 启动 Gateway 服务

**安装并启动 systemd 服务**：
```bash
ssh <user>@<host> "openclaw gateway install && sleep 2 && openclaw gateway start"
```

**验证状态**：
```bash
ssh <user>@<host> "openclaw gateway status"
```

**查看日志**：
```bash
ssh <user>@<host> "journalctl --user -u openclaw-gateway -n 30 --no-pager"
```

### 8. 测试 Agent

```bash
ssh <user>@<host> "openclaw agent -m '请自我介绍一下' --agent main"
```

## 常见问题

### 飞书/企业微信等长连接冲突

**问题**：多个 OpenClaw 实例同时连接同一飞书应用，会互相踢。

**解决**：只在一个实例启用飞书 channel，其他实例禁用：
```bash
ssh <user>@<host> "sed -i 's/\"enabled\": true/\"enabled\": false/' ~/.openclaw/openclaw.json # 仅对 channels.feishu"
```

或手动编辑 `openclaw.json`，将 `channels.feishu.enabled` 设为 `false`。

### Gateway 只监听 loopback

默认 `bind: loopback` 只允许本地连接。如需远程访问，修改配置：
```json
{
  "gateway": {
    "bind": "0.0.0.0"
  }
}
```

**安全警告**：暴露到公网需要配置防火墙或使用 auth token。

### 插件找不到

如果复制配置后报插件不存在，从 `plugins.allow` 数组中移除：
```bash
ssh <user>@<host> "sed -i 's|\"<plugin-name>\",||g' ~/.openclaw/openclaw.json"
```

## 配置检查清单

部署完成后确认：

- [ ] `openclaw --version` 正常
- [ ] `openclaw config get auth.profiles` 显示正确的 providers
- [ ] `openclaw gateway status` 显示 running
- [ ] `openclaw agent -m 'test' --agent main` 能正常响应
- [ ] 日志无报错：`journalctl --user -u openclaw-gateway -n 20`

## 快速部署命令汇总

```bash
# 一键部署（假设已有 SSH 密钥）
USER=<user> HOST=<host>

# 1. 安装 Node.js
ssh $USER@$HOST "curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - && sudo apt-get install -y nodejs"

# 2. 安装 OpenClaw
ssh $USER@$HOST "sudo npm install -g openclaw"

# 3. 创建目录
ssh $USER@$HOST "mkdir -p ~/.openclaw/agents/main/agent ~/.openclaw/workspace"

# 4. 复制配置
scp ~/.openclaw/openclaw.json $USER@$HOST:~/.openclaw/
scp ~/.openclaw/agents/main/agent/auth-profiles.json $USER@$HOST:~/.openclaw/agents/main/agent/

# 5. 修复路径
ssh $USER@$HOST "sed -i 's|/root/.openclaw/workspace|/home/$USER/.openclaw/workspace|g' ~/.openclaw/openclaw.json"

# 6. 启动 Gateway
ssh $USER@$HOST "openclaw gateway install && openclaw gateway start"

# 7. 验证
ssh $USER@$HOST "openclaw gateway status && openclaw agent -m 'OK' --agent main"
```
