import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faArrowLeft, faCheck } from "@fortawesome/free-solid-svg-icons";
import type { ToolDefinition } from "../site";
import type { Locale } from "../types";
import { MarketingDropzone } from "./MarketingDropzone";

interface ToolLandingPageProps {
  tool: ToolDefinition;
  locale: Locale;
  dragging: boolean;
  onChoose: () => void;
  onNavigate: (path: string) => void;
}

export function ToolLandingPage({ tool, locale, dragging, onChoose, onNavigate }: ToolLandingPageProps) {
  return (
    <main className="tool-page">
      <button className="back-link" type="button" onClick={() => onNavigate("/")}>
        <FontAwesomeIcon icon={faArrowLeft} />{locale === "en" ? "All image tools" : "全部图片工具"}
      </button>
      <section className="tool-hero">
        <div className="tool-hero__copy">
          <h1>{tool.title[locale]}</h1>
          <p>{tool.description[locale]}</p>
          <ul>
            <li><FontAwesomeIcon icon={faCheck} />{locale === "en" ? "Apply one setting to the whole batch" : "一套设置应用到整批文件"}</li>
            <li><FontAwesomeIcon icon={faCheck} />{locale === "en" ? "Fine-tune individual files when needed" : "需要时仍可单独调整文件"}</li>
            <li><FontAwesomeIcon icon={faCheck} />{locale === "en" ? "Processed locally in this browser" : "在当前浏览器内本地处理"}</li>
          </ul>
        </div>
        <MarketingDropzone locale={locale} dragging={dragging} hint={tool.dropHint[locale]} onChoose={onChoose} />
      </section>
      <p className="tool-page__note">{locale === "en"
        ? "PNG, JPEG and WebP are fully supported. HEIC support depends on your browser."
        : "完整支持 PNG、JPEG 和 WebP；HEIC 取决于当前浏览器。"}</p>
    </main>
  );
}
