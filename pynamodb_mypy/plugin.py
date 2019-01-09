from typing import Callable
from typing import Optional

import mypy.types
from mypy.nodes import NameExpr
from mypy.nodes import TypeInfo
from mypy.plugin import FunctionContext
from mypy.plugin import Plugin

ATTR_FULL_NAME = 'pynamodb.attributes.Attribute'
NULL_ATTR_WRAPPER_FULL_NAME = 'pynamodb.attributes._NullableAttributeWrapper'


class PynamodbPlugin(Plugin):
    @staticmethod
    def _get_attribute_underlying_type(attribute_class: TypeInfo) -> Optional[mypy.types.Type]:
        """
        e.g. for `class MyAttribute(Attribute[int])`, this will return `int`.
        """
        for base_instance in attribute_class.bases:
            if base_instance.type.fullname() == ATTR_FULL_NAME:
                return base_instance.args[0]
        return None

    def get_function_hook(self, fullname: str) -> Optional[Callable[[FunctionContext], mypy.types.Type]]:
        symbol_table_node = self.lookup_fully_qualified(fullname)
        if not symbol_table_node:
            return None

        if isinstance(symbol_table_node.node, TypeInfo):
            underlying_type = self._get_attribute_underlying_type(symbol_table_node.node)
            if underlying_type:
                _underlying_type = underlying_type  # https://github.com/python/mypy/issues/4297
                return lambda ctx: _attribute_instantiation_hook(ctx, _underlying_type)

        return None


def _attribute_instantiation_hook(ctx: FunctionContext,
                                  underlying_type: mypy.types.Type) -> mypy.types.Type:
    """
    Handles attribute instantiation, e.g. MyAttribute(null=True)
    """
    args = dict(zip(ctx.callee_arg_names, ctx.args))

    # If initializer is passed null=True, wrap in _NullableAttribute
    # to make the underlying type optional
    null_arg_exprs = args.get('null')
    if null_arg_exprs and len(null_arg_exprs) == 1:
        (null_arg_expr,) = null_arg_exprs
        if (
            not isinstance(null_arg_expr, NameExpr) or
            null_arg_expr.fullname not in ('builtins.False', 'builtins.True')
        ):
            ctx.api.fail("'null' argument is not constant False or True, "
                         "cannot deduce optionality", ctx.context)
            return ctx.default_return_type

        if null_arg_expr.fullname == 'builtins.True':
            return ctx.api.named_generic_type(NULL_ATTR_WRAPPER_FULL_NAME, [
                ctx.default_return_type,
                underlying_type,
            ])

    return ctx.default_return_type
