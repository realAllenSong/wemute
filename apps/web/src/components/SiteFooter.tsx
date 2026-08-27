import type { Locale } from "../types";

interface SiteFooterProps {
  locale: Locale;
  onNavigate: (path: string) => void;
}

function NavLink({ href, label, onNavigate }: { href: string; label: string; onNavigate: (path: string) => void }) {
  return <a href={href} onClick={(event) => { event.preventDefault(); onNavigate(href); }}>{label}</a>;
}

export function SiteFooter({ locale, onNavigate }: SiteFooterProps) {
  return (
    <footer className="site-footer">
      <div className="site-footer__brand">
        <img className="brand-icon brand-icon--small" src="/wemute-icon-256.png" alt="" width="26" height="26" />
        <span><strong>Wemute</strong><small>{locale === "en" ? "Simple tools. Local by default." : "简单工具，默认本地。"}</small></span>
      </div>
      <nav aria-label={locale === "en" ? "Footer navigation" : "页脚导航"}>
        <NavLink href="/about" label={locale === "en" ? "About" : "关于"} onNavigate={onNavigate} />
        <NavLink href="/privacy" label={locale === "en" ? "Privacy" : "隐私"} onNavigate={onNavigate} />
        <NavLink href="/terms" label={locale === "en" ? "Terms" : "条款"} onNavigate={onNavigate} />
        <a href="https://github.com/realAllenSong" target="_blank" rel="noreferrer">AllenSong</a>
      </nav>
    </footer>
  );
}
