import { text, type Locale, type Text } from "./locale";

export type Category = "image" | "video" | "audio";
export type ImageOutput = "jpeg" | "png" | "webp" | "auto" | "keep";
export type MediaOutput = "mp3" | "wav" | "m4a" | "mp4" | "gif";
export type Output = ImageOutput | MediaOutput;

export type ToolMode =
  | "image-convert"
  | "image-compress"
  | "image-target-size"
  | "image-resize"
  | "image-corners"
  | "media-convert"
  | "video-gif"
  | "video-compress";

export interface Faq {
  q: Text;
  a: Text;
}

export interface ImagePreset {
  quality?: "small" | "balanced" | "high";
  resize?: "original" | "half" | "long-1920" | "long-1080" | "custom";
  cornerRadius?: number;
  targetKB?: number;
}

export interface Tool {
  slug: string;
  category: Category;
  mode: ToolMode;
  /** Formats named in the title, e.g. ["heic"] → used for the comparison table. */
  from: string[];
  to?: string;
  /** File picker filter. */
  accept: string;
  output: Output;
  /** Alternatives offered in the output selector. */
  outputs: Output[];
  preset?: ImagePreset;
  related: string[];
  name: Text;
  h1: Text;
  metaTitle: Text;
  metaDescription: Text;
  answer: Text;
  steps: Text[];
  useCases: Text[];
  faqs: Faq[];
}

const IMAGE_ACCEPT = "image/*,.heic,.heif,.avif";
const VIDEO_ACCEPT = "video/*,.mov,.mkv,.webm,.m4v,.avi";
const AUDIO_ACCEPT = "audio/*,.m4a,.flac,.wav,.aiff,.aif,.ogg,.opus";

const PRIVACY_FAQ: Faq = {
  q: text("Are my files uploaded?", "文件会被上传吗？"),
  a: text(
    "No. Wemute converts files inside your browser tab with your device's own processor. The file contents and names never reach our servers, and nothing is kept after you close the page.",
    "不会。Wemute 在浏览器标签页内用你自己设备的处理器完成转换。文件内容和文件名不会发送到我们的服务器，关闭页面后也不会留下任何副本。",
  ),
};

const IMAGE_BATCH_FAQ: Faq = {
  q: text("Can I convert many images at once?", "可以一次处理很多张图片吗？"),
  a: text(
    "Yes. Drop a whole folder's worth of images, set one output for the whole batch, and convert them in one go. Several results download together as a single ZIP.",
    "可以。一次拖入整批图片，统一设置输出，一次转换完成。多个结果会打包成一个 ZIP 一起下载。",
  ),
};

const MEDIA_LIMIT_FAQ: Faq = {
  q: text("Is there a file size limit?", "有文件大小限制吗？"),
  a: text(
    "There is no upload limit because nothing is uploaded, but your browser's memory sets a practical ceiling: files up to about 2 GB work on most computers. The first conversion downloads the converter engine (about 10 MB) once; after that it is cached.",
    "因为不需要上传，所以没有上传限制，但浏览器内存决定了实际上限：大多数电脑可以处理约 2 GB 以内的文件。第一次转换会下载一次约 10 MB 的转换引擎，之后会被缓存。",
  ),
};

const MEDIA_SPEED_FAQ: Faq = {
  q: text("Why is video slower than a desktop app?", "为什么视频转换比桌面软件慢？"),
  a: text(
    "Browser video encoding runs on the CPU without hardware acceleration. Wemute avoids re-encoding whenever the video stream can simply be moved into the new container, which makes most MOV and MKV to MP4 jobs finish in seconds.",
    "浏览器里的视频编码只能用 CPU，没有硬件加速。只要视频流可以直接装进新格式，Wemute 就会跳过重新编码，因此大多数 MOV、MKV 转 MP4 只需几秒。",
  ),
};

function imageConvert(
  slug: string,
  from: string,
  to: "jpg" | "png" | "webp",
  copy: Pick<Tool, "name" | "h1" | "metaTitle" | "metaDescription" | "answer" | "useCases" | "related"> & {
    specific: Faq[];
  },
): Tool {
  const output = to === "jpg" ? "jpeg" : to;
  const FROM = from.toUpperCase();
  const TO = to === "jpg" ? "JPG" : to === "webp" ? "WebP" : "PNG";
  return {
    slug,
    category: "image",
    mode: "image-convert",
    from: [from],
    to,
    accept: from === "heic" ? ".heic,.heif,image/heic,image/heif" : IMAGE_ACCEPT,
    output,
    outputs: ["jpeg", "png", "webp"],
    preset: { quality: "high" },
    related: copy.related,
    name: copy.name,
    h1: copy.h1,
    metaTitle: copy.metaTitle,
    metaDescription: copy.metaDescription,
    answer: copy.answer,
    steps: [
      text(`Drop your ${FROM} files, or click to choose them.`, `拖入 ${FROM} 文件，或点击选择。`),
      text(`${TO} is already selected — adjust quality or size only if you want to.`, `已默认选择 ${TO}，如有需要再调整质量或尺寸。`),
      text("Convert, then download each file or everything as a ZIP.", "开始转换，然后逐个下载或打包为 ZIP 下载。"),
    ],
    useCases: copy.useCases,
    faqs: [...copy.specific, IMAGE_BATCH_FAQ, PRIVACY_FAQ],
  };
}

function audioConvert(
  slug: string,
  from: string,
  output: "mp3" | "wav",
  copy: Pick<Tool, "name" | "h1" | "metaTitle" | "metaDescription" | "answer" | "useCases" | "related"> & {
    specific: Faq[];
  },
): Tool {
  const FROM = from.toUpperCase();
  const TO = output.toUpperCase();
  return {
    slug,
    category: "audio",
    mode: "media-convert",
    from: [from],
    to: output,
    accept: AUDIO_ACCEPT,
    output,
    outputs: ["mp3", "wav", "m4a"],
    related: copy.related,
    name: copy.name,
    h1: copy.h1,
    metaTitle: copy.metaTitle,
    metaDescription: copy.metaDescription,
    answer: copy.answer,
    steps: [
      text(`Drop one or more ${FROM} files.`, `拖入一个或多个 ${FROM} 文件。`),
      text(`Keep ${TO} selected and convert.`, `保持选择 ${TO}，开始转换。`),
      text("Download the results individually or as a ZIP.", "逐个下载结果，或打包为 ZIP 下载。"),
    ],
    useCases: copy.useCases,
    faqs: [...copy.specific, PRIVACY_FAQ, MEDIA_LIMIT_FAQ],
  };
}

export const TOOLS: Tool[] = [
  // ── Image conversion ─────────────────────────────────────────────────
  imageConvert("heic-to-jpg", "heic", "jpg", {
    name: text("HEIC to JPG", "HEIC 转 JPG"),
    h1: text("Convert HEIC to JPG", "HEIC 转 JPG"),
    metaTitle: text("HEIC to JPG Converter — Free, Private, No Upload | Wemute", "HEIC 转 JPG 在线转换 — 免费、无需上传 | Wemute"),
    metaDescription: text(
      "Convert iPhone HEIC photos to JPG in your browser. Batch convert, keep full resolution, and download instantly — files never leave your device.",
      "在浏览器中把 iPhone 的 HEIC 照片转换为 JPG。支持批量、保留原始分辨率、即时下载，文件不会离开你的设备。",
    ),
    answer: text(
      "To convert HEIC to JPG, drop your iPhone photos below. Wemute decodes each HEIC image in your browser and saves it as a high-quality JPG at the original resolution, so it opens on Windows, Android and any website — without uploading your photos.",
      "要把 HEIC 转成 JPG，只需把 iPhone 照片拖到下方即可。Wemute 在浏览器中解码每张 HEIC 照片，并以原始分辨率保存为高质量 JPG，可在 Windows、安卓和任何网站上打开，全程无需上传照片。",
    ),
    useCases: [
      text("Open iPhone photos on a Windows PC", "在 Windows 电脑上打开 iPhone 照片"),
      text("Upload photos to forms that reject HEIC", "上传到不接受 HEIC 的网页表单"),
      text("Send pictures to friends on Android", "把照片发给使用安卓手机的朋友"),
    ],
    related: ["heic-to-png", "compress-image", "jpg-to-webp"],
    specific: [
      {
        q: text("Why are my iPhone photos HEIC?", "为什么 iPhone 照片是 HEIC 格式？"),
        a: text(
          "Since iOS 11, the iPhone camera saves photos as HEIC ('High Efficiency') to use about half the storage of JPG. You can switch the camera to 'Most Compatible' in Settings → Camera → Formats, but converting existing photos is quicker.",
          "从 iOS 11 开始，iPhone 相机默认以 HEIC（“高效”）格式保存照片，占用空间约为 JPG 的一半。可以在“设置 → 相机 → 格式”中改为“兼容性最佳”，但对已有照片直接转换更快。",
        ),
      },
      {
        q: text("Will the JPG lose quality?", "转成 JPG 会损失画质吗？"),
        a: text(
          "JPG is also a lossy format, but Wemute uses a high quality setting by default, so the difference is not visible in normal viewing. The JPG will usually be larger than the HEIC file.",
          "JPG 同样是有损格式，但 Wemute 默认使用高质量设置，正常查看时看不出差别。生成的 JPG 通常会比原 HEIC 文件更大。",
        ),
      },
    ],
  }),
  imageConvert("heic-to-png", "heic", "png", {
    name: text("HEIC to PNG", "HEIC 转 PNG"),
    h1: text("Convert HEIC to PNG", "HEIC 转 PNG"),
    metaTitle: text("HEIC to PNG Converter — Lossless & Private | Wemute", "HEIC 转 PNG 在线转换 — 无损、无需上传 | Wemute"),
    metaDescription: text(
      "Turn HEIC images into lossless PNG files directly in your browser. Batch conversion, transparency preserved, no upload or sign-up.",
      "直接在浏览器中把 HEIC 图片转换为无损 PNG。支持批量转换、保留透明度，无需上传或注册。",
    ),
    answer: text(
      "Drop HEIC files below and Wemute converts them to PNG in your browser. PNG is lossless, so every pixel from the decoded HEIC is kept, along with any transparency — ideal when you will edit the image further.",
      "把 HEIC 文件拖到下方，Wemute 会在浏览器中将其转换为 PNG。PNG 是无损格式，会保留解码后 HEIC 的每一个像素以及透明区域，适合后续继续编辑。",
    ),
    useCases: [
      text("Edit iPhone photos in software without HEIC support", "在不支持 HEIC 的软件中编辑 iPhone 照片"),
      text("Keep cut-out subjects with transparent backgrounds", "保留抠图主体的透明背景"),
      text("Prepare images for design tools and slides", "为设计工具和幻灯片准备图片"),
    ],
    related: ["heic-to-jpg", "png-to-jpg", "round-corners"],
    specific: [
      {
        q: text("Should I choose PNG or JPG for HEIC photos?", "HEIC 照片该转 PNG 还是 JPG？"),
        a: text(
          "Choose JPG for sharing photos — the files are far smaller. Choose PNG when you will keep editing the image or need transparency, and file size matters less.",
          "用于分享照片时选 JPG，体积小得多；需要继续编辑或保留透明度、并且不太在意文件大小时选 PNG。",
        ),
      },
      {
        q: text("Why is the PNG so large?", "为什么 PNG 文件这么大？"),
        a: text(
          "HEIC compresses photos very efficiently, while PNG stores every pixel without loss. A 2 MB iPhone photo can become a 10–20 MB PNG. Use HEIC to JPG if size matters.",
          "HEIC 对照片压缩率很高，而 PNG 以无损方式保存每个像素。一张 2 MB 的 iPhone 照片可能变成 10–20 MB 的 PNG。如果在意体积，请使用 HEIC 转 JPG。",
        ),
      },
    ],
  }),
  imageConvert("png-to-jpg", "png", "jpg", {
    name: text("PNG to JPG", "PNG 转 JPG"),
    h1: text("Convert PNG to JPG", "PNG 转 JPG"),
    metaTitle: text("PNG to JPG Converter — Batch & Free, No Upload | Wemute", "PNG 转 JPG 在线转换 — 批量、免费、无需上传 | Wemute"),
    metaDescription: text(
      "Convert PNG to JPG online in seconds. Shrink large PNG photos and screenshots, pick quality, batch convert — all inside your browser.",
      "几秒内在线把 PNG 转成 JPG。缩小大体积 PNG 照片和截图，可选质量，支持批量，全部在浏览器内完成。",
    ),
    answer: text(
      "To convert PNG to JPG, drop the PNG files below. Wemute re-encodes them as JPG in your browser, which typically makes photos 70–90% smaller. Transparent areas are filled with white because JPG has no transparency.",
      "要把 PNG 转成 JPG，把 PNG 文件拖到下方即可。Wemute 在浏览器中重新编码为 JPG，照片通常会缩小 70–90%。由于 JPG 不支持透明，透明区域会被填充为白色。",
    ),
    useCases: [
      text("Make large PNG photos small enough to email", "把大体积 PNG 照片缩小到可以邮件发送"),
      text("Meet upload rules that only accept JPG", "满足只接受 JPG 的上传要求"),
      text("Reduce the size of screenshots of photos", "减小照片类截图的体积"),
    ],
    related: ["jpg-to-png", "png-to-webp", "compress-image"],
    specific: [
      {
        q: text("What happens to transparent backgrounds?", "透明背景会怎样？"),
        a: text(
          "JPG cannot store transparency, so transparent pixels become white. If you need to keep transparency, convert to WebP instead — it is also small and supports alpha.",
          "JPG 无法保存透明度，透明像素会变成白色。如果需要保留透明，请改为转换成 WebP，它同样体积小并支持透明。",
        ),
      },
      {
        q: text("Is JPG always smaller than PNG?", "JPG 一定比 PNG 小吗？"),
        a: text(
          "For photos, almost always. For flat graphics, logos or text screenshots, PNG can be smaller and sharper — JPG may add blurry artifacts around edges.",
          "对于照片几乎总是如此。但对于纯色图形、Logo 或文字截图，PNG 可能更小、更清晰，而 JPG 可能在边缘产生模糊的压缩痕迹。",
        ),
      },
    ],
  }),
  imageConvert("jpg-to-png", "jpg", "png", {
    name: text("JPG to PNG", "JPG 转 PNG"),
    h1: text("Convert JPG to PNG", "JPG 转 PNG"),
    metaTitle: text("JPG to PNG Converter — Free & Lossless Output | Wemute", "JPG 转 PNG 在线转换 — 免费、无损输出 | Wemute"),
    metaDescription: text(
      "Convert JPG or JPEG images to PNG in your browser. Lossless output for editing, batch conversion, no upload and no watermark.",
      "在浏览器中把 JPG/JPEG 图片转换为 PNG。无损输出便于编辑，支持批量，无需上传，没有水印。",
    ),
    answer: text(
      "Drop JPG files below and Wemute saves each one as a PNG in your browser. The conversion itself adds no further loss, so the PNG is a pixel-exact copy of the JPG that you can edit and re-save without more degradation.",
      "把 JPG 文件拖到下方，Wemute 会在浏览器中把每个文件保存为 PNG。转换过程不会带来额外损失，PNG 是 JPG 的逐像素副本，之后反复编辑保存也不会继续降质。",
    ),
    useCases: [
      text("Edit an image repeatedly without adding JPG artifacts", "反复编辑图片而不累积 JPG 压缩痕迹"),
      text("Supply PNG files to apps that require them", "为要求 PNG 的软件提供文件"),
      text("Start a graphic you will later add transparency to", "准备之后要添加透明效果的图形"),
    ],
    related: ["png-to-jpg", "round-corners", "jpg-to-webp"],
    specific: [
      {
        q: text("Does converting JPG to PNG improve quality?", "JPG 转 PNG 能提高画质吗？"),
        a: text(
          "No. PNG preserves the image exactly as it is, but it cannot restore detail the JPG compression already removed. It prevents further loss when you keep editing.",
          "不能。PNG 会原样保留图像，但无法恢复 JPG 压缩时已经丢失的细节。它的作用是在后续编辑时避免继续损失。",
        ),
      },
      {
        q: text("Will the PNG have a transparent background?", "PNG 会有透明背景吗？"),
        a: text(
          "Not automatically — a JPG has no transparency to carry over. Use Round Corners to add transparent corners, or a background remover for cut-outs.",
          "不会自动变透明，因为 JPG 本身没有透明信息。可以用圆角工具添加透明圆角，或使用抠图工具去除背景。",
        ),
      },
    ],
  }),
  imageConvert("webp-to-jpg", "webp", "jpg", {
    name: text("WebP to JPG", "WebP 转 JPG"),
    h1: text("Convert WebP to JPG", "WebP 转 JPG"),
    metaTitle: text("WebP to JPG Converter — Open WebP Anywhere | Wemute", "WebP 转 JPG 在线转换 — 让 WebP 随处可用 | Wemute"),
    metaDescription: text(
      "Convert WebP images saved from websites into JPG. Free batch conversion in your browser, high quality, no upload.",
      "把从网页保存的 WebP 图片转换为 JPG。浏览器内免费批量转换，高画质，无需上传。",
    ),
    answer: text(
      "To turn WebP into JPG, drop the WebP images below. Wemute decodes them in your browser and saves high-quality JPGs that open in every photo viewer, editor and upload form.",
      "要把 WebP 转成 JPG，把 WebP 图片拖到下方即可。Wemute 在浏览器中解码并保存为高质量 JPG，可在所有看图软件、编辑器和上传表单中使用。",
    ),
    useCases: [
      text("Use images saved from websites in older apps", "在老版本软件中使用从网页保存的图片"),
      text("Print or attach images where WebP isn't accepted", "在不接受 WebP 的场合打印或作为附件"),
      text("Edit downloaded product photos", "编辑下载的商品图片"),
    ],
    related: ["webp-to-png", "jpg-to-webp", "compress-image"],
    specific: [
      {
        q: text("Why do websites give me WebP files?", "为什么网站下载的图片是 WebP？"),
        a: text(
          "Most large sites serve WebP because it loads faster than JPG at the same quality. When you right-click and save, you get that WebP file rather than the original.",
          "多数大型网站使用 WebP，因为同等画质下加载更快。右键另存时，你得到的就是这个 WebP 文件，而不是原图。",
        ),
      },
      {
        q: text("What if the WebP is animated?", "如果 WebP 是动图怎么办？"),
        a: text(
          "Wemute converts the first frame of an animated WebP to a still JPG. To keep the animation, you need a GIF or video output instead.",
          "Wemute 会把动态 WebP 的第一帧转换为静态 JPG。如需保留动画，需要转换为 GIF 或视频。",
        ),
      },
    ],
  }),
  imageConvert("webp-to-png", "webp", "png", {
    name: text("WebP to PNG", "WebP 转 PNG"),
    h1: text("Convert WebP to PNG", "WebP 转 PNG"),
    metaTitle: text("WebP to PNG Converter — Keep Transparency | Wemute", "WebP 转 PNG 在线转换 — 保留透明背景 | Wemute"),
    metaDescription: text(
      "Convert WebP to PNG and keep transparent backgrounds. Lossless output, batch conversion, processed privately in your browser.",
      "把 WebP 转换为 PNG 并保留透明背景。无损输出，支持批量，在浏览器中私密处理。",
    ),
    answer: text(
      "Drop WebP files below to convert them to PNG in your browser. Transparent areas stay transparent and the PNG keeps every decoded pixel, making it the best choice for logos, stickers and graphics.",
      "把 WebP 文件拖到下方，即可在浏览器中转换为 PNG。透明区域保持透明，PNG 会保留解码后的每个像素，最适合 Logo、贴纸和图形。",
    ),
    useCases: [
      text("Reuse transparent logos and icons from the web", "复用网页上的透明 Logo 和图标"),
      text("Import WebP stickers into design tools", "把 WebP 贴纸导入设计工具"),
      text("Edit graphics without adding compression", "编辑图形而不增加压缩"),
    ],
    related: ["webp-to-jpg", "png-to-webp", "round-corners"],
    specific: [
      {
        q: text("Is PNG or JPG better for WebP graphics?", "WebP 图形转 PNG 好还是 JPG 好？"),
        a: text(
          "PNG for logos, icons and anything with transparency or text; JPG for photographs where a smaller file matters more.",
          "Logo、图标以及带透明或文字的内容选 PNG；照片类且更在意体积时选 JPG。",
        ),
      },
      {
        q: text("Is transparency preserved?", "透明度会保留吗？"),
        a: text(
          "Yes. Both WebP and PNG support full alpha transparency, and Wemute keeps it pixel for pixel.",
          "会。WebP 和 PNG 都支持完整的透明通道，Wemute 会逐像素保留。",
        ),
      },
    ],
  }),
  imageConvert("jpg-to-webp", "jpg", "webp", {
    name: text("JPG to WebP", "JPG 转 WebP"),
    h1: text("Convert JPG to WebP", "JPG 转 WebP"),
    metaTitle: text("JPG to WebP Converter — Smaller Images for the Web | Wemute", "JPG 转 WebP 在线转换 — 让网页图片更小 | Wemute"),
    metaDescription: text(
      "Convert JPG to WebP for faster websites. Typically 25–35% smaller at similar quality. Batch convert locally in your browser.",
      "把 JPG 转成 WebP 让网站更快。同等画质下通常小 25–35%。在浏览器本地批量转换。",
    ),
    answer: text(
      "To convert JPG to WebP, drop your images below. WebP is usually 25–35% smaller than JPG at similar visual quality, which speeds up page loads and improves Core Web Vitals.",
      "要把 JPG 转成 WebP，把图片拖到下方即可。同等视觉质量下，WebP 通常比 JPG 小 25–35%，可以加快网页加载并改善 Core Web Vitals。",
    ),
    useCases: [
      text("Speed up blog and store pages", "加快博客和商店页面加载"),
      text("Improve Lighthouse and PageSpeed scores", "提升 Lighthouse 和 PageSpeed 得分"),
      text("Save storage on image-heavy sites", "为图片较多的网站节省存储"),
    ],
    related: ["png-to-webp", "compress-image", "resize-image"],
    specific: [
      {
        q: text("Do all browsers support WebP?", "所有浏览器都支持 WebP 吗？"),
        a: text(
          "Yes. Chrome, Edge, Firefox and Safari (since Safari 14 on macOS Big Sur and iOS 14) all display WebP.",
          "是的。Chrome、Edge、Firefox 和 Safari（macOS Big Sur 与 iOS 14 起的 Safari 14）都能显示 WebP。",
        ),
      },
      {
        q: text("Which quality setting should I use?", "应该选择哪个质量档位？"),
        a: text(
          "Balanced is a good default for websites. Choose High for hero images and photography portfolios, Small for thumbnails.",
          "网站一般选“均衡”即可；首屏大图和摄影作品选“高质量”；缩略图选“更小”。",
        ),
      },
    ],
  }),
  imageConvert("png-to-webp", "png", "webp", {
    name: text("PNG to WebP", "PNG 转 WebP"),
    h1: text("Convert PNG to WebP", "PNG 转 WebP"),
    metaTitle: text("PNG to WebP Converter — Smaller, Keeps Transparency | Wemute", "PNG 转 WebP 在线转换 — 更小且保留透明 | Wemute"),
    metaDescription: text(
      "Convert PNG to WebP to shrink files while keeping transparency. Free, private batch conversion in your browser.",
      "把 PNG 转成 WebP，在保留透明的同时大幅缩小体积。在浏览器中免费、私密地批量转换。",
    ),
    answer: text(
      "Drop PNG images below and Wemute converts them to WebP in your browser. WebP keeps transparency like PNG but is often several times smaller, especially for photos and detailed artwork.",
      "把 PNG 图片拖到下方，Wemute 会在浏览器中把它们转换为 WebP。WebP 和 PNG 一样支持透明，但体积往往小好几倍，尤其适合照片和细节丰富的插画。",
    ),
    useCases: [
      text("Shrink transparent product shots for online stores", "缩小网店的透明背景商品图"),
      text("Lighten UI screenshots in documentation", "减小文档中界面截图的体积"),
      text("Replace heavy PNGs on a website", "替换网站上的大体积 PNG"),
    ],
    related: ["jpg-to-webp", "webp-to-png", "compress-image"],
    specific: [
      {
        q: text("Will my transparent background survive?", "透明背景会保留吗？"),
        a: text(
          "Yes. WebP supports full alpha transparency, so cut-outs and logos keep their transparent areas.",
          "会。WebP 支持完整的透明通道，抠图和 Logo 的透明区域都会保留。",
        ),
      },
      {
        q: text("Is WebP lossless like PNG?", "WebP 像 PNG 一样无损吗？"),
        a: text(
          "WebP can be either. Wemute uses lossy WebP for the biggest savings; at the High setting the difference is very hard to see.",
          "WebP 可以有损也可以无损。Wemute 使用有损 WebP 以获得最大压缩；在“高质量”档位下几乎看不出差别。",
        ),
      },
    ],
  }),
  imageConvert("avif-to-jpg", "avif", "jpg", {
    name: text("AVIF to JPG", "AVIF 转 JPG"),
    h1: text("Convert AVIF to JPG", "AVIF 转 JPG"),
    metaTitle: text("AVIF to JPG Converter — Free & Private | Wemute", "AVIF 转 JPG 在线转换 — 免费、私密 | Wemute"),
    metaDescription: text(
      "Convert AVIF images to JPG so they open in any app. Batch conversion in your browser with no upload.",
      "把 AVIF 图片转换为 JPG，让它们能在任何软件中打开。在浏览器中批量转换，无需上传。",
    ),
    answer: text(
      "Drop AVIF files below — it converts to JPG straight away. Your browser decodes the AVIF and Wemute saves a high-quality JPG that works in every editor, viewer and upload form.",
      "把 AVIF 文件拖到下方即可直接得到 JPG。浏览器负责解码 AVIF，Wemute 保存为可在任何编辑器、看图软件和上传表单中使用的高质量 JPG。",
    ),
    useCases: [
      text("Open AVIF images saved from websites", "打开从网页保存的 AVIF 图片"),
      text("Edit AVIF pictures in older software", "在老版本软件中编辑 AVIF 图片"),
      text("Share images with people on older devices", "与使用旧设备的人分享图片"),
    ],
    related: ["webp-to-jpg", "heic-to-jpg", "compress-image"],
    specific: [
      {
        q: text("Why can't I open AVIF files?", "为什么打不开 AVIF 文件？"),
        a: text(
          "AVIF is a new format based on the AV1 video codec. Browsers display it, but many photo viewers, editors and upload forms don't yet support it.",
          "AVIF 是基于 AV1 视频编码的新格式。浏览器可以显示，但很多看图软件、编辑器和上传表单还不支持。",
        ),
      },
      {
        q: text("My browser says it can't read the file", "浏览器提示无法读取文件"),
        a: text(
          "AVIF decoding comes from your browser. Update to a recent Chrome, Edge, Firefox or Safari 16+ and try again.",
          "AVIF 解码由浏览器提供。请更新到较新的 Chrome、Edge、Firefox 或 Safari 16 以上版本后重试。",
        ),
      },
    ],
  }),
  {
    slug: "image-converter",
    category: "image",
    mode: "image-convert",
    from: [],
    accept: IMAGE_ACCEPT,
    output: "jpeg",
    outputs: ["jpeg", "png", "webp"],
    preset: { quality: "high" },
    related: ["heic-to-jpg", "png-to-jpg", "jpg-to-webp"],
    name: text("Image Converter", "图片格式转换"),
    h1: text("Image converter for any format", "图片格式转换器"),
    metaTitle: text("Free Image Converter — HEIC, PNG, JPG, WebP, AVIF | Wemute", "免费图片格式转换 — HEIC、PNG、JPG、WebP、AVIF | Wemute"),
    metaDescription: text(
      "Convert images between JPG, PNG and WebP — including HEIC and AVIF input — in one private browser batch. No upload, no account.",
      "在浏览器中批量把图片转换为 JPG、PNG 或 WebP，支持 HEIC 和 AVIF 输入。无需上传，无需账号。",
    ),
    answer: text(
      "Wemute converts images between JPG, PNG and WebP in your browser and reads HEIC and AVIF too. Drop a mixed batch, choose one output for all of them, and convert the whole set in one go.",
      "Wemute 可以在浏览器中把图片在 JPG、PNG、WebP 之间转换，也能读取 HEIC 和 AVIF。拖入混合格式的一批图片，统一选择输出格式，一次全部转换。",
    ),
    steps: [
      text("Drop images in any common format.", "拖入任意常见格式的图片。"),
      text("Choose JPG, PNG or WebP for the whole batch.", "为整批图片选择 JPG、PNG 或 WebP。"),
      text("Convert and download the results.", "转换并下载结果。"),
    ],
    useCases: [
      text("Standardise a mixed folder of images", "统一一个混合格式的图片文件夹"),
      text("Prepare assets for a website or app", "为网站或应用准备素材"),
      text("Convert screenshots and photos in one go", "一次性转换截图和照片"),
    ],
    faqs: [
      {
        q: text("Which formats can I convert from?", "支持哪些输入格式？"),
        a: text(
          "JPG, PNG, WebP, GIF (first frame), BMP, AVIF and HEIC. AVIF depends on your browser; HEIC is decoded by Wemute itself.",
          "JPG、PNG、WebP、GIF（第一帧）、BMP、AVIF 和 HEIC。AVIF 取决于浏览器支持；HEIC 由 Wemute 自行解码。",
        ),
      },
      IMAGE_BATCH_FAQ,
      PRIVACY_FAQ,
    ],
  },

  // ── Image compression and editing ────────────────────────────────────
  {
    slug: "compress-image",
    category: "image",
    mode: "image-compress",
    from: [],
    accept: IMAGE_ACCEPT,
    output: "auto",
    outputs: ["auto", "jpeg", "webp"],
    preset: { quality: "balanced" },
    related: ["compress-image-to-100kb", "resize-image", "jpg-to-webp"],
    name: text("Compress Image", "图片压缩"),
    h1: text("Compress images without visible quality loss", "压缩图片，画质肉眼无损"),
    metaTitle: text("Compress Images Online — JPG, PNG, WebP, HEIC | Wemute", "在线压缩图片 — 支持 JPG、PNG、WebP、HEIC | Wemute"),
    metaDescription: text(
      "Reduce image file size by up to 80% in your browser. Batch compress JPG, PNG, WebP and HEIC with practical quality presets — no upload.",
      "在浏览器中把图片体积减少多达 80%。用实用的质量预设批量压缩 JPG、PNG、WebP 和 HEIC，无需上传。",
    ),
    answer: text(
      "To compress an image, drop it below. Wemute re-encodes it with a balanced quality setting — usually 50–80% smaller with no difference you can see — and shows the exact size saved for every file.",
      "要压缩图片，把它拖到下方即可。Wemute 会用“均衡”质量重新编码，通常可缩小 50–80% 且肉眼看不出差别，并显示每个文件具体节省了多少。",
    ),
    steps: [
      text("Drop one image or a whole batch.", "拖入一张或一批图片。"),
      text("Keep Balanced, or choose Smaller or High quality.", "保持“均衡”，或选择“更小”“高质量”。"),
      text("Compress, compare the savings, and download.", "压缩后对比节省的体积，然后下载。"),
    ],
    useCases: [
      text("Fit photos under email attachment limits", "让照片符合邮件附件大小限制"),
      text("Speed up website pages", "加快网页加载速度"),
      text("Free up space before sharing an album", "分享相册前节省空间"),
    ],
    faqs: [
      {
        q: text("How does Wemute choose the output format?", "Wemute 如何选择输出格式？"),
        a: text(
          "With 'Keep type', JPG stays JPG and WebP stays WebP. PNG and HEIC photos become JPG, or WebP if they have transparency, because PNG cannot be compressed much without changing format.",
          "选择“保持类型”时，JPG 仍为 JPG，WebP 仍为 WebP。PNG 和 HEIC 照片会转为 JPG；若有透明区域则转为 WebP，因为 PNG 不换格式很难大幅压缩。",
        ),
      },
      {
        q: text("Can I compress to an exact size?", "可以压缩到指定大小吗？"),
        a: text(
          "Yes — use the target size option, or a ready-made tool such as Compress to 100 KB. Wemute searches for the highest quality that fits under your limit.",
          "可以。使用“目标大小”选项，或直接使用“压缩到 100KB”等工具。Wemute 会找出不超过限制的最高质量。",
        ),
      },
      IMAGE_BATCH_FAQ,
      PRIVACY_FAQ,
    ],
  },
  ...([50, 100, 200] as const).map<Tool>((kb) => ({
    slug: `compress-image-to-${kb}kb`,
    category: "image",
    mode: "image-target-size",
    from: [],
    accept: IMAGE_ACCEPT,
    output: "jpeg",
    outputs: ["jpeg", "webp"],
    preset: { targetKB: kb, quality: "high" },
    related: [
      kb === 50 ? "compress-image-to-100kb" : "compress-image-to-50kb",
      kb === 200 ? "compress-image-to-100kb" : "compress-image-to-200kb",
      "resize-image",
    ],
    name: text(`Compress to ${kb} KB`, `压缩到 ${kb}KB`),
    h1: text(`Compress an image to ${kb} KB`, `把图片压缩到 ${kb}KB 以内`),
    metaTitle: text(
      `Compress Image to ${kb}KB Online — Free, No Upload | Wemute`,
      `图片压缩到 ${kb}KB — 在线免费、无需上传 | Wemute`,
    ),
    metaDescription: text(
      `Reduce a photo to under ${kb} KB for forms and applications. Wemute finds the best quality that fits — privately, in your browser.`,
      `把照片压缩到 ${kb}KB 以内，用于各类表单和报名。Wemute 自动找到不超限的最佳画质，全程在浏览器中私密完成。`,
    ),
    answer: text(
      `Drop your image below and Wemute compresses it to ${kb} KB or less. It tries progressively lower quality and, only if needed, smaller dimensions, stopping at the best-looking version that fits under ${kb} KB.`,
      `把图片拖到下方，Wemute 会把它压缩到 ${kb}KB 以内。它会逐步降低质量，只有在必要时才缩小尺寸，并停在不超过 ${kb}KB 的最佳画质版本。`,
    ),
    steps: [
      text("Drop the photo or scan you need to submit.", "拖入需要提交的照片或扫描件。"),
      text(`The ${kb} KB target is already set.`, `已预设 ${kb}KB 目标大小。`),
      text("Convert and download a JPG that fits the limit.", "转换并下载符合限制的 JPG。"),
    ],
    useCases:
      kb === 50
        ? [
            text("Passport and ID photos for online applications", "网上报名、证件申请的证件照"),
            text("Signature scans for exam and job portals", "考试或招聘网站要求的签名扫描件"),
            text("Profile pictures with strict limits", "有严格大小限制的头像"),
          ]
        : kb === 100
          ? [
              text("Government and visa application uploads", "政务服务和签证申请上传"),
              text("Job portals and university forms", "招聘网站和高校报名表"),
              text("Photos for online marketplaces", "二手平台和网店的商品照片"),
            ]
          : [
              text("Document scans for online submissions", "网上提交的文件扫描件"),
              text("Clear product photos with size caps", "有大小上限的清晰商品图"),
              text("Images for newsletters and email", "用于邮件和电子报的图片"),
            ],
    faqs: [
      {
        q: text(`Will the image be exactly ${kb} KB?`, `压缩后会正好是 ${kb}KB 吗？`),
        a: text(
          `It will be at or below ${kb} KB, usually within a few kilobytes of the limit, because Wemute keeps the highest quality that still fits.`,
          `会等于或略低于 ${kb}KB，通常与上限只差几 KB，因为 Wemute 会保留仍能满足限制的最高画质。`,
        ),
      },
      {
        q: text("Will the dimensions change?", "图片尺寸会改变吗？"),
        a: text(
          "Only when quality alone can't get under the limit — for example a 12-megapixel photo to 50 KB. Then the image is scaled down step by step, keeping its aspect ratio.",
          "只有单靠降低质量无法达标时才会缩小尺寸，例如把 1200 万像素的照片压到 50KB。此时会按比例逐步缩小。",
        ),
      },
      PRIVACY_FAQ,
    ],
  })),
  {
    slug: "resize-image",
    category: "image",
    mode: "image-resize",
    from: [],
    accept: IMAGE_ACCEPT,
    output: "keep",
    outputs: ["keep", "jpeg", "png", "webp"],
    preset: { resize: "long-1920", quality: "high" },
    related: ["compress-image", "round-corners", "compress-image-to-200kb"],
    name: text("Resize Image", "调整图片尺寸"),
    h1: text("Resize images in one batch", "批量调整图片尺寸"),
    metaTitle: text("Resize Images Online — Batch, Keep Aspect Ratio | Wemute", "在线批量调整图片尺寸 — 保持比例 | Wemute"),
    metaDescription: text(
      "Resize many images at once by percentage, longest edge or exact width. Aspect ratio preserved. Free, private and in your browser.",
      "按百分比、最长边或指定宽度一次调整多张图片尺寸，保持原始比例。免费、私密，在浏览器中完成。",
    ),
    answer: text(
      "To resize images, drop them below, pick a size rule — 50%, longest edge 1920 px or 1080 px, or a custom width — in Options. Every image keeps its proportions, and nothing is ever enlarged beyond its original size.",
      "要调整图片尺寸，把图片拖到下方，选择尺寸规则（50%、最长边 1920 或 1080 像素，或自定义宽度）。每张图片都会保持原始比例，且不会被放大到超过原尺寸。",
    ),
    steps: [
      text("Drop the images you want to resize.", "拖入需要调整尺寸的图片。"),
      text("Choose a percentage, longest edge or custom width.", "选择百分比、最长边或自定义宽度。"),
      text("Resize and download — the format stays the same.", "调整并下载，格式保持不变。"),
    ],
    useCases: [
      text("Make camera photos web-friendly", "让相机照片适合网页使用"),
      text("Prepare a consistent set of product images", "制作尺寸一致的商品图"),
      text("Shrink images for slides and documents", "为幻灯片和文档缩小图片"),
    ],
    faqs: [
      {
        q: text("Will resizing stretch my images?", "调整尺寸会把图片拉伸变形吗？"),
        a: text(
          "No. Wemute always preserves the aspect ratio. A custom width sets the width and calculates the matching height.",
          "不会。Wemute 始终保持原始比例。自定义宽度时，会自动计算对应的高度。",
        ),
      },
      {
        q: text("Can it make small images bigger?", "能把小图放大吗？"),
        a: text(
          "Wemute never upscales: images already smaller than the chosen size are kept at their original dimensions, because enlarging only adds blur.",
          "Wemute 不会放大图片：已经小于目标尺寸的图片会保持原尺寸，因为放大只会让画面更模糊。",
        ),
      },
      IMAGE_BATCH_FAQ,
      PRIVACY_FAQ,
    ],
  },
  {
    slug: "round-corners",
    category: "image",
    mode: "image-corners",
    from: [],
    accept: IMAGE_ACCEPT,
    output: "png",
    outputs: ["png", "webp"],
    preset: { cornerRadius: 48, quality: "high" },
    related: ["resize-image", "png-to-webp", "jpg-to-png"],
    name: text("Round Corners", "图片圆角"),
    h1: text("Round image corners with a transparent background", "给图片加圆角，透明背景"),
    metaTitle: text("Round Image Corners Online — Transparent PNG | Wemute", "在线给图片加圆角 — 透明 PNG | Wemute"),
    metaDescription: text(
      "Add rounded corners to images in one batch. Adjustable radius, transparent PNG or WebP output, processed privately in your browser.",
      "批量给图片添加圆角。半径可调，输出透明 PNG 或 WebP，在浏览器中私密处理。",
    ),
    answer: text(
      "Drop images below and Wemute rounds their corners with the radius you choose, cutting the corners to true transparency. The result is a PNG (or WebP) that sits cleanly on any background.",
      "把图片拖到下方，Wemute 会按你选择的半径给图片加圆角，并把切掉的角变为真正的透明。结果是可以放在任何背景上的 PNG（或 WebP）。",
    ),
    steps: [
      text("Drop screenshots, photos or artwork.", "拖入截图、照片或作品。"),
      text("Choose a corner radius.", "选择圆角半径。"),
      text("Download transparent PNG results.", "下载透明 PNG 结果。"),
    ],
    useCases: [
      text("Polish app screenshots for marketing", "美化用于宣传的应用截图"),
      text("Create avatar-style images", "制作头像风格的图片"),
      text("Match the rounded look of slides and docs", "与幻灯片和文档的圆角风格保持一致"),
    ],
    faqs: [
      {
        q: text("Why is the output a PNG?", "为什么输出是 PNG？"),
        a: text(
          "The cut-away corners must be transparent, and JPG has no transparency. PNG and WebP both keep it; choose WebP for smaller files.",
          "切掉的角必须是透明的，而 JPG 不支持透明。PNG 和 WebP 都能保留透明，想要更小的文件可选 WebP。",
        ),
      },
      {
        q: text("Is the radius the same on every image?", "每张图片的圆角半径都一样吗？"),
        a: text(
          "Yes — the radius is in pixels, so images of the same size get identical corners. Resize first if you want a perfectly uniform set.",
          "是的。半径以像素为单位，相同尺寸的图片会得到完全相同的圆角。若要整组完全统一，可先统一尺寸。",
        ),
      },
      PRIVACY_FAQ,
    ],
  },

  // ── Video ────────────────────────────────────────────────────────────
  {
    slug: "mp4-to-mp3",
    category: "video",
    mode: "media-convert",
    from: ["mp4"],
    to: "mp3",
    accept: VIDEO_ACCEPT,
    output: "mp3",
    outputs: ["mp3", "m4a", "wav"],
    related: ["mov-to-mp4", "m4a-to-mp3", "video-to-gif"],
    name: text("MP4 to MP3", "MP4 转 MP3"),
    h1: text("Convert MP4 to MP3", "MP4 转 MP3"),
    metaTitle: text("MP4 to MP3 Converter — Extract Audio, No Upload | Wemute", "MP4 转 MP3 — 提取视频音频，无需上传 | Wemute"),
    metaDescription: text(
      "Extract the audio from MP4 videos as high-quality MP3. Works with MOV, MKV and WebM too. Private conversion in your browser.",
      "把 MP4 视频中的音频提取为高质量 MP3，也支持 MOV、MKV 和 WebM。在浏览器中私密转换。",
    ),
    answer: text(
      "To convert MP4 to MP3, drop the video below and press Convert. Wemute reads the soundtrack in your browser and saves it as a variable-bitrate MP3 (around 190 kbps), discarding the video so the file is small.",
      "要把 MP4 转成 MP3，把视频拖到下方并点击转换。Wemute 在浏览器中读取音轨，保存为可变码率 MP3（约 190 kbps），并丢弃画面，因此文件很小。",
    ),
    steps: [
      text("Drop MP4, MOV, MKV or WebM videos.", "拖入 MP4、MOV、MKV 或 WebM 视频。"),
      text("MP3 is selected — or pick M4A or WAV.", "已选择 MP3，也可以改为 M4A 或 WAV。"),
      text("Convert and download the audio.", "转换并下载音频。"),
    ],
    useCases: [
      text("Save lectures and podcasts as audio", "把讲座和播客保存为音频"),
      text("Listen to recorded talks on the go", "外出时收听录制的演讲"),
      text("Pull music from your own video clips", "从自己的视频中提取音乐"),
    ],
    faqs: [
      {
        q: text("Does it work with iPhone videos?", "支持 iPhone 拍的视频吗？"),
        a: text(
          "Yes. iPhone MOV videos work the same way — drop them in and you get an MP3 of the audio.",
          "支持。iPhone 的 MOV 视频用法完全相同，拖入后即可得到音频的 MP3。",
        ),
      },
      PRIVACY_FAQ,
      MEDIA_LIMIT_FAQ,
    ],
  },
  {
    slug: "mov-to-mp4",
    category: "video",
    mode: "media-convert",
    from: ["mov"],
    to: "mp4",
    accept: VIDEO_ACCEPT,
    output: "mp4",
    outputs: ["mp4", "gif", "mp3"],
    related: ["compress-video", "mkv-to-mp4", "mp4-to-mp3"],
    name: text("MOV to MP4", "MOV 转 MP4"),
    h1: text("Convert MOV to MP4", "MOV 转 MP4"),
    metaTitle: text("MOV to MP4 Converter — Fast, Free, No Upload | Wemute", "MOV 转 MP4 在线转换 — 快速、免费、无需上传 | Wemute"),
    metaDescription: text(
      "Convert iPhone and QuickTime MOV videos to MP4 that plays everywhere. Fast remux when possible, private processing in your browser.",
      "把 iPhone 和 QuickTime 的 MOV 视频转换为随处可播的 MP4。能直接换封装时极速完成，在浏览器中私密处理。",
    ),
    answer: text(
      "Drop a MOV file below and press Convert to get an MP4. If the video is already H.264, Wemute moves it into MP4 without re-encoding — seconds, with zero quality loss. iPhone HEVC videos are re-encoded to H.264 so they play on Windows and every website.",
      "把 MOV 文件拖到下方并点击转换即可得到 MP4。如果视频已是 H.264，Wemute 会直接换成 MP4 封装而不重新编码，几秒完成且零画质损失。iPhone 的 HEVC 视频会重新编码为 H.264，以便在 Windows 和所有网站上播放。",
    ),
    steps: [
      text("Drop MOV videos from your iPhone or Mac.", "拖入来自 iPhone 或 Mac 的 MOV 视频。"),
      text("Press Convert — no settings needed.", "点击转换，无需任何设置。"),
      text("Download MP4 files that play anywhere.", "下载可随处播放的 MP4 文件。"),
    ],
    useCases: [
      text("Play iPhone videos on Windows or Android", "在 Windows 或安卓设备上播放 iPhone 视频"),
      text("Upload to sites that reject MOV", "上传到不接受 MOV 的网站"),
      text("Share screen recordings from a Mac", "分享 Mac 上的录屏"),
    ],
    faqs: [
      {
        q: text("Is MOV to MP4 lossless?", "MOV 转 MP4 是无损的吗？"),
        a: text(
          "When the video inside is H.264, yes: Wemute copies the streams into MP4 unchanged. HEVC and ProRes have to be re-encoded, which uses a high-quality setting.",
          "如果里面的视频是 H.264，是无损的：Wemute 会原样把音视频流复制进 MP4。HEVC 和 ProRes 需要重新编码，此时会使用高质量设置。",
        ),
      },
      MEDIA_SPEED_FAQ,
      PRIVACY_FAQ,
      MEDIA_LIMIT_FAQ,
    ],
  },
  {
    slug: "video-to-gif",
    category: "video",
    mode: "video-gif",
    from: ["mp4"],
    to: "gif",
    accept: VIDEO_ACCEPT,
    output: "gif",
    outputs: ["gif"],
    related: ["mov-to-mp4", "compress-video", "mp4-to-mp3"],
    name: text("Video to GIF", "视频转 GIF"),
    h1: text("Turn a video into a GIF", "把视频转成 GIF 动图"),
    metaTitle: text("MP4 to GIF Converter — Video to GIF, No Upload | Wemute", "视频转 GIF / MP4 转 GIF — 无需上传 | Wemute"),
    metaDescription: text(
      "Make a GIF from MP4, MOV or WebM. Choose start, length, width and frame rate; high-quality palette, processed in your browser.",
      "用 MP4、MOV 或 WebM 制作 GIF。可设置起点、时长、宽度和帧率，高质量调色，在浏览器中完成。",
    ),
    answer: text(
      "To make a GIF, drop a video below, set where it should start and how long it lasts, and press Convert. Wemute builds an optimised colour palette for the clip, so the GIF looks clean while staying small enough to share.",
      "要制作 GIF，把视频拖到下方，设置开始时间和时长，然后点击转换。Wemute 会为这段视频生成优化的调色板，使 GIF 画面干净且体积适合分享。",
    ),
    steps: [
      text("Drop an MP4, MOV or WebM clip.", "拖入 MP4、MOV 或 WebM 片段。"),
      text("Set the start time, length, width and frame rate.", "设置开始时间、时长、宽度和帧率。"),
      text("Convert and download the GIF.", "转换并下载 GIF。"),
    ],
    useCases: [
      text("Reaction GIFs from your own clips", "用自己的视频片段做表情动图"),
      text("Short product demos for docs and READMEs", "为文档和 README 制作简短的产品演示"),
      text("Loops for slides and chats", "用于幻灯片和聊天的循环动图"),
    ],
    faqs: [
      {
        q: text("How do I keep the GIF small?", "怎样让 GIF 更小？"),
        a: text(
          "Keep it short (under 6 seconds), narrow (480 px or less) and use 10–12 fps. Every extra second and pixel multiplies the size because GIF compresses poorly.",
          "尽量短（6 秒以内）、窄（480 像素或更小），帧率用 10–12。GIF 压缩效率很低，每多一秒、每多一个像素都会让体积成倍增长。",
        ),
      },
      {
        q: text("Is there sound in the GIF?", "GIF 有声音吗？"),
        a: text(
          "No — GIF is an image format and cannot carry audio. Convert to MP4 instead if you need sound.",
          "没有。GIF 是图片格式，无法包含音频。如果需要声音，请转换为 MP4。",
        ),
      },
      PRIVACY_FAQ,
    ],
  },
  {
    slug: "compress-video",
    category: "video",
    mode: "video-compress",
    from: [],
    accept: VIDEO_ACCEPT,
    output: "mp4",
    outputs: ["mp4"],
    related: ["mov-to-mp4", "video-to-gif", "mp4-to-mp3"],
    name: text("Compress Video", "视频压缩"),
    h1: text("Compress a video to a smaller MP4", "压缩视频，生成更小的 MP4"),
    metaTitle: text("Compress Video Online — Smaller MP4, No Upload | Wemute", "在线压缩视频 — 更小的 MP4，无需上传 | Wemute"),
    metaDescription: text(
      "Reduce video file size for email, WhatsApp, WeChat or Discord. Choose quality and resolution; compressed privately in your browser.",
      "缩小视频体积，方便通过邮件、微信、WhatsApp 或 Discord 发送。可选质量和分辨率，在浏览器中私密压缩。",
    ),
    answer: text(
      "Drop a video below, choose a quality and maximum resolution, and press Compress. Wemute re-encodes it as an efficient H.264 MP4 — lowering the resolution to 720p often makes a phone video 5–10 times smaller.",
      "把视频拖到下方，选择质量和最大分辨率，然后点击压缩。Wemute 会重新编码为高效的 H.264 MP4；把分辨率降到 720p，手机视频通常能缩小 5–10 倍。",
    ),
    steps: [
      text("Drop the video you need to shrink.", "拖入需要缩小的视频。"),
      text("Choose quality and a maximum resolution.", "选择质量和最大分辨率。"),
      text("Compress and download the MP4.", "压缩并下载 MP4。"),
    ],
    useCases: [
      text("Fit videos under chat and email limits", "让视频符合聊天软件和邮件的大小限制"),
      text("Save phone storage", "节省手机存储空间"),
      text("Upload faster on slow connections", "在网络较慢时更快上传"),
    ],
    faqs: [
      {
        q: text("Which setting gives the biggest saving?", "哪个设置压缩得最多？"),
        a: text(
          "Resolution matters most: 4K to 1080p or 1080p to 720p cuts the size dramatically. Then lower the quality step for further savings.",
          "分辨率影响最大：从 4K 降到 1080p 或从 1080p 降到 720p 会大幅缩小体积。然后再降低质量档位可以进一步压缩。",
        ),
      },
      MEDIA_SPEED_FAQ,
      PRIVACY_FAQ,
      MEDIA_LIMIT_FAQ,
    ],
  },
  {
    slug: "webm-to-mp4",
    category: "video",
    mode: "media-convert",
    from: ["webm"],
    to: "mp4",
    accept: VIDEO_ACCEPT,
    output: "mp4",
    outputs: ["mp4", "gif", "mp3"],
    related: ["mkv-to-mp4", "compress-video", "video-to-gif"],
    name: text("WebM to MP4", "WebM 转 MP4"),
    h1: text("Convert WebM to MP4", "WebM 转 MP4"),
    metaTitle: text("WebM to MP4 Converter — Free & Private | Wemute", "WebM 转 MP4 在线转换 — 免费、私密 | Wemute"),
    metaDescription: text(
      "Convert WebM screen recordings and downloads to MP4 that plays on iPhone, in editors and on every site. No upload.",
      "把 WebM 录屏和下载的视频转换为可在 iPhone、剪辑软件和所有网站上播放的 MP4。无需上传。",
    ),
    answer: text(
      "Drop a WebM file below and press Convert. Wemute re-encodes the VP8/VP9 video to H.264 and the audio to AAC inside your browser, producing an MP4 that iPhone, Premiere, Final Cut and social sites accept.",
      "把 WebM 文件拖到下方并点击转换。Wemute 在浏览器中把 VP8/VP9 视频重新编码为 H.264、音频编码为 AAC，生成 iPhone、Premiere、Final Cut 和社交网站都能接受的 MP4。",
    ),
    steps: [
      text("Drop WebM recordings.", "拖入 WebM 录屏或视频。"),
      text("Press Convert.", "点击转换。"),
      text("Download the MP4.", "下载 MP4。"),
    ],
    useCases: [
      text("Edit browser screen recordings", "编辑浏览器录屏"),
      text("Play WebM on iPhone", "在 iPhone 上播放 WebM"),
      text("Upload recordings to social platforms", "把录屏上传到社交平台"),
    ],
    faqs: [
      {
        q: text("Why don't some apps open WebM?", "为什么有些软件打不开 WebM？"),
        a: text(
          "WebM uses Google's VP8/VP9 codecs, which Apple devices and many editors don't support natively. MP4 with H.264 is the universal alternative.",
          "WebM 使用谷歌的 VP8/VP9 编码，苹果设备和很多剪辑软件不原生支持。H.264 编码的 MP4 是通用的替代格式。",
        ),
      },
      MEDIA_SPEED_FAQ,
      PRIVACY_FAQ,
    ],
  },
  {
    slug: "mkv-to-mp4",
    category: "video",
    mode: "media-convert",
    from: ["mkv"],
    to: "mp4",
    accept: VIDEO_ACCEPT,
    output: "mp4",
    outputs: ["mp4", "mp3"],
    related: ["mov-to-mp4", "webm-to-mp4", "compress-video"],
    name: text("MKV to MP4", "MKV 转 MP4"),
    h1: text("Convert MKV to MP4", "MKV 转 MP4"),
    metaTitle: text("MKV to MP4 Converter — Fast Remux, No Upload | Wemute", "MKV 转 MP4 在线转换 — 极速换封装，无需上传 | Wemute"),
    metaDescription: text(
      "Convert MKV to MP4 for phones, TVs and editors. Lossless remux in seconds when the video is H.264. Private, in your browser.",
      "把 MKV 转换为适合手机、电视和剪辑软件的 MP4。视频为 H.264 时几秒内无损换封装。在浏览器中私密完成。",
    ),
    answer: text(
      "Drop an MKV file below and press Convert. Most MKV files already contain H.264 video, so Wemute simply moves the streams into an MP4 container — no quality loss and usually done in seconds. Other codecs are re-encoded automatically.",
      "把 MKV 文件拖到下方并点击转换。大多数 MKV 里本来就是 H.264 视频，Wemute 只需把音视频流移入 MP4 封装，无画质损失，通常几秒完成。其他编码会自动重新编码。",
    ),
    steps: [
      text("Drop MKV files.", "拖入 MKV 文件。"),
      text("Press Convert.", "点击转换。"),
      text("Download the MP4.", "下载 MP4。"),
    ],
    useCases: [
      text("Play videos on phones and smart TVs", "在手机和智能电视上播放"),
      text("Import into iMovie, Premiere or CapCut", "导入 iMovie、Premiere 或剪映"),
      text("Share with people without VLC", "分享给没有安装 VLC 的人"),
    ],
    faqs: [
      {
        q: text("What about subtitles and extra audio tracks?", "字幕和多条音轨怎么办？"),
        a: text(
          "Wemute keeps the main video and first audio track. MP4 handles MKV-style subtitles poorly, so they are not carried over.",
          "Wemute 保留主视频和第一条音轨。MP4 对 MKV 类型的字幕支持很差，因此不会保留字幕。",
        ),
      },
      MEDIA_SPEED_FAQ,
      PRIVACY_FAQ,
    ],
  },

  // ── Audio ────────────────────────────────────────────────────────────
  audioConvert("wav-to-mp3", "wav", "mp3", {
    name: text("WAV to MP3", "WAV 转 MP3"),
    h1: text("Convert WAV to MP3", "WAV 转 MP3"),
    metaTitle: text("WAV to MP3 Converter — High Quality, No Upload | Wemute", "WAV 转 MP3 在线转换 — 高音质、无需上传 | Wemute"),
    metaDescription: text(
      "Convert large WAV recordings to MP3 about 10× smaller. High-quality VBR encoding, batch conversion, private in your browser.",
      "把体积巨大的 WAV 录音转换为小约 10 倍的 MP3。高质量 VBR 编码，支持批量，在浏览器中私密完成。",
    ),
    answer: text(
      "Drop WAV files below. Wemute encodes them as high-quality variable-bitrate MP3s (around 190 kbps) in your browser — roughly a tenth of the size with sound most people can't tell apart from the original.",
      "把 WAV 文件拖到下方即可。Wemute 在浏览器中把它们编码为高质量可变码率 MP3（约 190 kbps），体积约为原来的十分之一，大多数人听不出与原始音频的区别。",
    ),
    useCases: [
      text("Share recordings and demos by email or chat", "通过邮件或聊天发送录音和小样"),
      text("Put studio bounces on a phone", "把录音室导出的音频放到手机上"),
      text("Shrink voice recordings for transcription", "缩小语音录音以便转写"),
    ],
    related: ["mp3-to-wav", "flac-to-mp3", "m4a-to-mp3"],
    specific: [
      {
        q: text("What bitrate does Wemute use?", "Wemute 使用什么码率？"),
        a: text(
          "LAME VBR quality 2, which averages about 170–210 kbps. It's the setting audio engineers commonly recommend as transparent for most music.",
          "使用 LAME VBR 质量 2，平均约 170–210 kbps。这是音频工程师普遍推荐的、对多数音乐听感无损的设置。",
        ),
      },
    ],
  }),
  audioConvert("m4a-to-mp3", "m4a", "mp3", {
    name: text("M4A to MP3", "M4A 转 MP3"),
    h1: text("Convert M4A to MP3", "M4A 转 MP3"),
    metaTitle: text("M4A to MP3 Converter — Voice Memos & Music | Wemute", "M4A 转 MP3 在线转换 — 语音备忘录与音乐 | Wemute"),
    metaDescription: text(
      "Convert iPhone voice memos and M4A/AAC music to MP3 for any player. Batch conversion, no upload, no sign-up.",
      "把 iPhone 语音备忘录和 M4A/AAC 音乐转换为任何播放器都能用的 MP3。支持批量，无需上传和注册。",
    ),
    answer: text(
      "Drop M4A files below — each one converts to MP3 straight away. It works for iPhone Voice Memos, GarageBand exports and AAC music, and the MP3 plays in every car stereo, web form and media player.",
      "把 M4A 文件拖到下方即可直接得到 MP3。适用于 iPhone 语音备忘录、库乐队导出文件和 AAC 音乐，生成的 MP3 可在任何车载音响、网页表单和播放器中使用。",
    ),
    useCases: [
      text("Share iPhone voice memos with anyone", "把 iPhone 语音备忘录分享给任何人"),
      text("Play AAC music on older players and cars", "在老播放器和车载音响上播放 AAC 音乐"),
      text("Submit audio to forms that require MP3", "向只接受 MP3 的表单提交音频"),
    ],
    related: ["wav-to-mp3", "mp4-to-mp3", "flac-to-mp3"],
    specific: [
      {
        q: text("Can it convert protected iTunes purchases?", "能转换受保护的 iTunes 购买音乐吗？"),
        a: text(
          "No. Old DRM-protected M4P files can't be decoded. Unprotected M4A files, including all modern iTunes purchases, work.",
          "不能。旧版受 DRM 保护的 M4P 文件无法解码。未加密的 M4A 文件（包括所有新近购买的 iTunes 音乐）都可以转换。",
        ),
      },
    ],
  }),
  audioConvert("flac-to-mp3", "flac", "mp3", {
    name: text("FLAC to MP3", "FLAC 转 MP3"),
    h1: text("Convert FLAC to MP3", "FLAC 转 MP3"),
    metaTitle: text("FLAC to MP3 Converter — Batch, High Quality | Wemute", "FLAC 转 MP3 在线转换 — 批量、高音质 | Wemute"),
    metaDescription: text(
      "Convert lossless FLAC albums to high-quality MP3 for phones and cars. Batch conversion in your browser with no upload.",
      "把无损 FLAC 专辑转换为适合手机和车载的高质量 MP3。在浏览器中批量转换，无需上传。",
    ),
    answer: text(
      "Drop FLAC tracks below. Wemute encodes high-quality VBR MP3s in your browser — about a fifth of the size of the FLAC — so a whole album fits comfortably on a phone or USB stick.",
      "把 FLAC 曲目拖到下方即可。Wemute 在浏览器中编码为高质量 VBR MP3，体积约为 FLAC 的五分之一，整张专辑都能轻松放进手机或 U 盘。",
    ),
    useCases: [
      text("Load albums onto a phone or car USB", "把专辑放进手机或车载 U 盘"),
      text("Share tracks without huge downloads", "分享曲目而不必传超大文件"),
      text("Keep FLAC masters and use MP3 copies", "保留 FLAC 母带，日常使用 MP3 副本"),
    ],
    related: ["wav-to-mp3", "m4a-to-mp3", "mp3-to-wav"],
    specific: [
      {
        q: text("Will converting FLAC to MP3 reduce quality?", "FLAC 转 MP3 会降低音质吗？"),
        a: text(
          "Technically yes — MP3 is lossy — but at the high VBR setting Wemute uses, the difference is inaudible to most listeners. Keep your FLAC files as the master copy.",
          "严格来说会，因为 MP3 是有损格式。但在 Wemute 使用的高质量 VBR 设置下，大多数人听不出差别。建议保留 FLAC 作为母带。",
        ),
      },
    ],
  }),
  audioConvert("mp3-to-wav", "mp3", "wav", {
    name: text("MP3 to WAV", "MP3 转 WAV"),
    h1: text("Convert MP3 to WAV", "MP3 转 WAV"),
    metaTitle: text("MP3 to WAV Converter — For Editing & Burning | Wemute", "MP3 转 WAV 在线转换 — 适合剪辑和刻录 | Wemute"),
    metaDescription: text(
      "Convert MP3 to uncompressed WAV for audio editors, DJ software and CD burning. Batch conversion, private in your browser.",
      "把 MP3 转换为未压缩的 WAV，用于音频编辑器、DJ 软件和光盘刻录。支持批量，在浏览器中私密完成。",
    ),
    answer: text(
      "Drop MP3 files below. Wemute decodes them to 16-bit PCM WAV in your browser — the format every audio editor, sampler and CD burner accepts.",
      "把 MP3 文件拖到下方即可。Wemute 在浏览器中把它们解码为 16 位 PCM WAV，这是所有音频编辑器、采样器和光盘刻录软件都接受的格式。",
    ),
    useCases: [
      text("Import into editors that prefer WAV", "导入更适合 WAV 的编辑软件"),
      text("Burn audio CDs", "刻录音频 CD"),
      text("Load samples into hardware and DJ gear", "把采样导入硬件设备和 DJ 设备"),
    ],
    related: ["wav-to-mp3", "flac-to-mp3", "m4a-to-mp3"],
    specific: [
      {
        q: text("Does WAV sound better than the MP3?", "WAV 会比 MP3 音质更好吗？"),
        a: text(
          "No. The WAV is an exact, uncompressed copy of what the MP3 contains — it avoids further loss while editing but can't restore detail.",
          "不会。WAV 是 MP3 内容的完整未压缩副本，可以避免编辑时继续损失，但无法恢复已丢失的细节。",
        ),
      },
    ],
  }),
];

export const TOOL_BY_SLUG = new Map(TOOLS.map((tool) => [tool.slug, tool]));

export const CATEGORY_ORDER: Category[] = ["image", "video", "audio"];

export const CATEGORY_LABEL: Record<Category, Text> = {
  image: text("Image", "图片"),
  video: text("Video", "视频"),
  audio: text("Audio", "音频"),
};

export function toolsIn(category: Category): Tool[] {
  return TOOLS.filter((tool) => tool.category === category);
}

export function localized<T extends Text>(value: T, locale: Locale): string {
  return value[locale];
}
