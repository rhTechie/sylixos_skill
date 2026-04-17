# SylixOS Skill 仓库

本仓库用于存放面向 SylixOS 开发场景的 AI Skill 文件。

## 仓库用途

- 沉淀 SylixOS 开发中的常见工作流
- 为 AI 工具提供结构化的任务执行说明
- 降低重复性操作的沟通成本
- 便于后续持续扩展更多专项 Skill

## 目录结构

```text
sylixos_skill/
├── README.md
└── sylixos_cli_build/
    └── SKILL.md
```

## 目录说明

### `sylixos_cli_build/`

用于存放 SylixOS CLI 命令行构建相关的 Skill。

当前该目录下的 Skill 主要面向命令行编译场景，帮助 AI 工具在 Linux 环境中识别 SylixOS 工程依赖关系、构建入口和关键路径配置，并按约束完成构建流程。


