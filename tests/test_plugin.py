def test_number_attribute(assert_mypy_output):
    assert_mypy_output("""
    from pynamodb.attributes import NumberAttribute
    from pynamodb.models import Model

    class MyModel(Model):
        my_attr = NumberAttribute()
        my_nullable_attr = NumberAttribute(null=True)
        my_not_nullable_attr = NumberAttribute(null=False)

    reveal_type(MyModel.my_attr)  # N: Revealed type is 'pynamodb.attributes.NumberAttribute'
    reveal_type(MyModel().my_attr)  # N: Revealed type is 'builtins.float*'
    reveal_type(MyModel().my_nullable_attr)  # N: Revealed type is 'Union[builtins.float*, None]'
    reveal_type(MyModel().my_not_nullable_attr)  # N: Revealed type is 'builtins.float*'

    my_model = MyModel()
    my_model.my_attr = None
    my_model.my_nullable_attr = None
    my_model.my_not_nullable_attr = None
    my_model.my_attr = 42
    my_model.my_nullable_attr = 42
    my_model.my_not_nullable_attr = 42
    """)


def test_unicode_attribute(assert_mypy_output):
    assert_mypy_output("""
    from pynamodb.attributes import UnicodeAttribute
    from pynamodb.models import Model

    class MyModel(Model):
        my_attr = UnicodeAttribute()
        my_nullable_attr = UnicodeAttribute(null=True)

    reveal_type(MyModel.my_attr)  # N: Revealed type is 'pynamodb.attributes.UnicodeAttribute'
    reveal_type(MyModel.my_nullable_attr)  # N: Revealed type is 'pynamodb.attributes.UnicodeAttribute[None]'
    reveal_type(MyModel().my_attr)  # N: Revealed type is 'builtins.str*'
    reveal_type(MyModel().my_nullable_attr)  # N: Revealed type is 'Union[builtins.str*, None]'

    MyModel().my_attr.lower()
    MyModel().my_nullable_attr.lower()  # E: Item "None" of "Optional[str]" has no attribute "lower"  [union-attr]
    """)


def test_custom_attribute(assert_mypy_output):
    assert_mypy_output("""
    from pynamodb.attributes import Attribute
    from pynamodb.models import Model

    class BinaryAttribute(Attribute[bytes]):
        def do_something(self) -> None: ...

    class MyModel(Model):
        my_attr = BinaryAttribute()
        my_nullable_attr = BinaryAttribute(null=True)

    reveal_type(MyModel.my_attr)  # N: Revealed type is '__main__.BinaryAttribute'
    reveal_type(MyModel.my_attr.exists)  # N: Revealed type is 'def () -> pynamodb.expressions.condition.Exists'
    reveal_type(MyModel.my_attr.do_something)  # N: Revealed type is 'def ()'
    reveal_type(MyModel().my_attr)  # N: Revealed type is 'builtins.bytes*'

    reveal_type(MyModel.my_nullable_attr)  # N: Revealed type is '__main__.BinaryAttribute[None]'
    reveal_type(MyModel.my_nullable_attr.exists)  # N: Revealed type is 'def () -> pynamodb.expressions.condition.Exists'
    reveal_type(MyModel.my_nullable_attr.do_something)  # N: Revealed type is 'def ()'
    reveal_type(MyModel().my_nullable_attr)  # N: Revealed type is 'Union[builtins.bytes*, None]'
    """)  # noqa: E501


def test_unexpected_number_of_nulls(assert_mypy_output):
    assert_mypy_output("""
    from pynamodb.attributes import NumberAttribute
    from pynamodb.models import Model

    class MyModel(Model):
        my_attr = NumberAttribute(True, True, True, null=True)  # E: "NumberAttribute" gets multiple values for keyword argument "null"  [misc]

    reveal_type(MyModel().my_attr)  # N: Revealed type is 'builtins.float*'
    """)  # noqa: E501


def test_unexpected_value_of_null(assert_mypy_output):
    assert_mypy_output("""
    from pynamodb.attributes import NumberAttribute
    from pynamodb.models import Model

    class MyModel(Model):
        my_attr = NumberAttribute(null=bool(5))  # E: 'null' argument is not constant False or True, cannot deduce optionality  [misc]

    reveal_type(MyModel().my_attr)  # N: Revealed type is 'builtins.float*'
    """)  # noqa: E501


def test_function_hook_fallback(assert_mypy_output):
    assert_mypy_output("""
    def foo():
        pass

    foo()
    """)
