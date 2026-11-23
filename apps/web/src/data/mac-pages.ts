import { text, type Text } from "./locale";
import type { Faq } from "./tools";

// Pages about the Mac app. Facts follow the README, docs/cli.md and the
// competitors' own pages (checked 2026-11-22); keep comparisons fair.

export type MacSlug = "mac" | "permute-alternative" | "file-to-text-for-ai";

export interface MacPage {
  slug: MacSlug;
  metaTitle: Text;
  metaDescription: Text;
  /** Breadcrumb and link label. */
  name: Text;
  h1: Text;
  answer: Text;
  pointsTitle: Text;
  points: { title: Text; body: Text }[];
  steps: Text[];
  compare: {
    title: Text;
    columns: Text[];
    rows: { label: Text; cells: Text[] }[];
    note?: Text;
  };
  elseTitle: Text;
  otherChoices: Text[];
  faqs: Faq[];
}

const STEPS_INSTALL = [
  text(
    "Download Wemute.dmg, drag Wemute to Applications and open it. It is signed and notarized by Apple.",
    "下载 Wemute.dmg，把 Wemute 拖进“应用程序”后打开。安装包已经过 Apple 签名和公证。",
  ),
];

export const MAC_PAGES: MacPage[] = [
  {
    slug: "mac",
    metaTitle: text("Wemute for Mac — Free, Offline File Converter for macOS", "Wemute Mac 版 — 免费、离线的 Mac 文件转换器"),
    metaDescription: text(
      "A free, open-source Mac app that converts images, video, audio, Office, iWork, PDF and e-books, with OCR, background removal and subtitles. Nothing is uploaded.",
      "免费开源的 Mac 应用：图片、视频、音频、Office、iWork、PDF、电子书都在本机转换，还能识别文字、抠图、生成字幕。文件不上传。",
    ),
    name: text("Wemute for Mac", "Mac 版"),
    h1: text("Wemute for Mac", "Wemute Mac 版"),
    answer: text(
      "Wemute for Mac is a free, open-source file converter for macOS 14 or later on Apple silicon. Drop in any mix of files, read one sentence per kind, press Convert. Images, video, audio, Word, Excel, PowerPoint, Pages, Numbers, Keynote, PDF and e-books are all handled on your Mac, with no account and nothing uploaded.",
      "Wemute Mac 版是一款免费开源的文件转换器，适用于 macOS 14 及以上、Apple 芯片的 Mac。把一堆文件拖进去，每类文件一句话，点“转换”就好。图片、视频、音频、Word、Excel、PowerPoint、Pages、Numbers、Keynote、PDF 和电子书，都在你的 Mac 上完成，不用注册，也不上传。",
    ),
    pointsTitle: text("What sets it apart", "它的不同之处"),
    points: [
      {
        title: text("One app for almost every file", "一个应用，几乎什么文件都能转"),
        body: text(
          "Media, documents, PDFs, e-books, fonts, archives and data files, in one window. A mixed batch is sorted by kind, and each kind runs in its own queue.",
          "音视频、文档、PDF、电子书、字体、压缩包、数据文件，都在一个窗口里。混在一起拖进来也没关系，按类别分好，各走各的队列。",
        ),
      },
      {
        title: text("Photo and scan tools on Apple's frameworks", "照片和扫描工具，用的是 Apple 自己的框架"),
        body: text(
          "Remove a background, make an ID photo, blur a portrait background, recognize Chinese and English text, flatten a phone photo of a page into a scan. These run on the Neural Engine, with nothing to download.",
          "抠图去背景、证件照换底色、人像背景虚化、中英文文字识别、把手机拍的纸页压平成扫描件。都跑在神经网络引擎上，不用额外下载。",
        ),
      },
      {
        title: text("Ready for scripts and AI agents", "脚本和 AI 智能体也能用"),
        body: text(
          "The wemute command converts without the window and turns any file into Markdown a language model can read. wemute mcp lets Claude Code, Codex, Cursor and Claude Desktop use it directly.",
          "wemute 命令行不开窗口也能转换，还能把任何文件变成大模型读得懂的 Markdown。wemute mcp 让 Claude Code、Codex、Cursor、Claude Desktop 直接调用它。",
        ),
      },
    ],
    steps: [
      ...STEPS_INSTALL,
      text("Drop files onto the window. Each kind of file gets one sentence, such as “Convert 3 images to WebP”.", "把文件拖进窗口。每类文件一句话，比如“把 3 张图片转成 WebP”。"),
      text("Change a format by clicking the word in the sentence, then press Convert. Results appear next to the originals.", "想换格式，点句子里的那个词，然后点“转换”。结果就放在原文件旁边。"),
    ],
    compare: {
      title: text("What it converts", "能转什么"),
      columns: [text("Files", "文件"), text("Become", "转成")],
      rows: [
        { label: text("Images", "图片"), cells: [text("HEIC, RAW, JPG, PNG, WebP, AVIF, TIFF, GIF", "HEIC、RAW、JPG、PNG、WebP、AVIF、TIFF、GIF"), text("any of those, one PDF, a ZIP", "以上任意格式、合成一个 PDF、打包 ZIP")] },
        { label: text("Video", "视频"), cells: [text("MOV, MP4, MKV, WebM, AVI", "MOV、MP4、MKV、WebM、AVI"), text("H.264 or H.265 (hardware encoded), ProRes, WebM, GIF, subtitles", "H.264 或 H.265（硬件编码）、ProRes、WebM、GIF、字幕")] },
        { label: text("Audio", "音频"), cells: [text("WAV, MP3, M4A, FLAC, AIFF, OGG", "WAV、MP3、M4A、FLAC、AIFF、OGG"), text("any of those, a transcript", "以上任意格式、文字稿")] },
        { label: text("Documents", "文档"), cells: [text("Word, Excel, PowerPoint, Pages, Numbers, Keynote", "Word、Excel、PowerPoint、Pages、Numbers、Keynote"), text("PDF, DOCX, XLSX, PPTX, CSV, one PNG per slide", "PDF、DOCX、XLSX、PPTX、CSV、每页幻灯片一张 PNG")] },
        { label: text("PDF", "PDF"), cells: [text("PDF, scanned PDF", "PDF、扫描版 PDF"), text("Word, page images, text, a smaller PDF, a searchable PDF", "Word、逐页图片、文字、更小的 PDF、可搜索的 PDF")] },
        { label: text("E-books", "电子书"), cells: [text("EPUB, MOBI, AZW3", "EPUB、MOBI、AZW3"), text("EPUB, MOBI, AZW3, PDF", "EPUB、MOBI、AZW3、PDF")] },
      ],
      note: text(
        "Fonts, SVG, archives, Markdown, HTML and JSON are covered too. Subtitles and read-aloud need ThunderTalk, a free companion app.",
        "字体、SVG、压缩包、Markdown、HTML、JSON 也都支持。生成字幕和朗读需要另装免费的 ThunderTalk。",
      ),
    },
    elseTitle: text("When this website is enough", "什么时候用网页版就够了"),
    otherChoices: [
      text("You only need a quick image, video or audio conversion: the tools on this site run in your browser with nothing to install.", "只是临时转一下图片、视频或音频：这个网站上的工具在浏览器里就能用，什么都不用装。"),
      text("You are on Windows, Linux, an Intel Mac or a phone: the Mac app needs Apple silicon and macOS 14 or later.", "你用的是 Windows、Linux、Intel Mac 或手机：Mac 版需要 Apple 芯片和 macOS 14 及以上。"),
    ],
    faqs: [
      {
        q: text("Is Wemute for Mac free?", "Wemute Mac 版免费吗？"),
        a: text("Yes. It is free and open source under the AGPL-3.0 licence, with no account, trial, watermark or in-app purchase.", "免费。它以 AGPL-3.0 协议开源，不用注册，没有试用期、水印或内购。"),
      },
      {
        q: text("Which Macs does it run on?", "哪些 Mac 能用？"),
        a: text("Macs with Apple silicon (M1 or later) running macOS 14 Sonoma or later. Intel Macs are not supported.", "Apple 芯片（M1 及以后）、macOS 14 Sonoma 及以上的 Mac。不支持 Intel Mac。"),
      },
      {
        q: text("Are my files uploaded anywhere?", "文件会被上传吗？"),
        a: text("No. Every conversion, OCR pass and transcript runs on your Mac. Optional models are downloaded once, the first time you use them, and then work offline.", "不会。转换、文字识别、转写都在你的 Mac 上完成。少数可选模型会在第一次使用时下载一次，之后离线可用。"),
      },
      {
        q: text("Where do I get it?", "在哪里下载？"),
        a: text("From the latest GitHub release. The download is a DMG signed and notarized by Apple. The source code is on GitHub at realAllenSong/wemute.", "从 GitHub 最新版本下载，安装包是经过 Apple 签名和公证的 DMG。源代码在 GitHub 的 realAllenSong/wemute。"),
      },
    ],
  },
  {
    slug: "permute-alternative",
    metaTitle: text("Free Permute Alternative for Mac — Wemute", "免费的 Permute 替代品 — Wemute Mac 版"),
    metaDescription: text(
      "A free, open-source Permute alternative for Mac. Wemute runs on macOS 14 or later and converts documents, PDFs and e-books as well as video, audio and images.",
      "想找免费的 Permute 替代品？Wemute 开源免费，支持 macOS 14 及以上，除了音视频和图片，还能转文档、PDF 和电子书。",
    ),
    name: text("Permute alternative", "Permute 替代品"),
    h1: text("A free Permute alternative for Mac", "一个免费的 Permute 替代品"),
    answer: text(
      "Wemute is a free, open-source alternative to Permute. Both are drag-and-drop converters that work offline. Wemute costs nothing, runs on macOS 14 or later, and also handles Word, Excel, PowerPoint, iWork, PDF and e-books. Permute 4 is a polished paid app ($14.99) that needs macOS 26.",
      "Wemute 是 Permute 的免费开源替代品。两者都是拖进去就能转、离线可用的转换器。Wemute 不要钱，macOS 14 及以上就能用，还能处理 Word、Excel、PowerPoint、iWork、PDF 和电子书。Permute 4 是一款打磨得很好的付费应用（14.99 美元），需要 macOS 26。",
    ),
    pointsTitle: text("Why people switch", "为什么换"),
    points: [
      {
        title: text("Free, and the code is open", "免费，代码公开"),
        body: text("No licence to buy and no upgrade to pay for. Anyone can read the source on GitHub.", "不用买授权，也没有升级费。源代码在 GitHub 上，谁都能看。"),
      },
      {
        title: text("Runs on the macOS you already have", "不用先升级系统"),
        body: text("Wemute needs macOS 14 Sonoma or later. Permute 4 needs macOS 26; older systems stay on Permute 3.", "Wemute 从 macOS 14 Sonoma 起就能用。Permute 4 需要 macOS 26，旧系统只能用 Permute 3。"),
      },
      {
        title: text("Documents in the same window", "文档也在同一个窗口里转"),
        body: text("Word to PDF, PDF to Word, Keynote to PowerPoint, EPUB to PDF, scanned PDF to searchable PDF, next to your video and photo conversions.", "Word 转 PDF、PDF 转 Word、Keynote 转 PowerPoint、EPUB 转 PDF、扫描件转可搜索 PDF，和音视频、照片放在一起处理。"),
      },
    ],
    steps: [
      ...STEPS_INSTALL,
      text("Drop the files you used to give Permute. Video, audio and images each get one line.", "把原来交给 Permute 的文件拖进来。视频、音频、图片各占一行。"),
      text("Pick the format in each line and press Convert. Your choice becomes the default next time.", "在每一行里选好格式，点“转换”。这次的选择会成为下次的默认值。"),
    ],
    compare: {
      title: text("Wemute and Permute side by side", "Wemute 和 Permute 对比"),
      columns: [text("Wemute", "Wemute"), text("Permute 4", "Permute 4")],
      rows: [
        { label: text("Price", "价格"), cells: [text("Free", "免费"), text("$14.99, one-time", "14.99 美元，一次买断")] },
        { label: text("Source code", "源代码"), cells: [text("Open (AGPL-3.0)", "开源（AGPL-3.0）"), text("Closed", "闭源")] },
        { label: text("System", "系统"), cells: [text("macOS 14 or later, Apple silicon", "macOS 14 及以上，Apple 芯片"), text("macOS 26 or later, Apple silicon", "macOS 26 及以上，Apple 芯片")] },
        { label: text("Video, audio, images", "视频、音频、图片"), cells: [text("Yes", "支持"), text("Yes", "支持")] },
        { label: text("Office, iWork, PDF, e-books", "Office、iWork、PDF、电子书"), cells: [text("Yes", "支持"), text("Not its focus", "不是它的重点")] },
        { label: text("OCR, background removal", "文字识别、抠图"), cells: [text("Yes, on Apple Vision", "支持，基于 Apple Vision"), text("—", "—")] },
        { label: text("Command line, MCP for AI agents", "命令行、给 AI 用的 MCP"), cells: [text("Yes", "支持"), text("—", "—")] },
      ],
      note: text("Permute details from its developer's site, November 2026.", "Permute 信息来自其开发者官网，2026 年 11 月。"),
    },
    elseTitle: text("When Permute is the better pick", "什么时候 Permute 更合适"),
    otherChoices: [
      text("You want a paid app with years of polish and a developer you can buy support from.", "你更想要一款打磨多年、有开发者提供支持的付费应用。"),
      text("You already own Permute, or use it through a Downie bundle, and only convert video and audio.", "你已经买了 Permute，或者通过 Downie 套装在用，而且只转音视频。"),
    ],
    faqs: [
      {
        q: text("Is Wemute really free, or is there a Pro version?", "Wemute 真的免费吗？有没有专业版？"),
        a: text("It is free. There is no trial, no watermark and no paid tier in the app. The code is open under AGPL-3.0.", "真的免费。应用里没有试用期、水印，也没有付费档。代码以 AGPL-3.0 开源。"),
      },
      {
        q: text("Can I use it on an older Mac?", "旧一点的 Mac 能用吗？"),
        a: text("Any Mac with Apple silicon on macOS 14 Sonoma or later. Intel Macs are not supported; Permute 3 still runs on them.", "只要是 Apple 芯片、macOS 14 Sonoma 及以上就行。不支持 Intel Mac，Intel Mac 上仍可以用 Permute 3。"),
      },
      {
        q: text("Does Wemute use the hardware video encoder?", "Wemute 用硬件编码吗？"),
        a: text("Yes. H.264 and H.265 output is encoded with the Mac's hardware encoder, and images use several cores at once.", "用。H.264 和 H.265 走 Mac 的硬件编码器，图片会同时用多个核心。"),
      },
      {
        q: text("Does it overwrite my originals?", "会覆盖原文件吗？"),
        a: text("Never. Results go next to the originals or into a folder you choose, and you can add a “-wemute” suffix to every output name.", "不会。结果放在原文件旁边，或者你指定的文件夹；还可以给所有输出文件名加上“-wemute”后缀。"),
      },
    ],
  },
  {
    slug: "file-to-text-for-ai",
    metaTitle: text("Turn Any File into Text for AI on Mac — wemute extract", "在 Mac 上把任何文件变成 AI 能读的文字 — wemute extract"),
    metaDescription: text(
      "wemute extract turns PDFs, scans, Office files, screenshots, recordings and e-mails into Markdown for language models, on your Mac. Local OCR and an MCP server.",
      "wemute extract 在你的 Mac 上把 PDF、扫描件、Office 和 iWork 文件、截图、录音、邮件变成大模型能读的 Markdown。本地文字识别，区分说话人，自带 MCP。",
    ),
    name: text("File to text for AI", "文件转 AI 可读文字"),
    h1: text("Turn any file into text an AI can read", "把任何文件，变成 AI 读得懂的文字"),
    answer: text(
      "On a Mac, wemute extract turns a file or a whole folder into Markdown, plain text or JSON lines for a language model. Scanned pages and screenshots are read with Apple's on-device OCR, recordings become transcripts with speaker labels, and nothing leaves the Mac. AI agents can call it through wemute mcp.",
      "在 Mac 上，wemute extract 能把一个文件或整个文件夹变成 Markdown、纯文本或 JSON 行，交给大模型。扫描页和截图用 Apple 的本机文字识别读取，录音变成区分说话人的文字稿，文件不出这台 Mac。AI 智能体可以通过 wemute mcp 直接调用。",
    ),
    pointsTitle: text("Why use it", "为什么用它"),
    points: [
      {
        title: text("Scans and screenshots work offline", "扫描件和截图，离线也能读"),
        body: text("PDF pages and images without a text layer go through Apple Vision OCR, in Chinese and English. No API key and no cloud service.", "没有文字层的 PDF 页和图片，走 Apple Vision 文字识别，中英文都行。不需要 API Key，也不经过云端。"),
      },
      {
        title: text("Structure survives", "结构不丢"),
        body: text("Headings, lists and tables stay Markdown. PDFs keep their pages, slides keep their speaker notes, sheets keep computed values, e-mails bring every attachment along.", "标题、列表、表格保留成 Markdown。PDF 分页，幻灯片带演讲者备注，表格是计算后的值，邮件连附件一起读出来。"),
      },
      {
        title: text("Made for agents", "为智能体准备好了"),
        body: text("wemute mcp is an MCP server for Claude Code, Codex, Cursor and Claude Desktop, and the app installs a wemute skill for Claude Code and Codex.", "wemute mcp 是给 Claude Code、Codex、Cursor、Claude Desktop 用的 MCP 服务；应用还会给 Claude Code 和 Codex 装好 wemute 技能。"),
      },
    ],
    steps: [
      ...STEPS_INSTALL,
      text("In Settings › Integrations › Command line, choose Install. This adds the wemute command.", "在“设置 › 集成 › 命令行”里点“安装”，就有了 wemute 命令。"),
      text("Run wemute extract report.pdf for Markdown, add --speakers for recordings, or --format json for a folder.", "运行 wemute extract report.pdf 得到 Markdown；录音加 --speakers，整个文件夹可以用 --format json。"),
    ],
    compare: {
      title: text("wemute extract, MarkItDown and Docling", "wemute extract、MarkItDown 和 Docling"),
      columns: [text("wemute extract", "wemute extract"), text("MarkItDown", "MarkItDown"), text("Docling", "Docling")],
      rows: [
        { label: text("Runs on", "运行平台"), cells: [text("macOS 14+, Apple silicon", "macOS 14+，Apple 芯片"), text("Any system with Python", "装了 Python 的任何系统"), text("Any system with Python", "装了 Python 的任何系统")] },
        { label: text("Install", "安装方式"), cells: [text("Mac app, then the CLI", "Mac 应用，再装命令行"), text("pip", "pip"), text("pip", "pip")] },
        { label: text("Scanned PDFs", "扫描版 PDF"), cells: [text("Local OCR (Apple Vision)", "本机文字识别（Apple Vision）"), text("Needs a plugin and a vision LLM, or Azure", "需要插件加视觉大模型，或 Azure"), text("Local OCR", "本机文字识别")] },
        { label: text("Recordings", "录音"), cells: [text("Transcript with speaker labels (via ThunderTalk)", "区分说话人的文字稿（借助 ThunderTalk）"), text("Transcript", "文字稿"), text("Transcript", "文字稿")] },
        { label: text("Pages, Numbers, Keynote", "Pages、Numbers、Keynote"), cells: [text("Yes", "支持"), text("No", "不支持"), text("No", "不支持")] },
        { label: text("MCP server", "MCP 服务"), cells: [text("Yes", "有"), text("Yes", "有"), text("Yes", "有")] },
        { label: text("Licence", "协议"), cells: [text("AGPL-3.0", "AGPL-3.0"), text("MIT", "MIT"), text("MIT", "MIT")] },
      ],
      note: text("MarkItDown and Docling details from their GitHub pages, November 2026.", "MarkItDown 和 Docling 信息来自它们的 GitHub 页面，2026 年 11 月。"),
    },
    elseTitle: text("When MarkItDown or Docling is the better pick", "什么时候 MarkItDown 或 Docling 更合适"),
    otherChoices: [
      text("You work on Linux or Windows, or run conversions on a server: both are Python packages that run anywhere.", "你在 Linux 或 Windows 上，或者要在服务器上跑：这两个都是 Python 包，哪里都能用。"),
      text("You need to import a converter into your own Python code under the MIT licence.", "你要把转换器嵌进自己的 Python 代码，并且需要 MIT 协议。"),
      text("Your PDFs are dense papers with complex layouts and formulas: Docling's layout models are built for that.", "你的 PDF 是版式复杂、带公式的论文：Docling 的版面模型就是为此做的。"),
    ],
    faqs: [
      {
        q: text("What file types can wemute extract read?", "wemute extract 能读哪些文件？"),
        a: text("PDF, Word, Excel, PowerPoint, Pages, Numbers, Keynote, RTF, ODT, HTML, EPUB, MOBI, images, audio and video, .eml e-mails with attachments, and ZIP, 7Z, TAR and RAR archives.", "PDF、Word、Excel、PowerPoint、Pages、Numbers、Keynote、RTF、ODT、HTML、EPUB、MOBI、图片、音视频、带附件的 .eml 邮件，以及 ZIP、7Z、TAR、RAR 压缩包。"),
      },
      {
        q: text("Does it need an API key or the internet?", "需要 API Key 或联网吗？"),
        a: text("No. OCR uses Apple's on-device Vision framework and transcripts use ThunderTalk's local models. A few optional components download once, then work offline.", "不需要。文字识别用的是 Apple 本机的 Vision 框架，转写用的是 ThunderTalk 的本地模型。少数可选组件下载一次后即可离线使用。"),
      },
      {
        q: text("How do I connect it to Claude Code or Cursor?", "怎么接入 Claude Code 或 Cursor？"),
        a: text("Add wemute mcp as an MCP server in your client, or install the wemute skill from Settings › Integrations. The command line reference is in docs/cli.md on GitHub.", "在客户端里把 wemute mcp 加为 MCP 服务，或者在“设置 › 集成”里安装 wemute 技能。命令行说明见 GitHub 上的 docs/cli.md。"),
      },
      {
        q: text("What does the JSON output look like?", "JSON 输出是什么样的？"),
        a: text("One JSON object per line, one line per document, with the extracted text and metadata such as page count and how many pages needed OCR.", "每行一个 JSON 对象，一个文件一行，包含提取出的文字，以及页数、有几页用了文字识别等元数据。"),
      },
    ],
  },
];

export const MAC_PAGE_BY_SLUG = new Map(MAC_PAGES.map((page) => [page.slug, page]));
