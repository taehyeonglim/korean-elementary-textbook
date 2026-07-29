# 초등 학습지 한 장

2022 개정 교육과정에 연결된 무료 초등 학습지를 과목별로 탐색하고 PDF로 내려받는 정적 사이트입니다. 현재 수학 53권, 영어 16권, 국어 18권을 공개하고 있습니다. 영어는 40개 성취기준을 input → practice → production 흐름의 6쪽으로, 국어는 87개 성취기준을 읽기 → 탐구 → 표현 흐름의 8쪽으로 연결합니다.

## 개발

```sh
npm install
npm run dev
npm run check
npm run build
```

콘텐츠는 `content/workbooks/*.json`에 추가하고 `subject`로 과목을 구분합니다. 공개 가능 상태인 학습지만 `published: true`로 설정할 수 있습니다.

- `npm run validate:content`: 카탈로그·학습지 메타데이터 검사
- `npm run validate:assets`: 승인 이미지, 해시, PDF 페이지 수와 메타데이터 검사
- `npm run build:thumbnails -- --workbook <id>`: 원본 이미지에서 WebP 썸네일 생성
- `npm run build:pdf -- --workbook <id>`: 승인 원본 이미지만 사용해 A4 PDF 생성 (텍스트 오버레이 없음)
- `npm run validate:public`: Pages 산출물 allowlist 및 비공개 자료 유출 검사

GitHub Pages의 고정 배포 경로는 `/korean-elementary-textbook/`입니다. Pages 환경에서 GitHub Actions를 허용하고 배포 소스를 **GitHub Actions**로 설정해야 합니다.

## Gongnyang Prompt Kit

The project ships the upstream [Gongnyang Prompt Kit](https://github.com/gongnyang/gongnyang-prompt-kit) as a pinned, shallow checkout at `vendor/gongnyang-prompt-kit`. Its `image-prompt` skill is exposed to Codex at `.agents/skills/image-prompt` through a relative symlink, so it is available whenever Codex is started from this directory (or a child directory).

Restart Codex or start a new session after this setup, then invoke `$image-prompt` (or use a matching Korean image-prompt request). The skill compiles requests for gpt-image-2 / `$imagegen` and includes its own guidance and reference library.

Validate a saved prompt:

```sh
./scripts/check-image-prompt path/to/prompt.txt
```

Run the toolkit's deterministic regression checks:

```sh
./scripts/check-image-prompt --test
```

Update the vendored source later:

```sh
./scripts/update-gongnyang-prompt-kit
```

The current upstream revision is `fb5f75f2f6dbaaa649464dc089f573bea4a9ebf1`.
