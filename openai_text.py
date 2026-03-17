from __future__ import annotations

import json
import os
from base64 import b64encode
from dataclasses import dataclass
from mimetypes import guess_type
from pathlib import Path
from typing import Any

from parser import BlogDocument, Section
from seo import SEOKeywords, TextComposer


@dataclass(frozen=True)
class OpenAIComposerConfig:
    model: str = "gpt-5.4"
    image_detail: str = "auto"


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
            f"{section.main_number}번 이미지를 중심으로 핵심 내용을 정리했습니다.",
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
            }
            for insight in section_insights
        ]

        prompt = (
            "당신은 네이버 블로그 전문 에디터입니다. "
            "아래 정보를 바탕으로 SEO를 고려한 자연스러운 한국어 블로그 문구를 작성하세요. "
            "결과는 반드시 JSON만 반환하세요. 형식은 "
            '{"title":"", "intro":"", "sections":{"1":"", "2":""}, "closing":""} 입니다. '
            "조건: 제목/도입부/본문/마무리에 주요 키워드와 서브 키워드를 자연스럽게 포함하고, "
            "과도한 반복은 피하며, 도입부는 3~5문장, 마무리에는 요약과 CTA를 포함하세요. "
            "본문 각 섹션 설명은 메인 번호당 1개 문단만 작성하세요.\n\n"
            f"폴더명: {document.folder.name}\n"
            f"주요 키워드: {keywords.primary}\n"
            f"서브 키워드: {', '.join(keywords.secondary)}\n"
            f"섹션 분석 데이터: {json.dumps(sections_data, ensure_ascii=False)}"
        )

        payload = [{"role": "user", "content": [{"type": "input_text", "text": prompt}]}]
        response_text = self._request_text(payload)
        parsed = self._parse_json_object(response_text)

        section_texts_raw = parsed.get("sections", {})
        section_texts = {
            int(section_number): str(text).strip()
            for section_number, text in section_texts_raw.items()
            if str(text).strip()
        }

        return GeneratedPostCopy(
            title=str(parsed.get("title", "")).strip() or f"{keywords.primary} 이미지 정리",
            intro=str(parsed.get("intro", "")).strip()
            or f"이번 글에서는 {keywords.primary} 흐름을 이미지 중심으로 정리해보겠습니다.",
            section_texts=section_texts,
            closing=str(parsed.get("closing", "")).strip()
            or "도움이 되셨다면 공감과 댓글로 의견 남겨주세요.",
        )

    def _request_text(self, payload: list[dict[str, Any]]) -> str:
        request_kwargs: dict[str, Any] = {
            "model": self._config.model,
            "input": payload,
        }
        response = self._client.responses.create(**request_kwargs)
        text = getattr(response, "output_text", "")
        if text:
            return text
        raise RuntimeError("OpenAI response did not contain output text.")

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
    def _parse_json_object(raw_text: str) -> dict[str, Any]:
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if len(lines) >= 3:
                cleaned = "\n".join(lines[1:-1]).strip()

        return json.loads(cleaned)

    @staticmethod
    def _to_data_url(image_path: Path) -> str:
        mime_type = guess_type(image_path.name)[0] or "application/octet-stream"
        encoded = b64encode(image_path.read_bytes()).decode("ascii")
        return f"data:{mime_type};base64,{encoded}"
