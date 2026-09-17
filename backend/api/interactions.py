from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.security import get_current_user
from backend.db.session import get_db
from backend.models.entities import (
    Action,
    Comment,
    Interaction,
    ITProduct,
    University,
    User,
    WorkflowStageRef,
)
from backend.schemas.entities import (
    ActionCreate,
    ActionRead,
    ActionUpdate,
    BoardColumn,
    BoardResponse,
    CommentCreate,
    CommentRead,
    InteractionCard,
    InteractionCreate,
    InteractionRead,
    InteractionUpdate,
)

router = APIRouter(prefix="/api/interactions", tags=["interactions"])


# ---------- Вспомогательные функции ----------
async def _get_or_404(db: AsyncSession, interaction_id: int) -> Interaction:
    interaction = await db.get(Interaction, interaction_id)
    if interaction is None:
        raise HTTPException(status_code=404, detail="Взаимодействие не найдено")
    return interaction


async def _default_stage(db: AsyncSession) -> WorkflowStageRef:
    stage = await db.scalar(
        select(WorkflowStageRef)
        .where(WorkflowStageRef.is_active.is_(True))
        .order_by(WorkflowStageRef.order)
    )
    if stage is None:
        raise HTTPException(
            status_code=409,
            detail="Воркфлоу не настроен: добавьте хотя бы один этап",
        )
    return stage


async def _card(db: AsyncSession, interaction: Interaction) -> InteractionCard:
    """Карточка канбан-доски с tên вуза/продукта/этапа и счётчиками."""
    university = await db.get(University, interaction.university_id)
    product = (
        await db.get(ITProduct, interaction.product_id)
        if interaction.product_id
        else None
    )
    stage = await db.get(WorkflowStageRef, interaction.stage_id)
    specialist = (
        await db.get(User, interaction.rkn_specialist_id)
        if interaction.rkn_specialist_id
        else None
    )
    actions_total = await db.scalar(
        select(func.count(Action.id)).where(Action.interaction_id == interaction.id)
    )
    actions_open = await db.scalar(
        select(func.count(Action.id)).where(
            Action.interaction_id == interaction.id,
            Action.is_completed.is_(False),
        )
    )
    comments_count = await db.scalar(
        select(func.count(Comment.id)).where(
            Comment.interaction_id == interaction.id
        )
    )
    return InteractionCard(
        id=interaction.id,
        university_id=interaction.university_id,
        university_name=university.name if university else None,
        product_id=interaction.product_id,
        product_name=product.name if product else None,
        stage_id=interaction.stage_id,
        stage_name=stage.name if stage else None,
        stage_code=stage.code if stage else None,
        contract_number=interaction.contract_number,
        university_specialist=interaction.university_specialist,
        rkn_specialist_name=specialist.full_name if specialist else None,
        is_active=interaction.is_active,
        actions_open=actions_open or 0,
        actions_total=actions_total or 0,
        comments_count=comments_count or 0,
    )


async def _read(db: AsyncSession, interaction: Interaction) -> InteractionRead:
    university = await db.get(University, interaction.university_id)
    product = (
        await db.get(ITProduct, interaction.product_id)
        if interaction.product_id
        else None
    )
    stage = await db.get(WorkflowStageRef, interaction.stage_id)
    specialist = (
        await db.get(User, interaction.rkn_specialist_id)
        if interaction.rkn_specialist_id
        else None
    )
    payload = InteractionRead.model_validate(interaction)
    return payload.model_copy(
        update={
            "university_name": university.name if university else None,
            "product_name": product.name if product else None,
            "stage_name": stage.name if stage else None,
            "stage_code": stage.code if stage else None,
            "rkn_specialist_name": specialist.full_name if specialist else None,
        }
    )


async def _ensure_unique(
    db: AsyncSession,
    university_id: int,
    product_id: int | None,
    exclude_id: int | None = None,
) -> None:
    """Взаимодействие «вуз + продукт» должно быть единственным."""
    stmt = select(Interaction.id).where(
        Interaction.university_id == university_id,
        Interaction.product_id.is_(None)
        if product_id is None
        else Interaction.product_id == product_id,
    )
    if exclude_id is not None:
        stmt = stmt.where(Interaction.id != exclude_id)
    clash = await db.scalar(stmt)
    if clash:
        raise HTTPException(
            status_code=409,
            detail="Такое взаимодействие уже зарегистрировано (вуз + продукт)",
        )


# ---------- Канбан-доска ----------
@router.get("/board", response_model=BoardResponse)
async def get_board(
    search: str | None = Query(default=None, description="Поиск по названию вуза"),
    product_id: int | None = None,
    rkn_specialist_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> BoardResponse:
    """Колонки = этапы воркфлоу, карточки = взаимодействия."""
    stmt = select(WorkflowStageRef).order_by(WorkflowStageRef.order)

    filters: list = [Interaction.is_active.is_(True)]
    if product_id is not None:
        filters.append(Interaction.product_id == product_id)
    if rkn_specialist_id is not None:
        filters.append(Interaction.rkn_specialist_id == rkn_specialist_id)
    if search:
        matching = select(University.id).where(University.name.ilike(f"%{search}%"))
        filters.append(Interaction.university_id.in_(matching))

    interactions = list(
        await db.scalars(
            select(Interaction).where(*filters).order_by(Interaction.id)
        )
    )
    cards = [await _card(db, item) for item in interactions]

    stages = list(await db.scalars(stmt))
    columns = [
        BoardColumn(
            stage=await _stage_with_count(db, stage),
            interactions=[c for c in cards if c.stage_id == stage.id],
        )
        for stage in stages
    ]
    return BoardResponse(columns=columns, total=len(cards))


async def _stage_with_count(
    db: AsyncSession, stage: WorkflowStageRef
) -> "object":
    from backend.schemas.entities import WorkflowStageRead

    count = await db.scalar(
        select(func.count(Interaction.id)).where(
            Interaction.stage_id == stage.id, Interaction.is_active.is_(True)
        )
    )
    return WorkflowStageRead.model_validate(stage).model_copy(
        update={"interaction_count": count or 0}
    )


# ---------- Список взаимодействий ----------
@router.get("", response_model=list[InteractionRead])
async def list_interactions(
    stage_id: int | None = None,
    university_id: int | None = None,
    product_id: int | None = None,
    include_inactive: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[InteractionRead]:
    filters: list = []
    if not include_inactive:
        filters.append(Interaction.is_active.is_(True))
    if stage_id is not None:
        filters.append(Interaction.stage_id == stage_id)
    if university_id is not None:
        filters.append(Interaction.university_id == university_id)
    if product_id is not None:
        filters.append(Interaction.product_id == product_id)

    stmt = select(Interaction).order_by(Interaction.id)
    if filters:
        stmt = stmt.where(*filters)
    interactions = list(await db.scalars(stmt))
    return [await _read(db, item) for item in interactions]


@router.get("/{interaction_id}", response_model=InteractionRead)
async def get_interaction(
    interaction_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> InteractionRead:
    return await _read(db, await _get_or_404(db, interaction_id))


@router.post("", response_model=InteractionRead, status_code=201)
async def create_interaction(
    payload: InteractionCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> InteractionRead:
    """Регистрация взаимодействия «вуз + продукт» на первом этапе."""
    if await db.get(University, payload.university_id) is None:
        raise HTTPException(status_code=404, detail="Вуз не найден")
    if payload.product_id is not None:
        if await db.get(ITProduct, payload.product_id) is None:
            raise HTTPException(status_code=404, detail="Продукт не найден")

    await _ensure_unique(db, payload.university_id, payload.product_id)

    if payload.stage_id is not None:
        stage = await db.get(WorkflowStageRef, payload.stage_id)
        if stage is None:
            raise HTTPException(status_code=404, detail="Этап не найден")
    else:
        stage = await _default_stage(db)

    interaction = Interaction(
        university_id=payload.university_id,
        product_id=payload.product_id,
        stage_id=stage.id,
    )
    db.add(interaction)
    await db.commit()
    await db.refresh(interaction)
    return await _read(db, interaction)


@router.patch("/{interaction_id}", response_model=InteractionRead)
async def update_interaction(
    interaction_id: int,
    payload: InteractionUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> InteractionRead:
    interaction = await _get_or_404(db, interaction_id)
    data = payload.model_dump(exclude_unset=True)

    if "product_id" in data or "stage_id" in data:
        product_id = data.get("product_id", interaction.product_id)
        await _ensure_unique(
            db, interaction.university_id, product_id, exclude_id=interaction.id
        )
        if product_id is not None and await db.get(ITProduct, product_id) is None:
            raise HTTPException(status_code=404, detail="Продукт не найден")
        stage_id = data.get("stage_id", interaction.stage_id)
        if stage_id is not None and await db.get(WorkflowStageRef, stage_id) is None:
            raise HTTPException(status_code=404, detail="Этап не найден")

    for field, value in data.items():
        setattr(interaction, field, value)
    await db.commit()
    await db.refresh(interaction)
    return await _read(db, interaction)


@router.delete("/{interaction_id}", status_code=204)
async def delete_interaction(
    interaction_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> None:
    interaction = await _get_or_404(db, interaction_id)
    await db.delete(interaction)
    await db.commit()


# ---------- Перемещение по этапам ----------
@router.post("/{interaction_id}/move", response_model=InteractionRead)
async def move_interaction(
    interaction_id: int,
    stage_id: int = Query(description="Целевой этап"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> InteractionRead:
    """Перемещение карточки на другой этап (drag-and-drop на доске)."""
    interaction = await _get_or_404(db, interaction_id)
    stage = await db.get(WorkflowStageRef, stage_id)
    if stage is None:
        raise HTTPException(status_code=404, detail="Этап не найден")
    if not stage.is_active:
        raise HTTPException(status_code=409, detail="Этап отключён")
    interaction.stage_id = stage_id
    await db.commit()
    await db.refresh(interaction)
    return await _read(db, interaction)


# ---------- Задачи ----------
@router.get("/{interaction_id}/actions", response_model=list[ActionRead])
async def list_actions(
    interaction_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[ActionRead]:
    await _get_or_404(db, interaction_id)
    rows = (
        await db.execute(
            select(Action, User.full_name)
            .outerjoin(User, Action.author_id == User.id)
            .where(Action.interaction_id == interaction_id)
            .order_by(Action.is_completed, Action.due_date)
        )
    ).all()
    return [
        ActionRead(
            id=action.id,
            interaction_id=action.interaction_id,
            title=action.title,
            description=action.description,
            due_date=action.due_date,
            is_completed=action.is_completed,
            author_name=author_name,
        )
        for action, author_name in rows
    ]


@router.post("/{interaction_id}/actions", response_model=ActionRead, status_code=201)
async def create_action(
    interaction_id: int,
    payload: ActionCreate,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
) -> ActionRead:
    await _get_or_404(db, interaction_id)
    action = Action(
        interaction_id=interaction_id,
        author_id=current.id,
        **payload.model_dump(),
    )
    db.add(action)
    await db.commit()
    await db.refresh(action)
    return ActionRead(
        id=action.id,
        interaction_id=action.interaction_id,
        title=action.title,
        description=action.description,
        due_date=action.due_date,
        is_completed=action.is_completed,
        author_name=current.full_name,
    )


@router.patch("/actions/{action_id}", response_model=ActionRead)
async def update_action(
    action_id: int,
    payload: ActionUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ActionRead:
    action = await db.get(Action, action_id)
    if action is None:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(action, field, value)
    await db.commit()
    await db.refresh(action)
    author = await db.get(User, action.author_id) if action.author_id else None
    return ActionRead(
        id=action.id,
        interaction_id=action.interaction_id,
        title=action.title,
        description=action.description,
        due_date=action.due_date,
        is_completed=action.is_completed,
        author_name=author.full_name if author else None,
    )


@router.delete("/actions/{action_id}", status_code=204)
async def delete_action(
    action_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> None:
    action = await db.get(Action, action_id)
    if action is None:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    await db.delete(action)
    await db.commit()


# ---------- Комментарии ----------
@router.get("/{interaction_id}/comments", response_model=list[CommentRead])
async def list_comments(
    interaction_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[CommentRead]:
    await _get_or_404(db, interaction_id)
    rows = (
        await db.execute(
            select(Comment, User.full_name)
            .outerjoin(User, Comment.author_id == User.id)
            .where(Comment.interaction_id == interaction_id)
            .order_by(Comment.created_at)
        )
    ).all()
    return [
        CommentRead(
            id=comment.id,
            interaction_id=comment.interaction_id,
            text=comment.text,
            author_name=author_name,
            created_at=comment.created_at,
        )
        for comment, author_name in rows
    ]


@router.post(
    "/{interaction_id}/comments", response_model=CommentRead, status_code=201
)
async def create_comment(
    interaction_id: int,
    payload: CommentCreate,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
) -> CommentRead:
    await _get_or_404(db, interaction_id)
    comment = Comment(
        interaction_id=interaction_id, text=payload.text, author_id=current.id
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return CommentRead(
        id=comment.id,
        interaction_id=comment.interaction_id,
        text=comment.text,
        author_name=current.full_name,
        created_at=comment.created_at,
    )


@router.delete("/comments/{comment_id}", status_code=204)
async def delete_comment(
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
) -> None:
    comment = await db.get(Comment, comment_id)
    if comment is None:
        raise HTTPException(status_code=404, detail="Комментарий не найден")
    if not current.is_admin and comment.author_id != current.id:
        raise HTTPException(
            status_code=403, detail="Можно удалять только свои комментарии"
        )
    await db.delete(comment)
    await db.commit()
