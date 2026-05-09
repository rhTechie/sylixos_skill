# SylixOS Skill 仓库

本仓库用于存放面向 SylixOS 开发场景的 AI Skill 文件。

## 仓库用途

- 沉淀 SylixOS 开发中的常见工作流
- 为 AI 工具提供结构化的任务执行说明
- 降低重复性操作的沟通成本
- 便于后续持续扩展更多专项 Skill

## 快速开始

只需加载主 skill 文件即可使用所有功能：

```
加载 /workspace/code_workspace/sylixos_skill skill
```

AI 会根据你的指令自动判断使用哪个子 skill：
- **编译项目**: "编译 xxx 项目" → 自动使用编译 skill
- **上传到板卡**: "上传 xxx 到板卡" → 自动使用上传 skill
- **完整流程**: "编译并上传 xxx" → 自动依次执行编译和上传

## 目录结构

```text
sylixos_skill/
├── SKILL.md                      # 主 skill 入口（统一加载点）
├── README.md                     # 本文档
├── sylixos_cli_build/
│   └── SKILL.md                  # 编译构建子 skill
└── sylixos_ftp_upload/
    └── SKILL.md                  # FTP 上传子 skill
```

## 文件说明

### `SKILL.md` (主入口)

**这是唯一需要加载的 skill 文件**，作为统一入口点。

- 自动判断用户意图（编译、上传或两者）
- 路由到相应的子 skill
- 包含完整的决策逻辑和使用示例

### `README.md`

本文档，面向人类用户的说明文档。

### `sylixos_cli_build/SKILL.md`

SylixOS CLI 命令行构建子 skill。

**功能**:
- 发现工作区布局（base、compat layer、license SDK、BSP）
- 更新 config.mk 配置文件（使用绝对路径）
- 确定正确的平台配置（ARM64_GENERIC 等）
- 执行 multi-platform.mk 构建
- 处理编译错误和依赖问题

**适用场景**:
- 编译 SylixOS 驱动、库、应用程序
- 修复编译错误
- 重新构建项目

### `sylixos_ftp_upload/SKILL.md`

SylixOS 项目文件上传到目标板卡子 skill。

**功能**:
- 解析 `.reproject` 配置文件（GB2312 编码）
- 提取板卡 IP、上传文件列表和目标路径
- 验证网络连通性
- 通过 FTP 上传文件（默认 root/root）
- 自动创建目标目录
- 报告上传结果

**适用场景**:
- 部署驱动模块（*.ko）到 `/lib/modules/drivers/`
- 部署库文件（*.so）到 `/lib/`
- 部署测试工具到 `/apps/`

## 注意事项

1. **编译前提**: 确保 SylixOS 工具链已安装并在 PATH 中
2. **网络要求**: 上传前确保能 ping 通板卡 IP
3. **FTP 服务**: 板卡上必须运行 FTP 服务
4. **文件权限**: 上传的可执行文件需要在板卡上设置执行权限
5. **路径规范**: config.mk 中必须使用绝对路径，不能使用相对路径

## 扩展说明

本仓库采用模块化设计，便于后续扩展：
- 每个子 skill 独立维护
- 主 skill 负责路由和协调
- 可随时添加新的子 skill（如调试、测试等）


