"""Referia config dialect detection and in-memory normalisation (CIP-000F).

Dialect generations:

* **v0** — proto ``_config.yml`` shapes (report only; not normalised)
* **v1** — convenience keys: ``allocation``, ``scores``, ``scorer``, …
* **v2** — canonical lynguine keys: ``input``, ``output``, ``review``, …

``detect_config_dialect`` is pure (no I/O). ``normalise_referia_config``
mutates *data* in place and returns it, matching the historical behaviour
of ``Interface.__init__``.
"""

from __future__ import annotations

import copy
import warnings
from dataclasses import dataclass, field
from typing import Any

# Highest dialect generation this package understands.
SUPPORTED_CONFIG_VERSION = 2

V1_TOP_LEVEL_MARKERS = (
    "allocation",
    "additional",
    "scores",
    "scorer",
    "global_consts",
    "globals",
)

V2_TOP_LEVEL_MARKERS = (
    "input",
    "output",
    "review",
    "constants",
    "parameters",
)

# Same-slot pairs that must not both appear.
_SLOT_CONFLICTS = (
    ("allocation", "input"),
    ("scores", "output"),
    ("scorer", "review"),
    ("global_consts", "constants"),
    ("globals", "parameters"),
)


@dataclass
class DialectReport:
    """Result of inspecting a loaded ``_referia.yml`` dict."""

    version_declared: int | None
    version_inferred: int
    markers: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    needs_normalise: bool = False
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "version_declared": self.version_declared,
            "version_inferred": self.version_inferred,
            "markers": list(self.markers),
            "conflicts": list(self.conflicts),
            "needs_normalise": self.needs_normalise,
            "notes": list(self.notes),
        }


def _extract_mapping_columns(data: dict) -> tuple[dict, list]:
    """Extract and remove ``mapping`` / ``columns`` from a data-spec dict."""
    mapping: dict = {}
    columns: list = []
    if "mapping" in data:
        mapping = data["mapping"].copy()
        del data["mapping"]
    if "columns" in data:
        columns = data["columns"].copy()
        del data["columns"]
    return mapping, columns


def _has_converters(obj: Any) -> bool:
    """Return True if any nested dict uses a ``converters`` key."""
    if isinstance(obj, dict):
        if "converters" in obj:
            return True
        return any(_has_converters(v) for v in obj.values())
    if isinstance(obj, list):
        return any(_has_converters(v) for v in obj)
    return False


def _rewrite_converters(obj: Any) -> bool:
    """Rename ``converters`` → ``dtypes`` recursively. Return True if changed."""
    changed = False
    if isinstance(obj, dict):
        if "converters" in obj:
            if "dtypes" in obj:
                raise ValueError(
                    'Cannot have both "converters" and "dtypes" on the same data spec.'
                )
            obj["dtypes"] = obj.pop("converters")
            changed = True
        for v in obj.values():
            if _rewrite_converters(v):
                changed = True
    elif isinstance(obj, list):
        for item in obj:
            if _rewrite_converters(item):
                changed = True
    return changed


def _looks_like_proto_v0(data: dict) -> bool:
    """Heuristic for June-2021 proto configs (not normalised)."""
    if not isinstance(data, dict):
        return False
    if "datadirectory" in data:
        return True
    allocation = data.get("allocation")
    if isinstance(allocation, str):
        return True
    return False


def detect_config_dialect(data: dict | None) -> DialectReport:
    """Classify a loaded referia config dict without mutating it.

    :param data: Parsed YAML mapping (or ``None`` / empty).
    :return: :class:`DialectReport`
    """
    if not data:
        return DialectReport(
            version_declared=None,
            version_inferred=2,
            notes=["empty or missing config; treating as v2"],
        )

    notes: list[str] = []
    markers: list[str] = []
    conflicts: list[str] = []

    declared_raw = data.get("referia_config_version")
    version_declared: int | None
    if declared_raw is None:
        version_declared = None
    else:
        try:
            version_declared = int(declared_raw)
        except (TypeError, ValueError):
            version_declared = None
            notes.append(
                f"unparseable referia_config_version: {declared_raw!r}"
            )

    if _looks_like_proto_v0(data):
        if "datadirectory" in data:
            markers.append("datadirectory")
        if isinstance(data.get("allocation"), str):
            markers.append("allocation(string)")
        return DialectReport(
            version_declared=version_declared,
            version_inferred=0,
            markers=markers,
            conflicts=conflicts,
            needs_normalise=False,
            notes=notes
            + ["proto v0 shape; not normalised by referia"],
        )

    for key in V1_TOP_LEVEL_MARKERS:
        if key in data:
            markers.append(key)

    for key in V2_TOP_LEVEL_MARKERS:
        if key in data and key not in markers:
            # Record v2 presence only for reporting when mixed/interesting
            pass

    for old, new in _SLOT_CONFLICTS:
        if old in data and new in data:
            conflicts.append(f"{old}+{new}")

    has_converters = _has_converters(data)
    if has_converters:
        markers.append("converters")
        notes.append("data spec uses converters (will rewrite to dtypes)")

    has_v1 = any(k in data for k in V1_TOP_LEVEL_MARKERS) or has_converters
    has_v2_slot = any(k in data for k in ("input", "output", "review"))

    if has_v1:
        version_inferred = 1
    elif has_v2_slot or any(k in data for k in V2_TOP_LEVEL_MARKERS):
        version_inferred = 2
    else:
        # Viewer-only or metadata-only files: treat as current canonical.
        version_inferred = 2
        notes.append("no dialect markers; treating as v2")

    needs_normalise = has_v1

    if version_declared is not None and version_declared > SUPPORTED_CONFIG_VERSION:
        notes.append(
            f"declared version {version_declared} is newer than "
            f"supported {SUPPORTED_CONFIG_VERSION}"
        )

    return DialectReport(
        version_declared=version_declared,
        version_inferred=version_inferred,
        markers=markers,
        conflicts=conflicts,
        needs_normalise=needs_normalise,
        notes=notes,
    )


def normalise_referia_config(
    data: dict,
    *,
    directory: str | None = None,
    user_file: str | None = None,
) -> dict:
    """Rewrite v1 convenience keys to lynguine form **in place**.

    Does **not** expand ``CriterionComment*`` composites or templates; those
    remain runtime-only steps in ``Interface``.

    :param data: Config mapping (mutated).
    :param directory: Optional config directory (for deprecation messages).
    :param user_file: Optional config filename (for deprecation messages).
    :return: The same *data* dict after normalisation.
    """
    if not data:
        return data

    report = detect_config_dialect(data)
    if report.version_inferred == 0:
        return data
    if report.conflicts:
        # Preserve historical behaviour: raise with the same messages as
        # the individual rewrite branches below.
        pass

    if "allocation" in data:
        allocation = data["allocation"]
        if not isinstance(allocation, list):
            allocation = [allocation]
        index = None
        columns: list = []
        mapping: dict = {}
        for i, item in enumerate(allocation):
            if "index" in item:
                if index is None:
                    index = item["index"]
                elif index != item["index"]:
                    raise ValueError(
                        'All "allocation" items must have the same "index".'
                    )
                del item["index"]

                item_mapping, item_columns = _extract_mapping_columns(item)

                for column in item_columns:
                    if column not in columns:
                        columns.append(column)
                for column in item_mapping:
                    if column not in mapping:
                        mapping[column] = item_mapping[column]
                    else:
                        if mapping[column] != item_mapping[column]:
                            raise ValueError(
                                f'"mapping" for column "{column}" must be '
                                'the same for all "allocation" items.'
                            )
            else:
                if "index" in item:
                    index = item["index"]
                    del item["index"]
            allocation[i] = item

        if "input" not in data:
            data["input"] = {
                "type": "hstack",
                "index": index,
                "mapping": mapping,
                "specifications": [
                    {
                        "type": "vstack",
                        "specifications": allocation,
                    }
                ],
            }
        else:
            raise ValueError(
                '"allocation" is not allowed when "input" is present.'
            )

        if "mapping" in data["input"]:
            data["input"]["mapping"].update(mapping)
        else:
            data["input"]["mapping"] = mapping
        if "columns" in data["input"]:
            data["input"]["columns"] += columns
        else:
            data["input"]["columns"] = columns
        del data["allocation"]

    if "additional" in data:
        additional = data["additional"]
        mapping, columns = _extract_mapping_columns(additional)
        if "mapping" in additional:
            del additional["mapping"]
        if "columns" in additional:
            del additional["columns"]
        if not isinstance(additional, list):
            additional = [additional]
        if "input" not in data:
            data["input"] = {
                "type": "hstack",
                "specifications": additional,
            }
        else:
            data["input"]["specifications"] += additional

        if "mapping" in data["input"]:
            data["input"]["mapping"].update(mapping)
        else:
            data["input"]["mapping"] = mapping
        if "columns" in data["input"]:
            data["input"]["columns"] += columns
        else:
            data["input"]["columns"] = columns
        del data["additional"]

    if "global_consts" in data:
        constants = data["global_consts"]
        if isinstance(constants, list):
            const_index = None
            for constant in constants:
                if "index" in constant:
                    if const_index is None:
                        const_index = constant["index"]
                    elif const_index != constant["index"]:
                        raise ValueError(
                            'All "global_consts" items must have the same "index".'
                        )
                    del constant["index"]
            stacked = {"type": "stack", "specifications": constants}
            if const_index is not None:
                stacked["index"] = const_index
            data["constants"] = stacked
        else:
            data["constants"] = constants
        del data["global_consts"]

    if "globals" in data:
        parameters = data["globals"]
        if isinstance(parameters, list):
            index = None
            for i, parameter in enumerate(parameters):
                if "index" in parameter:
                    if i == 0:
                        index = parameter["index"]
                    elif index != parameter["index"]:
                        raise ValueError(
                            'All "globals" items must have the same "index".'
                        )
                    del parameter["index"]
            data["parameters"] = {
                "type": "hstack",
                "index": index,
                "specifications": parameters,
            }
        else:
            data["parameters"] = parameters
        del data["globals"]

    if "scores" in data:
        if "output" not in data:
            data["output"] = data["scores"]
            del data["scores"]
        else:
            raise ValueError(
                'Cannot have both "scores" and "output" entries in referia.'
            )

    if "scorer" in data:
        if "review" not in data:
            data["review"] = data["scorer"]
            del data["scorer"]
            path_hint = ""
            if directory is not None and user_file is not None:
                import os

                path_hint = f' "{os.path.join(directory, user_file)}"'
            warnmsg = (
                'The "scorer" entry in referia is deprecated, please update '
                f"the file{path_hint}."
            )
            warnings.warn(warnmsg, DeprecationWarning)
        else:
            raise ValueError(
                'Cannot have both "scorer" and "review" entries in referia.'
            )

    _rewrite_converters(data)
    return data



def effective_config_version(data: dict | None) -> int:
    """Declared ``referia_config_version`` if present, else inferred dialect.

    Used for policy defaults (e.g. ``strict_columns``) that should follow the
    living dialect generation rather than only an explicit stamp.
    Proto v0 is treated as generation 0.
    """
    report = detect_config_dialect(data)
    if report.version_declared is not None:
        return int(report.version_declared)
    return int(report.version_inferred)


def inferred_stamp_version(data: dict | None) -> int | None:
    """Version integer to write for stamp-only migrate, or ``None`` to skip.

    Proto v0 files return ``None`` (do not stamp).
    """
    report = detect_config_dialect(data)
    if report.version_inferred == 0:
        return None
    if report.version_declared is not None:
        return None
    return report.version_inferred


def stamp_version_text(text: str, version: int) -> str:
    """Surgically insert ``referia_config_version`` into YAML text.

    Preserves comments and key order by inserting a single line after any
    leading comment/blank block (or at the top of the document). Does not
    rewrite the rest of the file.
    """
    if _text_has_version_key(text):
        return text

    line = f"referia_config_version: {int(version)}\n"
    lines = text.splitlines(keepends=True)
    if not lines:
        return line

    insert_at = 0
    # Skip UTF-8 BOM if present on first line
    start = 0
    if lines and lines[0].startswith("\ufeff"):
        # Keep BOM on first line; insert after comment block still
        pass

    i = start
    while i < len(lines):
        stripped = lines[i].lstrip("\ufeff").strip()
        if stripped == "" or stripped.startswith("#"):
            i += 1
            continue
        # Skip YAML document start marker
        if stripped == "---":
            i += 1
            insert_at = i
            # continue through following comments
            while i < len(lines):
                s2 = lines[i].strip()
                if s2 == "" or s2.startswith("#"):
                    i += 1
                    continue
                break
            insert_at = i
            break
        insert_at = i
        break
    else:
        insert_at = len(lines)

    lines.insert(insert_at, line)
    return "".join(lines)


def _text_has_version_key(text: str) -> bool:
    """True if a top-level ``referia_config_version`` key appears in text."""
    for raw in text.splitlines():
        line = raw.lstrip("\ufeff")
        if line.startswith(" ") or line.startswith("\t"):
            continue
        stripped = line.strip()
        if stripped.startswith("#") or stripped == "" or stripped == "---":
            continue
        if stripped.startswith("referia_config_version:"):
            return True
        # First non-comment top-level key that isn't version — keep scanning
        # only top-level lines (no indent). Nested keys are indented.
    return False


def deep_copy_config(data: dict) -> dict:
    """Deep-copy helper for tests that need an unmutated original."""
    return copy.deepcopy(data)
