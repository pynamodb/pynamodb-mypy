from typing import Callable
from typing import Optional

import mypy.nodes
import mypy.plugin
import mypy.types

ATTR_FULL_NAME = 'pynamodb.attributes.Attribute'


class PynamodbPlugin(mypy.plugin.Plugin):
    def get_function_hook(self, fullname: str) -> Optional[Callable[[mypy.plugin.FunctionContext], mypy.types.Type]]:
        sym = self.lookup_fully_qualified(fullname)
        if sym and isinstance(sym.node, mypy.nodes.TypeInfo) and _is_attribute_type_node(sym.node):
            return _attribute_instantiation_hook
        return None

    def get_attribute_hook(self, fullname: str
                           ) -> Optional[Callable[[mypy.plugin.AttributeContext], mypy.types.Type]]:
        sym = self.lookup_fully_qualified(fullname)
        if sym and sym.type and _is_attribute_marked_nullable(sym.type):
            return lambda ctx: mypy.types.UnionType([ctx.default_attr_type, mypy.types.NoneType()])
        return None


def _is_attribute_type_node(type_node: mypy.nodes.TypeInfo) -> bool:
    return any(base.type.fullname == ATTR_FULL_NAME for base in type_node.bases)


def _attribute_marked_as_nullable(t: mypy.types.Instance) -> mypy.types.Instance:
    return t.copy_modified(args=t.args + [mypy.types.NoneType()])


def _is_attribute_marked_nullable(t: mypy.types.Type) -> bool:
    return (
            isinstance(t, mypy.types.Instance) and
            _is_attribute_type_node(t.type) and
            # In lieu of being able to attach metadata to an instance,
            # having a None "fake" type argument is our way of marking the attribute as nullable
            bool(t.args) and isinstance(t.args[-1], mypy.types.NoneType)
    )


def _get_bool_literal(n: mypy.nodes.Node) -> Optional[bool]:
    return {
        'builtins.False': False,
        'builtins.True': True,
    }.get(n.fullname or '') if isinstance(n, mypy.nodes.NameExpr) else None


def _attribute_instantiation_hook(ctx: mypy.plugin.FunctionContext) -> mypy.types.Type:
    """
    Handles attribute instantiation, e.g. MyAttribute(null=True)
    """
    args = dict(zip(ctx.callee_arg_names, ctx.args))

    # If initializer is passed null=True, mark attribute type instance as nullable
    null_arg_exprs = args.get('null')
    nullable = False
    if null_arg_exprs and len(null_arg_exprs) == 1:
        null_literal = _get_bool_literal(null_arg_exprs[0])
        if null_literal is not None:
            nullable = null_literal
        else:
            ctx.api.fail("'null' argument is not constant False or True, cannot deduce optionality", ctx.context)

    assert isinstance(ctx.default_return_type, mypy.types.Instance)
    return _attribute_marked_as_nullable(ctx.default_return_type) if nullable else ctx.default_return_type
