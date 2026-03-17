from __future__ import annotations

import argparse
import os
from pathlib import Path

from generator import BlogPostGenerator
from openai_text import OpenAIComposerConfig, build_text_composer
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

    return parser


def handle_generate(folder: str, mode: str, openai_model: str, image_detail: str) -> None:
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
    print(markdown)


def main() -> None:
    load_dotenv(Path(".env").resolve())
    args = build_parser().parse_args()

    if args.command == "generate":
        handle_generate(
            folder=args.folder,
            mode=args.mode,
            openai_model=args.openai_model,
            image_detail=args.image_detail,
        )


if __name__ == "__main__":
    main()
