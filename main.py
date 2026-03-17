from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from generator import BlogPostGenerator
from openai_text import (
    OpenAIComposerConfig,
    OpenAIRequestError,
    OpenAIUnavailableError,
    build_text_composer,
)
from parser import ImageFolderParser
from seo import BasicTextComposer, SEOKeywordGenerator


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

    return parser


def handle_generate(
    folder: str,
    mode: str,
    openai_model: str,
    image_detail: str,
    output: str,
) -> None:
    folder_path = Path(folder).expanduser().resolve()
    parser = ImageFolderParser()
    document = parser.parse_folder(folder_path)

    keyword_generator = SEOKeywordGenerator()
    text_composer = build_text_composer(
        mode=mode,
        fallback=BasicTextComposer(),
        config=OpenAIComposerConfig(
            model=openai_model,
            image_detail=image_detail,
        ),
    )
    generator = BlogPostGenerator(
        keyword_generator=keyword_generator,
        text_composer=text_composer,
    )

    markdown = generator.generate(document)
    output_path = Path(output).expanduser()
    if not output_path.is_absolute():
        output_path = Path.cwd() / output_path
    output_path.write_text(markdown, encoding="utf-8")

    print(f"Markdown saved to: {output_path}")


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
            )
    except OpenAIUnavailableError as exc:
        print(f"OpenAI mode is unavailable: {exc}", file=sys.stderr)
        sys.exit(2)
    except OpenAIRequestError as exc:
        print(f"OpenAI request failed: {exc}", file=sys.stderr)
        sys.exit(2)
    except (FileNotFoundError, NotADirectoryError, ValueError) as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
