# 在线 man 手册

Miyu 脚本包，带一件工具 `online_man`：在线搜、读 Linux man 手册。数据来自 Arch Linux 的手册站 <https://man.archlinux.org/>（Arch 官方源里所有包的手册，多种语言）；那边没有的再找 <https://man7.org/>。

| 参数 | 说明 |
|---|---|
| `action` | `search` 搜，`read` 读一页 |
| `query` | search：关键词，名字和一句话描述里都搜 |
| `name` | read：页名，如 `ls`、`pacman.conf`，也可以写 `printf(3)` |
| `section` | 章节，如 `1`、`3`、`5`、`8`、`3p`；read 不写时由手册站挑常用的那一节 |
| `language` | 语言，如 `en`、`zh_CN`、`ja`、`de`，默认 `en`；没有这个语言的照英文版给，并说明 |
| `limit` | search：列几条，1–50，默认 10 |
| `find` | read：从第一处含这段字的那一行开始，比如某个选项 `--color`、某一节 `EXAMPLES` |
| `offset` | read：从第几个字开始，接着上次没读完的地方往下读 |
| `max_chars` | read：一次给多少字，2000–60000，默认 12000 |
| `format` | `md`（默认）给人和 AI 读；`json` 给代码用，比如 `miyu call` 接 `jq`、Python。出错也是 JSON：`{"ok": false, "error": …}` |

长的手册一次给一段，末尾写下一段的 `offset`。英文版读手册站的纯文本；别的语言读网页版再转成文本（手册站的纯文本会把非 ASCII 字母全丢掉）。只用标准库。
