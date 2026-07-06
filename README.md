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
- **移植分析**: "把 Linux 驱动移植到 SylixOS" / "总结移植经验" → 自动使用移植分析 skill
- **编译项目**: "编译 xxx 项目" → 自动使用编译 skill
- **上传到板卡**: "上传 xxx 到板卡" → 自动使用上传 skill
- **板卡测试**: "telnet 登录板卡并测试 xxx" → 自动使用 telnet 测试 skill
- **网络验证与接口差异**: "不使用陪测机做双网口物理链路自测" / "总结 Linux 和 SylixOS 的网络接口差异" → 自动使用网络 skill
- **长期验证方法**: "先短测再长测验证" / "做 30 分钟或 1 小时 soak 验证" → 自动使用长期验证 skill
- **完整流程**: "编译上传并测试 xxx" → 自动依次执行编译、上传和板卡测试

## 目录结构

```text
sylixos_skill/
├── SKILL.md                      # 主 skill 入口（统一加载点）
├── README.md                     # 本文档
├── sylixos-driver-porting/
│   └── SKILL.md                  # Linux 驱动/SDK 向 SylixOS 移植分析 skill
├── sylixos-network/
│   └── SKILL.md                  # SylixOS 网络验证与接口差异 skill
├── sylixos-long-run-validation/
│   └── SKILL.md                  # 长时间测试 / soak / staged validation 方法 skill
├── sylixos_cli_build/
│   └── SKILL.md                  # 编译构建子 skill
├── sylixos_telnet_test/
│   └── SKILL.md                  # Telnet 登录板卡并执行测试子 skill
└── sylixos_ftp_upload/
    └── SKILL.md                  # FTP 上传子 skill
```

## 文件说明

### `SKILL.md` (主入口)

**这是唯一需要加载的 skill 文件**，作为统一入口点。

- 自动判断用户意图（编译、上传、板卡测试或完整链路）
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
- 约束 companion project 通过 `multi-platform.mk` 做平台感知的 `all/clean`
- 处理编译错误和依赖问题

**适用场景**:
- 编译 SylixOS 驱动、库、应用程序
- 修复编译错误
- 重新构建项目

### `sylixos-driver-porting/SKILL.md`

Linux 驱动/SDK 向 SylixOS 迁移分析子 skill。

**功能**:
- 对照 Linux 原始代码与 SylixOS 移植代码
- 从实际源码和构建文件中提取已落地的移植模式
- 区分“代码已验证”和“仅文档猜测”的结论
- 总结驱动层、HAL 层、SDK 层、sample 层与构建层的迁移要点

**适用场景**:
- 评审现有 SylixOS 移植质量
- 为类似驱动后续移植沉淀 checklist 或 skill
- 排查迁移文档与当前代码不一致的问题

### `sylixos-network/SKILL.md`

SylixOS 网络验证与接口差异子 skill。

**功能**:
- 帮助 AI 区分“本机地址通信成功”和“物理链路验证成功”
- 沉淀 Linux 与 SylixOS 在网络接口、`AF_PACKET`、MTU、计数解释方面的差异
- 指导在无外部陪测机时如何选择 local-IP、raw L2 或 PHY 级验证
- 为后续网络 bring-up / 物理路径验证 / 网络调试提供统一检查清单

**适用场景**:
- 单板双网口物理路径验证
- Linux 网络代码迁移到 SylixOS
- 排查“为什么 ping/UDP 成功但不一定过物理链路”
- 为后续 AI 会话快速建立可复用的网络调试上下文

### `sylixos-long-run-validation/SKILL.md`

长期测试 / soak / staged validation 方法子 skill。

**功能**:
- 总结长期板卡问题的通用验证方法，而不是单次问题结论
- 约束问题排查顺序为：短测复现 → 单变量 A/B → 30 分钟验证 → 1 小时确认
- 强制在自定义压力模型后回到默认真实压力混合场景复测
- 强调 CPU 放置、IRQ 放置、压力线程放置、结果文件化、脚本化执行、会话噪声规避等方法
- 强调多轮重大验证前优先 reboot，避免上轮环境污染结果

**适用场景**:
- 长时间抖动、超时、耐久、soak、endurance、压力敏感问题
- “短测看起来好了，但需要 30 分钟 / 1 小时确认”的问题
- 板卡侧需要多轮假设验证和长期确认的问题

### `sylixos_ftp_upload/SKILL.md`

SylixOS 项目文件上传到目标板卡子 skill。

**功能**:
- 解析 `.reproject` 配置文件（GB2312 编码）
- 提取板卡 IP、上传文件列表和目标路径
- 验证网络连通性
- 默认通过 bundled FTP 脚本上传文件（默认 root/root）
- 自动创建目标目录
- 上传后默认执行远端 `chmod 755`
- 全部上传完成后默认执行一次远端 `sync`
- 对于 BSP 启动镜像，覆盖 `/boot` 前优先备份当前活动镜像
- 为新建的可复用 SylixOS 工程沉淀 `.reproject` 模板
- 报告上传结果

**适用场景**:
- 部署驱动模块（*.ko）到 `/lib/modules/drivers/`
- 部署库文件（*.so）到 `/lib/`
- 部署测试工具到 `/apps/`

### `sylixos_telnet_test/SKILL.md`

SylixOS 板卡 Telnet 登录与板端测试子 skill。

**功能**:
- 从用户输入或 `.reproject` 中提取板卡 IP、工作目录和远端文件路径
- 验证板卡 `23` 端口可达
- 通过 telnet 登录板卡
- 检查上传文件是否存在并修正执行权限
- 执行板端测试命令并采集输出
- 汇总真实板端运行结果

**适用场景**:
- 上传后立即在板卡上运行应用程序
- 通过 telnet 做板端冒烟测试
- 将“编译 + 上传 + 运行验证”串成完整闭环

### `sylixos_telnet_test/SKILL.md`

SylixOS 板卡 Telnet 登录与板端测试子 skill。

**功能**:
- 从用户输入或 `.reproject` 中提取板卡 IP、工作目录和远端文件路径
- 验证板卡 `23` 端口可达
- 通过 telnet 登录板卡
- 检查上传文件是否存在并修正执行权限
- 执行板端测试命令并采集输出
- 汇总真实板端运行结果

**适用场景**:
- 上传后立即在板卡上运行应用程序
- 通过 telnet 做板端冒烟测试
- 将“编译 + 上传 + 运行验证”串成完整闭环

## 注意事项

1. **编译前提**: 确保 SylixOS 工具链已安装并在 PATH 中
2. **网络要求**: 上传前确保能 ping 通板卡 IP
3. **FTP 服务**: 板卡上必须运行 FTP 服务
4. **Telnet 服务**: 板卡测试前确保 `23` 端口可访问
5. **文件权限**: FTP 上传子 skill 现已默认在上传后执行远端 `chmod 755`，不要省略该步骤
6. **路径规范**: config.mk 中必须使用绝对路径，不能使用相对路径
7. **构建入口**: companion project 优先使用 `make all|clean -f "$BASE/libsylixos/SylixOS/mktemp/multi-platform.mk"`；未做 wrapper 的本地 `Makefile` 直接执行 `make clean` 可能只清掉 `build//Release`，不会清掉真实的 `build/<PLATFORM>/Release`
8. **输出目录**: 标准输出目录是 `build/<PLATFORM>/Debug/` 或 `build/<PLATFORM>/Release/`，例如 `build/ARM64_GENERIC/Release/`
9. **新建工程元数据**: 对于后续会反复上传和板测的 SylixOS 新工程，创建时就应生成 `.reproject`，至少包含 `DeviceSetting`、`OutputSetting` 和一个正确的 `UploadPath`
10. **长期测试轮次**: 对于长时间板卡验证问题，重大策略变更、绑核变更或核心二进制变更前优先 reboot，再进入下一轮验证
11. **BSP 镜像替换**: 替换 `/boot` 下的 BSP 镜像时，先备份当前镜像，再上传新镜像；上传后执行 `sync`、显式 `reboot`，并在重启后核对 build time 是否与新镜像一致
12. **仓库维护约束**: 每次新增或创建 skill 文件时，同步更新 `README.md`，确保人类读仓库时能看到新 skill 的用途和位置

## 扩展说明

本仓库采用模块化设计，便于后续扩展：
- 每个子 skill 独立维护
- 主 skill 负责路由和协调
- 完整链路推荐顺序为：编译 → 上传 → telnet 测试
- FTP 上传默认入口为 `sylixos_ftp_upload/scripts/ftp_sylixos_upload.py`，统一处理路径解析、权限修正和最终 `sync`
- 可随时添加新的子 skill（如调试、专项验证等）
