from .mypy_helpers import assert_mypy_output


def test_number_attribute():
    assert_mypy_output("""
    from pynamodb.attributes import NumberAttribute
    from pynamodb.models import Model

    class MyModel(Model):
        my_attr = NumberAttribute()
        my_nullable_attr = NumberAttribute(null=True)
        my_not_nullable_attr = NumberAttribute(null=False)

    reveal_type(MyModel.my_attr)  # E: Revealed type is 'pynamodb.attributes.NumberAttribute'
    reveal_type(MyModel().my_attr)  # E: Revealed type is 'builtins.float*'
    reveal_type(MyModel().my_nullable_attr)  # E: Revealed type is 'Union[builtins.float*, None]'
    reveal_type(MyModel().my_not_nullable_attr)  # E: Revealed type is 'builtins.float*'
    """)


def test_unicode_attribute():
    assert_mypy_output("""
    from pynamodb.attributes import UnicodeAttribute
    from pynamodb.models import Model

    class MyModel(Model):
        my_attr = UnicodeAttribute()
        my_nullable_attr = UnicodeAttribute(null=True)

    reveal_type(MyModel.my_attr)  # E: Revealed type is 'pynamodb.attributes.UnicodeAttribute'
    reveal_type(MyModel.my_nullable_attr)  # E: Revealed type is 'pynamodb.attributes.UnicodeAttribute*'
    reveal_type(MyModel().my_attr)  # E: Revealed type is 'builtins.str*'
    reveal_type(MyModel().my_nullable_attr)  # E: Revealed type is 'Union[builtins.str*, None]'

    MyModel().my_attr.lower()
    MyModel().my_nullable_attr.lower()  # E: Item "None" of "Optional[str]" has no attribute "lower"
    """)


def test_custom_attribute():
    assert_mypy_output("""
    from pynamodb.attributes import Attribute
    from pynamodb.models import Model

    class BinaryAttribute(Attribute[bytes]):
        def do_something(self) -> None: ...

    class MyModel(Model):
        my_attr = BinaryAttribute()
        my_nullable_attr = BinaryAttribute(null=True)

    reveal_type(MyModel.my_attr)  # E: Revealed type is '__main__.BinaryAttribute'
    reveal_type(MyModel.my_attr.exists)  # E: Revealed type is 'def () -> pynamodb.expressions.condition.Exists'
    reveal_type(MyModel.my_attr.do_something)  # E: Revealed type is 'def ()'
    reveal_type(MyModel().my_attr)  # E: Revealed type is 'builtins.bytes*'

    reveal_type(MyModel.my_nullable_attr)  # E: Revealed type is '__main__.BinaryAttribute*'
    reveal_type(MyModel.my_nullable_attr.exists)  # E: Revealed type is 'def () -> pynamodb.expressions.condition.Exists'
    reveal_type(MyModel.my_nullable_attr.do_something)  # E: Revealed type is 'def ()'
    reveal_type(MyModel().my_nullable_attr)  # E: Revealed type is 'Union[builtins.bytes*, None]'
    """)  # noqa: E501


def test_unexpected_number_of_nulls():
    assert_mypy_output("""
    from pynamodb.attributes import NumberAttribute
    from pynamodb.models import Model

    class MyModel(Model):
        my_attr = NumberAttribute(True, True, True, null=True)  # E: "NumberAttribute" gets multiple values for keyword argument "null"

    reveal_type(MyModel().my_attr)  # E: Revealed type is 'builtins.float*'
    """)  # noqa: E501


def test_unexpected_value_of_null():
    assert_mypy_output("""
    from pynamodb.attributes import NumberAttribute
    from pynamodb.models import Model

    class MyModel(Model):
        my_attr = NumberAttribute(null=bool(5))  # E: 'null' argument is not constant False or True, cannot deduce optionality

    reveal_type(MyModel().my_attr)  # E: Revealed type is 'builtins.float*'
    """)  # noqa: E501


def test_function_hook_fallback():
    assert_mypy_output("""
    def foo():
        pass

    foo()
    """)
