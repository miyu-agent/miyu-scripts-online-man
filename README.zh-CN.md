<p align="center">
  <a href="README.md">English</a> | 简体中文
</p>

# 在线 man 手册

> <sub>本文档由 Anthropic 的 Claude Fable 5.2 生成。</sub>

这是 Miyu 的一个脚本软件包，提供一件工具 `online_man`，可以在线搜索和阅读 Linux 的 man 手册。数据来自 Arch Linux 的手册站 <https://man.archlinux.org/>，里面有 Arch 官方软件源中所有软件包的手册，并且有多种语言；如果这个手册站没有你要的手册，工具会再到 <https://man7.org/> 查找。

工具的参数如下：

| 参数 | 说明 |
|---|---|
| `action` | 要执行的操作：`search` 搜索手册，`read` 阅读一页手册。 |
| `query` | 用于 `search`：要搜索的关键词。工具会同时在手册的名字和一句话描述里搜索。 |
| `name` | 用于 `read`：手册页的名字，例如 `ls`、`pacman.conf`，也可以写成 `printf(3)`。 |
| `section` | 手册的章节，例如 `1`、`3`、`5`、`8`、`3p`。使用 `read` 时如果没有填写章节，由手册站选择常用的那一节。 |
| `language` | 手册的语言，例如 `en`、`zh_CN`、`ja`、`de`，默认是 `en`。如果没有这种语言的版本，工具会返回英文版，并说明这一点。 |
| `limit` | 用于 `search`：列出的条数，范围是 1–50，默认是 10。 |
| `find` | 用于 `read`：从第一处包含这段文字的那一行开始阅读，例如某个选项 `--color`、某一节 `EXAMPLES`。 |
| `offset` | 用于 `read`：从第几个字符开始阅读，用来接着上次没有读完的地方继续往下读。 |
| `max_chars` | 用于 `read`：一次返回的字符数，范围是 2000–60000，默认是 12000。 |
| `format` | 输出的格式。`md`（默认）供人和 AI 阅读；`json` 供代码使用，例如用 `miyu call` 把结果交给 `jq`、Python 处理。出错时输出的也是 JSON：`{"ok": false, "error": …}`。 |

如果手册很长，工具一次只返回一段，并在末尾写出下一段的 `offset`。英文版读取的是手册站的纯文本；其他语言读取的是网页版，再转换成文本，因为手册站的纯文本会把非 ASCII 的字母全部丢掉。这个工具只使用 Python 标准库。
