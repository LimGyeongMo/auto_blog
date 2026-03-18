from __future__ import annotations

import json
import os
from base64 import b64encode
from dataclasses import dataclass
from mimetypes import guess_type
from pathlib import Path
from typing import Any

from parser import BlogDocument, Section
from seo import SEOConfig, SEOKeywords, StyleConfig, TextComposer


@dataclass(frozen=True)
class OpenAIComposerConfig:
    model: str = "gpt-5.4"
    image_detail: str = "auto"
    concept: str = ""
    seo: SEOConfig = SEOConfig()
    style: StyleConfig = StyleConfig()


@dataclass(frozen=True)
class SectionInsight:
    section_number: int
    summary: str
    scene_keywords: list[str]


@dataclass(frozen=True)
class GeneratedPostCopy:
    title: str
    intro: str
    section_texts: dict[int, str]
    closing: str


class OpenAIUnavailableError(RuntimeError):
    pass


class OpenAIRequestError(RuntimeError):
    pass


def build_text_composer(
    mode: str,
    fallback: TextComposer,
    config: OpenAIComposerConfig,
) -> TextComposer:
    if mode == "template":
        return fallback

    try:
        composer = OpenAITextComposer(config=config)
    except OpenAIUnavailableError:
        if mode == "openai":
            raise
        return fallback

    if mode == "auto":
        return SafeTextComposer(primary=composer, fallback=fallback)

    return composer


class SafeTextComposer(TextComposer):
    def __init__(self, primary: TextComposer, fallback: TextComposer) -> None:
        self._primary = primary
        self._fallback = fallback
        self._use_fallback = False

    def compose_title(self, document: BlogDocument, keywords: SEOKeywords) -> str:
        return self._call("compose_title", document, keywords)

    def compose_intro(self, document: BlogDocument, keywords: SEOKeywords) -> str:
        return self._call("compose_intro", document, keywords)

    def compose_section_text(
        self, section: Section, document: BlogDocument, keywords: SEOKeywords
    ) -> str:
        if self._use_fallback:
            return self._fallback.compose_section_text(section, document, keywords)

        try:
            return self._primary.compose_section_text(section, document, keywords)
        except Exception:
            self._use_fallback = True
            return self._fallback.compose_section_text(section, document, keywords)

    def compose_closing(self, document: BlogDocument, keywords: SEOKeywords) -> str:
        return self._call("compose_closing", document, keywords)

    def _call(self, method_name: str, document: BlogDocument, keywords: SEOKeywords) -> str:
        if self._use_fallback:
            return getattr(self._fallback, method_name)(document, keywords)

        try:
            return getattr(self._primary, method_name)(document, keywords)
        except Exception:
            self._use_fallback = True
            return getattr(self._fallback, method_name)(document, keywords)


class OpenAITextComposer(TextComposer):
    def __init__(self, config: OpenAIComposerConfig) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise OpenAIUnavailableError(
                "OPENAI_API_KEY is not set. Use --mode template or configure the API key."
            )

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise OpenAIUnavailableError(
                "The 'openai' package is not installed. Install it with 'pip install openai'."
            ) from exc

        self._client = OpenAI(api_key=api_key)
        self._config = config
        self._cached_document_key: str | None = None
        self._cached_post_copy: GeneratedPostCopy | None = None

    def compose_title(self, document: BlogDocument, keywords: SEOKeywords) -> str:
        return self._ensure_post_copy(document, keywords).title

    def compose_intro(self, document: BlogDocument, keywords: SEOKeywords) -> str:
        return self._ensure_post_copy(document, keywords).intro

    def compose_section_text(
        self, section: Section, document: BlogDocument, keywords: SEOKeywords
    ) -> str:
        post_copy = self._ensure_post_copy(document, keywords)
        return post_copy.section_texts.get(
            section.main_number,
            self._default_section_text(section, keywords),
        )

    def compose_closing(self, document: BlogDocument, keywords: SEOKeywords) -> str:
        return self._ensure_post_copy(document, keywords).closing

    def _ensure_post_copy(
        self,
        document: BlogDocument,
        keywords: SEOKeywords,
    ) -> GeneratedPostCopy:
        document_key = self._build_document_key(document)
        if self._cached_document_key == document_key and self._cached_post_copy is not None:
            return self._cached_post_copy

        section_insights = [self._analyze_section(section) for section in document.sections]
        post_copy = self._generate_post_copy(document, keywords, section_insights)
        self._cached_document_key = document_key
        self._cached_post_copy = post_copy
        return post_copy

    @staticmethod
    def _build_document_key(document: BlogDocument) -> str:
        ordered_names = ",".join(image.original_name for image in document.ordered_images)
        return f"{document.folder.resolve()}::{ordered_names}"

    def _analyze_section(self, section: Section) -> SectionInsight:
        image_paths = []
        if section.main_image is not None:
            image_paths.append(section.main_image.file_path)
        image_paths.extend(image.file_path for image in section.sub_images)

        prompt = (
            "당신은 네이버 블로그 초안 작성을 돕는 이미지 분석가입니다. "
            "입력된 이미지 묶음을 보고 공통 장면과 핵심 포인트를 한국어로 요약하세요. "
            "반드시 JSON만 반환하세요. 형식은 "
            '{"summary":"한두 문장 요약","scene_keywords":["키워드1","키워드2","키워드3"]} 입니다. '
            "브랜드나 대상이 불명확하면 추측하지 말고 일반적인 표현을 사용하세요."
        )

        payload = self._create_multimodal_payload(prompt, image_paths)
        response_text = self._request_text(payload)
        parsed = self._parse_json_object(response_text)

        summary = str(parsed.get("summary", "")).strip()
        keywords = [
            str(keyword).strip()
            for keyword in parsed.get("scene_keywords", [])
            if str(keyword).strip()
        ]
        if not summary:
            summary = f"{section.main_number}번 구간의 이미지를 바탕으로 핵심 장면을 정리한 섹션입니다."

        return SectionInsight(
            section_number=section.main_number,
            summary=summary,
            scene_keywords=keywords[:3],
        )

    def _generate_post_copy(
        self,
        document: BlogDocument,
        keywords: SEOKeywords,
        section_insights: list[SectionInsight],
    ) -> GeneratedPostCopy:
        sections_data = [
            {
                "section_number": insight.section_number,
                "summary": insight.summary,
                "scene_keywords": insight.scene_keywords,
                "image_count": self._section_image_count(document, insight.section_number),
                "image_names_in_order": self._section_image_names(document, insight.section_number),
            }
            for insight in section_insights
        ]

        prompt = (
            "당신은 네이버 블로그 전문 에디터입니다. "
            "아래 정보를 바탕으로 SEO를 고려한 자연스러운 한국어 블로그 문구를 작성하세요. "
            "결과는 반드시 JSON만 반환하세요. 형식은 "
            '{"title":"", "intro":"", "sections":{"1":"", "2":""}, "closing":""} 입니다. '
            "조건: 제목/도입부/본문/마무리에 주요 키워드와 서브 키워드를 자연스럽게 포함하고, "
            f"과도한 반복은 피하며, {self._intro_length_instruction()} "
            f"{self._closing_length_instruction()} "
            "본문 각 섹션 설명은 메인 번호당 반드시 내용이 있는 본문으로 작성하세요. "
            f"{self._section_length_instruction()} "
            "장면 설명만 하지 말고 분위기, 포인트, 짧은 감상이나 팁까지 함께 넣으세요. "
            "사용자가 제공한 컨셉이 있으면 톤과 표현, 분위기에 반드시 반영하세요. "
            "이미지 순서는 절대 바꾸지 말고, 섹션 데이터의 이미지 순서를 기준으로만 설명을 작성하세요. "
            "이미지 번호를 기계적으로 나열하지 말고, 이미지 순서가 의미하는 방문 흐름이나 시선 흐름을 자연스럽게 풀어 쓰세요.\n\n"
            f"폴더명: {document.folder.name}\n"
            f"작성 컨셉: {self._config.concept or '기본'}\n"
            f"말투 예시: {self._config.style.tone_sample}\n"
            f"문장 길이 선호: {self._config.style.sentence_length}\n"
            f"이모지 사용 선호: {self._config.style.emoji_style}\n"
            f"SEO 지역명: {self._config.seo.region or '없음'}\n"
            f"SEO 주제: {self._config.seo.topic or '없음'}\n"
            f"사용자 메인 키워드: {self._config.seo.primary_keyword or '없음'}\n"
            f"사용자 서브 키워드: {', '.join(self._config.seo.secondary_keywords) or '없음'}\n"
            f"주요 키워드: {keywords.primary}\n"
            f"서브 키워드: {', '.join(keywords.secondary)}\n"
            f"섹션 분석 데이터: {json.dumps(sections_data, ensure_ascii=False)}"
        )

        payload = [{"role": "user", "content": [{"type": "input_text", "text": prompt}]}]
        response_text = self._request_text(payload)
        parsed = self._parse_json_object(response_text)

        section_texts_raw = parsed.get("sections", {})
        section_texts = {
            int(section_number): self._normalize_generated_text(str(text))
            for section_number, text in section_texts_raw.items()
            if self._normalize_generated_text(str(text))
        }

        return GeneratedPostCopy(
            title=str(parsed.get("title", "")).strip() or f"{keywords.primary} 이미지 정리",
            intro=self._normalize_generated_text(str(parsed.get("intro", "")))
            or f"이번 글에서는 {keywords.primary} 흐름을 이미지 중심으로 정리해보겠습니다.",
            section_texts=section_texts,
            closing=self._normalize_generated_text(str(parsed.get("closing", "")))
            or "도움이 되셨다면 공감과 댓글로 의견 남겨주세요.",
        )

    def _default_section_text(self, section: Section, keywords: SEOKeywords) -> str:
        image_count = (1 if section.main_image else 0) + len(section.sub_images)
        if self._config.style.sentence_length == "short":
            return (
                f"{section.main_number}번 구간은 {keywords.primary} 흐름이 짧고 또렷하게 보이는 부분입니다. "
                f"이미지 {image_count}장을 따라가면 분위기 변화가 자연스럽게 이어져서 가볍게 보기 좋습니다."
            )

        return (
            f"{section.main_number}번 구간에서는 {keywords.primary} 흐름이 조금 더 또렷하게 보입니다. "
            f"총 {image_count}장의 이미지를 차례대로 보다 보면 분위기 변화와 시선이 자연스럽게 이어져서, "
            f"어떤 포인트를 중심으로 보면 좋은지 금방 감이 오는 구간입니다. "
            f"가볍게 보기에도 좋지만 실제 방문이나 정리용 후기 문장으로 풀기에도 괜찮은 장면들이 이어집니다."
        )

    def _intro_length_instruction(self) -> str:
        if self._config.style.sentence_length == "short":
            return "도입부는 2~3문장으로 짧게 쓰고,"
        if self._config.style.sentence_length == "long":
            return "도입부는 4~5문장으로 충분히 풀어 쓰고,"
        return "도입부는 3~4문장으로 쓰고,"

    def _section_length_instruction(self) -> str:
        if self._config.style.sentence_length == "short":
            return (
                "각 섹션은 1~2개의 아주 짧은 문단으로 쓰고, 문단당 1~2문장 정도로만 정리하세요."
            )
        if self._config.style.sentence_length == "long":
            return (
                "각 섹션은 최소 3문장 이상으로 쓰고, 필요하면 2개의 짧은 문단으로 나눠도 됩니다."
            )
        return "각 섹션은 2~3문장 정도로 간결하게 쓰세요."

    def _closing_length_instruction(self) -> str:
        if self._config.style.sentence_length == "short":
            return "마무리는 2문장 안쪽으로 요약과 CTA를 넣으세요."
        if self._config.style.sentence_length == "long":
            return "마무리에는 요약과 CTA를 충분히 포함하세요."
        return "마무리에는 요약과 CTA를 간결하게 포함하세요."

    def _request_text(self, payload: list[dict[str, Any]]) -> str:
        request_kwargs: dict[str, Any] = {
            "model": self._config.model,
            "input": payload,
        }
        try:
            response = self._client.responses.create(**request_kwargs)
        except Exception as exc:
            raise OpenAIRequestError(self._describe_openai_error(exc)) from exc

        text = getattr(response, "output_text", "")
        if text:
            return text
        raise OpenAIRequestError("OpenAI response did not contain output text.")

    def _create_multimodal_payload(
        self,
        prompt: str,
        image_paths: list[Path],
    ) -> list[dict[str, Any]]:
        content: list[dict[str, Any]] = [{"type": "input_text", "text": prompt}]

        for image_path in image_paths:
            content.append(
                {
                    "type": "input_image",
                    "image_url": self._to_data_url(image_path),
                    "detail": self._config.image_detail,
                }
            )

        return [{"role": "user", "content": content}]

    @staticmethod
    def _section_image_count(document: BlogDocument, section_number: int) -> int:
        for section in document.sections:
            if section.main_number == section_number:
                return (1 if section.main_image else 0) + len(section.sub_images)
        return 0

    @staticmethod
    def _section_image_names(document: BlogDocument, section_number: int) -> list[str]:
        for section in document.sections:
            if section.main_number != section_number:
                continue

            names: list[str] = []
            if section.main_image is not None:
                names.append(section.main_image.original_name)
            names.extend(
                image.original_name
                for image in sorted(section.sub_images, key=lambda image: image.sub_number or 0)
            )
            return names
        return []

    @staticmethod
    def _parse_json_object(raw_text: str) -> dict[str, Any]:
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if len(lines) >= 3:
                cleaned = "\n".join(lines[1:-1]).strip()

        return json.loads(cleaned)

    @staticmethod
    def _normalize_generated_text(text: str) -> str:
        normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
        if not normalized:
            return ""

        paragraphs: list[str] = []
        current_lines: list[str] = []

        for raw_line in normalized.split("\n"):
            line = raw_line.strip()
            if not line:
                if current_lines:
                    paragraphs.append(" ".join(current_lines))
                    current_lines = []
                continue
            current_lines.append(line)

        if current_lines:
            paragraphs.append(" ".join(current_lines))

        return "\n\n".join(paragraphs)

    @staticmethod
    def _to_data_url(image_path: Path) -> str:
        mime_type = guess_type(image_path.name)[0] or "application/octet-stream"
        encoded = b64encode(image_path.read_bytes()).decode("ascii")
        return f"data:{mime_type};base64,{encoded}"

    @staticmethod
    def _describe_openai_error(exc: Exception) -> str:
        error_code = getattr(exc, "code", None)
        status_code = getattr(exc, "status_code", None)
        message = str(exc).strip() or exc.__class__.__name__

        if error_code == "insufficient_quota":
            return (
                "API quota is exhausted. Check your OpenAI plan and billing, "
                "or run with '--mode template'."
            )

        if status_code == 429:
            return "OpenAI request was rate-limited. Wait and try again, or run with '--mode template'."

        if status_code in {401, 403}:
            return "OpenAI authentication failed. Check OPENAI_API_KEY and project permissions."

        return f"OpenAI API request failed: {message}"
