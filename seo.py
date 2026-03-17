from __future__ import annotations

from dataclasses import dataclass

from parser import BlogDocument, Section


@dataclass(frozen=True)
class SEOKeywords:
    primary: str
    secondary: list[str]

    @property
    def all_keywords(self) -> list[str]:
        return [self.primary, *self.secondary]


class SEOKeywordGenerator:
    def generate(self, document: BlogDocument) -> SEOKeywords:
        folder_name = document.folder.name.replace("_", " ").replace("-", " ").strip()
        normalized = " ".join(folder_name.split())

        if normalized:
            primary = f"{normalized} 후기"
            secondary = [
                f"{normalized} 사진 정리",
                f"{normalized} 블로그 포스팅",
                "네이버 블로그 작성",
            ]
        else:
            primary = "사진 후기"
            secondary = ["사진 정리", "블로그 포스팅", "네이버 블로그 작성"]

        return SEOKeywords(primary=primary, secondary=secondary)


class TextComposer:
    def compose_title(self, document: BlogDocument, keywords: SEOKeywords) -> str:
        raise NotImplementedError

    def compose_intro(self, document: BlogDocument, keywords: SEOKeywords) -> str:
        raise NotImplementedError

    def compose_section_text(
        self, section: Section, document: BlogDocument, keywords: SEOKeywords
    ) -> str:
        raise NotImplementedError

    def compose_closing(self, document: BlogDocument, keywords: SEOKeywords) -> str:
        raise NotImplementedError


class BasicTextComposer(TextComposer):
    def compose_title(self, document: BlogDocument, keywords: SEOKeywords) -> str:
        section_count = len(document.sections)
        return (
            f"{keywords.primary} 사진으로 정리한 {section_count}개 포인트 "
            f"| {keywords.secondary[0]} 가이드"
        )

    def compose_intro(self, document: BlogDocument, keywords: SEOKeywords) -> str:
        lines = [
            f"이번 글에서는 {keywords.primary} 흐름을 이미지 순서대로 차분하게 정리해보겠습니다.",
            f"사진을 하나씩 따라가면 {keywords.secondary[0]}와 {keywords.secondary[1]}에 필요한 구성이 자연스럽게 보이도록 구성했습니다.",
            f"특히 네이버 블로그에 바로 활용할 수 있도록 문장 톤은 부드럽게 유지하고, 핵심 장면은 번호별로 빠르게 확인할 수 있게 정리했습니다.",
            f"처음부터 끝까지 살펴보시면서 {keywords.secondary[2]}에 필요한 포인트를 편하게 참고해보세요.",
        ]
        return "\n".join(lines)

    def compose_section_text(
        self, section: Section, document: BlogDocument, keywords: SEOKeywords
    ) -> str:
        total_images = 1 if section.main_image else 0
        total_images += len(section.sub_images)
        detail_hint = "세부 장면까지 함께" if section.sub_images else "핵심 장면 중심으로"

        return (
            f"{section.main_number}번 구간은 {keywords.primary} 내용을 {detail_hint} 정리한 부분입니다. "
            f"이 구간에서는 총 {total_images}장의 이미지를 기준으로 흐름을 살펴볼 수 있어 "
            f"{keywords.secondary[1]} 구성을 잡을 때도 참고하기 좋습니다."
        )

    def compose_closing(self, document: BlogDocument, keywords: SEOKeywords) -> str:
        return (
            f"지금까지 {keywords.primary} 흐름을 번호 순서대로 정리해보았습니다. "
            f"이미지와 함께 내용을 정리하면 {keywords.secondary[0]} 완성도가 훨씬 높아지고, "
            f"{keywords.secondary[2]}에서도 읽기 편한 글 구성이 가능합니다.\n\n"
            "도움이 되셨다면 공감과 댓글로 의견 남겨주세요. 필요한 주제가 있다면 다음 글에서도 이어서 정리해보겠습니다."
        )
