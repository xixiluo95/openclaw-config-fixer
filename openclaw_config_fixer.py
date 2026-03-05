#!/usr/bin/env python3
"""
OpenClaw 配置修复脚本
一键修复 main agent 无法唤醒其他 agent 的问题

功能：
1. 添加 agents.defaults.subagents 配置
2. 为 main agent 添加完整的 subagents 权限
3. 添加 sessions 工具权限
4. 设置 sessions.visibility = all
5. 启用 agentToAgent 通信
6. 自动备份原配置

使用方法：
    python openclaw_config_fixer.py [--config CONFIG_PATH] [--restore BACKUP_PATH]
"""

import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import argparse
import sys


# 默认配置路径
DEFAULT_CONFIG_PATH = Path.home() / ".openclaw" / "openclaw.json"

# 默认的 subagents 配置
DEFAULT_SUBAGENTS_CONFIG = {
    "maxSpawnDepth": 2,
    "maxChildrenPerAgent": 5,
    "maxConcurrent": 8,
    "runTimeoutSeconds": 900
}

# sessions 相关工具
SESSIONS_TOOLS = [
    "sessions_spawn",
    "sessions_list",
    "sessions_send",
    "sessions_history",
    "sessions_status"
]

# 基础工具（所有 agent 都应该有）
BASE_TOOLS = [
    "read",
    "write",
    "edit",
    "exec",
    "memory_search",
    "memory_get"
]

# main agent 的完整工具列表
MAIN_AGENT_TOOLS = BASE_TOOLS + SESSIONS_TOOLS + [
    "process",
    "tts",
    "web_fetch",
    "canvas",
    "browser",
    "gateway",
    "message"
]


def backup_config(config_path: Path) -> Path:
    """备份配置文件"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = config_path.parent / f"openclaw.json.backup_{timestamp}"
    shutil.copy2(config_path, backup_path)
    return backup_path


def load_config(config_path: Path) -> Dict[str, Any]:
    """加载配置文件"""
    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_config(config_path: Path, config: Dict[str, Any]) -> None:
    """保存配置文件"""
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def get_all_agent_ids(config: Dict[str, Any]) -> List[str]:
    """获取所有 agent ID"""
    agents_list = config.get("agents", {}).get("list", [])
    return [agent.get("id") for agent in agents_list if agent.get("id")]


def fix_agents_defaults(config: Dict[str, Any]) -> Dict[str, Any]:
    """修复 agents.defaults 配置"""
    if "agents" not in config:
        config["agents"] = {}

    if "defaults" not in config["agents"]:
        config["agents"]["defaults"] = {}

    # 添加 subagents 配置
    config["agents"]["defaults"]["subagents"] = DEFAULT_SUBAGENTS_CONFIG

    return config


def fix_main_agent(config: Dict[str, Any], all_agent_ids: List[str]) -> Dict[str, Any]:
    """修复 main agent 配置，给予最大权限"""
    agents_list = config.get("agents", {}).get("list", [])

    for agent in agents_list:
        if agent.get("id") == "main":
            # 设置 subagents 权限 - 允许所有 agent
            agent["subagents"] = {
                "allowAgents": ["*"]  # 使用通配符允许所有
            }

            # 确保沙箱关闭
            agent["sandbox"] = {"mode": "off"}

            # 设置完整的工具权限
            if "tools" not in agent:
                agent["tools"] = {}

            agent["tools"]["allow"] = MAIN_AGENT_TOOLS
            agent["tools"]["deny"] = []

            break

    return config


def fix_tools_config(config: Dict[str, Any], all_agent_ids: List[str]) -> Dict[str, Any]:
    """修复 tools 配置"""
    if "tools" not in config:
        config["tools"] = {}

    # 设置 sessions 可见性
    config["tools"]["sessions"] = {
        "visibility": "all"
    }

    # 启用 agentToAgent 通信
    config["tools"]["agentToAgent"] = {
        "enabled": True,
        "allow": ["*"]  # 允许所有 agent 互相通信
    }

    return config


def fix_all_agents_sessions_tools(config: Dict[str, Any]) -> Dict[str, Any]:
    """为所有 agent 添加 sessions 工具权限（可选）"""
    agents_list = config.get("agents", {}).get("list", [])

    for agent in agents_list:
        if agent.get("id") == "main":
            continue  # main agent 已经处理过了

        tools = agent.get("tools", {})
        if "allow" in tools:
            # 添加 sessions 工具
            for tool in SESSIONS_TOOLS:
                if tool not in tools["allow"]:
                    tools["allow"].append(tool)

    return config


def restore_config(backup_path: Path, config_path: Path) -> None:
    """从备份恢复配置"""
    if not backup_path.exists():
        raise FileNotFoundError(f"备份文件不存在: {backup_path}")
    shutil.copy2(backup_path, config_path)
    print(f"✅ 已从备份恢复配置: {backup_path}")


def restart_openclaw() -> bool:
    """尝试重启 OpenClaw 服务"""
    import subprocess

    restart_commands = [
        ["systemctl", "--user", "restart", "openclaw-gateway.service"],
        ["openclaw", "restart"],
    ]

    for cmd in restart_commands:
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=30)
            if result.returncode == 0:
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue

    return False


def main():
    parser = argparse.ArgumentParser(
        description="OpenClaw 配置修复脚本 - 一键修复 agent 通信问题"
    )
    parser.add_argument(
        "--config", "-c",
        type=str,
        default=str(DEFAULT_CONFIG_PATH),
        help=f"配置文件路径 (默认: {DEFAULT_CONFIG_PATH})"
    )
    parser.add_argument(
        "--restore", "-r",
        type=str,
        help="从指定备份文件恢复配置"
    )
    parser.add_argument(
        "--no-restart",
        action="store_true",
        help="不自动重启 OpenClaw 服务"
    )
    parser.add_argument(
        "--fix-all-agents",
        action="store_true",
        help="为所有 agent 添加 sessions 工具权限"
    )

    args = parser.parse_args()
    config_path = Path(args.config)

    print("=" * 60)
    print("  OpenClaw 配置修复脚本")
    print("=" * 60)

    # 恢复模式
    if args.restore:
        restore_config(Path(args.restore), config_path)
        return 0

    # 修复模式
    try:
        # 1. 加载配置
        print(f"\n📖 加载配置文件: {config_path}")
        config = load_config(config_path)

        # 2. 备份原配置
        print("💾 备份原配置文件...")
        backup_path = backup_config(config_path)
        print(f"   备份位置: {backup_path}")

        # 3. 获取所有 agent ID
        all_agent_ids = get_all_agent_ids(config)
        print(f"\n📋 发现 {len(all_agent_ids)} 个 agent: {', '.join(all_agent_ids)}")

        # 4. 执行修复
        print("\n🔧 执行修复...")

        print("   [1/4] 修复 agents.defaults.subagents 配置")
        config = fix_agents_defaults(config)

        print("   [2/4] 修复 main agent 权限")
        config = fix_main_agent(config, all_agent_ids)

        print("   [3/4] 修复 tools.sessions 和 agentToAgent 配置")
        config = fix_tools_config(config, all_agent_ids)

        if args.fix_all_agents:
            print("   [4/4] 为所有 agent 添加 sessions 工具")
            config = fix_all_agents_sessions_tools(config)
        else:
            print("   [4/4] 跳过（使用 --fix-all-agents 为所有 agent 添加权限）")

        # 5. 保存配置
        print("\n💾 保存配置文件...")
        save_config(config_path, config)

        # 6. 重启服务
        if not args.no_restart:
            print("\n🔄 重启 OpenClaw 服务...")
            if restart_openclaw():
                print("   ✅ 服务重启成功")
            else:
                print("   ⚠️  无法自动重启，请手动执行: systemctl --user restart openclaw-gateway.service")

        print("\n" + "=" * 60)
        print("  ✅ 修复完成！")
        print("=" * 60)
        print("\n修复内容:")
        print("  • maxSpawnDepth: 2 (允许嵌套子代理)")
        print("  • main agent 可唤醒所有 agent")
        print("  • sessions.visibility: all")
        print("  • agentToAgent 已启用")
        print("\n测试命令:")
        print('  /subagents spawn project-manager "测试任务"')
        print()

        return 0

    except FileNotFoundError as e:
        print(f"\n❌ 错误: {e}")
        return 1
    except json.JSONDecodeError as e:
        print(f"\n❌ JSON 解析错误: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ 未知错误: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
