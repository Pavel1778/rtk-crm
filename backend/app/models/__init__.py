"""Я не могу напрямую зайти на GitHub и сделать пуш, так как у меня нет доступа к твоему аккаунту и токену. Но я подготовил для тебя **готовый код**, который нужно просто скопировать и вставить через интерфейс GitHub. Это займет 1 минуту.

### 🛠 Шаг 1: Исправь `backend/app/models/__init__.py`

1. Открой файл по ссылке: [github.com/Pavel1778/rtk-crm/edit/main/backend/app/models/__init__.py](https://github.com/Pavel1778/rtk-crm/edit/main/backend/app/models/__init__.py)
2. Полностью замени его содержимое на этот код:

```python
"""Экспорт моделей."""
from .base import Base
from .user import User
from .university import University
from .workflow import WorkflowStage
from .comment import Comment
from .file import AttachedFile
from .log import ActionLog

# Временно отключено до создания файлов
# from .it_product import ITProduct
# from .it_direction import ITDirection
# from .interaction import Interaction
# from .interaction_history import InteractionHistory

__all__ = [
    "Base",
    "User",
    "University",
    "WorkflowStage",
    "Comment",
    "AttachedFile",
    "ActionLog",
]
