# config

## vars

-   `condition` (`bool`, def.: `True`)

if `condition`:

-   `var` (`int`, def.:`1`)
-   `the_str` (`str`)
-   `test` (`{{ 'bool' if var else 'str' }}`, def.: `{{ '' if var else 'my_str' }}`)

## `_exclude`

-   `copier.yml`
-   `include_me_also.yml`

if `condition`:

-   `include_me.yml`

## Files

-   `{% if test %}test.py{% endif %}`
-   `{% if not_exist %}test_none.py{% endif %}`

# Use case

## Initial

| name        | type                             | default                                                                 | value | when |
| :---------- | :------------------------------- | :---------------------------------------------------------------------- | :---- | :--- |
| `condition` | `bool`                           | `True`                                                                  |       | `O`  |
| `var`       | `int`                            | `1`                                                                     |       | ``   |
| `the_str`   | `str`                            | `"my_str"`                                                              |       | ``   |
| `test`      | `{{ 'bool' if var else 'str' }}` | `{{ '' if var else 'my_str' }}`                                         |       | ``   |
| `_exclude`  |                                  | `copier.yml`, `include_me_also.yml`, (if `condition`: `include_me.yml`) |       |

Files:

- `{% if var %}var.py{% endif %}`
-   `{% if test %}test.py{% endif %}`
-   `{% if not_exist %}test_none.py{% endif %}`

## 1.

```py
{
    "condition": True,
    "var": 1,
    "the_str": "my_str",
    "test": False,
},
```

| name        | type   | default                                               | value      | when |
| :---------- | :----- | :---------------------------------------------------- | :--------- | :--- |
| `condition` | `bool` | `True`                                                | `True`     | `O`  |
| `var`       | `int`  | `1`                                                   | `1`        | `O`  |
| `the_str`   | `str`  | `"my_str"`                                            | `"my_str"` | `O`  |
| `test`      | `bool` | `''`                                                  | `False`    | `O`  |
| `_exclude`  |        | `copier.yml`, `include_me_also.yml`, `include_me.yml` |            |

Files:

- `var.py`

## 2.

```py
{
    "condition": False,
    "var": None,
    "the_str": None,
    "test": None,
},
```

| name        | type                             | default                             | value   | when |
| :---------- | :------------------------------- | :---------------------------------- | :------ | :--- |
| `condition` | `bool`                           | `True`                              | `False` | `O`  |
| `var`       | `int`                            | `1`                                 |         | `X`  |
| `the_str`   | `str`                            | `"my_str"`                          |         | `X`  |
| `test`      | `{{ 'bool' if var else 'str' }}` | `{{ '' if var else 'my_str' }}`     |         | `X`  |
| `_exclude`  |                                  | `copier.yml`, `include_me_also.yml` |         |

Files: None

## 3.

```py
{
    "condition": True,
    "var": 0,
    "the_str": "my_str",
    "test": None,
},
```

| name        | type   | default                                               | value      | when |
| :---------- | :----- | :---------------------------------------------------- | :--------- | :--- |
| `condition` | `bool` | `True`                                                | `True`     | `O`  |
| `var`       | `int`  | `1`                                                   | `0`        | `O`  |
| `the_str`   | `str`  | `"my_str"`                                            | `"my_str"` | `O`  |
| `test`      | `str`  | `'my_str'`                                            | `'my_str'` | `O`  |
| `_exclude`  |        | `copier.yml`, `include_me_also.yml`, `include_me.yml` |            |

Files:

-   `test.py`
