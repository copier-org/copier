"""JSON Schema generation for copier.yml files."""

from __future__ import annotations

from typing import Any

_QUESTION_TYPES = ("bool", "float", "int", "json", "path", "str", "yaml")

_BOOL_STR = {"oneOf": [{"type": "boolean"}, {"type": "string"}]}

_SCALAR_OR_TEMPLATE = {
    "oneOf": [
        {"type": "boolean"},
        {"type": "integer"},
        {"type": "number"},
        {"type": "string"},
    ]
}

_TASK_DEFS: dict[str, Any] = {
    "task": {
        "oneOf": [
            {
                "type": "string",
                "description": "Shell command to run.",
            },
            {
                "type": "array",
                "items": {"type": "string"},
                "description": "Command with arguments (bypasses shell).",
            },
            {
                "type": "object",
                "description": "Task with options.",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The command to run.",
                    },
                    "when": {
                        "type": "string",
                        "description": "Jinja template condition.",
                    },
                    "working_directory": {
                        "type": "string",
                        "description": "Directory to run in (relative to project root).",
                    },
                },
                "required": ["command"],
                "additionalProperties": False,
            },
        ]
    },
    "migration": {
        "oneOf": [
            {
                "type": "string",
                "description": "Shell command to run as migration.",
            },
            {
                "type": "array",
                "items": {"type": "string"},
                "description": "Command with arguments.",
            },
            {
                "type": "object",
                "description": "Migration with options.",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The command to run.",
                    },
                    "version": {
                        "type": "string",
                        "description": "PEP 440 version this migration applies to.",
                    },
                    "when": {
                        "type": "string",
                        "description": "Jinja template condition.",
                    },
                    "working_directory": {
                        "type": "string",
                        "description": "Directory to run in (relative to project root).",
                    },
                },
                "required": ["command"],
                "additionalProperties": False,
            },
        ]
    },
}

_QUESTION_SHORTHAND: dict[str, Any] = {
    "title": "Shorthand question",
    "description": (
        "A question defined as just its default value. "
        "The type is auto-detected from the value."
    ),
}

_QUESTION_FULL: dict[str, Any] = {
    "title": "Full question",
    "type": "object",
    "description": "A question with explicit options.",
    "properties": {
        "type": {
            "type": "string",
            "enum": list(_QUESTION_TYPES),
            "description": ("Question type. Auto-detected from default if not set."),
        },
        "default": {
            "description": "Default value. Can be a Jinja template.",
        },
        "help": {
            "type": "string",
            "description": "Help text explaining the question.",
        },
        "choices": {
            "oneOf": [
                {
                    "type": "array",
                    "description": "List of allowed values.",
                    "items": {},
                },
                {
                    "type": "object",
                    "description": "Mapping of display labels to stored values.",
                },
                {
                    "type": "string",
                    "description": "Jinja template that renders to a list or mapping.",
                },
            ],
            "description": (
                "Restrict answers to a set of choices. "
                "Can be a list, a dict (label -> value), or a Jinja template."
            ),
        },
        "multiselect": {
            "type": "boolean",
            "description": "Allow multiple selections. Only meaningful with choices.",
        },
        "multiline": {
            "oneOf": [
                {"type": "boolean"},
                {"type": "string"},
            ],
            "description": (
                "Allow multiline input. "
                "Defaults to True for json/yaml types, False otherwise."
            ),
        },
        "placeholder": {
            "type": "string",
            "description": "Ghost text shown when input is empty.",
        },
        "qmark": {
            "type": "string",
            "description": "Custom mark displayed before the question prompt.",
        },
        "secret": {
            "type": "boolean",
            "description": ("Hide input with asterisks and exclude from answers file."),
        },
        "validator": {
            "type": "string",
            "description": (
                "Jinja template for validation. "
                "Render nothing if valid, or an error message."
            ),
        },
        "when": {
            "oneOf": [
                {"type": "boolean"},
                {"type": "string"},
            ],
            "description": (
                "Condition that skips the question if False. "
                "Can be a boolean or a Jinja template."
            ),
        },
    },
    "additionalProperties": False,
}


def generate_copier_yml_schema() -> dict[str, Any]:
    """Generate a JSON Schema for copier.yml files.

    Returns:
        A JSON Schema (Draft 2020-12) as a dict.
    """
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://copier.readthedocs.io/en/latest/schemas/copier.schema.json",
        "title": "Copier Template Configuration",
        "description": (
            "Schema for copier.yml template configuration files used by Copier."
        ),
        "type": ["object", "string"],
        "properties": {
            "$schema": {
                "type": "string",
                "format": "uri",
                "description": ("JSON Schema URL for IDE validation support."),
            },
            "_answers_file": {
                "type": "string",
                "description": (
                    "Path to the answers file, relative to the project root. "
                    "Default: .copier-answers.yml"
                ),
            },
            "_envops": {
                "type": "object",
                "description": "Jinja2 environment options.",
                "properties": {
                    "autoescape": {"type": "boolean"},
                    "block_start_string": {"type": "string"},
                    "block_end_string": {"type": "string"},
                    "variable_start_string": {"type": "string"},
                    "variable_end_string": {"type": "string"},
                    "comment_start_string": {"type": "string"},
                    "comment_end_string": {"type": "string"},
                    "keep_trailing_newline": {
                        "type": "boolean",
                        "description": "Default: true",
                    },
                    "undefined": {
                        "type": "string",
                        "enum": [
                            "jinja2.Undefined",
                            "jinja2.StrictUndefined",
                        ],
                    },
                    "line_statement_prefix": {"type": "string"},
                    "line_comment_prefix": {"type": "string"},
                    "trim_blocks": {"type": "boolean"},
                    "lstrip_blocks": {"type": "boolean"},
                    "newline_sequence": {
                        "type": "string",
                        "enum": ["\n", "\r\n", "\r"],
                    },
                    "optimized": {"type": "boolean"},
                },
                "additionalProperties": False,
            },
            "_exclude": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Shell-style patterns for files/folders to exclude "
                    "from the rendered project."
                ),
            },
            "_external_data": {
                "type": "object",
                "additionalProperties": {"type": "string"},
                "description": (
                    "Map of variable names to YAML file paths (relative to "
                    "project root) for lazy-loaded external data."
                ),
            },
            "_jinja_extensions": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Additional Jinja2 extensions to load. "
                    "Specified as dotted Python paths."
                ),
            },
            "_message_after_copy": {
                "type": "string",
                "description": (
                    "Message printed after a copy or recopy succeeds. "
                    "Can be a Jinja template."
                ),
            },
            "_message_after_update": {
                "type": "string",
                "description": (
                    "Message printed after an update succeeds. Can be a Jinja template."
                ),
            },
            "_message_before_copy": {
                "type": "string",
                "description": (
                    "Message printed before a copy or recopy. Can be a Jinja template."
                ),
            },
            "_message_before_update": {
                "type": "string",
                "description": (
                    "Message printed before an update. Can be a Jinja template."
                ),
            },
            "_migrations": {
                "type": "array",
                "items": {"$ref": "#/$defs/migration"},
                "description": (
                    "Migration tasks run during updates. "
                    "Items can be a string, a list of strings, or a dict."
                ),
            },
            "_min_copier_version": {
                "type": "string",
                "description": ("Minimum Copier version required (PEP 440 format)."),
            },
            "_preserve_symlinks": {
                "type": "boolean",
                "description": (
                    "Preserve symlinks as symlinks in the rendered project. "
                    "Default: false."
                ),
            },
            "_secret_questions": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "List of question names to treat as secret. "
                    "Their values are hidden from the answers file."
                ),
            },
            "_skip_if_exists": {
                "type": "array",
                "items": {"type": "string"},
                "description": ("Patterns for files to skip if they already exist."),
            },
            "_subdirectory": {
                "type": "string",
                "description": (
                    "Subdirectory within the template where the real "
                    "template code resides."
                ),
            },
            "_tasks": {
                "type": "array",
                "items": {"$ref": "#/$defs/task"},
                "description": (
                    "Post-render tasks to execute. "
                    "Items can be a string, a list of strings, or a dict."
                ),
            },
            "_templates_suffix": {
                "type": "string",
                "description": (
                    "File suffix that triggers Jinja rendering. Default: .jinja"
                ),
            },
        },
        "patternProperties": {
            "^(?!_)(?!\\$schema)": {
                "title": "Question",
                "anyOf": [
                    _QUESTION_SHORTHAND,
                    _QUESTION_FULL,
                ],
            },
        },
        "additionalProperties": False,
        "$defs": _TASK_DEFS,
    }
