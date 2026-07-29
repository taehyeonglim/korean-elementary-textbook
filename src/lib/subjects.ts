import type { GradeBand, SubjectId } from "./catalog";

export interface SubjectDefinition {
  id: SubjectId;
  slug: string;
  label: string;
  englishLabel: string;
  shortLabel: string;
  status: "published" | "preparing";
  summary: string;
  accent: "math" | "english" | "korean";
  gradeBands: GradeBand[];
  areas: string[];
  standardCount: number;
}

export const SUBJECTS: Record<SubjectId, SubjectDefinition> = {
  math: {
    id: "math",
    slug: "math",
    label: "초등 수학 한 장",
    englishLabel: "Elementary Mathematics",
    shortLabel: "수학",
    status: "published",
    summary: "성취기준에 연결한 짧고 정확한 수학 학습지를 찾아 바로 인쇄해 보세요.",
    accent: "math",
    gradeBands: ["1-2", "3-4", "5-6"],
    areas: ["수와 연산", "변화와 관계", "도형과 측정", "자료와 가능성"],
    standardCount: 121,
  },
  english: {
    id: "english",
    slug: "english",
    label: "초등 영어 한 장",
    englishLabel: "Elementary English",
    shortLabel: "영어",
    status: "published",
    summary: "읽고 이해한 내용을 말하고 쓰며 표현하는 6쪽 영어 학습지 16권을 제공합니다.",
    accent: "english",
    gradeBands: ["3-4", "5-6"],
    areas: ["이해", "표현"],
    standardCount: 40,
  },
  korean: {
    id: "korean",
    slug: "korean",
    label: "초등 국어 한 장",
    englishLabel: "Elementary Korean",
    shortLabel: "국어",
    status: "published",
    summary: "읽고 탐구한 내용을 말과 글로 표현하는 8쪽 국어 학습지 18권을 제공합니다.",
    accent: "korean",
    gradeBands: ["1-2", "3-4", "5-6"],
    areas: ["듣기·말하기", "읽기", "쓰기", "문법", "문학", "매체"],
    standardCount: 87,
  },
};

export const SUBJECT_LIST = Object.values(SUBJECTS);

export function subjectDefinition(subject: SubjectId): SubjectDefinition {
  return SUBJECTS[subject];
}
