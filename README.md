# Auto Blog Generator

이미지 폴더를 기반으로 네이버 블로그용 Markdown 초안을 자동 생성하는 Python CLI 프로젝트입니다.
기본 템플릿 생성과 OpenAI 기반 이미지 분석 생성을 지원하며, 결과는 Markdown 파일로 저장하거나 네이버 블로그 에디터에 자동으로 초안 입력할 수 있습니다.

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
네이버 자동 입력까지 사용하려면 `NAVER_BLOG_ID`도 함께 준비하면 편합니다.

## 새 기기에서 처음 시작하기

아무 설정도 없는 새 PC나 새 작업 환경에서는 아래 순서대로 진행하면 됩니다.

1. Git을 설치하고 저장소를 클론합니다.
2. Python 3.11 이상을 설치합니다.
3. 프로젝트 루트에서 `pip install -r requirements.txt`를 실행합니다.
4. `.env.example`를 복사해 `.env`를 만들고 `OPENAI_API_KEY`를 입력합니다.
5. 이미지 파일을 `images` 폴더에 넣습니다.
6. Markdown 초안만 필요하면 `python main.py generate --folder ./images --mode auto`를 실행합니다.
7. 네이버 블로그 자동 입력까지 필요하면 `python main.py publish --folder ./images --mode openai --blog-id <blog_id>`를 실행합니다.
8. `publish`를 처음 실행한 기기에서는 네이버 로그인이 필요할 수 있습니다.
9. 로그인 이후에는 브라우저 세션이 `.playwright-profile` 폴더에 저장되어 다음 실행부터 재사용됩니다.

처음부터 네이버 자동 입력까지 바로 써야 한다면 아래 항목도 함께 확인합니다.

- Chrome이 설치되어 있으면 기본적으로 그 브라우저를 우선 사용합니다.
- 브라우저 실행이 되지 않으면 `python -m playwright install chromium`로 Playwright 브라우저를 한 번 설치합니다.
- 새 기기에서는 기존 `.playwright-profile`이 없어도 괜찮습니다. 실행 중 필요할 때 자동으로 생성됩니다.
- 단, 로그인 상태까지 자동 복원되지는 않으므로 새 기기에서는 보통 한 번 직접 로그인해야 합니다.

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
10. 단축 실행 스크립트 사용 시 블로그 컨셉, 네이버 블로그 아이디, SEO 관련 질문, 스타일 관련 질문을 먼저 입력받습니다.

## 파일 구조

- `main.py`: CLI 엔트리 포인트
- `parser.py`: 이미지 파일 수집, 파일명 파싱, 숫자 기준 정렬, 섹션 구조 생성
- `generator.py`: Markdown 블로그 글 생성
- `openai_text.py`: OpenAI 기반 이미지 분석 및 문구 생성
- `seo.py`: SEO 키워드 생성과 사용자 SEO 입력 반영
- `naver_uploader.py`: Playwright 기반 네이버 블로그 에디터 자동 입력
- `start_blogging.ps1`: Windows 단축 실행 시 컨셉, 블로그 아이디 입력을 받고 `publish`를 호출
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
각 섹션 내부에서도 메인 이미지가 먼저, 서브 이미지는 `1`, `2`, `3` 순서대로 유지합니다.

## 설치와 준비

필수:

- Python 3.11 이상
- `pip install -r requirements.txt`

OpenAI 모드 사용 시 추가 필요:

- `.env` 파일 또는 환경 변수 `OPENAI_API_KEY`
- 선택 사항: `.env` 파일 또는 환경 변수 `NAVER_BLOG_ID`
- Python 패키지 `openai` (`requirements.txt`에 포함)

네이버 업로드 자동화 사용 시 추가 필요:

- Python 패키지 `playwright` (`requirements.txt`에 포함)
- 설치된 Chrome 브라우저 권장, 또는 `python -m playwright install chromium`
- 크롬 로그인 세션을 저장할 브라우저 프로필 디렉터리
- 네이버 블로그 글쓰기 화면에 직접 로그인할 수 있는 환경

`.env` 설정 방법:

1. `.env.example` 파일을 복사해 `.env` 파일을 만듭니다.
2. `.env`에 API 키를 넣습니다.
3. `.env`는 `.gitignore`에 포함되어 Git에 올라가지 않습니다.
4. 실제 이미지 파일(`.jpg`, `.png` 등)도 `.gitignore`에 포함되어 Git에 올라가지 않습니다.

`.playwright-profile` 관련 메모:

- 이 폴더는 `publish` 실행 시 브라우저 프로필 저장용으로 사용됩니다.
- 폴더가 없어도 실행 중 자동으로 새로 만들어질 수 있습니다.
- 새 기기에서는 로그인 세션이 없으므로 네이버 로그인을 한 번 다시 해야 할 수 있습니다.
- 로그인 쿠키와 세션 정보가 남을 수 있으니 저장소에 커밋하거나 외부에 공유하지 않는 편이 안전합니다.

예시:

```env
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-5.4
NAVER_BLOG_ID=your_naver_blog_id_here
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

컨셉을 함께 전달:

```bash
python main.py generate --folder ./images --mode openai --concept "감성 후기"
```

SEO 입력을 함께 전달:

```bash
python main.py generate --folder ./images --mode openai --seo-region "성수" --seo-topic "카페" --seo-primary-keyword "성수 카페 후기" --seo-secondary-keywords "성수 카페 추천,성수 카페 사진,서울 카페"
```

스타일 입력까지 함께 전달:

```bash
python main.py generate --folder ./images --mode openai --tone-sample "이번에 다녀온 곳인데요 ㅋㅋㅋ 생각보다 너무 좋더라구요" --sentence-length short --emoji-style light --image-placement after --section-image-placement "1:before,2:after"
```

네이버 블로그 에디터에 자동 입력:

```bash
python main.py publish --folder ./images --mode template
```

OpenAI 기반으로 생성 후 에디터 자동 입력:

```bash
python main.py publish --folder ./images --mode openai
```

블로그 아이디와 컨셉까지 함께 전달:

```bash
python main.py publish --folder ./images --mode openai --blog-id myblogid --concept "감성 후기"
```

SEO 입력까지 함께 전달:

```bash
python main.py publish --folder ./images --mode openai --blog-id myblogid --concept "감성 후기" --seo-region "성수" --seo-topic "카페" --seo-primary-keyword "성수 카페 후기" --seo-secondary-keywords "성수 카페 추천,성수 데이트,서울 카페"
```

말투와 이미지 위치까지 함께 전달:

```bash
python main.py publish --folder ./images --mode openai --blog-id myblogid --tone-sample "저는 본가가 제주도라 잠시 다녀왔는데요 ㅋㅋㅋ" --sentence-length short --emoji-style light --image-placement after --section-image-placement "1:before,2:after"
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

단축 실행 스크립트 `start_blogging`과 `start_bloging.bat`은 현재 항상 `publish --mode openai`로 실행합니다.
실행 시 아래 순서로 진행합니다.

1. 블로그 컨셉 입력
2. 네이버 블로그 아이디 입력
3. SEO 지역명 입력
4. SEO 주제 입력
5. 메인 키워드 입력
6. 서브 키워드 입력
7. 말투 예시 입력
8. 문장 길이 입력
9. 이모지 사용 여부 입력
10. 이미지 기본 위치 입력
11. 섹션별 이미지 위치 입력
12. OpenAI 글 생성
13. 네이버 블로그 글쓰기 화면 열기
14. 제목, 본문, 사진 초안 입력
15. 초안 입력 완료 후 자동 종료

따라서 `OPENAI_API_KEY` 또는 `.env` 설정이 없으면 실행되지 않습니다.
CLI에서 `python main.py generate ...`를 직접 실행할 때만 Markdown 저장용 생성 흐름을 따로 사용할 수 있습니다.

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
python main.py publish --folder ./images --mode auto --blog-id myblogid --user-data-dir .playwright-profile
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
- `blogId`가 있으면 글쓰기 URL에 함께 붙여 이동합니다.
- 로그인이 안 되어 있으면 사용자가 직접 로그인합니다.
- 사용자 입력 SEO 정보가 있으면 제목과 키워드 생성에 우선 반영합니다.
- 사용자 입력 말투 예시, 문장 길이, 이모지 사용 여부를 OpenAI 프롬프트에 반영합니다.
- 기본 말투는 잔잔한 감성 후기 문체로 설정되어 있습니다.
- 컨셉에 `감성` 또는 `잔잔`이 들어가면, 말투 예시를 비워둔 경우에도 그 감성 문체와 짧은 문장 길이를 자동 적용합니다.
- `sentence-length`가 `short`면 도입부와 섹션 문장을 더 짧게 줄여, 예시처럼 1~2문장 중심으로 작성하도록 유도합니다.
- 이미지 위치 설정이 있으면 섹션별 텍스트 앞 또는 뒤에 이미지를 배치합니다.
- 이미지 순서는 항상 원본 파일명의 숫자 순서를 유지하며, OpenAI도 그 순서를 바꾸지 않도록 제한합니다.
- 네이버 업로드도 파서가 정리한 원본 이미지 순서를 그대로 따릅니다. 예를 들어 `20.jpg -> 20-1.jpg` 순서면 화면에서도 같은 순서로 유지되도록 처리합니다.
- 숫자만 있는 섹션 제목은 본문에 넣지 않고, OpenAI가 넣은 단일 줄바꿈은 같은 문단으로 정리해 중간 문장이 어색하게 끊기지 않게 처리합니다.
- 본문 입력 직전 문자 서식을 한 번 초기화해서, 취소선 같은 inline 서식이 다음 문장에 끌려오지 않게 보정합니다.
- 취소선 버튼이 활성화된 상태로 남아 있으면 입력 전에 자동으로 해제합니다.
- 이미지 업로드 뒤에 뜨는 네이버 레이아웃 팝업은 자동으로 닫고 본문 입력 포커스를 다시 맞춥니다.
- 네이버의 `작성 중인 글이 있습니다` 복구 팝업이 뜨면 우선 확인 처리한 뒤 에디터 탐색을 다시 시도합니다.
- 본문 입력은 항상 현재 마지막 문단을 다시 찾아 이어 쓰도록 처리해서, 뒤 섹션이 위로 끼어드는 현상을 줄입니다.
- 실행 로그는 스피너와 섞이지 않도록 새 줄에 따로 출력하며, 이미지 업로드 시 `화면 순서`와 `실제 업로드 순서`를 함께 보여줍니다.
- 제목, 문단, 이미지 업로드를 순서대로 자동 입력합니다.
- 진행 중 콘솔에 단계 메시지와 스피너를 출력합니다.
- 기본값은 초안 작성까지만 수행하고 입력 완료 후 자동 종료합니다.
- 초안 작성 모드에서는 브라우저를 자동으로 닫지 않고, 사용자가 직접 닫을 때까지 유지합니다.
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
- 컨셉 기반 문체 반영
- SEO 지역명, 주제, 메인 키워드, 서브 키워드 입력 반영
- 말투 예시, 문장 길이, 이모지 사용 반영
- 섹션별 이미지 위치 반영
- Markdown 글 저장
- 네이버 블로그 에디터 자동 입력
- 이미지 순서대로 업로드
- 네이버 블로그 아이디 기반 글쓰기 URL 진입
- 실행 중 단계별 진행 메시지 출력

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
Windows 환경에서는 내부적으로 `start_blogging.ps1`을 사용해 한글 입력 프롬프트와 실행 인자를 처리합니다.

## 공유 시 주의사항

- 저장소에는 이미지 파일이 포함되지 않습니다. 각 환경에서 `images` 폴더에 직접 넣어야 합니다.
- `.env`는 포함되지 않습니다. 각 환경에서 따로 만들어야 합니다.
- OpenAI API 결제 상태와 프로젝트 권한은 사용하는 계정마다 별도입니다.
- 네이버 블로그 자동 입력은 에디터 UI 변경에 따라 선택자 조정이 필요할 수 있습니다.
- `.playwright-profile`에 로그인 세션이 저장될 수 있으므로 공유 시 주의합니다.

## 현재 상태 메모

- `generate`는 Markdown 초안을 파일로 저장합니다.
- `publish`는 네이버 글쓰기 화면을 열어 제목, 문단, 이미지를 자동 입력합니다.
- `publish`는 `--blog-id` 또는 `NAVER_BLOG_ID`를 사용하면 더 안정적으로 글쓰기 화면에 진입합니다.
- 단축 실행 스크립트는 현재 `publish` 중심 흐름입니다.
- 이미지가 `images/` 바로 아래가 아니라 하위 폴더 하나 안에 들어 있어도 자동으로 탐색해 사용합니다.
- OpenAI 섹션 본문은 전체를 한 번에 만들지 않고, 섹션별로 개별 생성해서 구간이 서로 섞이지 않도록 보정합니다.
- OpenAI 이미지 입력은 `jpg`, `jpeg`, `png`, `gif`, `webp`를 직접 사용하고, `heic`는 변환 지원 패키지가 있을 때 JPEG로 변환해 처리합니다.
- 초안 입력 모드에서는 브라우저를 분리 실행한 뒤 초안 작성이 끝나면 Python만 종료하고 브라우저는 유지합니다.
- 기본 구현은 완료됐지만, 네이버 에디터 DOM 변경 시 선택자 보정 테스트는 계속 필요할 수 있습니다.
- 이어서 볼 때 핵심 파일은 `README.md`, `main.py`, `naver_uploader.py` 입니다.

## 다음 작업 체크리스트

- 집 환경에서 `python main.py publish --folder ./images --mode template --blog-id <blog_id> --user-data-dir .playwright-profile` 실행
- 네이버 로그인 후 제목 입력, 본문 입력, 이미지 업로드가 정상 동작하는지 확인
- 실패 시 `naver_uploader.py`의 제목 영역, 본문 에디터, 이미지 버튼 선택자 보정
- `start_blogging` 입력 프롬프트와 실제 사용자 흐름이 계속 맞는지 확인
- 필요하면 `--publish-now` 최종 발행 단계도 실사용 기준으로 검증

## 유지보수 원칙

앞으로 로직 변경이나 기능 수정이 생기면 아래 내용을 함께 갱신합니다.

- 프로젝트가 무엇인지
- 현재 어떻게 동작하는지
- 실행 방법
- 새로 추가되거나 변경된 기능
- 수정사항 및 변경사항은 매번 `README.md`에 반드시 함께 반영
- 코드 변경 커밋 전에는 `README.md` 반영 여부를 먼저 확인합니다.
- `README.md` 반영이 빠진 상태로 기능 커밋을 남기지 않습니다.
- 동작 방식, 실행 방법, 옵션, 예외 처리, 출력 흐름이 바뀌면 관련 섹션을 같은 작업에서 함께 수정합니다.

## 커밋 규칙

이 저장소의 기본 커밋 메시지 형식은 아래처럼 맞춥니다.

```text
[GMLIM_YYMMDD] Update : 변경 내용
```

예시:

- `[GMLIM_260321] Update : 이미지 처리, OpenAI 섹션 생성, 초안 브라우저 유지 흐름 보정`
- `[GMLIM_260318] Docs : 새 기기 초기 설정 및 Playwright 프로필 안내 정리`

커밋 작성 기준:

- 기능 수정, 동작 변경, 버그 수정은 기본적으로 `Update`를 사용합니다.
- 문서 수정 중심 작업은 `Docs`를 사용합니다.
- 날짜는 커밋 시점 기준 `YYMMDD` 형식으로 맞춥니다.
- 메시지는 실제 변경사항이 바로 보이도록 한국어로 구체적으로 적습니다.
- 여러 작업을 한 번에 커밋할 때도 핵심 변경 2~4개가 드러나게 요약합니다.
