# OpenClaw Config Fixer

一键修复 OpenClaw main agent 无法唤醒其他 agent 的问题。

## 问题背景

OpenClaw 的 main agent 默认情况下可能无法正常唤醒（spawn）其他 sub-agent，原因包括：

1. 缺少 `agents.defaults.subagents` 配置
2. `sessions_spawn` 等工具权限未配置
3. `sessions.visibility` 设置限制了跨 agent 访问
4. `agentToAgent` 通信未启用

## 功能

- ✅ 添加 `agents.defaults.subagents` 配置（maxSpawnDepth: 2）
- ✅ 为 main agent 添加完整的 subagents 权限（允许所有 agent）
- ✅ 添加 sessions 相关工具权限
- ✅ 设置 `sessions.visibility = all`
- ✅ 启用 `agentToAgent` 通信
- ✅ 自动备份原配置文件
- ✅ 可选自动重启 OpenClaw 服务

## 使用方法

### 基本使用

```bash
# 一键修复
python openclaw_config_fixer.py

# 指定配置文件路径
python openclaw_config_fixer.py --config /path/to/openclaw.json

# 同时修复所有 agent 的 sessions 权限
python openclaw_config_fixer.py --fix-all-agents

# 不自动重启服务
python openclaw_config_fixer.py --no-restart
```

### 恢复备份

```bash
# 从备份恢复
python openclaw_config_fixer.py --restore ~/.openclaw/openclaw.json.backup_20260305_120000
```

## 命令行参数

| 参数 | 简写 | 说明 |
|------|------|------|
| `--config` | `-c` | 配置文件路径（默认: `~/.openclaw/openclaw.json`） |
| `--restore` | `-r` | 从指定备份文件恢复配置 |
| `--no-restart` | | 不自动重启 OpenClaw 服务 |
| `--fix-all-agents` | | 为所有 agent 添加 sessions 工具权限 |

## 修复内容

### 1. agents.defaults.subagents

```json
{
  "agents": {
    "defaults": {
      "subagents": {
        "maxSpawnDepth": 2,
        "maxChildrenPerAgent": 5,
        "maxConcurrent": 8,
        "runTimeoutSeconds": 900
      }
    }
  }
}
```

### 2. main agent 权限

```json
{
  "id": "main",
  "subagents": {
    "allowAgents": ["*"]
  },
  "sandbox": {
    "mode": "off"
  },
  "tools": {
    "allow": [
      "read", "write", "edit", "exec",
      "sessions_spawn", "sessions_list", "sessions_send",
      "sessions_history", "sessions_status",
      "process", "tts", "web_fetch", "canvas",
      "browser", "gateway", "message",
      "memory_search", "memory_get"
    ],
    "deny": []
  }
}
```

### 3. tools 配置

```json
{
  "tools": {
    "sessions": {
      "visibility": "all"
    },
    "agentToAgent": {
      "enabled": true,
      "allow": ["*"]
    }
  }
}
```

## 验证修复

修复后，在 OpenClaw 中测试：

```
/subagents spawn project-manager "测试任务"
```

或在对话中：

```
让项目经理帮我规划一个任务
```

## 依赖

- Python 3.6+
- 无外部依赖（仅使用标准库）

## 安全说明

- 脚本会自动备份原配置文件
- 备份文件命名格式：`openclaw.json.backup_YYYYMMDD_HHMMSS`
- 可随时使用 `--restore` 参数恢复

## License

MIT License
