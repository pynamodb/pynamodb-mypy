# pynamodb-mypy

A plugin for mypy which gives it deeper understanding of PynamoDB (beyond what's possible through type stubs).

# Usage

Add it to the `plugins` option of the `[mypy]` section in your mypy.ini:
```ini
[mypy]
plugins = pynamodb_mypy
```

# Nullable attributes

When declaring attributes with `null=True`, the value types would become optional. For example:
```py
from pynamodb.attributes import UnicodeAttribute
from pynamodb.models import Model

class MyModel(Model):
  my_key = UnicodeAttribute()
  my_value = UnicodeAttribute(null=True)

...
my_model = MyModel.get('key')
if my_model.my_value.lower() == 'foo':  # error: Item "None" of "Optional[str]" has no attribute "lower"
   print("Value is foo")
```
would have to be changed to, e.g.:
```py
if my_model.my_value and my_model.my_value.lower() == 'foo':
   print("Value is foo")
```

# Typed model initializers

When declaring models, the `__init__` method would be typed to accept only the attributes declared in the model. For example:
```py
from pynamodb.models import Model
from pynamodb.attributes import NumberAttribute
from pynamodb.attributes import UnicodeAttribute

class MyModel(Model):
  my_key = UnicodeAttribute(hash_key=True)
  my_value = NumberAttribute(null=True)

# Existing attributes would be enforced:
_ = MyModel(my_key='key', my_value=42, my_other_value='other_value')  # error: Unexpected keyword argument "my_other_value" for "MyModel"

# Typing would be enforced:
_ = MyModel(my_key='key', my_value='42')  # error: Argument 2 to "MyModel" has incompatible type "str"; expected "Optional[int]"

# Nullability will be enforced::
_ = MyModel(my_key='key', my_value=None)
_ = MyModel(my_key=None, my_value=None)  # error: Argument "my_key" to "MyModel" has incompatible type "None"; expected "str"

# The hash key and range key can also be passed as positional arguments:
_ = MyModel('key')
_ = MyModel(42)  # error: Argument 1 to "MyModel" has incompatible type "int"; expected "str"
```
