from __future__ import annotations

import json
import socket
import subprocess
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

    @staticmethod
    def _log(message: str) -> None:
        print(f"\n{message}", flush=True)

    def publish_post(self, post: RenderedPost) -> None:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise NaverPublishError(
                "The 'playwright' package is not installed. Install dependencies with "
                "'pip install -r requirements.txt'."
            ) from exc

        self._config.user_data_dir.mkdir(parents=True, exist_ok=True)
        self._log(f"프로필 경로 준비 완료: {self._config.user_data_dir}")

        if self._config.publish:
            with sync_playwright() as playwright:
                browser_type = playwright.chromium
                self._log("브라우저 실행 중...")
                context = self._launch_context(browser_type)
                try:
                    page = context.pages[0] if context.pages else context.new_page()
                    self._fill_post(page, post)
                    self._log("최종 발행 버튼 클릭 시도 중...")
                    self._publish(page)
                finally:
                    context.close()
            return

        playwright = sync_playwright().start()
        try:
            self._log("브라우저 실행 중...")
            browser, context = self._launch_detached_browser(playwright)
            page = context.pages[0] if context.pages else context.new_page()
            self._fill_post(page, post)
            self._log("초안 입력 완료. 브라우저는 열린 상태로 유지하고 Python 프로세스를 종료합니다.")
        finally:
            playwright.stop()

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

    def _launch_detached_browser(self, playwright):
        chrome_path = self._resolve_chrome_path()
        debug_port = self._find_free_port()
        command = [
            str(chrome_path),
            f"--remote-debugging-port={debug_port}",
            f"--user-data-dir={self._config.user_data_dir}",
            "--new-window",
            self._editor_url(),
        ]
        creationflags = 0
        if hasattr(subprocess, "DETACHED_PROCESS"):
            creationflags |= subprocess.DETACHED_PROCESS
        if hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
            creationflags |= subprocess.CREATE_NEW_PROCESS_GROUP

        subprocess.Popen(
            command,
            creationflags=creationflags,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
        )
        browser = self._connect_over_cdp(playwright, debug_port)
        contexts = browser.contexts
        if not contexts:
            raise NaverPublishError("Detached Chrome started, but no browser context was available.")
        return browser, contexts[0]

    def _fill_post(self, page, post: RenderedPost) -> None:
        self._log("네이버 글쓰기 화면으로 이동 중...")
        page.goto(self._editor_url(), wait_until="domcontentloaded")
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass
        page.bring_to_front()
        self._log("에디터 로딩 대기 중...")
        self._wait_for_editor(page)
        self._dismiss_optional_dialogs(page)
        title_target = self._locate_title_target(page)
        body_target = self._locate_body_target(page)
        self._log("제목과 본문 입력 중...")
        self._fill_title(title_target, post.title)
        self._clear_body(page, body_target)
        self._append_paragraph(page, body_target, post.keyword_line)
        self._append_blank(page, body_target)
        self._append_text_block(page, body_target, post.intro)
        for section in post.sections:
            self._append_section(page, body_target, section)
        self._append_heading(page, body_target, post.closing_heading.replace("## ", ""))
        self._append_text_block(page, body_target, post.closing)

    @staticmethod
    def _find_free_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            return int(sock.getsockname()[1])

    def _connect_over_cdp(self, playwright, port: int):
        endpoint = f"http://127.0.0.1:{port}"
        deadline = time.time() + 20
        last_error: Exception | None = None
        while time.time() < deadline:
            try:
                return playwright.chromium.connect_over_cdp(endpoint)
            except Exception as exc:
                last_error = exc
                time.sleep(0.5)
        raise NaverPublishError(f"Could not connect to detached Chrome over CDP: {last_error}")

    def _resolve_chrome_path(self) -> Path:
        candidates = [
            Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
            Path("C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"),
            Path.home() / "AppData/Local/Google/Chrome/Application/chrome.exe",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        raise NaverPublishError("Could not find Chrome executable for detached browser mode.")

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
                    self._log(f"현재 페이지: {page.url}")
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
            self._log(f"디버그 HTML 저장: {html_path}")
            self._log(f"디버그 JSON 저장: {json_path}")
            return json_path
        except Exception:
            return None

    def _dismiss_optional_dialogs(self, page) -> None:
        priority_candidates = [
            "[data-name='se-popup-alert se-popup-alert-confirm'] .se-popup-button-confirm",
            "[data-name='se-popup-alert se-popup-alert-confirm'] button:has-text('확인')",
        ]
        for selector in priority_candidates:
            try:
                locator = page.locator(selector).first
                if locator.count() > 0 and locator.is_visible(timeout=500):
                    locator.click(timeout=500)
                    time.sleep(0.3)
                    return
            except Exception:
                continue

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
                if locator.count() > 0 and locator.is_visible(timeout=500):
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
                if locator.count() > 0 and locator.is_visible(timeout=500):
                    return locator
            except Exception:
                continue

        # Some Naver states keep the editor mounted but covered by a restore popup.
        # If the node exists in the DOM, allow later focus/click recovery to proceed.
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if locator.count() > 0:
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
        self._focus_body_target(page, body_target)
        page.keyboard.press("Control+A")
        page.keyboard.press("Delete")

    def _append_section(self, page, body_target, section: SectionPost) -> None:
        ordered_image_names = ", ".join(image.original_name for image in section.images) or "없음"
        section_label = section.heading or "본문 섹션"
        self._log(f"섹션 입력 중: {section_label} | 이미지 순서: {ordered_image_names}")
        if section.heading:
            self._append_heading(page, body_target, section.heading.replace("## ", ""))
        if section.image_placement == "before":
            self._upload_images(page, body_target, section.images)
            self._append_text_block(page, body_target, section.text)
            self._append_blank(page, body_target)
            return

        self._append_text_block(page, body_target, section.text)
        self._upload_images(page, body_target, section.images)
        self._append_blank(page, body_target)

    def _append_heading(self, page, body_target, heading: str) -> None:
        self._append_paragraph(page, body_target, heading)

    def _append_text_block(self, page, body_target, text: str) -> None:
        for paragraph in [line.strip() for line in text.splitlines() if line.strip()]:
            self._append_paragraph(page, body_target, paragraph)

    def _append_paragraph(self, page, body_target, text: str) -> None:
        self._focus_body_target(page, body_target)
        self._ensure_plain_text_mode(page)
        self._reset_inline_format(page)
        page.keyboard.type(text)
        page.keyboard.press("Enter")

    def _append_blank(self, page, body_target) -> None:
        self._focus_body_target(page, body_target)
        page.keyboard.press("Enter")

    def _upload_images(self, page, body_target, images: list) -> None:
        if not images:
            return

        image_names = ", ".join(image.original_name for image in images)
        upload_order = list(images)
        upload_names = ", ".join(image.original_name for image in upload_order)
        self._log(f"이미지 업로드 중: 화면 순서={image_names} | 실제 업로드 순서={upload_names}")

        # Keep the original parsed order as-is so section images stay main -> sub.
        for image in upload_order:
            self._upload_single_image(page, body_target, image.file_path)

    def _upload_single_image(self, page, body_target, image_path: Path) -> None:
        image_button = self._find_image_button(page, body_target)
        image_input = self._find_file_input(page, body_target, image_button)
        if image_input is not None:
            image_input.set_input_files(str(image_path))
        else:
            self._upload_via_file_chooser(page, image_button, [str(image_path)])
        time.sleep(self._config.upload_wait_seconds)
        self._close_image_type_popup(page)

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
                locator = candidate_container.locator("input[type='file']").last
                if locator.count() > 0:
                    return locator
            except Exception:
                continue

        try:
            image_button.click()
        except Exception:
            return None

        deadline = time.time() + 10
        while time.time() < deadline:
            for candidate_container in (page,):
                try:
                    locator = candidate_container.locator("input[type='file']").last
                    if locator.count() > 0:
                        return locator
                except Exception:
                    continue
            time.sleep(0.5)

        return None

    def _upload_via_file_chooser(self, page, image_button, file_paths: list[str]) -> None:
        try:
            with page.expect_file_chooser(timeout=10000) as chooser_info:
                image_button.click()
            chooser = chooser_info.value
            chooser.set_files(file_paths)
            return
        except Exception as exc:
            raise NaverPublishError(
                "Could not find the file input for image upload."
            ) from exc

    def _current_body_target(self, page, body_target):
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
                locator = page.locator(selector)
                count = locator.count()
            except Exception:
                continue

            for index in range(count - 1, -1, -1):
                candidate = locator.nth(index)
                try:
                    if candidate.is_visible(timeout=250):
                        return candidate
                except Exception:
                    continue

        return body_target

    def _focus_body_target(self, page, body_target) -> None:
        self._dismiss_optional_dialogs(page)
        self._close_image_type_popup(page)
        active_body_target = self._current_body_target(page, body_target)
        try:
            active_body_target.click(timeout=3000)
            return
        except Exception:
            pass

        self._close_image_type_popup(page)
        active_body_target = self._current_body_target(page, body_target)
        active_body_target.click(force=True, timeout=3000)

    @staticmethod
    def _reset_inline_format(page) -> None:
        shortcuts = [
            "Control+Space",
            "Control+\\",
        ]
        for shortcut in shortcuts:
            try:
                page.keyboard.press(shortcut)
                time.sleep(0.05)
            except Exception:
                continue

    def _ensure_plain_text_mode(self, page) -> None:
        selectors = [
            ".se-strikethrough-toolbar-button",
            "button[data-name='strikethrough']",
            "button[aria-label*='취소선']",
        ]
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if locator.count() == 0:
                    continue

                pressed = (locator.get_attribute("aria-pressed") or "").lower()
                class_name = locator.get_attribute("class") or ""
                if pressed == "true" or "se-is-selected" in class_name or "active" in class_name:
                    locator.click(timeout=500)
                    time.sleep(0.1)
                    return
            except Exception:
                continue

    def _close_image_type_popup(self, page) -> None:
        popup_root = "[data-name='se-popup-image-type']"
        dismiss_selectors = [
            f"{popup_root} button:has-text('닫기')",
            f"{popup_root} .se-popup-close",
            f"{popup_root} .se-popup-dim",
            f"{popup_root} .se-popup-dim-transparent",
        ]

        for selector in dismiss_selectors:
            try:
                locator = page.locator(selector).first
                if locator.count() > 0 and locator.is_visible(timeout=300):
                    locator.click(timeout=500, force=True)
                    time.sleep(0.2)
                    return
            except Exception:
                continue

        try:
            page.keyboard.press("Escape")
            time.sleep(0.2)
        except Exception:
            pass

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

    @staticmethod
    def _wait_until_browser_closed(context) -> None:
        while True:
            try:
                if len(context.pages) == 0:
                    return
                time.sleep(1)
            except Exception:
                return
