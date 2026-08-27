import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faArrowRight, faCheck, faClock, faFileImage } from "@fortawesome/free-solid-svg-icons";
import type { Locale } from "../types";

interface BatchStoryProps {
  locale: Locale;
}

const rows = [
  { name: "portrait.heic", meta: "3024 × 4032 · 3.1 MB", target: "WebP", tone: "portrait", state: "ready" },
  { name: "studio-light.png", meta: "2400 × 1600 · 8.6 MB", target: "WebP", tone: "studio", state: "working" },
  { name: "weekend.jpg", meta: "4032 × 3024 · 4.7 MB", target: "WebP", tone: "weekend", state: "queued" },
] as const;

export function BatchStory({ locale }: BatchStoryProps) {
  return (
    <section className="batch-story" aria-labelledby="batch-story-heading">
      <div className="batch-story__copy">
        <span className="section-kicker">{locale === "en" ? "Batch by design" : "为批量而设计"}</span>
        <h2 id="batch-story-heading">{locale === "en" ? "Set it once. Keep control when you need it." : "设置一次，需要时再单独调整。"}</h2>
        <p>{locale === "en"
          ? "Drop ten images, choose one result for the whole set, and change only the exceptions. Wemute keeps the common path fast without hiding the details."
          : "拖入十张图片，为整组选择一个结果，只修改少数例外。Wemute 让常用流程足够快，也不会藏起必要细节。"}</p>
        <ol className="batch-story__steps">
          <li><span>1</span><div><strong>{locale === "en" ? "Add a batch" : "加入整批文件"}</strong><small>{locale === "en" ? "Drop images or choose a folder-sized set." : "拖入图片，或一次选择整组文件。"}</small></div></li>
          <li><span>2</span><div><strong>{locale === "en" ? "Choose once" : "统一设置一次"}</strong><small>{locale === "en" ? "Format and quality apply to every ready file." : "格式与质量应用到所有待处理文件。"}</small></div></li>
          <li><span>3</span><div><strong>{locale === "en" ? "Download together" : "一起下载"}</strong><small>{locale === "en" ? "Keep individual files or one tidy ZIP." : "保留单个文件，或下载一个整洁的 ZIP。"}</small></div></li>
        </ol>
      </div>

      <div className="batch-window" aria-label={locale === "en" ? "Example batch conversion workspace" : "批量转换工作区示例"}>
        <div className="batch-window__titlebar">
          <span className="batch-window__lights" aria-hidden="true"><i /><i /><i /></span>
          <strong>{locale === "en" ? "3 images" : "3 张图片"}</strong>
          <span>{locale === "en" ? "All to WebP" : "全部转为 WebP"}</span>
        </div>
        <div className="batch-window__rows">
          {rows.map((row) => (
            <div className="batch-window__row" key={row.name}>
              <span className={`batch-thumb batch-thumb--${row.tone}`} aria-hidden="true"><FontAwesomeIcon icon={faFileImage} /></span>
              <span className="batch-file"><strong>{row.name}</strong><small>{row.meta}</small></span>
              <FontAwesomeIcon className="batch-arrow" icon={faArrowRight} />
              <span className="batch-target">{row.target}</span>
              {row.state === "ready" ? (
                <span className="batch-state batch-state--ready"><FontAwesomeIcon icon={faCheck} />{locale === "en" ? "Ready" : "就绪"}</span>
              ) : row.state === "working" ? (
                <span className="batch-state batch-state--working"><strong>68%</strong><i><b /></i></span>
              ) : (
                <span className="batch-state"><FontAwesomeIcon icon={faClock} />{locale === "en" ? "Queued" : "排队中"}</span>
              )}
            </div>
          ))}
        </div>
        <div className="batch-window__footer">
          <span><small>{locale === "en" ? "Estimated total" : "预计总体积"}</small><strong>16.4 MB → 5.2 MB</strong></span>
          <span className="batch-window__button">{locale === "en" ? "Convert all" : "全部转换"}</span>
        </div>
      </div>
    </section>
  );
}
