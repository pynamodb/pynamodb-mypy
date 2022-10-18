"""
Here we'll be using mypy private API shamelessly.
"""
from __future__ import annotations

from typing import Optional

import mypy.checker
import mypy.checkmember
from mypy.nodes import Context
from mypy.types import Type


def get_descriptor_access_type(ctx: Context, chk: mypy.checker.TypeChecker, descriptor: Type) -> Optional[Type]:
    """
    Given a descriptor type, returns the type its __get__ method returns.
    """
    return mypy.checkmember.analyze_descriptor_access(
        descriptor,
        mypy.checkmember.MemberContext(
            is_lvalue=False,
            is_super=False,
            is_operator=False,
            original_type=descriptor,
            context=ctx,
            msg=chk.msg,
            chk=chk,
            self_type=None,
        ),
    )
