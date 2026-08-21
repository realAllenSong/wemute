import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faArrowLeft } from "@fortawesome/free-solid-svg-icons";
import type { StaticPageDefinition } from "../site";
import type { Locale } from "../types";
import { SiteFooter } from "./SiteFooter";

interface StaticPageProps {
  page: StaticPageDefinition;
  locale: Locale;
  onNavigate: (path: string) => void;
}

export function StaticPage({ page, locale, onNavigate }: StaticPageProps) {
  return (
    <main className="static-page">
      <a className="back-link" href="/" onClick={(event) => { event.preventDefault(); onNavigate("/"); }}>
        <FontAwesomeIcon icon={faArrowLeft} />{locale === "en" ? "Back to image tools" : "返回图片工具"}
      </a>
      <article>
        <header className="static-page__header">
          <span>{page.slug === "about" ? "Wemute" : locale === "en" ? "Legal" : "法律信息"}</span>
          <h1>{page.title[locale]}</h1>
          <p>{page.intro[locale]}</p>
          <small>{locale === "en" ? `Updated ${page.updated}` : `更新于 ${page.updated}`}</small>
        </header>
        <div className="static-page__sections">
          {page.sections.map((section) => (
            <section key={section.heading.en}>
              <h2>{section.heading[locale]}</h2>
              <p>{section.body[locale]}</p>
            </section>
          ))}
        </div>
      </article>
      <SiteFooter locale={locale} onNavigate={onNavigate} />
    </main>
  );
}
