from __future__ import annotations

from dataclasses import dataclass, field

from parser import BlogDocument, Section

CALM_EMOTIONAL_TONE_SAMPLE = (
    "내가 가장 좋아했던 공원이지만 이번에 가지는 않은.\n\n"
    "뭐랄까 2017년에는 집에서 가장 가까운 공원이어서 자주 가다 보니 좋아졌던 것 같기는 하지만, "
    "여기선 늘 현실 현재 미래 등 온갖 고민들이 복합적으로 나를 괴롭힐 때 자주 갔던 곳이라 "
    "행복여행인 이번 신혼여행에서는 왜인지.. 가고 싶지 않아서 오빠에게 가자고 하지 않았다.\n\n"
    "아마 오빠는 내가 가장 자주 갔고 가장 좋아한 공원에 가지 않았다는 사실도 이 포스팅을 봐야 알게 되겠지? 우하하\n\n"
    "여하튼 꼭 들리지 않았더라도 지나가면서 봐도 충분히 반가웠던 공원.\n\n"
    "잘 지냈니\n\n"
    "나는 그 사이 더 성숙하고 더 나은 사람이 된 것 같은데\n\n"
    "나의 사색과 행복을 여기서 비우고 채우고 비우고 채우고 한 덕분이다야"
)


@dataclass(frozen=True)
class SEOKeywords:
    primary: str
    secondary: list[str]

    @property
    def all_keywords(self) -> list[str]:
        return [self.primary, *self.secondary]


@dataclass(frozen=True)
class SEOConfig:
    topic: str = ""
    region: str = ""
    primary_keyword: str = ""
    secondary_keywords: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class StyleConfig:
    tone_sample: str = CALM_EMOTIONAL_TONE_SAMPLE
    sentence_length: str = "short"
    emoji_style: str = "none"


def resolve_style_config(
    concept: str,
    tone_sample: str,
    sentence_length: str,
    emoji_style: str,
) -> StyleConfig:
    default_style = StyleConfig()
    concept_normalized = concept.strip().lower()
    use_calm_emotional = any(token in concept_normalized for token in ("감성", "잔잔"))

    resolved_tone_sample = tone_sample.strip()
    resolved_sentence_length = sentence_length.strip()
    resolved_emoji_style = emoji_style.strip()

    if use_calm_emotional:
        if not resolved_tone_sample:
            resolved_tone_sample = CALM_EMOTIONAL_TONE_SAMPLE
        if not resolved_sentence_length:
            resolved_sentence_length = "short"
        if not resolved_emoji_style:
            resolved_emoji_style = "none"

    return StyleConfig(
        tone_sample=resolved_tone_sample or default_style.tone_sample,
        sentence_length=resolved_sentence_length or default_style.sentence_length,
        emoji_style=resolved_emoji_style or default_style.emoji_style,
    )


class SEOKeywordGenerator:
    def __init__(self, config: SEOConfig | None = None) -> None:
        self._config = config or SEOConfig()

    def generate(self, document: BlogDocument) -> SEOKeywords:
        folder_name = document.folder.name.replace("_", " ").replace("-", " ").strip()
        normalized = " ".join(folder_name.split())
        base_topic = self._build_base_topic(normalized)

        if self._config.primary_keyword.strip():
            primary = self._config.primary_keyword.strip()
        elif base_topic:
            primary = f"{base_topic} 후기"
        else:
            primary = "사진 후기"

        custom_secondary = [keyword.strip() for keyword in self._config.secondary_keywords if keyword.strip()]
        if custom_secondary:
            secondary = custom_secondary[:3]
        elif base_topic:
            secondary = [
                f"{base_topic} 사진 정리",
                f"{base_topic} 블로그 포스팅",
                "네이버 블로그 작성",
            ]
        else:
            secondary = ["사진 정리", "블로그 포스팅", "네이버 블로그 작성"]

        return SEOKeywords(primary=primary, secondary=secondary)

    def _build_base_topic(self, normalized_folder_name: str) -> str:
        parts = [
            self._config.region.strip(),
            self._config.topic.strip(),
        ]
        combined = " ".join(part for part in parts if part).strip()
        if combined:
            return combined
        return normalized_folder_name


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
    def __init__(self, style_config: StyleConfig | None = None) -> None:
        self._style_config = style_config or StyleConfig()

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
        return self._apply_style("\n".join(lines))

    def compose_section_text(
        self, section: Section, document: BlogDocument, keywords: SEOKeywords
    ) -> str:
        total_images = 1 if section.main_image else 0
        total_images += len(section.sub_images)
        detail_hint = "세부 장면까지 함께" if section.sub_images else "핵심 장면 중심으로"

        if self._style_config.sentence_length == "short":
            return (
                f"{section.main_number}번 구간은 {keywords.primary} 포인트가 짧게 보이는 부분입니다. "
                f"이미지 {total_images}장만 따라가도 흐름이 금방 잡힙니다."
            )

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

    def _apply_style(self, text: str) -> str:
        styled = text
        if self._style_config.sentence_length == "short":
            styled = styled.replace("정리해보겠습니다.", "정리해볼게요.")
        if self._style_config.emoji_style == "light":
            styled = styled.replace("참고해보세요.", "참고해보세요 :)")
        return styled
