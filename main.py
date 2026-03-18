from __future__ import annotations

import argparse
import os
import sys
import threading
import time
from contextlib import contextmanager
from pathlib import Path

from generator import BlogPostGenerator
from naver_uploader import NaverBlogPublisher, NaverPublishConfig, NaverPublishError
from openai_text import (
    OpenAIComposerConfig,
    OpenAIRequestError,
    OpenAIUnavailableError,
    build_text_composer,
)
from parser import ImageFolderParser
from seo import BasicTextComposer, SEOKeywordGenerator


class ConsoleSpinner:
    def __init__(self, message: str) -> None:
        self._message = message
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def __enter__(self) -> "ConsoleSpinner":
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join()
        sys.stdout.write("\r" + (" " * 120) + "\r")
        sys.stdout.flush()

    def _run(self) -> None:
        frames = ["|", "/", "-", "\\"]
        index = 0
        while not self._stop_event.is_set():
            sys.stdout.write(f"\r{frames[index % len(frames)]} {self._message}")
            sys.stdout.flush()
            index += 1
            time.sleep(0.12)


@contextmanager
def spinner(message: str):
    with ConsoleSpinner(message):
        yield


def load_dotenv(dotenv_path: Path) -> None:
    if not dotenv_path.exists() or not dotenv_path.is_file():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a Naver blog markdown post from an image folder."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate_parser = subparsers.add_parser(
        "generate", help="Generate a markdown blog post from images."
    )
    generate_parser.add_argument(
        "--folder",
        required=True,
        help="Path to the folder containing image files.",
    )
    generate_parser.add_argument(
        "--mode",
        choices=("auto", "template", "openai"),
        default="auto",
        help="Text generation mode. 'auto' uses OpenAI when available, otherwise falls back to templates.",
    )
    generate_parser.add_argument(
        "--openai-model",
        default=os.getenv("OPENAI_MODEL", "gpt-5.4"),
        help="OpenAI model name used for image-aware generation.",
    )
    generate_parser.add_argument(
        "--image-detail",
        choices=("low", "high", "auto"),
        default="auto",
        help="Detail level for image analysis requests.",
    )
    generate_parser.add_argument(
        "--output",
        default="blog_post.md",
        help="Output markdown file path.",
    )
    generate_parser.add_argument(
        "--concept",
        default="",
        help="Optional writing concept or tone to guide generation.",
    )

    publish_parser = subparsers.add_parser(
        "publish", help="Generate a post and populate the Naver blog editor."
    )
    publish_parser.add_argument(
        "--folder",
        required=True,
        help="Path to the folder containing image files.",
    )
    publish_parser.add_argument(
        "--mode",
        choices=("auto", "template", "openai"),
        default="auto",
        help="Text generation mode. 'auto' uses OpenAI when available, otherwise falls back to templates.",
    )
    publish_parser.add_argument(
        "--openai-model",
        default=os.getenv("OPENAI_MODEL", "gpt-5.4"),
        help="OpenAI model name used for image-aware generation.",
    )
    publish_parser.add_argument(
        "--image-detail",
        choices=("low", "high", "auto"),
        default="auto",
        help="Detail level for image analysis requests.",
    )
    publish_parser.add_argument(
        "--publish-url",
        default="https://blog.naver.com/PostWriteForm.naver",
        help="Naver blog editor URL.",
    )
    publish_parser.add_argument(
        "--blog-id",
        default=os.getenv("NAVER_BLOG_ID", ""),
        help="Naver blog ID used for the editor URL.",
    )
    publish_parser.add_argument(
        "--user-data-dir",
        default=".playwright-profile",
        help="Browser profile directory used to keep the login session.",
    )
    publish_parser.add_argument(
        "--headless",
        action="store_true",
        help="Run the browser in headless mode.",
    )
    publish_parser.add_argument(
        "--publish-now",
        action="store_true",
        help="Click the final publish button after filling the editor.",
    )
    publish_parser.add_argument(
        "--upload-wait",
        type=float,
        default=2.0,
        help="Seconds to wait after each image upload.",
    )
    publish_parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=120,
        help="Seconds to wait for the editor to become ready.",
    )
    publish_parser.add_argument(
        "--concept",
        default="",
        help="Optional writing concept or tone to guide generation.",
    )

    return parser


def handle_generate(
    folder: str,
    mode: str,
    openai_model: str,
    image_detail: str,
    output: str,
    concept: str,
) -> None:
    folder_path = Path(folder).expanduser().resolve()
    print(f"[1/3] 이미지 폴더 확인: {folder_path}")
    parser = ImageFolderParser()
    document = parser.parse_folder(folder_path)
    print(f"[2/3] 글 생성 준비: 이미지 {len(document.ordered_images)}장, 섹션 {len(document.sections)}개")
    generator = build_generator(
        mode=mode,
        openai_model=openai_model,
        image_detail=image_detail,
        concept=concept,
    )

    with spinner("블로그 글 생성 중..."):
        markdown = generator.generate(document)
    output_path = Path(output).expanduser()
    if not output_path.is_absolute():
        output_path = Path.cwd() / output_path
    output_path.write_text(markdown, encoding="utf-8")

    print("[3/3] Markdown 저장 완료")
    print(f"Markdown saved to: {output_path}")


def build_generator(
    mode: str,
    openai_model: str,
    image_detail: str,
    concept: str,
) -> BlogPostGenerator:
    keyword_generator = SEOKeywordGenerator()
    text_composer = build_text_composer(
        mode=mode,
        fallback=BasicTextComposer(),
        config=OpenAIComposerConfig(
            model=openai_model,
            image_detail=image_detail,
            concept=concept.strip(),
        ),
    )
    return BlogPostGenerator(
        keyword_generator=keyword_generator,
        text_composer=text_composer,
    )


def handle_publish(
    folder: str,
    mode: str,
    openai_model: str,
    image_detail: str,
    publish_url: str,
    blog_id: str,
    user_data_dir: str,
    headless: bool,
    publish_now: bool,
    upload_wait: float,
    timeout_seconds: int,
    concept: str,
) -> None:
    folder_path = Path(folder).expanduser().resolve()
    print(f"[1/4] 이미지 폴더 확인: {folder_path}")
    parser = ImageFolderParser()
    document = parser.parse_folder(folder_path)
    print(f"[2/4] 글 생성 준비: 이미지 {len(document.ordered_images)}장, 섹션 {len(document.sections)}개")
    generator = build_generator(
        mode=mode,
        openai_model=openai_model,
        image_detail=image_detail,
        concept=concept,
    )
    with spinner("OpenAI로 글 생성 중..."):
        rendered = generator.render(document)
    print("[3/4] 글 생성 완료, 네이버 에디터 연결 시작")
    publisher = NaverBlogPublisher(
        NaverPublishConfig(
            user_data_dir=Path(user_data_dir).expanduser().resolve(),
            publish_url=publish_url,
            blog_id=blog_id.strip(),
            headless=headless,
            publish=publish_now,
            upload_wait_seconds=upload_wait,
            wait_timeout_ms=timeout_seconds * 1000,
        )
    )
    with spinner("네이버 블로그 에디터 작업 중..."):
        publisher.publish_post(rendered)
    print("[4/4] 네이버 블로그 입력 완료")


def main() -> None:
    load_dotenv(Path(".env").resolve())
    args = build_parser().parse_args()

    try:
        if args.command == "generate":
            handle_generate(
                folder=args.folder,
                mode=args.mode,
                openai_model=args.openai_model,
                image_detail=args.image_detail,
                output=args.output,
                concept=args.concept,
            )
        if args.command == "publish":
            handle_publish(
                folder=args.folder,
                mode=args.mode,
                openai_model=args.openai_model,
                image_detail=args.image_detail,
                publish_url=args.publish_url,
                blog_id=args.blog_id,
                user_data_dir=args.user_data_dir,
                headless=args.headless,
                publish_now=args.publish_now,
                upload_wait=args.upload_wait,
                timeout_seconds=args.timeout_seconds,
                concept=args.concept,
            )
    except OpenAIUnavailableError as exc:
        print(f"OpenAI mode is unavailable: {exc}", file=sys.stderr)
        sys.exit(2)
    except OpenAIRequestError as exc:
        print(f"OpenAI request failed: {exc}", file=sys.stderr)
        sys.exit(2)
    except NaverPublishError as exc:
        print(f"Naver publish failed: {exc}", file=sys.stderr)
        sys.exit(2)
    except (FileNotFoundError, NotADirectoryError, ValueError) as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
