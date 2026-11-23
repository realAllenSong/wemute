# 更新记录

Wemute 每个版本新增和修复的内容。下载见 [GitHub Releases](https://github.com/realAllenSong/wemute/releases)。

## v0.7.6

- **设置 › 关于**、[NOTICE](NOTICE) 和[贡献者许可协议](CLA.md)中的版权方改为法定姓名。

## v0.7.5

- **设置 › 关于** 中的版权方改为 realAllenSong，与 [NOTICE](NOTICE) 一致。外部贡献者在第一次提交 PR 时需签署[贡献者许可协议](CLA.md)。

## v0.7.4

- **给 AI 智能体用**：`wemute mcp` 是一个 MCP 服务器，Claude Code、Codex、Cursor、Claude Desktop 等智能体可以直接用 Wemute 读取和转换文件。**设置 › 集成** 里还能一键安装 `wemute` 技能，教 Claude Code 和 Codex 使用命令行。详见 [docs/cli.md](docs/cli.md#wemute-mcp--wemute-for-ai-agents)。
- `wemute convert --out 目录`：把这一次的输出存到你指定的文件夹。

## v0.7.3

- **擦除不再闪退**：涂抹完按「擦除」时 Wemute 可能直接退出。现在蒙版按你的笔画、以照片原尺寸生成，不再借助一块巨大的屏幕画布。

## v0.7.2

- **在哪台 Mac 上都能下载**：app 现在自带 HTTPS 证书。之前没装 Homebrew 的 Mac 下载不了模型和组件。
- **下载不会卡住**：连接卡住 30 秒就会放弃，自动换备用下载源。擦除和放大模型现在优先从 Wemute 自己的 GitHub 镜像下载。
- **`wemute models` 和 `wemute doctor`**：在命令行安装模型，以及一键检查这台 Mac 上哪些功能可用。

## v0.7.1

- **所有工具一个入口**：工具栏里的「工具」菜单和 ⌘K 搜索列的是同样的东西，所以去掉了「工具」菜单。**搜索工具 ⌘K** 能搜索全部工具，什么都不输入时直接列出全部。

## v0.7.0

- **首个签名版本**：使用 Developer ID 签名、经过 Apple 公证，并通过 Sparkle 自动更新。
- **`wemute extract`**：把任何文件或文件夹变成大模型能读的 Markdown、纯文本或 JSON 行。它能读出：
  - PDF 的分页和表格，扫描页自动 OCR；
  - Word 的标题、Excel 的工作表、PPT 的幻灯片和备注；
  - 截图；
  - 电话会录音，可以标出说话人；
  - 带附件的邮件、压缩包。

  详见[给脚本和 AI 智能体用](#给脚本和-ai-智能体用)。
- **字幕和朗读（借助 ThunderTalk）**：
  - 字幕可以是 SRT、VTT、文字稿，或者分说话人的文字稿；
  - 转写用你下载的最准的模型；
  - 朗读用 VoxCPM2。
- **照片工具更好用**：
  - 证件照换底和新增的背景虚化，改用 Apple 的主体抠图，换成红底、蓝底时发丝也干净；
  - 擦除大一点的物体时，不再留下残影或深色污迹。
- **和 macOS 融为一体**：
  - 访达右键快速操作、快捷指令；
  - `wemute` 命令行；
  - 设置窗口、原生菜单栏和 ⌘K 搜索。
