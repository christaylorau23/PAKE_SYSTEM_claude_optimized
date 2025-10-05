#!/usr/bin/env python3
"""LibCST UTCNowTransformer for DTZ Error Remediation.

This transformer addresses DTZ (DateTime-Timezone) errors by replacing
the deprecated datetime.utcnow() calls with the modern datetime.now(timezone.utc)
pattern. This eliminates naive datetime objects that cause timezone-related bugs.

Based on the engineering plan's Phase 1 requirements for automated remediation
of production incidents.

The transformer handles multiple DTZ patterns:
1. datetime.utcnow() -> datetime.now(timezone.utc)
2. datetime.now() without tzinfo -> datetime.now(timezone.utc)
3. datetime.fromtimestamp() without tzinfo -> datetime.fromtimestamp(ts, tz=timezone.utc)
4. datetime.strptime() without %z -> datetime.strptime(...).replace(tzinfo=timezone.utc)
"""

from typing import List, Optional, Set

import libcst as cst
from libcst import matchers as m
from libcst.codemod import CodemodContext, VisitorBasedCodemodCommand
from libcst.codemod.visitors import AddImportsVisitor


class ComprehensiveDTZTransformer(VisitorBasedCodemodCommand):
    """Comprehensive transformer for all DTZ-related issues.

    This transformer handles multiple DTZ patterns as described in the engineering plan:
    1. datetime.utcnow() -> datetime.now(timezone.utc)
    2. datetime.now() without tzinfo -> datetime.now(timezone.utc)
    3. datetime.fromtimestamp() without tzinfo -> datetime.fromtimestamp(ts, tz=timezone.utc)
    4. datetime.strptime() without %z -> datetime.strptime(...).replace(tzinfo=timezone.utc)

    This addresses the systemic mishandling of time-aware datetimes that causes
    production failures when data crosses timezone boundaries.
    """

    DESCRIPTION = "Fix all DTZ errors by ensuring timezone-aware datetime objects"

    def __init__(self, context: CodemodContext) -> None:
        super().__init__(context)
        self.timezone_import_added = False
        self.modifications_made = 0

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:
        """Transform various datetime calls to be timezone-aware."""
        # Pattern 1: datetime.utcnow() - Primary source of DTZ bugs
        if m.matches(
            updated_node,
            m.Call(func=m.Attribute(value=m.Name("datetime"), attr=m.Name("utcnow"))),
        ):
            self.modifications_made += 1
            return self._create_timezone_aware_now()

        # Pattern 2: datetime.now() without timezone
        if m.matches(
            updated_node,
            m.Call(
                func=m.Attribute(value=m.Name("datetime"), attr=m.Name("now")), args=[]
            ),
        ):
            self.modifications_made += 1
            return self._create_timezone_aware_now()

        # Pattern 3: datetime.fromtimestamp() without timezone
        if m.matches(
            updated_node,
            m.Call(
                func=m.Attribute(value=m.Name("datetime"), attr=m.Name("fromtimestamp"))
            ),
        ):
            # Check if tz parameter is already present
            has_tz_param = any(
                arg.keyword and arg.keyword.value == "tz" for arg in updated_node.args
            )

            if not has_tz_param:
                self.modifications_made += 1
                # Add tz=timezone.utc parameter
                new_args = list(updated_node.args) + [
                    cst.Arg(
                        keyword=cst.Name("tz"),
                        value=cst.Attribute(
                            value=cst.Name("timezone"), attr=cst.Name("utc")
                        ),
                    )
                ]

                self._ensure_timezone_import()
                return updated_node.with_changes(args=new_args)

        # Pattern 4: datetime.strptime() without %z - requires .replace(tzinfo=timezone.utc)
        if m.matches(
            updated_node,
            m.Call(func=m.Attribute(value=m.Name("datetime"), attr=m.Name("strptime"))),
        ):
            # Check if the format string contains %z (timezone info)
            format_string_arg = None
            for arg in updated_node.args:
                if arg.keyword is None:  # positional argument
                    if format_string_arg is None:
                        format_string_arg = arg
                    else:
                        # This is the format string (second positional arg)
                        if isinstance(arg.value, cst.SimpleString):
                            format_str = arg.value.value.strip("\"'")
                            if "%z" not in format_str:
                                self.modifications_made += 1
                                return self._wrap_strptime_with_replace(updated_node)

        return updated_node

    def _create_timezone_aware_now(self) -> cst.Call:
        """Create datetime.now(timezone.utc) call."""
        self._ensure_timezone_import()
        return cst.Call(
            func=cst.Attribute(value=cst.Name("datetime"), attr=cst.Name("now")),
            args=[
                cst.Arg(
                    value=cst.Attribute(
                        value=cst.Name("timezone"), attr=cst.Name("utc")
                    )
                )
            ],
        )

    def _wrap_strptime_with_replace(self, strptime_call: cst.Call) -> cst.Call:
        """Wrap datetime.strptime() with .replace(tzinfo=timezone.utc)."""
        self._ensure_timezone_import()

        # Create the .replace(tzinfo=timezone.utc) call
        return cst.Call(
            func=cst.Attribute(value=strptime_call, attr=cst.Name("replace")),
            args=[
                cst.Arg(
                    keyword=cst.Name("tzinfo"),
                    value=cst.Attribute(
                        value=cst.Name("timezone"), attr=cst.Name("utc")
                    ),
                )
            ],
        )

    def _ensure_timezone_import(self) -> None:
        """Ensure timezone is imported from datetime."""
        if not self.timezone_import_added:
            AddImportsVisitor.add_needed_import(self.context, "datetime", "timezone")
            self.timezone_import_added = True

    def get_modifications_count(self) -> int:
        """Return the number of modifications made by this transformer."""
        return self.modifications_made


# Legacy transformer for backward compatibility
class UTCNowTransformer(ComprehensiveDTZTransformer):
    """Legacy transformer that only handles datetime.utcnow() -> datetime.now(timezone.utc).

    This is kept for backward compatibility but ComprehensiveDTZTransformer
    should be used for new implementations.
    """

    DESCRIPTION = (
        "Replace datetime.utcnow() with datetime.now(timezone.utc) to fix DTZ errors"
    )

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:
        """Only handle datetime.utcnow() calls."""
        if m.matches(
            updated_node,
            m.Call(func=m.Attribute(value=m.Name("datetime"), attr=m.Name("utcnow"))),
        ):
            self.modifications_made += 1
            return self._create_timezone_aware_now()

        return updated_node


# Legacy transformer for backward compatibility
class DateTimeTimezoneTransformer(ComprehensiveDTZTransformer):
    """Legacy alias for ComprehensiveDTZTransformer."""


def create_comprehensive_dtz_transformer() -> ComprehensiveDTZTransformer:
    """Factory function to create the comprehensive DTZ transformer."""
    return ComprehensiveDTZTransformer(CodemodContext())


def create_utcnow_transformer() -> UTCNowTransformer:
    """Factory function to create the UTCNow transformer."""
    return UTCNowTransformer(CodemodContext())


def create_datetime_timezone_transformer() -> DateTimeTimezoneTransformer:
    """Factory function to create the comprehensive DTZ transformer."""
    return DateTimeTimezoneTransformer(CodemodContext())
