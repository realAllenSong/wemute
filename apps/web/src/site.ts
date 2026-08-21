import type { ConversionOptions, Locale, OutputFormat } from "./types";
import { LEGAL_CONTENT, SITE_CONTENT, TOOL_CONTENT, contentForPath } from "./site-content.js";

export type ToolSlug = "convert-image" | "compress-image" | "resize-image" | "round-corners";
export type StaticPageSlug = "privacy" | "terms" | "about";

export interface ToolDefinition {
  slug: ToolSlug;
  path: string;
  icon: "convert" | "compress" | "resize" | "corners";
  title: Record<Locale, string>;
  shortTitle: Record<Locale, string>;
  description: Record<Locale, string>;
  dropHint: Record<Locale, string>;
  seoTitle: string;
  seoDescription: string;
  answer: Record<Locale, string>;
  steps: Record<Locale, string>[];
  useCases: Record<Locale, string>[];
  faqs: { question: Record<Locale, string>; answer: Record<Locale, string> }[];
  options: ConversionOptions;
  format: OutputFormat;
}

export interface StaticPageDefinition {
  slug: StaticPageSlug;
  path: string;
  seoTitle: string;
  seoDescription: string;
  title: Record<Locale, string>;
  updated: string;
  intro: Record<Locale, string>;
  sections: { heading: Record<Locale, string>; body: Record<Locale, string> }[];
}

export const TOOL_DEFINITIONS = TOOL_CONTENT as ToolDefinition[];
export const STATIC_PAGE_DEFINITIONS = LEGAL_CONTENT as StaticPageDefinition[];
export const HOME_CONTENT = SITE_CONTENT.home;

export function toolFromPath(pathname: string): ToolDefinition | undefined {
  return TOOL_DEFINITIONS.find((tool) => tool.path === pathname.replace(/\/$/, ""));
}

export function staticPageFromPath(pathname: string): StaticPageDefinition | undefined {
  return STATIC_PAGE_DEFINITIONS.find((page) => page.path === pathname.replace(/\/$/, ""));
}

export function safePath(pathname: string): string {
  return contentForPath(pathname)?.path ?? "/";
}
