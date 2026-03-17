from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from generator import RenderedPost, SectionPost


class NaverPublishError(RuntimeError):
    pass


@dataclass(frozen=True)
class NaverPublishConfig:
    user_data_dir: Path
    publish_url: str = "https://blog.naver.com/PostWriteForm.naver"
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

        with sync_playwright() as playwright:
            browser_type = playwright.chromium
            context = self._launch_context(browser_type)
            try:
                page = context.pages[0] if context.pages else context.new_page()
                page.goto(self._config.publish_url, wait_until="domcontentloaded")
                page.bring_to_front()
                self._wait_for_editor(page)
                self._dismiss_optional_dialogs(page)
                title_target = self._locate_title_target(page)
                body_frame = self._locate_body_frame(page)
                self._fill_title(title_target, post.title)
                self._clear_body(body_frame)
                self._append_paragraph(body_frame, post.keyword_line)
                self._append_blank(body_frame)
                self._append_text_block(body_frame, post.intro)
                for section in post.sections:
                    self._append_section(page, body_frame, section)
                self._append_heading(body_frame, post.closing_heading.replace("## ", ""))
                self._append_text_block(body_frame, post.closing)
                if self._config.publish:
                    self._publish(page)
                else:
                    input(
                        "Draft has been populated in the editor. Review it in the browser, "
                        "then press Enter to close automation..."
                    )
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

    def _wait_for_editor(self, page) -> None:
        deadline = time.time() + (self._config.wait_timeout_ms / 1000)
        while time.time() < deadline:
            self._dismiss_optional_dialogs(page)
            try:
                self._locate_title_target(page)
                self._locate_body_frame(page)
                return
            except NaverPublishError:
                time.sleep(1)

        raise NaverPublishError(
            "Could not find the Naver editor. Log in to Naver and leave the post editor open."
        )

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

    def _locate_body_frame(self, page):
        deadline = time.time() + (self._config.wait_timeout_ms / 1000)
        while time.time() < deadline:
            for frame in page.frames:
                try:
                    locator = frame.locator("[contenteditable='true']").last
                    if locator.is_visible(timeout=500):
                        return frame
                except Exception:
                    continue
            time.sleep(1)

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

        title_target.press("Control+A")
        title_target.press("Delete")
        title_target.type(title)

    def _clear_body(self, frame) -> None:
        editor = self._body_editor(frame)
        editor.click()
        editor.press("Control+A")
        editor.press("Delete")

    def _append_section(self, page, frame, section: SectionPost) -> None:
        self._append_heading(frame, section.heading.replace("## ", ""))
        self._append_text_block(frame, section.text)
        for image in section.images:
            self._upload_image(page, frame, image.file_path)
        self._append_blank(frame)

    def _append_heading(self, frame, heading: str) -> None:
        editor = self._body_editor(frame)
        editor.click()
        self._insert_html(
            frame,
            f"<h2>{self._escape_html(heading)}</h2>",
        )

    def _append_text_block(self, frame, text: str) -> None:
        for paragraph in [line.strip() for line in text.splitlines() if line.strip()]:
            self._append_paragraph(frame, paragraph)

    def _append_paragraph(self, frame, text: str) -> None:
        editor = self._body_editor(frame)
        editor.click()
        self._insert_html(frame, f"<p>{self._escape_html(text)}</p>")

    def _append_blank(self, frame) -> None:
        editor = self._body_editor(frame)
        editor.click()
        self._insert_html(frame, "<p><br></p>")

    def _upload_image(self, page, frame, image_path: Path) -> None:
        image_button = self._find_image_button(page, frame)
        image_input = self._find_file_input(page, frame, image_button)
        image_input.set_input_files(str(image_path))
        time.sleep(self._config.upload_wait_seconds)

    def _find_image_button(self, page, frame):
        selectors = [
            "button:has-text('사진')",
            "button:has-text('이미지')",
            "[role='button']:has-text('사진')",
            "[role='button']:has-text('이미지')",
            "button[aria-label*='사진']",
            "button[aria-label*='이미지']",
        ]
        for selector in selectors:
            for container in (frame, page):
                try:
                    locator = container.locator(selector).first
                    if locator.is_visible(timeout=500):
                        return locator
                except Exception:
                    continue

        raise NaverPublishError("Could not find the image upload button in the editor.")

    def _find_file_input(self, page, frame, image_button):
        for container in (frame, page):
            try:
                locator = container.locator("input[type='file']").first
                if locator.count() > 0:
                    return locator
            except Exception:
                continue

        image_button.click()
        deadline = time.time() + 10
        while time.time() < deadline:
            for container in (frame, page):
                try:
                    locator = container.locator("input[type='file']").first
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

    @staticmethod
    def _body_editor(frame):
        editor = frame.locator("[contenteditable='true']").last
        return editor

    def _insert_html(self, frame, html: str) -> None:
        frame.evaluate(
            """
            ([html]) => {
                const selection = window.getSelection();
                if (!selection || selection.rangeCount === 0) {
                    return;
                }

                const range = selection.getRangeAt(0);
                range.deleteContents();
                const wrapper = document.createElement('div');
                wrapper.innerHTML = html;
                const fragment = document.createDocumentFragment();
                let node = null;
                let lastNode = null;
                while ((node = wrapper.firstChild)) {
                    lastNode = fragment.appendChild(node);
                }
                range.insertNode(fragment);
                if (lastNode) {
                    range.setStartAfter(lastNode);
                    range.collapse(true);
                    selection.removeAllRanges();
                    selection.addRange(range);
                }
            }
            """,
            [html],
        )

    @staticmethod
    def _escape_html(text: str) -> str:
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
