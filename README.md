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

# Model construction

When calling a model's constructor, we will ensure all keywords and their types match the model's attributes:
```py
from pynamodb.attributes import UnicodeAttribute
from pynamodb.models import Model

class MyModel(Model):
  my_key = UnicodeAttribute()
  my_value = UnicodeAttribute(null=True)

...
# error: Argument "my_key" to "MyModel" has incompatible type "None"; expected "str"
# error: Argument "my_value" to "MyModel" has incompatible type "int"; expected "Optional[str]"
my_model = MyModel(my_key=None, my_value=42)
```

Since it's common to initialize an empty or partial model (i.e. `MyModel()`),
all arguments (regardless of nullability or defaults) are keyword-only and optional.
