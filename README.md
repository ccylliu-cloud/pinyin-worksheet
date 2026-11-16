# pinyin-worksheet · V2.1

把老师发的词表图片或文本，整理成可打印的「看拼音写词语」练习纸。

**A4 · 15mm 等大田字格 · 单层 ɑ · 自动分页 · 不需要 Chrome**

[下载 V2.1 试用包](https://github.com/ccylliu-cloud/pinyin-worksheet/releases/tag/v2.1.0) · [查看示例 PDF](examples/sample-52.pdf) · [Skill 工作流](SKILL.md) · [反馈问题](https://github.com/ccylliu-cloud/pinyin-worksheet/issues)

![52词练习纸示例](examples/sample-52.png)

适合家长、老师制作生词默写单。Agent 负责一次识图、逐字核对和按词语语境注音，Python 负责校验与 PDF 排版。**这是配合 Agent 使用的 Skill，不是上传图片后自动识字注音的独立软件。**

## 1. 下载与安装

### 推荐：下载 ZIP

1. 打开 [Releases](https://github.com/ccylliu-cloud/pinyin-worksheet/releases/latest)，下载附件 **pinyin-worksheet-v2.1.zip**。
2. 解压得到 `pinyin-worksheet` 文件夹，保留里面的 `SKILL.md`、`scripts/`、`assets/` 等全部内容。
3. 将整个文件夹放入所用 Agent 的 Skills 目录。以 Codex 默认目录为例：`~/.codex/skills/pinyin-worksheet/`；自定义了 `CODEX_HOME` 时用其下的 `skills/pinyin-worksheet/`。完成后在下一轮对话中调用。
4. 不支持安装 Skill 的 Agent，也可以让它读取本地 `SKILL.md` 并按步骤操作；前提是它能阅读图片、读写文件和运行 Python。

只下载 `SKILL.md` 不够，生成 PDF 需要随包源码和字体。GitHub 的 **Code → Download ZIP** 也可用，解压后把根文件夹改名为 `pinyin-worksheet`。

### 使用 Git 下载

```bash
git clone https://github.com/ccylliu-cloud/pinyin-worksheet.git
cd pinyin-worksheet
```

克隆只是下载；需要自动发现 Skill 时，仍要把整个目录放到宿主的 Skills 目录。不要覆盖已有同名 Skill，先备份旧版。

## 2. 上传词表图片，让 Agent 制作

安装后，上传一张清楚的词表图片，并发送：

> 请用 pinyin-worksheet，把这张图片做成看拼音写词语 PDF。按原图顺序，一次识图后逐字核对，按词语语境注音，保持 A4、15mm 田字格，自动分页。

也可直接提供文本词表。字迹不清或多音字语境不足时，Agent 会向你确认。

- 每张新图片识别一次；同一次任务改标题、重新生成时，复用已核对的词表。
- 不建立跨任务读音库，不默认多 Agent 复核，不反复截图测试字体。
- PDF 默认只有拼音和空格，不印汉字答案。
- 打印选择 **A4、100%／实际大小**，不要选择「适合页面」。

## 3. 不用图片，先跑一个示例

需要 **Python 3.10+**。在本项目目录打开终端。

macOS / Linux：

```bash
python3 scripts/run_worksheet.py -i assets/words-sample.txt -o output/sample.pdf --report output/sample-report.json
```

Windows PowerShell：

```powershell
py -3 scripts/run_worksheet.py -i assets/words-sample.txt -o output/sample.pdf --report output/sample-report.json
```

成功后打开 `output/sample.pdf`。示例是 52 词、109 格、1 页；不是所有 52 词都能放一页，长词较多时会自动分页。

**第一次没有兼容依赖时**，启动器自动创建独立环境并安装；**之后复用**，不反复执行 pip，也不修改全局 Python。字体已随包提供，生成不需要浏览器、OCR 库或额外 API 密钥。使用的 Agent 可能有自己的联网与收费要求。

## 4. 用自己的文本词表

新建 UTF-8 文件 `words.txt`，每行「词语 空格 拼音」，一字一音节：

```text
麻雀 má què
无可奈何 wú kě nài hé
孩子 hái zi
```

运行：

```bash
python3 scripts/run_worksheet.py -i words.txt -o output/worksheet.pdf --title "看拼音写词语（1）" --report output/worksheet-report.json
```

Windows 把 `python3` 换成 `py -3`。含空格的文件路径需要加引号。词表放在本次任务目录，不要覆盖仓库的示例。

支持简单逗号、竖线或制表符分隔，也支持 JSON。轻声不标调；数字声调、`v`、`u:`、大写及非汉字词条会被拒绝。校验失败不会覆盖已有 PDF。Python 不能代替 Agent 判断多音字语义，也不穷举所有合法音节。

## 依赖、离线和常见问题

| 问题 | 处理 |
|---|---|
| 没有 Python，或版本太旧 | 安装 Python 3.10+，或使用宿主提供的兼容 Python。Windows 可用 `py -3 --version` 检查。 |
| 首次安装失败 | 首次缺依赖需要网络及 Python 的 venv/ensurepip 支持；受限环境可请宿主准备依赖。不会无限重试。 |
| 已经安装依赖，还要重新识图吗？ | 两者独立：依赖只在缺失或不兼容时安装；新图仍识别一次，同任务修改复用词表。 |
| 想离线生成 | 先在所选 Python 环境安装 `requirements.txt`；生成 PDF 可离线。Agent 能否离线取决于其宿主。 |
| 想先检查环境 | `python3 scripts/run_worksheet.py --check`，不安装、不生成；正常出题不必额外跑。 |
| 没有写入权限 | 输出选可写目录；缓存用 `--cache-dir "/your/cache"` 或环境变量 `PINYIN_WORKSHEET_CACHE` 指定。 |
| 词太多／超过一页 | 接受自动分页，不为了单页缩小 15mm 字格。 |
| 个别拼音太宽 | 可用 `--py-pt 12.5` 降低拼音字号，字格仍保持 15mm。 |
| 收到无声调警告 | 请 Agent 确认是轻声还是漏标，不直接忽略。 |
| 如何报告问题 | 到 [Issues](https://github.com/ccylliu-cloud/pinyin-worksheet/issues) 提供系统、Python版本、命令和错误信息；只附你愿意公开的词表示例。 |

运行依赖为 `reportlab>=4.2,<5` 和 `pypdf>=5,<7`。优先复用当前解释器，再检查独立缓存，均不可用才安装。缓存默认在 `~/.cache/pinyin-worksheet/`，按 Python 版本、平台和 requirements 指纹区分；换机器或清理缓存后可能需要重新准备。代码与字体随 ZIP 分发，Python 运行环境不随包复制。

已备好依赖时，也可直接运行 `scripts/build_worksheet.py`；`--summary` 显示短摘要，`--report` 保存完整 JSON。首次安装验收或字体/版式改动时才检查一次字形及代表性整页，日常出题不跑全套回归。

## 开发与验证

```bash
python3 scripts/test_launcher.py
python3 scripts/test_regression.py --output-dir output/regression
```

V2.1 发布前已通过 40 项原有回归与 10 项启动器测试，并实测全新环境首次安装、已有环境复用及缓存环境复用。实测平台为 macOS / Python 3.12；Windows/Linux 尚未做实机验证。详见 [验证记录](TEST-REPORT.txt)。

目录包括 `SKILL.md`、`scripts/`、`references/`、`assets/`、`examples/` 和 `requirements.txt`。公开仓库不含老师原图、个人任务词表、虚拟环境或历史备份。提交反馈前注意去除自己的私人路径和信息。

## 使用与字体许可

本仓库供下载试用；尚未为原创代码指定开源许可证，不应据此认定可任意商业分发。随包字体分别使用其原有许可，见 [DejaVu 许可](assets/fonts/LICENSE-DejaVu.txt) 和 [Noto Sans SC OFL](assets/fonts/OFL-NotoSansSC.txt)。
