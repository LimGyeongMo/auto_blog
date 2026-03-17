# Auto Blog Generator

이미지 폴더를 기반으로 네이버 블로그용 Markdown 초안을 자동 생성하는 Python CLI 프로젝트입니다.
기본 템플릿 생성과 OpenAI 기반 이미지 분석 생성 둘 다 지원합니다.

## 프로젝트 목적

- 번호 규칙이 있는 이미지 파일을 순서대로 정리합니다.
- 네이버 블로그 스타일에 맞는 글 구조를 자동 생성합니다.
- SEO 키워드를 포함한 제목, 도입부, 본문, 마무리를 만듭니다.
- 추후 GPT API나 네이버 자동 업로드 기능으로 확장할 수 있도록 구조를 분리합니다.

## 현재 동작 방식

이 프로젝트는 아래 순서로 동작합니다.

1. 사용자가 이미지 폴더 경로를 입력합니다.
2. 프로그램이 폴더 내 이미지 파일명을 읽습니다.
3. `1`, `2-1`, `2-2`, `2-10` 같은 형식을 파싱합니다.
4. 메인 번호와 서브 번호를 숫자 기준으로 정렬합니다.
5. 메인 번호별로 섹션을 구성합니다.
6. SEO 키워드를 생성합니다.
7. 선택한 모드에 따라 문구를 생성합니다.
8. 제목, 도입부, 본문, 마무리를 조합해 Markdown 글을 출력합니다.

## 파일 구조

- `main.py`: CLI 엔트리 포인트
- `parser.py`: 이미지 파일 수집, 파일명 파싱, 숫자 기준 정렬, 섹션 구조 생성
- `generator.py`: Markdown 블로그 글 생성
- `seo.py`: SEO 키워드 및 기본 문구 생성
- `openai_text.py`: OpenAI 기반 이미지 분석 및 문구 생성

## 지원 파일명 규칙

예시:

- `1.jpg`
- `2-1.jpg`
- `2-2.jpg`
- `2-10.jpg`
- `3.jpg`

정렬 예시:

- `1`
- `2-1`
- `2-2`
- `2-10`
- `3`

즉, 문자열 정렬이 아니라 숫자 정렬 방식으로 처리합니다.

## 실행 방법

```bash
python main.py generate --folder ./images
```

OpenAI 기반 이미지 분석을 사용하려면:

```bash
python main.py generate --folder ./images --mode openai
```

기본 OpenAI 모델은 `gpt-5.4`이며, 필요하면 `--openai-model`로 변경할 수 있습니다.

자동 모드:

```bash
python main.py generate --folder ./images --mode auto
```

- `template`: 규칙 기반 문구만 사용
- `openai`: OpenAI API로 이미지 내용을 분석해 글 작성
- `auto`: OpenAI 사용 가능하면 분석, 아니면 템플릿으로 자동 전환

## OpenAI 사용 조건

OpenAI 모드를 사용하려면 아래가 필요합니다.

- `.env` 파일 또는 환경 변수 `OPENAI_API_KEY`
- Python 패키지 `openai`

예시:

```bash
pip install openai
```

`.env` 설정 방법:

1. `.env.example` 파일을 복사해 `.env` 파일을 만듭니다.
2. `.env`에 API 키를 넣습니다.
3. `.env`는 `.gitignore`에 포함되어 있으므로 Git에 올라가지 않습니다.

예시:

```env
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-5.4
```

그 다음 아래처럼 실행하면 됩니다.

```bash
python main.py generate --folder ./images --mode openai
```

## 출력 형식

출력은 터미널에 Markdown 형태로 생성됩니다.

예시:

```md
# SEO 제목

도입부...

## 1
설명...
![1](1.jpg)

## 2
설명...
![2-1](2-1.jpg)
![2-2](2-2.jpg)

## 마무리
마무리...
```

## 현재 범위

현재는 네이버 블로그에 올릴 글 초안을 생성하는 단계입니다.

포함:

- 이미지 폴더 분석
- 번호 기반 정렬
- 섹션 구조 생성
- SEO 키워드 생성
- OpenAI 기반 이미지 설명 생성
- Markdown 글 출력

미포함:

- 네이버 블로그 자동 로그인
- 네이버 블로그 자동 업로드
- 이미지 자동 업로드

## 확장 방향

추후 아래 기능으로 확장 가능합니다.

- Markdown 파일 저장
- 네이버 블로그 자동 작성 및 발행
- 템플릿 기반 스타일 커스터마이징

## 유지보수 원칙

앞으로 로직 변경이나 기능 수정이 생기면 아래 내용을 함께 갱신합니다.

- 프로젝트가 무엇인지
- 현재 어떻게 동작하는지
- 실행 방법
- 새로 추가되거나 변경된 기능
