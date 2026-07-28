import catalogJson from "../../content/catalog.json";

export const GRADE_BANDS = ["1-2", "3-4", "5-6"] as const;
export const LEVELS = ["foundation", "standard", "challenge"] as const;
export const PAGE_ROLES = ["cover", "worksheet", "answer"] as const;

export type GradeBand = (typeof GRADE_BANDS)[number];
export type ProjectLevel = (typeof LEVELS)[number];
export type PageRole = (typeof PAGE_ROLES)[number];

export interface WorkbookPage {
  id: string;
  order: number;
  role: PageRole;
  imagePath: string;
  thumbnailPath: string;
  sha256: string;
  alt: string;
  approved: boolean;
}

export interface WorkbookPdf {
  path: string;
  pageCount: number;
  sha256: string;
}

export interface Workbook {
  id: string;
  slug: string;
  title: string;
  gradeBand: GradeBand;
  /** Only set when an official source supports this individual-grade mapping. */
  grade?: 1 | 2 | 3 | 4 | 5 | 6;
  domain: string;
  module: string;
  standardCodes: string[];
  /** Project-defined learning stages; they are not a national achievement-level label. */
  levels: ["foundation", "standard", "challenge"];
  pages: WorkbookPage[];
  pdf: WorkbookPdf;
  transcriptPath: string;
  license: "CC-BY-NC-SA-4.0";
  author: "Taehyeong Lim";
  publishedAt: string;
  published: boolean;
}

export interface WorkbookCatalog {
  version: 1;
  workbooks: Workbook[];
}

// JSON module imports widen literal arrays (for example, `levels`) to `string[]`.
// Runtime content validation owns the schema check before build and publication.
export const catalog = catalogJson as unknown as WorkbookCatalog;

export const GRADE_BAND_LABELS: Record<GradeBand, string> = {
  "1-2": "1–2학년군",
  "3-4": "3–4학년군",
  "5-6": "5–6학년군",
};

export const LEVEL_LABELS: Record<ProjectLevel, string> = {
  foundation: "기초",
  standard: "표준",
  challenge: "도전",
};

export function publishedWorkbooks(): Workbook[] {
  return catalog.workbooks.filter((workbook) => workbook.published);
}

export function findWorkbook(slug: string): Workbook | undefined {
  return publishedWorkbooks().find((workbook) => workbook.slug === slug);
}

export function coverPage(workbook: Workbook): WorkbookPage | undefined {
  return workbook.pages.find((page) => page.role === "cover") ?? workbook.pages[0];
}

export function publicAsset(path: string): string {
  return `${import.meta.env.BASE_URL}${path.replace(/^\//, "")}`;
}
