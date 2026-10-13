# 英文视频双语阅读 Skill

安装这一个 Skill，把 YouTube 英文视频链接发给 Agent，即可生成中文与英文对照阅读稿，首次使用会询问是否安装阅读器；确认后，桌面出现带图标的“阅·批注”快捷方式。

[下载 v0.1.1 安装包](https://github.com/yd1601970552-stack/xiaodao-video-to-reader/raw/refs/heads/main/downloads/xiaodao-video-to-reader-v0.1.1.zip)

## 怎么用

从仓库的 Code → Download ZIP 下载并解压，把完整文件夹交给支持本地 Skill 的 Agent 安装。若没有导入入口，让 Agent 读取文件夹里的 SKILL.md 并按其执行。豆包工作的原生 Skill 导入路径尚未验证，不承诺所有 Agent 都支持同一种安装方式。

可以直接把这段话发给 Agent：

> 请从 https://github.com/yd1601970552-stack/xiaodao-video-to-reader 下载并安装这个 Skill。完整保留其内置文件。然后处理这个视频：【粘贴 YouTube 链接】。稿件默认放桌面；首次安装阅读器时先让我确认，再创建带图标的桌面快捷方式。

如果 Agent 无法访问 GitHub，手动下载 ZIP 后提供解压文件夹位置即可。

安装后发送：

> 用 xiaodao-video-to-reader 处理这个视频：【YouTube 链接】。稿件默认交付桌面，自动准备必要依赖；首次使用请询问我是否安装阅读器。

也可以加一句“稿件放到【指定文件夹】”。首次运行时点选 Agent 提供的“安装”确认，即可创建桌面“阅·批注”快捷方式。若 Agent 没有按钮界面，回复“确认安装”即可。以后不用重复安装。点击快捷方式，把双语稿拖进去，即可划线、批注和导出；选择暂不安装也能正常获得双语稿。

## 包里有什么

- 当前 Agent 负责的完整字幕整理、翻译与逐段语义审校规范。
- 固定双语 HTML 模板：中文主标题、完整英文原题、弱化广告标记。
- 自动建立独立 Python 环境、获取字幕、校验并交付稿件的程序，以及须明确确认的阅读器安装程序。
- 完整宝玉翻译 Skill 与阅读批注器，均附来源与许可证，无需单独安装。

需要 Agent 具有本地文件、命令执行及翻译能力，Python 3.10+（可用 Agent 自带运行时），并且网络能够访问 YouTube 和首次依赖下载地址。网络方案和 Agent 是否收费由用户自行选择，本 Skill 不调用付费翻译 API。没有英文字幕时停止，第一版没有音频转录兜底。

## 验证边界

豆包此前已通过一个真实视频样例的字幕获取、842 段完整覆盖、翻译审校和渲染检查。集成版本的桌面交付与阅读器检查见 VALIDATION.md。程序校验不等于译文准确性证明；每篇仍由 Agent 逐段审校。批注保存在当前浏览器，建议导出备份。

## 开源来源

宝玉翻译 Skill：JimLiu/baoyu-skills，MIT，Copyright (c) 2026 Jim Liu；许可证位于 vendor/baoyu-translate/LICENSE。

阅读器：yd1601970552-stack/html-reader-annotator，MIT，小道（小道的修炼日常）；许可证位于 assets/reader/LICENSE。

第三方文件固定版本与 SHA-256 见 vendor-manifest.json。上游文件原样打包，新增 EXTEND.md 为本项目默认配置。新增代码与模板采用本项目 LICENSE。公开视频不等于开源资料，包内不附带他人视频全文。

## 阅读器更新

阅读器文件安装在用户本地应用目录，桌面为带图标的快捷方式。安装更新保留固定文件位置和旧版本备份。用户原有同名快捷方式不会被覆盖。当前快捷方式安装支持 Windows；其他系统可直接打开内置阅读器 HTML。

你在阅读器上游 GitHub 完成迭代后，通知维护 Agent 同步即可。维护入口：node scripts/sync-reader.mjs（只检查），node scripts/sync-reader.mjs --apply（更新包内文件），然后重新验证并运行 python scripts/package.py。用户安装版本的更新仍需明确确认，不会自动联网覆盖。
