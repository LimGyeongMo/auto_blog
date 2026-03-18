from __future__ import annotations

from dataclasses import dataclass

from parser import BlogDocument, ImageFile, Section
from seo import SEOKeywordGenerator, SEOKeywords, TextComposer


@dataclass(frozen=True)
class SectionPost:
    heading: str
    text: str
    images: list[ImageFile]
    image_placement: str = "after"


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
        default_image_placement: str = "after",
        section_image_placements: dict[int, str] | None = None,
    ) -> None:
        self.keyword_generator = keyword_generator
        self.text_composer = text_composer
        self.default_image_placement = default_image_placement
        self.section_image_placements = section_image_placements or {}

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
        images = self._ordered_section_images(section)
        return SectionPost(
            heading="",
            text=self.text_composer.compose_section_text(section, document, keywords),
            images=images,
            image_placement=self.section_image_placements.get(
                section.main_number,
                self.default_image_placement,
            ),
        )

    @staticmethod
    def _ordered_section_images(section: Section) -> list[ImageFile]:
        images: list[ImageFile] = []
        if section.main_image is not None:
            images.append(section.main_image)
        images.extend(sorted(section.sub_images, key=lambda image: image.sub_number or 0))
        return images

    def _render_section(self, section_post: SectionPost) -> list[str]:
        lines = [""]
        if section_post.heading:
            lines.append(section_post.heading)

        if section_post.image_placement == "before":
            lines.extend(self._render_images(section_post.images))
            lines.append(section_post.text)
            lines.append("")
            return lines

        lines.extend([section_post.text, ""])
        lines.extend(self._render_images(section_post.images))
        return lines

    def _render_images(self, images: list[ImageFile]) -> list[str]:
        return [self._render_image(image) for image in images]

    @staticmethod
    def _render_image(image: ImageFile) -> str:
        return f"![{image.alt_text}]({image.original_name})"
