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
