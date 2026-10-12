import { text, type Text } from "./locale";

export const SITE_NAME = "Wemute";
export const UPDATED = "2026-10-12";

// Operator details shown on legal pages. Set PUBLIC_CONTACT_EMAIL at build time;
// the pages state plainly when it is missing instead of inventing an address.
export const CONTACT_EMAIL = (import.meta.env.PUBLIC_CONTACT_EMAIL as string | undefined)?.trim() || "";

export const HOME = {
  metaTitle: text(
    "Free File Converter — Images, Video & Audio, No Upload | Wemute",
    "免费文件转换器 — 图片、视频、音频，无需上传 | Wemute",
  ),
  metaDescription: text(
    "Convert HEIC to JPG, compress images, turn MP4 into MP3 or GIF and more — free, in your browser, with nothing uploaded. Batch-ready and private.",
    "HEIC 转 JPG、图片压缩、MP4 转 MP3 或 GIF 等，免费在浏览器中完成，文件不会上传。支持批量，安全私密。",
  ),
  eyebrow: text("Free · private · runs in your browser", "免费 · 私密 · 在浏览器中运行"),
  h1: text("Convert files without uploading them.", "转换文件，无需上传。"),
  intro: text(
    "Drop images, video or audio and choose what they become. Wemute does the work on your own device, so it is fast, free and private by design.",
    "拖入图片、视频或音频，选择要转换成什么。Wemute 在你自己的设备上完成处理，因此快速、免费，而且天然私密。",
  ),
  whyTitle: text("Why convert locally?", "为什么要在本地转换？"),
  why: [
    {
      title: text("Nothing leaves your device", "文件不离开设备"),
      body: text(
        "Most online converters upload your files to their servers. Wemute processes them inside your browser, so personal photos and documents stay with you.",
        "大多数在线转换器会把文件上传到它们的服务器。Wemute 在浏览器内处理，个人照片和文件始终留在你手里。",
      ),
    },
    {
      title: text("No waiting on uploads", "无需等待上传"),
      body: text(
        "There is no upload or download queue. A batch of photos converts as fast as your computer can work.",
        "没有上传和下载排队，一批照片的转换速度只取决于你的电脑。",
      ),
    },
    {
      title: text("Made for batches", "为批量而设计"),
      body: text(
        "Drop a whole set, choose one result for all of them, and override individual files only when you need to.",
        "一次拖入整批文件，统一选择结果，只在需要时单独调整个别文件。",
      ),
    },
  ],
  faqs: [
    {
      q: text("Is Wemute really free?", "Wemute 真的免费吗？"),
      a: text(
        "Yes. There is no account, trial or watermark. The site is supported by a small number of clearly labelled ads placed away from the tools.",
        "是的。无需账号，没有试用期，也没有水印。网站依靠少量明确标注、且远离工具区域的广告维持运营。",
      ),
    },
    {
      q: text("How can a website convert files without uploading them?", "网站怎么能不上传就转换文件？"),
      a: text(
        "Modern browsers can run compiled code at near-native speed. Wemute ships its converters — including FFmpeg for video and audio — to your browser, which then processes files using your device's processor.",
        "现代浏览器可以以接近原生的速度运行编译后的代码。Wemute 把转换器（包括处理音视频的 FFmpeg）发送到你的浏览器，再由浏览器使用你设备的处理器处理文件。",
      ),
    },
    {
      q: text("Does it work on my phone?", "手机上可以用吗？"),
      a: text(
        "Image tools work well on phones. Video conversion works too but is slower and limited by the phone's memory, so very large videos are best converted on a computer.",
        "图片工具在手机上表现很好。视频转换也能用，但速度较慢并受手机内存限制，超大视频建议在电脑上转换。",
      ),
    },
  ],
};

export interface LegalPage {
  slug: "privacy" | "terms" | "about";
  metaTitle: Text;
  metaDescription: Text;
  title: Text;
  intro: Text;
  sections: { heading: Text; body: Text }[];
}

export const LEGAL: LegalPage[] = [
  {
    slug: "privacy",
    metaTitle: text("Privacy Policy | Wemute", "隐私政策 | Wemute"),
    metaDescription: text(
      "How Wemute keeps your files on your device, and what limited website data is used for optional analytics and advertising.",
      "Wemute 如何让你的文件留在本机，以及可选的统计和广告会使用哪些有限的网站数据。",
    ),
    title: text("Privacy Policy", "隐私政策"),
    intro: text(
      "Wemute is built so that the file work happens on your device. This policy separates that core processing from the limited data a public website needs to run and pay for itself.",
      "Wemute 的设计让文件处理在你的设备上完成。本政策将这一核心处理与公开网站运营和维持所需的有限数据区分开来。",
    ),
    sections: [
      {
        heading: text("Your files", "你的文件"),
        body: text(
          "Files you add are read and converted inside your browser. Their contents, names and metadata are never sent to Wemute or anyone else, and they disappear when you close or reload the page.",
          "你添加的文件在浏览器内读取和转换。文件内容、文件名和元数据不会发送给 Wemute 或任何第三方，关闭或刷新页面后即会消失。",
        ),
      },
      {
        heading: text("Converter code", "转换器代码"),
        body: text(
          "Video and audio tools download the open-source FFmpeg engine (about 10 MB to download) from the jsDelivr content network the first time you use them. This request contains no file data; jsDelivr sees only a normal request for a public file.",
          "视频和音频工具首次使用时会从 jsDelivr 内容分发网络下载开源的 FFmpeg 引擎（下载约 10 MB）。该请求不包含任何文件数据，jsDelivr 只会看到一个对公开文件的普通请求。",
        ),
      },
      {
        heading: text("Analytics", "访问统计"),
        body: text(
          "If you agree, Google Analytics records anonymous page views and counts of conversions (for example, '3 files converted to JPG'). It never receives file names, contents or sizes tied to a file. Declining has no effect on any tool.",
          "在你同意的情况下，Google Analytics 会记录匿名的页面访问和转换次数（例如“3 个文件转换为 JPG”）。它不会收到文件名、内容或与具体文件关联的大小。拒绝不会影响任何工具的使用。",
        ),
      },
      {
        heading: text("Advertising", "广告"),
        body: text(
          "Wemute shows Google AdSense ads on explanatory sections of the site. Google and its partners may use cookies to serve and measure ads; where required, you are asked for consent first and can change your choice through Cookie settings in the footer. Ads are never shown inside the converter.",
          "Wemute 在网站的说明性内容区域展示 Google AdSense 广告。Google 及其合作伙伴可能使用 Cookie 来投放和衡量广告；在法律要求的地区会先征得你的同意，你也可以通过页脚的“Cookie 设置”修改选择。转换器内部不会显示广告。",
        ),
      },
      {
        heading: text("Contact", "联系方式"),
        body: text(
          "Questions about privacy can be sent to the address below.",
          "关于隐私的问题可以发送至下方地址。",
        ),
      },
    ],
  },
  {
    slug: "terms",
    metaTitle: text("Terms of Use | Wemute", "使用条款 | Wemute"),
    metaDescription: text(
      "Terms for using Wemute's free browser-based file conversion tools.",
      "使用 Wemute 免费浏览器文件转换工具的条款。",
    ),
    title: text("Terms of Use", "使用条款"),
    intro: text(
      "You may use Wemute's tools free of charge for lawful purposes. By using the site you agree to these terms.",
      "你可以出于合法目的免费使用 Wemute 的工具。使用本网站即表示你同意以下条款。",
    ),
    sections: [
      {
        heading: text("Your content", "你的内容"),
        body: text(
          "You are responsible for the files you convert and must have the right to use them. Because processing happens on your device, Wemute never receives or stores your files.",
          "你需要对所转换的文件负责，并且必须拥有使用它们的权利。由于处理在你的设备上进行，Wemute 不会接收或存储你的文件。",
        ),
      },
      {
        heading: text("No warranty", "免责声明"),
        body: text(
          "The tools are provided as they are. Keep your original files: conversion results can differ between browsers and devices, and Wemute is not liable for lost or altered data.",
          "本工具按现状提供。请保留原始文件：不同浏览器和设备的转换结果可能有所不同，Wemute 不对数据丢失或改变承担责任。",
        ),
      },
      {
        heading: text("Open-source components", "开源组件"),
        body: text(
          "Wemute uses FFmpeg (LGPL/GPL), libheif via heic-to (LGPL-3.0), React (MIT) and fflate (MIT). Their source code is available from their projects.",
          "Wemute 使用了 FFmpeg（LGPL/GPL）、通过 heic-to 使用的 libheif（LGPL-3.0）、React（MIT）和 fflate（MIT）。其源代码可从各自项目获取。",
        ),
      },
      {
        heading: text("Changes", "条款变更"),
        body: text(
          "These terms may be updated as the service changes. The date at the top shows the latest version.",
          "随着服务调整，本条款可能会更新。页面顶部的日期为最新版本日期。",
        ),
      },
    ],
  },
  {
    slug: "about",
    metaTitle: text("About Wemute — Private File Conversion in Your Browser", "关于 Wemute — 在浏览器中私密地转换文件"),
    metaDescription: text(
      "Wemute is an independent set of free file tools built around one idea: convert files on your own device instead of uploading them.",
      "Wemute 是一组独立的免费文件工具，核心理念只有一个：在你自己的设备上转换文件，而不是上传。",
    ),
    title: text("About Wemute", "关于 Wemute"),
    intro: text(
      "Wemute is an independent utility made for one everyday job: turning a file into the format you need, without handing it to a stranger's server.",
      "Wemute 是一个独立的小工具，专注于一件日常小事：把文件转换成你需要的格式，而不必交给陌生的服务器。",
    ),
    sections: [
      {
        heading: text("How it works", "工作原理"),
        body: text(
          "Images are decoded and re-encoded with your browser's own graphics engine; HEIC uses libheif compiled to WebAssembly; video and audio use FFmpeg compiled to WebAssembly. Everything runs in your tab.",
          "图片使用浏览器自身的图形引擎解码和重新编码；HEIC 使用编译为 WebAssembly 的 libheif；音视频使用编译为 WebAssembly 的 FFmpeg。一切都在你的浏览器标签页中运行。",
        ),
      },
      {
        heading: text("Principles", "原则"),
        body: text(
          "Sensible defaults, batches first, no accounts, no watermarks, and ads kept well away from the tools.",
          "合理的默认设置、批量优先、无需账号、没有水印，广告远离工具区域。",
        ),
      },
      {
        heading: text("Contact", "联系"),
        body: text(
          "Suggestions for new tools and bug reports are welcome at the address below.",
          "欢迎通过下方地址提出新工具建议或反馈问题。",
        ),
      },
    ],
  },
];

export const LEGAL_BY_SLUG = new Map(LEGAL.map((page) => [page.slug, page]));
