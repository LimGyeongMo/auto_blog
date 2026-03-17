from __future__ import annotations

from parser import BlogDocument, ImageFile, Section
from seo import SEOKeywordGenerator, SEOKeywords, TextComposer


class BlogPostGenerator:
    def __init__(
        self,
        keyword_generator: SEOKeywordGenerator,
        text_composer: TextComposer,
    ) -> None:
        self.keyword_generator = keyword_generator
        self.text_composer = text_composer

    def generate(self, document: BlogDocument) -> str:
        keywords = self.keyword_generator.generate(document)
        lines: list[str] = []

        title = self.text_composer.compose_title(document, keywords)
        intro = self.text_composer.compose_intro(document, keywords)
        closing = self.text_composer.compose_closing(document, keywords)

        lines.append(f"# {title}")
        lines.append("")
        lines.append(self._render_keyword_line(keywords))
        lines.append("")
        lines.append(intro)

        for section in document.sections:
            lines.extend(self._render_section(section, document, keywords))

        lines.append("")
        lines.append("## 마무리")
        lines.append(closing)

        return "\n".join(lines).strip() + "\n"

    def _render_keyword_line(self, keywords: SEOKeywords) -> str:
        secondary = ", ".join(keywords.secondary)
        return f"> 주요 키워드: {keywords.primary} | 서브 키워드: {secondary}"

    def _render_section(
        self,
        section: Section,
        document: BlogDocument,
        keywords: SEOKeywords,
    ) -> list[str]:
        lines = ["", f"## {section.main_number}"]
        lines.append(self.text_composer.compose_section_text(section, document, keywords))
        lines.append("")

        if section.main_image is not None:
            lines.append(self._render_image(section.main_image))

        for sub_image in section.sub_images:
            lines.append(self._render_image(sub_image))

        return lines

    @staticmethod
    def _render_image(image: ImageFile) -> str:
        return f"![{image.alt_text}]({image.original_name})"
