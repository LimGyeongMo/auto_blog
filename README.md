# Auto Blog Generator

이미지 폴더를 기반으로 네이버 블로그용 Markdown 초안을 자동 생성하는 Python CLI 프로젝트입니다.
기본 템플릿 생성과 OpenAI 기반 이미지 분석 생성을 지원하며, 결과는 Markdown 파일로 저장하거나 네이버 블로그 에디터에 자동 입력할 수 있습니다.

## 빠른 시작

다른 PC나 다른 작업 환경에서도 아래 순서대로 바로 사용할 수 있습니다.

1. 저장소를 클론합니다.
2. Python 3.11+ 환경을 준비합니다.
3. 의존성을 설치합니다.
4. `images` 폴더에 이미지 파일을 넣습니다.
5. 필요하면 `.env`를 설정합니다.
6. 원하는 모드로 실행합니다.

Windows:

```bat
git clone <repo-url>
cd auto_blog
python -m pip install -r requirements.txt
copy .env.example .env
python main.py generate --folder .\images --mode template
```

macOS/Linux:

```bash
git clone <repo-url>
cd auto_blog
python -m pip install -r requirements.txt
cp .env.example .env
python main.py generate --folder ./images --mode template
```

OpenAI 모드까지 사용하려면 `.env`의 `OPENAI_API_KEY`를 실제 값으로 채운 뒤 실행하면 됩니다.

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
8. 제목, 도입부, 본문, 마무리를 조합합니다.
9. 선택에 따라 Markdown 파일로 저장하거나 네이버 블로그 에디터에 자동 입력합니다.

## 파일 구조

- `main.py`: CLI 엔트리 포인트
- `parser.py`: 이미지 파일 수집, 파일명 파싱, 숫자 기준 정렬, 섹션 구조 생성
- `generator.py`: Markdown 블로그 글 생성
- `seo.py`: SEO 키워드 및 기본 문구 생성
- `openai_text.py`: OpenAI 기반 이미지 분석 및 문구 생성
- `naver_uploader.py`: Playwright 기반 네이버 블로그 에디터 자동 입력
- `requirements.txt`: 설치해야 할 Python 패키지 목록
- `images/`: 사용자가 이미지 파일을 넣는 기본 폴더

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

## 설치와 준비

필수:

- Python 3.11 이상
- `pip install -r requirements.txt`

OpenAI 모드 사용 시 추가 필요:

- `.env` 파일 또는 환경 변수 `OPENAI_API_KEY`
- Python 패키지 `openai` (`requirements.txt`에 포함)

네이버 업로드 자동화 사용 시 추가 필요:

- Python 패키지 `playwright` (`requirements.txt`에 포함)
- 크롬 로그인 세션을 저장할 브라우저 프로필 디렉터리
- 네이버 블로그 글쓰기 화면에 직접 로그인할 수 있는 환경

`.env` 설정 방법:

1. `.env.example` 파일을 복사해 `.env` 파일을 만듭니다.
2. `.env`에 API 키를 넣습니다.
3. `.env`는 `.gitignore`에 포함되어 Git에 올라가지 않습니다.
4. 실제 이미지 파일(`.jpg`, `.png` 등)도 `.gitignore`에 포함되어 Git에 올라가지 않습니다.

예시:

```env
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-5.4
```

## 실행 방법

템플릿 모드:

```bash
python main.py generate --folder ./images --mode template
```

자동 모드:

```bash
python main.py generate --folder ./images --mode auto
```

OpenAI 모드:

```bash
python main.py generate --folder ./images --mode openai
```

네이버 블로그 에디터에 자동 입력:

```bash
python main.py publish --folder ./images --mode template
```

OpenAI 기반으로 생성 후 에디터 자동 입력:

```bash
python main.py publish --folder ./images --mode openai
```

짧게 실행하려면 프로젝트 루트에서 아래처럼 입력하면 됩니다.

Windows:

```bat
start_blogging.bat
```

`bash` 환경:

```bash
./start_blogging
```

기본값:

- 이미지 폴더: `.\images`
- CLI 기본 생성 모드: `auto`
- 출력 파일: `blog_post.md`

단축 실행 스크립트 `start_blogging`은 항상 `--mode openai`로 실행합니다. 따라서 `OPENAI_API_KEY` 또는 `.env` 설정이 없으면 실행되지 않습니다.
CLI에서 `python main.py generate ...`를 직접 실행할 때만 기본 모드 `auto`가 적용됩니다.

다른 이미지 폴더를 쓰려면 경로를 함께 넘길 수 있습니다.

```bash
start_blogging .\my_images
```

기본 OpenAI 모델은 `gpt-5.4`이며, 필요하면 `--openai-model`로 변경할 수 있습니다.

출력 파일명을 바꾸려면:

```bash
python main.py generate --folder ./images --output my_post.md
```

자동 입력 시 자주 쓰는 옵션:

```bash
python main.py publish --folder ./images --mode auto --user-data-dir .playwright-profile
```

최종 발행 버튼까지 자동으로 누르려면:

```bash
python main.py publish --folder ./images --mode auto --publish-now
```

- `template`: 규칙 기반 문구만 사용
- `openai`: OpenAI API로 이미지 내용을 분석해 글 작성
- `auto`: OpenAI 사용 가능하면 분석, 아니면 템플릿으로 자동 전환

`publish` 명령 동작 방식:

- 브라우저를 열고 네이버 글쓰기 화면으로 이동합니다.
- 로그인이 안 되어 있으면 사용자가 직접 로그인합니다.
- 제목, 문단, 이미지 업로드를 순서대로 자동 입력합니다.
- 기본값은 초안 작성까지만 수행하고 종료 전 사용자가 검토할 시간을 줍니다.
- `--publish-now`를 주면 마지막 발행 버튼까지 자동으로 시도합니다.

## 출력 형식

출력은 기본적으로 `blog_post.md` 파일에 저장됩니다.

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

현재는 네이버 블로그 초안 생성과 에디터 자동 입력 단계까지 지원합니다.

포함:

- 이미지 폴더 분석
- 번호 기반 정렬
- 섹션 구조 생성
- SEO 키워드 생성
- OpenAI 기반 이미지 설명 생성
- Markdown 글 저장
- 네이버 블로그 에디터 자동 입력
- 이미지 순서대로 업로드

미포함:

- 네이버 블로그 자동 로그인
- 네이버 블로그 발행 후 후속 관리 기능
- 네이버 에디터 구조 변경에 무관한 완전 무인 자동화

## 확장 방향

추후 아래 기능으로 확장 가능합니다.

- 네이버 블로그 자동 작성 및 발행
- 템플릿 기반 스타일 커스터마이징

## 호환성 메모

이전 버전 문서와 스크립트에는 `start_bloging` 오타가 포함되어 있었습니다.
현재는 `start_blogging`이 기본 이름이며, 기존 `start_bloging`과 `start_bloging.bat`도 호환용으로 함께 유지됩니다.

## 공유 시 주의사항

- 저장소에는 이미지 파일이 포함되지 않습니다. 각 환경에서 `images` 폴더에 직접 넣어야 합니다.
- `.env`는 포함되지 않습니다. 각 환경에서 따로 만들어야 합니다.
- OpenAI API 결제 상태와 프로젝트 권한은 사용하는 계정마다 별도입니다.
- 네이버 블로그 자동 입력은 에디터 UI 변경에 따라 선택자 조정이 필요할 수 있습니다.

## 유지보수 원칙

앞으로 로직 변경이나 기능 수정이 생기면 아래 내용을 함께 갱신합니다.

- 프로젝트가 무엇인지
- 현재 어떻게 동작하는지
- 실행 방법
- 새로 추가되거나 변경된 기능
