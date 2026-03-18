from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
FILENAME_PATTERN = re.compile(r"^(?P<main>\d+)(?:-(?P<sub>\d+))?$")


@dataclass(frozen=True)
class ImageFile:
    original_name: str
    file_path: Path
    main_number: int
    sub_number: int | None

    @property
    def alt_text(self) -> str:
        stem = Path(self.original_name).stem
        return stem


@dataclass
class Section:
    main_number: int
    main_image: ImageFile | None = None
    sub_images: list[ImageFile] = field(default_factory=list)


@dataclass
class BlogDocument:
    folder: Path
    sections: list[Section]
    ordered_images: list[ImageFile]


class ImageFolderParser:
    def parse_folder(self, folder: Path) -> BlogDocument:
        if not folder.exists():
            raise FileNotFoundError(f"Folder not found: {folder}")
        if not folder.is_dir():
            raise NotADirectoryError(f"Not a directory: {folder}")

        images = self._collect_images(folder.iterdir())
        if not images:
            raise ValueError(f"No supported image files found in: {folder}")

        ordered_images = sorted(images, key=self._sort_key)
        sections = self._build_sections(ordered_images)
        return BlogDocument(folder=folder, sections=sections, ordered_images=ordered_images)

    def _collect_images(self, paths: Iterable[Path]) -> list[ImageFile]:
        images: list[ImageFile] = []

        for path in paths:
            if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
                continue

            match = FILENAME_PATTERN.match(path.stem)
            if not match:
                continue

            main_number = int(match.group("main"))
            sub_number_raw = match.group("sub")
            sub_number = int(sub_number_raw) if sub_number_raw is not None else None
            images.append(
                ImageFile(
                    original_name=path.name,
                    file_path=path.resolve(),
                    main_number=main_number,
                    sub_number=sub_number,
                )
            )

        return images

    @staticmethod
    def _sort_key(image: ImageFile) -> tuple[int, int, int]:
        sub_rank = 0 if image.sub_number is None else 1
        sub_value = image.sub_number if image.sub_number is not None else 0
        return (image.main_number, sub_rank, sub_value)

    def _build_sections(self, ordered_images: list[ImageFile]) -> list[Section]:
        section_map: dict[int, Section] = {}

        for image in ordered_images:
            section = section_map.setdefault(image.main_number, Section(main_number=image.main_number))
            if image.sub_number is None:
                section.main_image = image
            else:
                section.sub_images.append(image)

        for section in section_map.values():
            section.sub_images.sort(key=lambda image: image.sub_number or 0)

        return [section_map[number] for number in sorted(section_map)]
