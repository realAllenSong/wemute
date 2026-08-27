export const SITE_CONTENT = {
  name: "Wemute",
  tagline: {
    en: "Free image tools that work in your browser",
    zh: "在浏览器里完成的免费图片工具",
  },
  home: {
    path: "/",
    seoTitle: "Free Image Converter, Compressor & Resizer | Wemute",
    seoDescription: "Convert, compress, resize, and round image corners in private browser-local batches. Free, fast, and no upload required.",
    h1: {
      en: "Convert, compress, and resize images in one batch.",
      zh: "一批图片，一次处理完成。",
    },
    intro: {
      en: "Drop a whole set, choose one result, and download. Everything runs locally in your browser — no account and no upload queue.",
      zh: "拖入整组图片，选择结果，然后下载。所有处理都在浏览器本地完成，无需账号，也无需等待上传。",
    },
    faqs: [
      {
        question: { en: "Are my files uploaded?", zh: "文件会被上传吗？" },
        answer: {
          en: "No. Supported image conversions run locally in your browser tab. Wemute never receives the image contents or filenames.",
          zh: "不会。支持的图片转换都在当前浏览器标签页内完成，Wemute 不会收到图片内容或文件名。",
        },
      },
      {
        question: { en: "Can I convert several images at once?", zh: "可以一次转换多张图片吗？" },
        answer: {
          en: "Yes. Add a whole batch, choose one output format for every image, then override individual files only when needed.",
          zh: "可以。一次加入整批图片，为所有图片选择同一种输出格式，需要时再单独覆盖某个文件。",
        },
      },
      {
        question: { en: "Which formats work in Wemute Web?", zh: "Wemute Web 支持哪些格式？" },
        answer: {
          en: "PNG, JPEG, and WebP are fully supported. HEIC input works when the current browser can decode it.",
          zh: "完整支持 PNG、JPEG 和 WebP。当前浏览器能够解码时，也支持 HEIC 输入。",
        },
      },
    ],
  },
};

export const TOOL_CONTENT = [
  {
    slug: "convert-image",
    path: "/tools/convert-image",
    icon: "convert",
    title: { en: "Convert images in one clean batch", zh: "一次转换整批图片" },
    shortTitle: { en: "Convert images", zh: "图片转换" },
    description: {
      en: "Turn PNG, JPEG, WebP and supported HEIC images into the format you need — without sending them anywhere.",
      zh: "将 PNG、JPEG、WebP 和支持的 HEIC 图片批量转成所需格式，全程无需上传。",
    },
    dropHint: { en: "Drop images to choose an output format", zh: "拖入图片，然后选择输出格式" },
    seoTitle: "Free Batch Image Converter — PNG, JPG & WebP | Wemute",
    seoDescription: "Convert PNG, JPG, WebP, and browser-supported HEIC images in one private batch. Free browser-local conversion with no upload.",
    answer: {
      en: "Wemute converts a batch of images to PNG, JPEG, or WebP directly in your browser. Choose one format for the batch, then change individual files only if needed.",
      zh: "Wemute 可以直接在浏览器里把整批图片转换为 PNG、JPEG 或 WebP。先统一选择格式，需要时再单独修改。",
    },
    steps: [
      { en: "Add or drop all the images you want to convert.", zh: "添加或拖入所有需要转换的图片。" },
      { en: "Choose PNG, JPEG, or WebP once for the whole batch.", zh: "为整批图片统一选择 PNG、JPEG 或 WebP。" },
      { en: "Convert and download the results together as a ZIP.", zh: "开始转换，并以 ZIP 一次下载所有结果。" },
    ],
    useCases: [
      { en: "Prepare lighter WebP images for a website", zh: "为网站准备更轻的 WebP 图片" },
      { en: "Turn transparent PNG assets into JPEG photos", zh: "将透明 PNG 素材转为 JPEG 照片" },
      { en: "Standardize a mixed image set before sharing", zh: "分享前统一一组混合格式图片" },
    ],
    faqs: [
      {
        question: { en: "Does conversion change image dimensions?", zh: "转换会改变图片尺寸吗？" },
        answer: { en: "Not by default. Original dimensions are preserved unless you choose a resize option.", zh: "默认不会。除非选择缩放选项，否则会保留原始尺寸。" },
      },
      {
        question: { en: "Can different images use different output formats?", zh: "不同图片可以选择不同输出格式吗？" },
        answer: { en: "Yes. Set a batch format first, then override any individual row before conversion.", zh: "可以。先设置整批格式，再在转换前覆盖任意单个文件。" },
      },
      {
        question: { en: "Why might HEIC fail?", zh: "为什么 HEIC 可能无法处理？" },
        answer: { en: "HEIC decoding depends on the browser and operating system. PNG, JPEG, and WebP have broader support.", zh: "HEIC 解码取决于浏览器和操作系统；PNG、JPEG 和 WebP 的支持更广。" },
      },
    ],
    options: { quality: "balanced", resize: "original", customWidth: 1920, cornerRadius: 0 },
    format: "webp",
  },
  {
    slug: "compress-image",
    path: "/tools/compress-image",
    icon: "compress",
    title: { en: "Make images lighter, not worse", zh: "缩小体积，保留质感" },
    shortTitle: { en: "Compress images", zh: "图片压缩" },
    description: {
      en: "Reduce image size locally with a sensible quality preset. Compare the result before you keep it.",
      zh: "使用合适的质量预设在本机压缩图片，并清楚查看压缩前后的体积。",
    },
    dropHint: { en: "Drop images to compress them locally", zh: "拖入图片，在本机完成压缩" },
    seoTitle: "Free Image Compressor — Compress Images Privately | Wemute",
    seoDescription: "Compress multiple PNG, JPG, and WebP images locally in your browser. Compare practical quality presets, reduce file size, and download without uploading.",
    answer: {
      en: "Wemute reduces image file size locally using practical quality presets. It shows the combined before-and-after size and downloads every result together.",
      zh: "Wemute 使用实用的质量预设在本地减小图片体积，并显示整批处理前后的大小，最后统一下载。",
    },
    steps: [
      { en: "Drop one image or a complete batch.", zh: "拖入一张图片或整批图片。" },
      { en: "Keep the Small File preset or choose another quality level.", zh: "保留“小文件”预设，或选择其他质量档位。" },
      { en: "Compress, compare the total size, and download.", zh: "压缩后比较总体积，然后下载。" },
    ],
    useCases: [
      { en: "Reduce page weight before publishing images online", zh: "发布到网页前降低图片体积" },
      { en: "Make a batch easier to email or message", zh: "让整批图片更适合邮件或消息发送" },
      { en: "Create smaller copies while keeping originals", zh: "保留原图的同时生成较小副本" },
    ],
    faqs: [
      {
        question: { en: "Will compression make images blurry?", zh: "压缩会让图片变糊吗？" },
        answer: { en: "Compression trades some encoded detail for a smaller file. The Balanced preset is designed as a sensible starting point.", zh: "压缩会用部分编码细节换取更小体积；“均衡”预设适合作为起点。" },
      },
      {
        question: { en: "Which output is usually smallest?", zh: "哪种输出通常最小？" },
        answer: { en: "WebP is often smaller than JPEG or PNG for photographic images, though the result depends on the source.", zh: "对于照片，WebP 通常比 JPEG 或 PNG 更小，但结果仍取决于原图。" },
      },
      {
        question: { en: "Are original files overwritten?", zh: "原文件会被覆盖吗？" },
        answer: { en: "No. Wemute creates new downloads and never modifies the source files on your device.", zh: "不会。Wemute 只生成新的下载文件，不会修改设备上的原文件。" },
      },
    ],
    options: { quality: "small", resize: "original", customWidth: 1920, cornerRadius: 0 },
    format: "webp",
  },
  {
    slug: "resize-image",
    path: "/tools/resize-image",
    icon: "resize",
    title: { en: "Resize a whole set at once", zh: "一次调整整组图片尺寸" },
    shortTitle: { en: "Resize images", zh: "调整尺寸" },
    description: {
      en: "Scale images by half, fit a long edge, or use a precise custom width while keeping proportions intact.",
      zh: "按比例缩小、限制最长边或输入精确宽度，同时保持图片比例不变。",
    },
    dropHint: { en: "Drop images to resize them together", zh: "拖入图片，统一调整尺寸" },
    seoTitle: "Free Batch Image Resizer — Resize Without Upload | Wemute",
    seoDescription: "Resize several images by percentage, longest edge, or custom width while preserving aspect ratio. Free and browser-local.",
    answer: {
      en: "Wemute resizes multiple images with one shared rule while preserving aspect ratio. Use 50%, a 1920 px longest edge, or a custom width.",
      zh: "Wemute 用一条统一规则调整多张图片，并保持宽高比。可选择 50%、最长边 1920 像素或自定义宽度。",
    },
    steps: [
      { en: "Add every image that needs the same size rule.", zh: "加入所有需要相同尺寸规则的图片。" },
      { en: "Choose 50%, longest edge 1920 px, or a custom width.", zh: "选择 50%、最长边 1920 像素或自定义宽度。" },
      { en: "Resize and download the new copies together.", zh: "完成缩放并一次下载所有新副本。" },
    ],
    useCases: [
      { en: "Prepare consistent product images", zh: "准备尺寸一致的商品图片" },
      { en: "Downsize camera photos for the web", zh: "将相机照片缩小后用于网页" },
      { en: "Create a smaller review or sharing set", zh: "生成较小的预览或分享版本" },
    ],
    faqs: [
      {
        question: { en: "Does Wemute preserve aspect ratio?", zh: "Wemute 会保持宽高比吗？" },
        answer: { en: "Yes. Height is calculated from each image's original proportions.", zh: "会。高度会根据每张图片的原始比例计算。" },
      },
      {
        question: { en: "Will the 1920 px preset enlarge small images?", zh: "1920 像素预设会放大小图吗？" },
        answer: { en: "No. The longest-edge preset only reduces images that exceed the limit.", zh: "不会。最长边预设只会缩小超过限制的图片。" },
      },
      {
        question: { en: "Can I enter an exact height?", zh: "可以输入精确高度吗？" },
        answer: { en: "The current web tool accepts an exact width and calculates height automatically to avoid distortion.", zh: "当前网页工具接受精确宽度，并自动计算高度以避免变形。" },
      },
    ],
    options: { quality: "balanced", resize: "half", customWidth: 1920, cornerRadius: 0 },
    format: "webp",
  },
  {
    slug: "round-corners",
    path: "/tools/round-corners",
    icon: "corners",
    title: { en: "Give images genuinely clean corners", zh: "给图片加上真正干净的圆角" },
    shortTitle: { en: "Round corners", zh: "图片圆角" },
    description: {
      en: "Create transparent rounded corners in one batch, with no editor and no upload step.",
      zh: "无需打开编辑器，也无需上传，一次为整批图片生成透明圆角。",
    },
    dropHint: { en: "Drop images to add transparent corners", zh: "拖入图片，添加透明圆角" },
    seoTitle: "Free Image Corner Rounder — Transparent PNG Corners | Wemute",
    seoDescription: "Round image corners in one browser-local batch. Choose an adjustable radius, create transparent PNG results, and download without uploading your files.",
    answer: {
      en: "Wemute adds transparent rounded corners to multiple images at once. Adjust the radius, keep original dimensions, and download PNG results.",
      zh: "Wemute 可以一次为多张图片添加透明圆角。调整圆角半径、保留原始尺寸，并下载 PNG 结果。",
    },
    steps: [
      { en: "Add the images that need rounded corners.", zh: "加入需要圆角的图片。" },
      { en: "Open Options and choose a corner radius.", zh: "打开“选项”并选择圆角半径。" },
      { en: "Create and download transparent PNG files.", zh: "生成并下载透明 PNG 文件。" },
    ],
    useCases: [
      { en: "Create polished profile and product cards", zh: "制作精致的头像和商品卡片" },
      { en: "Prepare transparent assets for presentations", zh: "为演示文稿准备透明素材" },
      { en: "Apply one visual treatment to a full set", zh: "为整组图片应用统一视觉效果" },
    ],
    faqs: [
      {
        question: { en: "Why are rounded results saved as PNG?", zh: "为什么圆角结果保存为 PNG？" },
        answer: { en: "PNG preserves the transparent pixels outside each rounded corner. JPEG cannot store transparency.", zh: "PNG 能保留圆角外的透明像素，而 JPEG 无法保存透明度。" },
      },
      {
        question: { en: "Does rounding crop the image?", zh: "添加圆角会裁剪图片吗？" },
        answer: { en: "No. The canvas keeps the original dimensions; only corner pixels become transparent.", zh: "不会。画布保留原始尺寸，只会让角落像素变为透明。" },
      },
      {
        question: { en: "Can every image use the same radius?", zh: "每张图片可以使用相同半径吗？" },
        answer: { en: "Yes. One radius applies to the full batch, which is the fastest way to keep a set consistent.", zh: "可以。一套半径应用到整批图片，是保持视觉一致最快的方式。" },
      },
    ],
    options: { quality: "balanced", resize: "original", customWidth: 1920, cornerRadius: 32 },
    format: "png",
  },
];

export const LEGAL_CONTENT = [
  {
    slug: "privacy",
    path: "/privacy",
    seoTitle: "Wemute Privacy Policy — Local Image Processing",
    seoDescription: "Learn how Wemute Web keeps supported image processing on your device, handles optional analytics and advertising, and stores only necessary browser preferences.",
    title: { en: "Privacy, in plain language", zh: "用简单的话说明隐私" },
    updated: "August 21, 2026",
    intro: {
      en: "Wemute is designed so the image work happens on your device. This policy separates that core processing from the limited website data needed to operate and fund the service.",
      zh: "Wemute 的设计原则是让图片处理发生在你的设备上。本政策会明确区分核心图片处理与运营、支持免费服务所需的少量网站数据。",
    },
    sections: [
      {
        heading: { en: "Your image files", zh: "你的图片文件" },
        body: { en: "Supported images are decoded, transformed, and packaged inside your browser. Wemute does not upload image contents or filenames to its servers. Closing the tab clears the active queue.", zh: "支持的图片会在浏览器内解码、转换和打包。Wemute 不会把图片内容或文件名上传到服务器；关闭标签页会清除当前队列。" },
      },
      {
        heading: { en: "Basic service data", zh: "基础服务数据" },
        body: { en: "The hosting provider may receive standard request data such as IP address, browser type, requested page, and time in order to deliver and secure the site. Wemute does not create user accounts.", zh: "为了交付并保护网站，托管服务商可能收到 IP 地址、浏览器类型、请求页面和时间等标准请求数据。Wemute 不创建用户账号。" },
      },
      {
        heading: { en: "Analytics and advertising", zh: "分析与广告" },
        body: { en: "Analytics and advertising are disabled unless the production site is configured with approved providers. If enabled, those providers may process device, browser, page, consent, and ad-interaction data under their own policies. Wemute analytics events never include filenames or image contents.", zh: "除非正式网站配置了获批准的服务商，否则分析和广告默认关闭。启用后，服务商可能依据其政策处理设备、浏览器、页面、同意状态和广告互动数据。Wemute 的分析事件绝不包含文件名或图片内容。" },
      },
      {
        heading: { en: "Choices and contact", zh: "你的选择与联系方式" },
        body: { en: "Where analytics consent is requested, you can decline it and continue using every tool. For privacy questions, contact the maker through the AllenSong profile linked on the About page.", zh: "在需要分析同意时，你可以拒绝，并继续使用所有工具。如有隐私问题，可通过“关于”页面中的 AllenSong 主页联系制作者。" },
      },
    ],
  },
  {
    slug: "terms",
    path: "/terms",
    seoTitle: "Wemute Terms of Use — Free Browser Image Tools",
    seoDescription: "Read the straightforward terms for using Wemute's free browser-local image tools, including acceptable use, file responsibility, availability, and service limits.",
    title: { en: "Simple terms for a simple tool", zh: "简单工具，简单条款" },
    updated: "August 21, 2026",
    intro: {
      en: "You may use Wemute's public web tools for lawful image processing without an account or fee.",
      zh: "你可以免费、无需账号地使用 Wemute 公共网页工具进行合法的图片处理。",
    },
    sections: [
      {
        heading: { en: "Your responsibility", zh: "你的责任" },
        body: { en: "Only process files you are allowed to use. You are responsible for reviewing downloaded results before publishing, deleting, or relying on them.", zh: "请只处理你有权使用的文件。在发布、删除或依赖处理结果之前，你有责任检查下载内容。" },
      },
      {
        heading: { en: "Service availability", zh: "服务可用性" },
        body: { en: "Wemute is provided as-is and may change, pause, or remove formats as browser capabilities evolve. Important source files should always be backed up.", zh: "Wemute 按现状提供，并可能随着浏览器能力变化而调整、暂停或移除某些格式。重要原文件应始终保留备份。" },
      },
      {
        heading: { en: "No warranty", zh: "不作保证" },
        body: { en: "To the extent permitted by law, Wemute makes no warranty that every file will convert successfully or that an output is suitable for a particular purpose.", zh: "在法律允许的范围内，Wemute 不保证每个文件都能成功转换，也不保证输出适合特定用途。" },
      },
      {
        heading: { en: "Fair use of the site", zh: "合理使用网站" },
        body: { en: "Do not attempt to disrupt the site, bypass security, misrepresent ads as Wemute controls, or use automated traffic to create invalid advertising activity.", zh: "请勿干扰网站、绕过安全措施、将广告冒充为 Wemute 控件，或使用自动流量制造无效广告活动。" },
      },
    ],
  },
  {
    slug: "about",
    path: "/about",
    seoTitle: "About Wemute | Private, Browser-Local Image Tools",
    seoDescription: "Learn why Wemute makes common image work simple, batch-first, free to use, and local to your browser, without accounts or unnecessary uploads.",
    title: { en: "A quieter way to work with images", zh: "一种更安静的图片处理方式" },
    updated: "August 21, 2026",
    intro: {
      en: "Wemute is an independent utility built around one idea: add a batch, choose the result, and get on with your work.",
      zh: "Wemute 是一款独立工具，只围绕一个想法构建：加入一批文件，选择结果，然后继续你的工作。",
    },
    sections: [
      {
        heading: { en: "Useful before impressive", zh: "先好用，再炫技" },
        body: { en: "The public web app focuses on a small set of dependable image jobs instead of presenting a wall of unrelated utilities.", zh: "公共网页应用专注于少量可靠的图片任务，而不是展示一整墙互不相关的工具。" },
      },
      {
        heading: { en: "Local by design", zh: "从设计上坚持本地处理" },
        body: { en: "Browser-local processing removes the upload wait and keeps source images away from an application server. It is a product decision, not just a slogan.", zh: "浏览器本地处理省去上传等待，也让原图远离应用服务器。这是一项产品决策，不只是一句口号。" },
      },
      {
        heading: { en: "Free, with separated advertising", zh: "免费使用，广告明确分离" },
        body: { en: "Wemute plans to fund the public tools with clearly labeled ads placed after useful content, never beside upload, conversion, or download controls.", zh: "Wemute 计划通过清晰标注的广告支持公共工具；广告只会出现在有用内容之后，绝不会紧贴上传、转换或下载控件。" },
      },
    ],
  },
];

export const INDEXABLE_PATHS = [
  SITE_CONTENT.home.path,
  ...TOOL_CONTENT.map((tool) => tool.path),
  ...LEGAL_CONTENT.map((page) => page.path),
];

export function contentForPath(pathname) {
  const normalized = pathname === "/" ? "/" : pathname.replace(/\/$/, "");
  if (normalized === "/") return { kind: "home", ...SITE_CONTENT.home };
  const tool = TOOL_CONTENT.find((item) => item.path === normalized);
  if (tool) return { kind: "tool", ...tool };
  const legal = LEGAL_CONTENT.find((item) => item.path === normalized);
  if (legal) return { kind: "legal", ...legal };
  return undefined;
}

export function metadataForPath(pathname) {
  const content = contentForPath(pathname) ?? contentForPath("/");
  return {
    title: content.seoTitle,
    description: content.seoDescription,
    path: content.path,
  };
}

export function structuredDataForPath(pathname, origin) {
  const content = contentForPath(pathname) ?? contentForPath("/");
  const siteUrl = new URL("/", origin).toString();
  const pageUrl = new URL(content.path, origin).toString();
  const graph = [];

  if (content.kind === "home") {
    graph.push({
      "@type": "WebSite",
      "@id": `${siteUrl}#website`,
      name: SITE_CONTENT.name,
      url: siteUrl,
      description: content.seoDescription,
      inLanguage: ["en", "zh-CN"],
    });
  }

  if (content.kind === "home" || content.kind === "tool") {
    graph.push({
      "@type": "WebApplication",
      "@id": `${pageUrl}#application`,
      name: content.kind === "home" ? SITE_CONTENT.name : `${SITE_CONTENT.name} ${content.shortTitle.en}`,
      url: pageUrl,
      description: content.seoDescription,
      applicationCategory: "UtilitiesApplication",
      operatingSystem: "Any operating system with a modern web browser",
      browserRequirements: "Requires JavaScript and Canvas support",
      isAccessibleForFree: true,
      offers: {
        "@type": "Offer",
        price: "0",
        priceCurrency: "USD",
      },
      featureList: content.kind === "tool"
        ? content.useCases.map((item) => item.en)
        : TOOL_CONTENT.map((tool) => tool.shortTitle.en),
    });
  }

  if (content.kind === "tool") {
    graph.push({
      "@type": "BreadcrumbList",
      "@id": `${pageUrl}#breadcrumb`,
      itemListElement: [
        { "@type": "ListItem", position: 1, name: "Image tools", item: siteUrl },
        { "@type": "ListItem", position: 2, name: content.shortTitle.en, item: pageUrl },
      ],
    });

    graph.push({
      "@type": "HowTo",
      "@id": `${pageUrl}#howto`,
      name: `How to ${content.shortTitle.en.toLowerCase()} with Wemute`,
      description: content.answer.en,
      totalTime: "PT2M",
      step: content.steps.map((step, index) => ({
        "@type": "HowToStep",
        position: index + 1,
        name: `Step ${index + 1}`,
        text: step.en,
        url: `${pageUrl}#tool-answer-heading`,
      })),
    });
  }

  if ((content.kind === "home" || content.kind === "tool") && content.faqs?.length) {
    graph.push({
      "@type": "FAQPage",
      "@id": `${pageUrl}#faq`,
      mainEntity: content.faqs.map((faq) => ({
        "@type": "Question",
        name: faq.question.en,
        acceptedAnswer: { "@type": "Answer", text: faq.answer.en },
      })),
    });
  }

  if (content.kind === "legal") {
    graph.push({
      "@type": content.slug === "about" ? "AboutPage" : "WebPage",
      "@id": `${pageUrl}#webpage`,
      name: content.title.en,
      url: pageUrl,
      description: content.seoDescription,
      dateModified: "2026-08-21",
      inLanguage: ["en", "zh-CN"],
    });
  }

  return { "@context": "https://schema.org", "@graph": graph };
}
