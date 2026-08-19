import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faArrowRight,
  faBolt,
  faCompress,
  faCropSimple,
  faDesktop,
  faExpand,
  faFileImage,
  faImage,
  faLayerGroup,
  faLock,
  faObjectGroup,
  faWandMagicSparkles,
} from "@fortawesome/free-solid-svg-icons";
import { TOOL_DEFINITIONS, type ToolDefinition } from "../site";
import type { Locale } from "../types";
import { MarketingDropzone } from "./MarketingDropzone";

interface HomePageProps {
  locale: Locale;
  dragging: boolean;
  onChoose: () => void;
  onNavigate: (path: string) => void;
}

const iconFor = (tool: ToolDefinition) => {
  if (tool.icon === "compress") return faCompress;
  if (tool.icon === "resize") return faExpand;
  if (tool.icon === "corners") return faCropSimple;
  return faFileImage;
};

export function HomePage({ locale, dragging, onChoose, onNavigate }: HomePageProps) {
  return (
    <main className="marketing-page">
      <section className="hero-section">
        <div className="hero-copy">
          <h1>{locale === "en" ? "The image tools you need. Nothing else." : "常用图片工具，刚刚好。"}</h1>
          <p>{locale === "en"
            ? "Convert, compress and resize a whole batch in your browser. Fast, private, and free to use."
            : "在浏览器里批量转换、压缩和调整尺寸。快速、私密，免费使用。"}</p>
        </div>
        <MarketingDropzone locale={locale} dragging={dragging} onChoose={onChoose} />
        <div className="hero-formats" aria-label={locale === "en" ? "Supported formats" : "支持格式"}>
          <span>PNG</span><span>JPEG</span><span>WEBP</span><span>HEIC*</span>
          <small>{locale === "en" ? "* when supported by your browser" : "* 取决于浏览器支持"}</small>
        </div>
      </section>

      <section className="tools-section" id="tools">
        <div className="section-heading">
          <h2>{locale === "en" ? "Start with one clear job" : "先选一件要做的事"}</h2>
          <p>{locale === "en" ? "Each tool opens with a sensible default. You can still fine-tune every batch." : "每个工具都有合适的默认值，也可以继续精细调整。"}</p>
        </div>
        <div className="tool-rail">
          {TOOL_DEFINITIONS.map((tool) => (
            <button key={tool.slug} type="button" className="tool-link" onClick={() => onNavigate(tool.path)}>
              <span className="tool-link__icon"><FontAwesomeIcon icon={iconFor(tool)} /></span>
              <span className="tool-link__copy">
                <strong>{tool.shortTitle[locale]}</strong>
                <small>{tool.description[locale]}</small>
              </span>
              <FontAwesomeIcon icon={faArrowRight} className="tool-link__arrow" />
            </button>
          ))}
        </div>
      </section>

      <section className="privacy-section" id="privacy">
        <div className="privacy-copy">
          <FontAwesomeIcon icon={faLock} className="section-symbol" />
          <h2>{locale === "en" ? "Your images stay yours" : "你的图片，只属于你"}</h2>
          <p>{locale === "en"
            ? "Wemute Web processes supported images inside your browser. There is no upload queue, account, or hidden copy on our servers."
            : "Wemute Web 会在浏览器内处理支持的图片。没有上传队列，不需要账号，我们的服务器也不会保留副本。"}</p>
        </div>
        <div className="privacy-points">
          <div><FontAwesomeIcon icon={faBolt} /><span><strong>{locale === "en" ? "Immediate" : "立即处理"}</strong><small>{locale === "en" ? "No waiting for uploads" : "无需等待上传"}</small></span></div>
          <div><FontAwesomeIcon icon={faLayerGroup} /><span><strong>{locale === "en" ? "Batch first" : "批量优先"}</strong><small>{locale === "en" ? "One setting for the whole set" : "一套设置应用到整组"}</small></span></div>
          <div><FontAwesomeIcon icon={faObjectGroup} /><span><strong>{locale === "en" ? "Still flexible" : "仍可自定义"}</strong><small>{locale === "en" ? "Override individual files when needed" : "需要时可单独调整文件"}</small></span></div>
        </div>
      </section>

      <aside className="ad-reservation" aria-label={locale === "en" ? "Reserved advertisement space" : "预留广告位"}>
        <span>{locale === "en" ? "Advertisement" : "广告"}</span>
      </aside>

      <section className="desktop-section" id="desktop">
        <div className="desktop-visual" aria-hidden="true">
          <FontAwesomeIcon icon={faDesktop} />
          <div><FontAwesomeIcon icon={faImage} /><FontAwesomeIcon icon={faArrowRight} /><FontAwesomeIcon icon={faWandMagicSparkles} /></div>
        </div>
        <div className="desktop-copy">
          <h2>{locale === "en" ? "More power lives on your Mac" : "更强的能力，留在 Mac 上"}</h2>
          <p>{locale === "en"
            ? "The Wemute desktop app handles video, audio and local AI tools with native performance — including background removal and more coming next."
            : "Wemute 桌面版可用原生性能处理视频、音频和本地 AI 工具，包括去背景，以及接下来会加入的更多能力。"}</p>
          <span>{locale === "en" ? "macOS Apple Silicon · private alpha" : "macOS Apple Silicon · 内测版"}</span>
        </div>
      </section>

      <section className="faq-section">
        <h2>{locale === "en" ? "Good to know" : "你可能会想知道"}</h2>
        <div className="faq-list">
          <details>
            <summary>{locale === "en" ? "Are my files uploaded?" : "文件会被上传吗？"}</summary>
            <p>{locale === "en" ? "No. Supported web conversions run locally in this browser tab." : "不会。网页版支持的转换都在当前浏览器标签页内完成。"}</p>
          </details>
          <details>
            <summary>{locale === "en" ? "Can I convert a whole folder?" : "可以转换整个文件夹吗？"}</summary>
            <p>{locale === "en" ? "You can select multiple images together. Folder workflows are coming to the desktop app." : "你可以一次选择多张图片；文件夹工作流将由桌面版提供。"}</p>
          </details>
          <details>
            <summary>{locale === "en" ? "Why are some formats desktop-only?" : "为什么有些格式只在桌面版支持？"}</summary>
            <p>{locale === "en" ? "Browsers expose fewer codecs. The desktop app bundles dedicated media engines for wider, more predictable support." : "浏览器能调用的编解码器更少；桌面版会内置专用媒体引擎，支持范围更广、更稳定。"}</p>
          </details>
        </div>
      </section>

      <footer className="site-footer">
        <div><span className="brand-mark brand-mark--small" aria-hidden="true"><span /></span><strong>Wemute</strong></div>
        <p>{locale === "en" ? "Simple tools. Local by default." : "简单工具，默认本地。"}</p>
      </footer>
    </main>
  );
}
