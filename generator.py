from __future__ import annotations

from dataclasses import dataclass

from parser import BlogDocument, ImageFile, Section
from seo import SEOKeywordGenerator, SEOKeywords, TextComposer


@dataclass(frozen=True)
class SectionPost:
    heading: str
    text: str
    images: list[ImageFile]


@dataclass(frozen=True)
class RenderedPost:
    title: str
    keyword_line: str
    intro: str
    sections: list[SectionPost]
    closing_heading: str
    closing: str
    markdown: str


class BlogPostGenerator:
    def __init__(
        self,
        keyword_generator: SEOKeywordGenerator,
        text_composer: TextComposer,
    ) -> None:
        self.keyword_generator = keyword_generator
        self.text_composer = text_composer

    def generate(self, document: BlogDocument) -> str:
        return self.render(document).markdown

    def render(self, document: BlogDocument) -> RenderedPost:
        keywords = self.keyword_generator.generate(document)
        lines: list[str] = []

        title = self.text_composer.compose_title(document, keywords)
        intro = self.text_composer.compose_intro(document, keywords)
        closing = self.text_composer.compose_closing(document, keywords)
        section_posts = [
            self._build_section_post(section, document, keywords) for section in document.sections
        ]
        keyword_line = self._render_keyword_line(keywords)
        closing_heading = "## 마무리"

        lines.append(f"# {title}")
        lines.append("")
        lines.append(keyword_line)
        lines.append("")
        lines.append(intro)

        for section_post in section_posts:
            lines.extend(self._render_section(section_post))

        lines.append("")
        lines.append(closing_heading)
        lines.append(closing)

        markdown = "\n".join(lines).strip() + "\n"
        return RenderedPost(
            title=title,
            keyword_line=keyword_line,
            intro=intro,
            sections=section_posts,
            closing_heading=closing_heading,
            closing=closing,
            markdown=markdown,
        )

    def _render_keyword_line(self, keywords: SEOKeywords) -> str:
        secondary = ", ".join(keywords.secondary)
        return f"> 주요 키워드: {keywords.primary} | 서브 키워드: {secondary}"

    def _build_section_post(
        self,
        section: Section,
        document: BlogDocument,
        keywords: SEOKeywords,
    ) -> SectionPost:
        images: list[ImageFile] = []
        if section.main_image is not None:
            images.append(section.main_image)
        images.extend(section.sub_images)
        return SectionPost(
            heading=f"## {section.main_number}",
            text=self.text_composer.compose_section_text(section, document, keywords),
            images=images,
        )

    def _render_section(self, section_post: SectionPost) -> list[str]:
        lines = ["", section_post.heading, section_post.text, ""]

        for image in section_post.images:
            lines.append(self._render_image(image))

        return lines

    @staticmethod
    def _render_image(image: ImageFile) -> str:
        return f"![{image.alt_text}]({image.original_name})"
