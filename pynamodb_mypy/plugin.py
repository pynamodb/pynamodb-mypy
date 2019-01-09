from typing import Callable
from typing import Optional

import mypy.types
from mypy.nodes import ARG_NAMED_OPT
from mypy.nodes import Argument
from mypy.nodes import NameExpr
from mypy.nodes import TypeInfo
from mypy.nodes import Var
from mypy.plugin import ClassDefContext
from mypy.plugin import FunctionContext
from mypy.plugin import Plugin
from mypy.plugins.common import add_method

ATTR_FULL_NAME = 'pynamodb.attributes.Attribute'
NULL_ATTR_WRAPPER_FULL_NAME = 'pynamodb.attributes._NullableAttributeWrapper'
MODEL_FULL_NAME = 'pynamodb.models.Model'


class PynamodbPlugin(Plugin):
    def get_function_hook(self, fullname: str) -> Optional[Callable[[FunctionContext], mypy.types.Type]]:
        sym = self.lookup_fully_qualified(fullname)
        if sym and isinstance(sym.node, TypeInfo):
            attr_underlying_type = _get_attribute_underlying_type(sym.node)
            if attr_underlying_type:
                _underlying_type = attr_underlying_type  # https://github.com/python/mypy/issues/4297
                return lambda ctx: _attribute_instantiation_hook(ctx, _underlying_type)

        return None

    def get_base_class_hook(self, fullname: str) -> Optional[Callable[[ClassDefContext], None]]:
        sym = self.lookup_fully_qualified(fullname)
        if sym and isinstance(sym.node, TypeInfo):
            if sym.node.has_base(MODEL_FULL_NAME):
                return _model_add_init_hook

        return None


def _get_attribute_underlying_type(attribute_class: TypeInfo) -> Optional[mypy.types.Type]:
    """
    For attribute classes, will return the underlying type.
    e.g. for `class MyAttribute(Attribute[int])`, this will return `int`.
    """
    for base_instance in attribute_class.bases:
        if base_instance.type.fullname() == ATTR_FULL_NAME:
            return base_instance.args[0]
    return None


def _model_add_init_hook(ctx: ClassDefContext) -> None:
    # We resort to matching the statements since the ClassDef doesn't have types for the names at this point.
    init_args = {}
    for stmt in ctx.cls.defs.body:
        if not (
                isinstance(stmt, mypy.nodes.AssignmentStmt) and
                isinstance(stmt.rvalue, mypy.nodes.CallExpr) and
                isinstance(stmt.rvalue.callee, mypy.nodes.NameExpr) and
                isinstance(stmt.rvalue.callee.node, mypy.nodes.TypeInfo)
        ):
            continue  # pragma: no cover -- CPython optimizes this out

        attr_underlying_type = _get_attribute_underlying_type(stmt.rvalue.callee.node)
        if not attr_underlying_type:
            continue

        args = dict(zip(stmt.rvalue.arg_names, stmt.rvalue.args))
        null_arg = args.get('null')
        if isinstance(null_arg, NameExpr) and null_arg.fullname == 'builtins.True':
            attr_underlying_type = mypy.types.UnionType([attr_underlying_type, mypy.types.NoneTyp()])

        for lvalue in stmt.lvalues:
            if isinstance(lvalue, mypy.nodes.NameExpr):
                # We mark even non-nullable arguments as ARG_NAMED_OPT to allow for common pattern:
                #    my_model = MyModel()
                #    my_model.my_attr = 5
                init_args[lvalue.name] = Argument(Var(lvalue.name), attr_underlying_type, None, ARG_NAMED_OPT)

    add_method(
        ctx,
        '__init__',
        list(init_args.values()),
        mypy.types.NoneTyp(),
    )


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
