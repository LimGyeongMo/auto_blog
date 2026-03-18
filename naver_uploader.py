from __future__ import annotations

import json
import time
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from dataclasses import dataclass
from pathlib import Path

from generator import RenderedPost, SectionPost


class NaverPublishError(RuntimeError):
    pass


@dataclass(frozen=True)
class NaverPublishConfig:
    user_data_dir: Path
    publish_url: str = "https://blog.naver.com/PostWriteForm.naver"
    blog_id: str = ""
    headless: bool = False
    publish: bool = False
    wait_timeout_ms: int = 120000
    upload_wait_seconds: float = 2.0
    chrome_channel: str = "chrome"


class NaverBlogPublisher:
    def __init__(self, config: NaverPublishConfig) -> None:
        self._config = config

    def publish_post(self, post: RenderedPost) -> None:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise NaverPublishError(
                "The 'playwright' package is not installed. Install dependencies with "
                "'pip install -r requirements.txt'."
            ) from exc

        self._config.user_data_dir.mkdir(parents=True, exist_ok=True)
        print(f"프로필 경로 준비 완료: {self._config.user_data_dir}")

        with sync_playwright() as playwright:
            browser_type = playwright.chromium
            print("브라우저 실행 중...")
            context = self._launch_context(browser_type)
            try:
                page = context.pages[0] if context.pages else context.new_page()
                print("네이버 글쓰기 화면으로 이동 중...")
                page.goto(self._editor_url(), wait_until="domcontentloaded")
                try:
                    page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    pass
                page.bring_to_front()
                print("에디터 로딩 대기 중...")
                self._wait_for_editor(page)
                self._dismiss_optional_dialogs(page)
                title_target = self._locate_title_target(page)
                body_target = self._locate_body_target(page)
                print("제목과 본문 입력 중...")
                self._fill_title(title_target, post.title)
                self._clear_body(page, body_target)
                self._append_paragraph(page, body_target, post.keyword_line)
                self._append_blank(page, body_target)
                self._append_text_block(page, body_target, post.intro)
                for section in post.sections:
                    self._append_section(page, body_target, section)
                self._append_heading(page, body_target, post.closing_heading.replace("## ", ""))
                self._append_text_block(page, body_target, post.closing)
                if self._config.publish:
                    print("최종 발행 버튼 클릭 시도 중...")
                    self._publish(page)
                else:
                    print("초안 입력 완료. 자동화를 종료합니다.")
            finally:
                context.close()

    def _launch_context(self, browser_type):
        launch_kwargs = {
            "user_data_dir": str(self._config.user_data_dir),
            "headless": self._config.headless,
        }
        try:
            return browser_type.launch_persistent_context(
                channel=self._config.chrome_channel,
                **launch_kwargs,
            )
        except Exception:
            return browser_type.launch_persistent_context(**launch_kwargs)

    def _wait_for_editor(self, page):
        deadline = time.time() + (self._config.wait_timeout_ms / 1000)
        prompted_for_login = False
        while time.time() < deadline:
            self._dismiss_optional_dialogs(page)
            try:
                self._locate_title_target(page)
                self._locate_body_target(page)
                return
            except NaverPublishError:
                if not prompted_for_login and self._looks_like_login_or_home(page):
                    prompted_for_login = True
                    print(f"현재 페이지: {page.url}")
                    input(
                        "네이버 로그인 또는 블로그 개설이 필요해 보입니다. "
                        "브라우저에서 로그인/이동을 완료한 뒤 Enter를 누르면 다시 시도합니다..."
                    )
                    try:
                        page.goto(self._editor_url(), wait_until="domcontentloaded")
                        page.bring_to_front()
                    except Exception:
                        pass
                time.sleep(1)

        debug_path = self._write_debug_snapshot(page)
        detail = f"Could not find the Naver editor. Current page: {page.url}"
        if debug_path is not None:
            detail = f"{detail}. Debug saved to: {debug_path}"
        raise NaverPublishError(detail)

    @staticmethod
    def _looks_like_login_or_home(page) -> bool:
        url = page.url.lower()
        return any(
            token in url
            for token in (
                "nid.naver.com",
                "login",
                "myblog",
                "blog.naver.com",
            )
        )

    def _editor_url(self) -> str:
        if not self._config.blog_id:
            return self._config.publish_url

        parsed = urlsplit(self._config.publish_url)
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query["blogId"] = self._config.blog_id
        return urlunsplit(
            (parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment)
        )

    def _write_debug_snapshot(self, page) -> Path | None:
        try:
            debug_dir = Path.cwd() / "debug"
            debug_dir.mkdir(parents=True, exist_ok=True)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            html_path = debug_dir / f"naver_editor_debug_{timestamp}.html"
            json_path = debug_dir / f"naver_editor_debug_{timestamp}.json"

            html_path.write_text(page.content(), encoding="utf-8")

            frame_data = []
            for frame in page.frames:
                try:
                    contenteditable_count = frame.locator("[contenteditable='true']").count()
                except Exception:
                    contenteditable_count = -1
                frame_data.append(
                    {
                        "url": frame.url,
                        "name": frame.name,
                        "contenteditable_count": contenteditable_count,
                    }
                )

            json_path.write_text(
                json.dumps(
                    {
                        "page_url": page.url,
                        "title": page.title(),
                        "frames": frame_data,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            print(f"디버그 HTML 저장: {html_path}")
            print(f"디버그 JSON 저장: {json_path}")
            return json_path
        except Exception:
            return None

    def _dismiss_optional_dialogs(self, page) -> None:
        candidates = [
            "button:has-text('취소')",
            "button:has-text('나중에')",
            "button:has-text('닫기')",
            "button:has-text('확인')",
            "button:has-text('도움말 닫기')",
        ]
        for selector in candidates:
            try:
                locator = page.locator(selector).first
                if locator.is_visible(timeout=500):
                    locator.click(timeout=500)
            except Exception:
                continue

    def _locate_title_target(self, page):
        selectors = [
            ".se-component.se-documentTitle .se-title-text",
            ".se-component.se-documentTitle .se-text-paragraph",
            ".se-component.se-documentTitle .__se_placeholder",
            "textarea[placeholder*='제목']",
            "input[placeholder*='제목']",
            "[contenteditable='true'][placeholder*='제목']",
            "[contenteditable='true'][aria-label*='제목']",
        ]
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if locator.is_visible(timeout=500):
                    return locator
            except Exception:
                continue

        fallback = page.locator("textarea, input[type='text'], [contenteditable='true']")
        try:
            count = fallback.count()
        except Exception:
            count = 0
        for index in range(count):
            candidate = fallback.nth(index)
            try:
                if candidate.is_visible(timeout=250):
                    box = candidate.bounding_box()
                    if box and box["y"] < 350 and box["height"] < 180:
                        return candidate
            except Exception:
                continue

        raise NaverPublishError("Could not find the post title field.")

    def _locate_body_target(self, page):
        selectors = [
            ".se-component[data-a11y-title='본문'] .se-text-paragraph",
            ".se-section-text .se-text-paragraph",
            ".se-module-text .se-text-paragraph",
            ".se-component[data-a11y-title='본문'] .__se-node",
            "[contenteditable='true'][data-placeholder*='내용']",
            "[contenteditable='true'][aria-label*='본문']",
            "[contenteditable='true'][placeholder*='내용']",
            "[contenteditable='true']",
        ]
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if locator.is_visible(timeout=500):
                    return locator
            except Exception:
                continue
        raise NaverPublishError("Could not find the post body editor.")

    @staticmethod
    def _fill_title(title_target, title: str) -> None:
        title_target.click()
        try:
            title_target.fill("")
            title_target.fill(title)
            return
        except Exception:
            pass

        try:
            title_target.press("Control+A")
            title_target.press("Delete")
        except Exception:
            pass

        title_target.press("Control+A")
        title_target.press("Delete")
        title_target.type(title)

    def _clear_body(self, page, body_target) -> None:
        body_target.click()
        page.keyboard.press("Control+A")
        page.keyboard.press("Delete")

    def _append_section(self, page, body_target, section: SectionPost) -> None:
        print(f"섹션 입력 중: {section.heading}")
        self._append_heading(page, body_target, section.heading.replace("## ", ""))
        self._append_text_block(page, body_target, section.text)
        for image in section.images:
            self._upload_image(page, body_target, image.file_path)
        self._append_blank(page, body_target)

    def _append_heading(self, page, body_target, heading: str) -> None:
        self._append_paragraph(page, body_target, heading)

    def _append_text_block(self, page, body_target, text: str) -> None:
        for paragraph in [line.strip() for line in text.splitlines() if line.strip()]:
            self._append_paragraph(page, body_target, paragraph)

    def _append_paragraph(self, page, body_target, text: str) -> None:
        body_target.click()
        page.keyboard.type(text)
        page.keyboard.press("Enter")

    def _append_blank(self, page, body_target) -> None:
        body_target.click()
        page.keyboard.press("Enter")

    def _upload_image(self, page, body_target, image_path: Path) -> None:
        print(f"이미지 업로드 중: {image_path.name}")
        image_button = self._find_image_button(page, body_target)
        image_input = self._find_file_input(page, body_target, image_button)
        image_input.set_input_files(str(image_path))
        time.sleep(self._config.upload_wait_seconds)

    def _find_image_button(self, page, body_target):
        selectors = [
            ".se-image-toolbar-button",
            ".se-insert-menu-button-image",
            "button:has-text('사진')",
            "button:has-text('이미지')",
            "[role='button']:has-text('사진')",
            "[role='button']:has-text('이미지')",
            "button[aria-label*='사진']",
            "button[aria-label*='이미지']",
        ]
        for selector in selectors:
            for candidate_container in (page,):
                try:
                    locator = candidate_container.locator(selector).first
                    if locator.is_visible(timeout=500):
                        return locator
                except Exception:
                    continue

        raise NaverPublishError("Could not find the image upload button in the editor.")

    def _find_file_input(self, page, body_target, image_button):
        for candidate_container in (page,):
            try:
                locator = candidate_container.locator("input[type='file']").first
                if locator.count() > 0:
                    return locator
            except Exception:
                continue

        image_button.click()
        deadline = time.time() + 10
        while time.time() < deadline:
            for candidate_container in (page,):
                try:
                    locator = candidate_container.locator("input[type='file']").first
                    if locator.count() > 0:
                        return locator
                except Exception:
                    continue
            time.sleep(0.5)

        raise NaverPublishError("Could not find the file input for image upload.")

    def _publish(self, page) -> None:
        selectors = [
            "button:has-text('발행')",
            "[role='button']:has-text('발행')",
        ]
        first_button = self._click_first_visible(page, selectors)
        if not first_button:
            raise NaverPublishError("Could not find the publish button.")

        time.sleep(1)
        self._click_first_visible(page, selectors)

    def _click_first_visible(self, page, selectors: list[str]) -> bool:
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if locator.is_visible(timeout=1000):
                    locator.click(timeout=1000)
                    return True
            except Exception:
                continue
        return False
