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

    def get_method_signature_hook(self, fullname: str
                                  ) -> Optional[Callable[[mypy.plugin.MethodSigContext], mypy.types.CallableType]]:
        class_name, method_name = fullname.rsplit('.', 1)
        sym = self.lookup_fully_qualified(class_name)
        if sym is not None and sym.node is not None and _is_attribute_type_node(sym.node):
            if method_name == '__get__':
                return _get_method_sig_hook
            elif method_name == '__set__':
                return _set_method_sig_hook
        return None


def _is_attribute_type_node(node: mypy.nodes.Node) -> bool:
    return (
        isinstance(node, mypy.nodes.TypeInfo) and
        any(base.type.fullname == ATTR_FULL_NAME for base in node.bases)
    )


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


def _get_bool_literal(node: mypy.nodes.Node) -> Optional[bool]:
    return {
        'builtins.False': False,
        'builtins.True': True,
    }.get(node.fullname or '') if isinstance(node, mypy.nodes.NameExpr) else None


def _make_optional(t: mypy.types.Type) -> mypy.types.UnionType:
    """Wraps a type in optionality"""
    return mypy.types.UnionType([t, mypy.types.NoneType()])


def _unwrap_optional(t: mypy.types.Type) -> mypy.types.Type:
    """Unwraps a potentially optional type"""
    if not isinstance(t, mypy.types.UnionType):
        return t
    t = mypy.types.UnionType([item for item in t.items if not isinstance(item, mypy.types.NoneType)])
    if len(t.items) == 0:
        return mypy.types.NoneType()
    elif len(t.items) == 1:
        return t.items[0]
    else:
        return t


def _get_method_sig_hook(ctx: mypy.plugin.MethodSigContext) -> mypy.types.CallableType:
    """
    Patches up the signature of Attribute.__get__ to respect attribute's nullability.
    """
    sig = ctx.default_signature
    if not _is_attribute_marked_nullable(ctx.type):
        return sig
    try:
        (instance_type, owner_type) = sig.arg_types
    except ValueError:
        return sig
    if not isinstance(instance_type, mypy.types.AnyType):  # instance attribute access
        return sig
    return sig.copy_modified(ret_type=_make_optional(sig.ret_type))


def _set_method_sig_hook(ctx: mypy.plugin.MethodSigContext) -> mypy.types.CallableType:
    """
    Patches up the signature of Attribute.__set__ to respect attribute's nullability.
    """
    sig = ctx.default_signature
    if _is_attribute_marked_nullable(ctx.type):
        return sig
    try:
        (instance_type, value_type) = sig.arg_types
    except ValueError:
        return sig
    if not isinstance(instance_type, mypy.types.AnyType):  # instance attribute access
        return sig
    return sig.copy_modified(arg_types=[instance_type, _unwrap_optional(value_type)])


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
