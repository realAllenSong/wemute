import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faArrowLeft, faCheck } from "@fortawesome/free-solid-svg-icons";
import type { ToolDefinition } from "../site";
import type { Locale } from "../types";
import { MarketingDropzone } from "./MarketingDropzone";
import { TOOL_DEFINITIONS } from "../site";
import { AdSlot } from "./AdSlot";
import { SiteFooter } from "./SiteFooter";

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
      <a className="back-link" href="/" onClick={(event) => { event.preventDefault(); onNavigate("/"); }}>
        <FontAwesomeIcon icon={faArrowLeft} />{locale === "en" ? "All image tools" : "全部图片工具"}
      </a>
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

      <section className="tool-explainer" aria-labelledby="tool-answer-heading">
        <div className="tool-answer">
          <span>{locale === "en" ? "Direct answer" : "直接说明"}</span>
          <h2 id="tool-answer-heading">{locale === "en" ? `How ${tool.shortTitle.en.toLowerCase()} works` : `${tool.shortTitle.zh}如何工作`}</h2>
          <p>{tool.answer[locale]}</p>
        </div>
        <ol className="tool-steps">
          {tool.steps.map((step, index) => (
            <li key={step.en}><span>{index + 1}</span><p>{step[locale]}</p></li>
          ))}
        </ol>
      </section>

      <section className="tool-use-cases">
        <div>
          <span>{locale === "en" ? "Useful for" : "适合用于"}</span>
          <h2>{locale === "en" ? "Common jobs, one batch" : "常见任务，一次完成"}</h2>
        </div>
        <ul>{tool.useCases.map((useCase) => <li key={useCase.en}><FontAwesomeIcon icon={faCheck} />{useCase[locale]}</li>)}</ul>
      </section>

      <AdSlot locale={locale} placement="tool" />

      <section className="faq-section tool-faq">
        <h2>{locale === "en" ? "Questions about this tool" : "关于这个工具"}</h2>
        <div className="faq-list">
          {tool.faqs.map((faq) => (
            <details key={faq.question.en}>
              <summary>{faq.question[locale]}</summary>
              <p>{faq.answer[locale]}</p>
            </details>
          ))}
        </div>
      </section>

      <section className="related-tools">
        <span>{locale === "en" ? "More local image tools" : "更多本地图片工具"}</span>
        <div>{TOOL_DEFINITIONS.filter((candidate) => candidate.slug !== tool.slug).map((candidate) => (
          <a key={candidate.slug} href={candidate.path} onClick={(event) => { event.preventDefault(); onNavigate(candidate.path); }}>
            {candidate.shortTitle[locale]}
          </a>
        ))}</div>
      </section>

      <SiteFooter locale={locale} onNavigate={onNavigate} />
    </main>
  );
}
