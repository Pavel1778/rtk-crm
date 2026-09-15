from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime
from typing import Optional
from app.models.log import ActionLog
from app.models.university import University


class AuditLogger:
    """Сервис логирования действий для соответствия 152-ФЗ и ФСТЭК."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_action(
        self,
        university_id: int,
        action: str,
        description: Optional[str] = None,
        user: Optional[str] = None,
        ip_address: Optional[str] = None,
        old_value: Optional[dict] = None,
        new_value: Optional[dict] = None,
    ):
        """Логирование действия над университетом."""
        import json
        
        log_entry = ActionLog(
            university_id=university_id,
            action=action,
            description=description,
            user=user,
            ip_address=ip_address,
            old_value=json.dumps(old_value) if old_value else None,
            new_value=json.dumps(new_value) if new_value else None,
        )
        
        self.db.add(log_entry)
        await self.db.commit()

    async def log_create(self, university: University, user: str, ip: Optional[str] = None):
        """Логирование создания записи."""
        await self.log_action(
            university_id=university.id,
            action="CREATE",
            description=f"Создана запись вуза: {university.name}",
            user=user,
            ip_address=ip,
            new_value={
                "name": university.name,
                "status": university.status,
                "manager_name": university.manager_name,
            }
        )

    async def log_update(
        self,
        university: University,
        old_data: dict,
        new_data: dict,
        user: str,
        ip: Optional[str] = None
    ):
        """Логирование обновления записи."""
        changes = []
        for key in set(old_data.keys()) | set(new_data.keys()):
            if old_data.get(key) != new_data.get(key):
                changes.append(f"{key}: {old_data.get(key)} -> {new_data.get(key)}")
        
        await self.log_action(
            university_id=university.id,
            action="UPDATE",
            description=f"Обновлены данные: {', '.join(changes)}",
            user=user,
            ip_address=ip,
            old_value=old_data,
            new_value=new_data,
        )

    async def log_delete(self, university_id: int, university_name: str, user: str, ip: Optional[str] = None):
        """Логирование удаления записи."""
        await self.log_action(
            university_id=university_id,
            action="DELETE",
            description=f"Удалена запись вуза: {university_name}",
            user=user,
            ip_address=ip,
        )

    async def log_workflow_change(
        self,
        university: University,
        old_stage: str,
        new_stage: str,
        user: str,
        ip: Optional[str] = None
    ):
        """Логирование изменения этапа воркфлоу."""
        await self.log_action(
            university_id=university.id,
            action="WORKFLOW_CHANGE",
            description=f"Этап изменён: {old_stage} -> {new_stage}",
            user=user,
            ip_address=ip,
            old_value={"stage": old_stage},
            new_value={"stage": new_stage},
        )
