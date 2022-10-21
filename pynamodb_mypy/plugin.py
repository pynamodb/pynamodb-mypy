from __future__ import annotations

import functools
from typing import Callable
from typing import TypedDict
from typing import Union

import mypy.checker
import mypy.checkmember
import mypy.options
import mypy.types
from mypy.fixup import TypeFixer
from mypy.nodes import ArgKind
from mypy.nodes import NameExpr
from mypy.nodes import TypeInfo
from mypy.plugin import AttributeContext
from mypy.plugin import FunctionContext
from mypy.plugin import FunctionSigContext
from mypy.plugin import Plugin
from mypy.typeanal import make_optional_type

from pynamodb_mypy._private_api import get_descriptor_access_type

PYNAMODB_MODEL_FULL_NAME = "pynamodb.models.Model"
PYNAMODB_ATTRIBUTE_FULL_NAME = "pynamodb.attributes.Attribute"

# A serialized type. Use `_rehydrate_type` to rehydrate.
SerializedType = Union[mypy.types.JsonDict, str]


class PynamodbAttributeDict(TypedDict):
    """
    The information persisted in the model type's metadata for each of the model's attributes.
    """

    # The type of the attribute in serialized form.
    type: SerializedType

    # Whether it's a hash key.
    is_hash_key: bool

    # Whether it's a range key.
    is_range_key: bool


def _pynamodb_attributes_metadata(info: mypy.nodes.TypeInfo) -> dict[str, PynamodbAttributeDict]:
    return info.metadata.setdefault("pynamodb_attributes", {})


def _rehydrate_type(api: mypy.plugin.CheckerPluginInterface, data: SerializedType) -> mypy.types.Type:
    """
    After analysis, we persist what we've learned in serialized form the in mypy metadata.
    This rehydrates a serialized type back to a mypy type.
    """
    internal_api = api
    assert isinstance(internal_api, mypy.checker.TypeChecker)

    typ = mypy.types.deserialize_type(data)
    typ.accept(TypeFixer(internal_api.modules, allow_missing=False))
    return typ


class PynamodbPlugin(Plugin):
    #
    # plugin callbacks which express interest in specific types (that the plugin handles) and provides return hooks
    # to handle them
    #
    # see: https://mypy.readthedocs.io/en/stable/extending_mypy.html#current-list-of-plugin-hooks

    def get_function_signature_hook(
        self,
        fullname: str,
    ) -> Callable[[FunctionSigContext], mypy.types.FunctionLike] | None:
        sym = self.lookup_fully_qualified(fullname)
        if sym and isinstance(sym.node, TypeInfo) and sym.node.has_base(PYNAMODB_MODEL_FULL_NAME):
            return self._get_function_signature_hook__pynamodb_model__init__
        return None

    def get_attribute_hook(self, fullname: str) -> Callable[[AttributeContext], mypy.types.Type] | None:
        class_name, _, attr_name = fullname.rpartition(".")
        sym = self.lookup_fully_qualified(class_name)
        if sym and isinstance(sym.node, TypeInfo) and sym.node.has_base(PYNAMODB_MODEL_FULL_NAME):
            return functools.partial(self._get_attribute_hook__pynamodb_model, sym.node, attr_name)
        return None

    def get_function_hook(self, fullname: str) -> Callable[[FunctionContext], mypy.types.Type] | None:
        sym = self.lookup_fully_qualified(fullname)
        if not sym:  # pragma: no cover
            return None
        if isinstance(sym.node, TypeInfo) and sym.node.has_base(PYNAMODB_ATTRIBUTE_FULL_NAME):
            return self._get_function_hook__pynamodb_attribute__init__
        return None

    #
    # hooks for specific types
    #

    def _get_function_signature_hook__pynamodb_model__init__(self, ctx: FunctionSigContext) -> mypy.types.FunctionLike:
        """
        Called when a model is initialized (e.g. MyModel(foo='bar')).
        """
        model_instance = ctx.default_signature.ret_type
        if not isinstance(model_instance, mypy.types.Instance):  # pragma: no cover
            return ctx.default_signature

        args = {}
        for model_cls in model_instance.type.mro:
            args.update({
                attr_name: _rehydrate_type(ctx.api, attr_data["type"])
                for attr_name, attr_data in _pynamodb_attributes_metadata(model_cls).items()
            })

        # substitute hash/range key types
        hash_key_type: mypy.types.Type = mypy.types.NoneTyp()
        range_key_type: mypy.types.Type = mypy.types.NoneTyp()
        for attr_data in _pynamodb_attributes_metadata(model_instance.type).values():
            if attr_data["is_hash_key"]:
                hash_key_type = _rehydrate_type(ctx.api, attr_data["type"])
            if attr_data["is_range_key"]:
                range_key_type = _rehydrate_type(ctx.api, attr_data["type"])

        # substitute the **kwargs with the named arguments based on model's attributes
        try:
            hash_key_idx = ctx.default_signature.arg_names.index("hash_key")
            range_key_idx = ctx.default_signature.arg_names.index("range_key")
            kwargs_idx = ctx.default_signature.arg_kinds.index(ArgKind.ARG_STAR2)
        except ValueError:
            ctx.api.fail(f"Unexpected signature '{ctx.default_signature}' for a PynamoDB model initializer: "
                         "expecting 'hash_key', 'range_key' and a keywords argument", ctx.context)
            return ctx.default_signature
        else:
            arg_kinds = ctx.default_signature.arg_kinds.copy()
            arg_names = ctx.default_signature.arg_names.copy()
            arg_types = ctx.default_signature.arg_types.copy()
            arg_types[hash_key_idx] = hash_key_type
            arg_types[range_key_idx] = range_key_type
            arg_kinds[kwargs_idx : kwargs_idx + 1] = [ArgKind.ARG_NAMED_OPT] * len(args)
            arg_names[kwargs_idx : kwargs_idx + 1] = args.keys()
            arg_types[kwargs_idx : kwargs_idx + 1] = args.values()
            return ctx.default_signature.copy_modified(
                arg_kinds=arg_kinds,
                arg_names=arg_names,
                arg_types=arg_types,
            )

    def _get_function_hook__pynamodb_attribute__init__(self, ctx: FunctionContext) -> mypy.types.Type:
        """
        Handles attribute instantiation, e.g. MyAttribute(null=True)
        """
        self._inspect_pynamodb_attribute_init(ctx)
        return ctx.default_return_type

    def _get_attribute_hook__pynamodb_model(
        self,
        model_typeinfo: mypy.nodes.TypeInfo,
        attr_name: str,
        ctx: AttributeContext,
    ) -> mypy.types.Type:
        """
        Called when a model's attribute is referenced, used to determine the attribute's type:
        this generally works well even without the plugin (thanks for mypy supporting the Descriptor protocol),
        the nullability (support for `null=True`) is what's being added here.
        """
        attr_data = _pynamodb_attributes_metadata(model_typeinfo).get(attr_name)
        if not attr_data:  # pragma: no cover
            return ctx.default_attr_type
        return _rehydrate_type(ctx.api, attr_data["type"])

    # utils

    def _inspect_pynamodb_attribute_init(self, ctx: FunctionContext) -> None:
        """
        Inspects the initialization of PynamoDB attributes to see:
        - which class field they're assigned to (a'la __set_name__)
        - how they're initialized (nullable?)

        All information we discover, we persist in the model type's mypy metadata.
        """
        internal_api = ctx.api
        assert isinstance(internal_api, mypy.checker.TypeChecker)

        attr_instance = ctx.default_return_type

        # determine which class we're assigned into
        scope_cls = internal_api.scope.active_class()
        if not scope_cls:
            return

        # Determine which class var name we're assigned to (to know the attribute's pythonic name)
        for stmt in scope_cls.defn.defs.body:
            if isinstance(stmt, mypy.nodes.AssignmentStmt) and stmt.rvalue is ctx.context:
                if len(stmt.lvalues) != 1:  # pragma: no cover
                    ctx.api.fail(f"PynamoDB attribute assigned to {len(stmt.lvalues)} names in a model", stmt)
                    continue
                lvalue = stmt.lvalues[0]
                if not isinstance(lvalue, mypy.nodes.NameExpr):  # pragma: no cover
                    ctx.api.fail("PynamoDB attribute assigned to non-name", stmt)
                    continue

                attr_name = lvalue.name
                break
        else:
            ctx.api.fail("PynamoDB attribute not assigned to a class variable", ctx.context)
            return

        # A PynamoDB attribute is a Python descriptor (https://docs.python.org/3/howto/descriptor.html)
        attr_type = get_descriptor_access_type(ctx.context, internal_api, attr_instance)
        if not attr_type:  # pragma: no cover
            ctx.api.fail("PynamoDB attribute does not act as a data descriptor (does it have __get__?)", ctx.context)
            return

        def _get_named_arg(arg_name: str) -> mypy.nodes.Expression | None:
            for names, args in zip(ctx.arg_names, ctx.args):
                for name, arg in zip(names, args):
                    if name == arg_name:
                        return arg
            return None

        def _check_literal_bool(arg_name: str, default: bool) -> bool:
            arg_expr = _get_named_arg(arg_name)
            if arg_expr is None:
                return default
            if not isinstance(arg_expr, NameExpr) or arg_expr.fullname not in ("builtins.False", "builtins.True"):
                ctx.api.fail(f"'{arg_name}' argument is not constant False or True", ctx.context)
                return default

            return arg_expr.fullname == "builtins.True"

        if _check_literal_bool("null", False):
            attr_type = make_optional_type(attr_type)

        _pynamodb_attributes_metadata(scope_cls)[attr_name] = PynamodbAttributeDict(
            type=attr_type.serialize(),
            is_hash_key=_check_literal_bool("hash_key", False),
            is_range_key=_check_literal_bool("range_key", False),
        )
