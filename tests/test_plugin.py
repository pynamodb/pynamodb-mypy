from __future__ import annotations

from .mypy_helpers import MypyAssert


def test_model_init(assert_mypy_output: MypyAssert) -> None:
    assert_mypy_output(
        """
    from pynamodb.attributes import NumberAttribute
    from pynamodb.models import Model

    class MyModel(Model):
        my_hash_key = NumberAttribute(hash_key=True)
        my_range_key = NumberAttribute(range_key=True)
        my_attr = NumberAttribute()

    class MyDerivedModel(MyModel):
        my_derived_attr = NumberAttribute()

    MyModel(my_attr=5.5)
    MyModel(5.5, my_attr=5.5)
    MyModel(5.5, 5.5, my_attr=5.5)
    MyModel(hash_key=5.5, range_key=5.5, my_attr=5.5)
    MyModel(hash_key='hello', range_key='world', my_attr=5.5)  # E: Argument "hash_key" to "MyModel" has incompatible type "str"; expected "float"  [arg-type]
                                                               # E: Argument "range_key" to "MyModel" has incompatible type "str"; expected "float"  [arg-type]
    MyModel(foobar=5.5)  # E: Unexpected keyword argument "foobar" for "MyModel"  [call-arg]
    
    # test with derived model

    MyDerivedModel(my_attr=5.5, my_derived_attr=42)
    MyDerivedModel(foobar=5.5)  # E: Unexpected keyword argument "foobar" for "MyDerivedModel"  [call-arg]
    """
    )


def test_model_init__no_attributes(assert_mypy_output: MypyAssert) -> None:
    assert_mypy_output(
        """
    from pynamodb.attributes import NumberAttribute
    from pynamodb.models import Model

    class MyModel(Model):
        pass

    MyModel('foo', 'bar')  # E: Argument 1 to "MyModel" has incompatible type "str"; expected "None"  [arg-type]
                           # E: Argument 2 to "MyModel" has incompatible type "str"; expected "None"  [arg-type]
    MyModel(hash_key='foo', range_key='bar', spam='ham')  # E: Unexpected keyword argument "spam" for "MyModel"  [call-arg]
                                                          # E: Argument "hash_key" to "MyModel" has incompatible type "str"; expected "None"  [arg-type]
                                                          # E: Argument "range_key" to "MyModel" has incompatible type "str"; expected "None"  [arg-type]
    """
    )


def test_model_init__custom_empty(assert_mypy_output: MypyAssert) -> None:
    assert_mypy_output(
        """
    from pynamodb.attributes import NumberAttribute
    from pynamodb.models import Model

    class MyModel(Model):
        my_hash_key = NumberAttribute(hash_key=True)
        my_range_key = NumberAttribute(range_key=True)
        my_attr = NumberAttribute()

        def __init__(self) -> None:
          ...

    MyModel('foo', 'bar')  # E: Unexpected signature 'def () -> __main__.MyModel' for a PynamoDB model initializer: expecting 'hash_key', 'range_key' and a keywords argument  [misc]
                           # E: Too many arguments for "MyModel"  [call-arg]
    """
    )


def test_model_init__custom_all_args(assert_mypy_output: MypyAssert) -> None:
    assert_mypy_output(
        """
    from typing import Any

    from pynamodb.attributes import NumberAttribute
    from pynamodb.models import Model

    class MyModel(Model):
        my_hash_key = NumberAttribute(hash_key=True)
        my_range_key = NumberAttribute(range_key=True)
        my_attr = NumberAttribute()

        def __init__(self, *args: Any, **kwargs: Any) -> None:
          ...

    MyModel(unknown=42)  # E: Unexpected signature 'def (*args: Any, **kwargs: Any) -> __main__.MyModel' for a PynamoDB model initializer: expecting 'hash_key', 'range_key' and a keywords argument  [misc]
    """
    )


def test_number_attribute(assert_mypy_output: MypyAssert) -> None:
    assert_mypy_output(
        """
    from typing import Optional
    from typing_extensions import assert_type

    from pynamodb.attributes import NumberAttribute
    from pynamodb.models import Model

    class MyModel(Model):
        my_attr = NumberAttribute()
        my_nullable_attr = NumberAttribute(null=True)
        my_not_nullable_attr = NumberAttribute(null=False)

    assert_type(MyModel.my_attr, NumberAttribute)
    assert_type(MyModel().my_attr, float)
    assert_type(MyModel().my_nullable_attr, Optional[float])
    assert_type(MyModel().my_not_nullable_attr, float)

    MyModel(my_attr=5.5)
    MyModel(my_attr='5.5')  # E: Argument "my_attr" to "MyModel" has incompatible type "str"; expected "float"  [arg-type]
    MyModel(my_attr=None)  # E: Argument "my_attr" to "MyModel" has incompatible type "None"; expected "float"  [arg-type]
    MyModel(my_nullable_attr=5.5)
    MyModel(my_nullable_attr='5.5')  # E: Argument "my_nullable_attr" to "MyModel" has incompatible type "str"; expected "Optional[float]"  [arg-type]
    MyModel(my_nullable_attr=None)
    """
    )


def test_unicode_attribute(assert_mypy_output: MypyAssert) -> None:
    assert_mypy_output(
        """
    from typing import Optional
    from typing_extensions import assert_type

    from pynamodb.attributes import UnicodeAttribute
    from pynamodb.models import Model

    class MyModel(Model):
        my_attr = UnicodeAttribute()
        my_nullable_attr = UnicodeAttribute(null=True)

    assert_type(MyModel.my_attr, UnicodeAttribute)
    assert_type(MyModel.my_nullable_attr, UnicodeAttribute)
    assert_type(MyModel().my_attr, str)
    assert_type(MyModel().my_nullable_attr, Optional[str])

    MyModel().my_attr.lower()
    MyModel().my_nullable_attr.lower()  # E: Item "None" of "Optional[str]" has no attribute "lower"  [union-attr]
    """
    )


def test_custom_attribute(assert_mypy_output: MypyAssert) -> None:
    assert_mypy_output(
        """
    from typing import Optional
    from typing_extensions import assert_type

    import pynamodb.expressions.condition
    from pynamodb.attributes import Attribute
    from pynamodb.models import Model

    class BinaryAttribute(Attribute[bytes]):
        def do_something(self) -> None: ...

    class MyModel(Model):
        my_attr = BinaryAttribute()
        my_nullable_attr = BinaryAttribute(null=True)

    assert_type(MyModel.my_attr, BinaryAttribute)
    assert_type(MyModel.my_attr.exists(), pynamodb.expressions.condition.Exists)
    assert_type(MyModel.my_attr.do_something(), None)
    assert_type(MyModel().my_attr, bytes)

    assert_type(MyModel.my_nullable_attr, BinaryAttribute)
    assert_type(MyModel.my_nullable_attr.exists(), pynamodb.expressions.condition.Exists)
    assert_type(MyModel.my_nullable_attr.do_something(), None)
    assert_type(MyModel().my_nullable_attr, Optional[bytes])
    """
    )


def test_map_attribute(assert_mypy_output: MypyAssert) -> None:
    assert_mypy_output(
        """
    from typing import Optional
    from typing_extensions import assert_type

    from pynamodb.attributes import MapAttribute, UnicodeAttribute
    from pynamodb.models import Model

    class MyMapAttribute(MapAttribute):
        my_sub_attr = UnicodeAttribute()

    class MyModel(Model):
        my_attr = MyMapAttribute()
        my_nullable_attr = MyMapAttribute(null=True)

    assert_type(MyModel.my_attr, MyMapAttribute)
    assert_type(MyModel.my_nullable_attr, MyMapAttribute)
    assert_type(MyModel().my_attr, MyMapAttribute)
    assert_type(MyModel().my_nullable_attr, Optional[MyMapAttribute])
    """
    )


def test_unexpected_value_of_null(assert_mypy_output: MypyAssert) -> None:
    assert_mypy_output(
        """
    from typing import Optional
    from typing_extensions import assert_type

    from pynamodb.attributes import NumberAttribute
    from pynamodb.models import Model

    class MyModel(Model):
        my_attr = NumberAttribute(null=bool(5))  # E: 'null' argument is not constant False or True  [misc]

    assert_type(MyModel().my_attr, float)
    """
    )


def test_attribute_assigned_out_of_class_scope(assert_mypy_output: MypyAssert) -> None:
    assert_mypy_output(
        """
    from pynamodb.models import Model
    from pynamodb.attributes import NumberAttribute

    num = NumberAttribute()
    """
    )


def test_attribute_not_assigned_to_class_var(assert_mypy_output: MypyAssert) -> None:
    assert_mypy_output(
        """
    from pynamodb.models import Model
    from pynamodb.attributes import NumberAttribute

    class MyModel(Model):
        NumberAttribute()  # E: PynamoDB attribute not assigned to a class variable  [misc]
    """
    )


def test_attribute_hook_fallback(assert_mypy_output: MypyAssert) -> None:
    assert_mypy_output(
        """
    class C:
        def __init__(self) -> None:
            self.d = 42

    _ = C().d
    """
    )


def test_function_hook_fallback(assert_mypy_output: MypyAssert) -> None:
    assert_mypy_output(
        """
    def foo():
        pass

    foo()
    """
    )
