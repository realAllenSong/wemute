import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faArrowRight,
  faBolt,
  faCompress,
  faCropSimple,
  faExpand,
  faFileImage,
  faLayerGroup,
  faLock,
  faObjectGroup,
} from "@fortawesome/free-solid-svg-icons";
import { HOME_CONTENT, TOOL_DEFINITIONS, type ToolDefinition } from "../site";
import type { Locale } from "../types";
import { AdSlot } from "./AdSlot";
import { MarketingDropzone } from "./MarketingDropzone";
import { SiteFooter } from "./SiteFooter";

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
          <h1>{HOME_CONTENT.h1[locale]}</h1>
          <p>{HOME_CONTENT.intro[locale]}</p>
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
            <a key={tool.slug} href={tool.path} className="tool-link" onClick={(event) => { event.preventDefault(); onNavigate(tool.path); }}>
              <span className="tool-link__icon"><FontAwesomeIcon icon={iconFor(tool)} /></span>
              <span className="tool-link__copy">
                <strong>{tool.shortTitle[locale]}</strong>
                <small>{tool.description[locale]}</small>
              </span>
              <FontAwesomeIcon icon={faArrowRight} className="tool-link__arrow" />
            </a>
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

      <AdSlot locale={locale} placement="home" />

      <section className="faq-section">
        <h2>{locale === "en" ? "Good to know" : "你可能会想知道"}</h2>
        <div className="faq-list">
          {HOME_CONTENT.faqs.map((faq) => (
            <details key={faq.question.en}>
              <summary>{faq.question[locale]}</summary>
              <p>{faq.answer[locale]}</p>
            </details>
          ))}
        </div>
      </section>

      <SiteFooter locale={locale} onNavigate={onNavigate} />
    </main>
  );
}
