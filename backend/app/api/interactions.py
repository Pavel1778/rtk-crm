"""Interactions API router."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.core.security import get_current_user, CurrentUser
from app.models.interaction import Interaction
from app.models.workflow_stage import WorkflowStage
from app.models.user import User
from app.schemas.interaction import (
    InteractionCreate,
    InteractionUpdate,
    InteractionResponse,
    InteractionListResponse,
    MoveRequest,
)
from app.services.email_service import send_status_change_notification

router = APIRouter()


@router.get("/", response_model=InteractionListResponse)
async def get_interactions(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    stage_id: Optional[int] = None,
    university_id: Optional[int] = None,
    product_id: Optional[int] = None,
    assigned_kam_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
):
    """Get all interactions with optional filters."""
    query = select(Interaction)
    
    # Filter by role
    if current_user.role == "user":
        query = query.where(Interaction.assigned_kam_id == current_user.id)
    
    # Apply filters
    if stage_id:
        query = query.where(Interaction.current_stage_id == stage_id)
    if university_id:
        query = query.where(Interaction.university_id == university_id)
    if product_id:
        query = query.where(Interaction.product_id == product_id)
    if assigned_kam_id and current_user.role in ["manager", "admin"]:
        query = query.where(Interaction.assigned_kam_id == assigned_kam_id)
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    interactions = result.scalars().all()
    
    # Get total count
    count_query = select(func.count()).select_from(Interaction)
    if current_user.role == "user":
        count_query = count_query.where(Interaction.assigned_kam_id == current_user.id)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    return InteractionListResponse(items=interactions, total=total)


@router.get("/{interaction_id}", response_model=InteractionResponse)
async def get_interaction(
    interaction_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get interaction by ID."""
    query = select(Interaction).where(Interaction.id == interaction_id)
    
    # Check permissions
    if current_user.role == "user":
        query = query.where(Interaction.assigned_kam_id == current_user.id)
    
    result = await db.execute(query)
    interaction = result.scalar_one_or_none()
    
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")
    
    return interaction


@router.post("/", response_model=InteractionResponse)
async def create_interaction(
    data: InteractionCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create new interaction."""
    # Check if user can assign to other KAMs
    if data.assigned_kam_id and data.assigned_kam_id != current_user.id:
        if current_user.role not in ["manager", "admin"]:
            raise HTTPException(status_code=403, detail="Not enough permissions")
    
    interaction = Interaction(**data.model_dump())
    db.add(interaction)
    await db.commit()
    await db.refresh(interaction)
    
    return interaction


@router.patch("/{interaction_id}", response_model=InteractionResponse)
async def update_interaction(
    interaction_id: int,
    data: InteractionUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update interaction."""
    query = select(Interaction).where(Interaction.id == interaction_id)
    if current_user.role == "user":
        query = query.where(Interaction.assigned_kam_id == current_user.id)
    
    result = await db.execute(query)
    interaction = result.scalar_one_or_none()
    
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")
    
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(interaction, field, value)
    
    await db.commit()
    await db.refresh(interaction)
    
    return interaction


@router.delete("/{interaction_id}")
async def delete_interaction(
    interaction_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete interaction."""
    query = select(Interaction).where(Interaction.id == interaction_id)
    if current_user.role == "user":
        query = query.where(Interaction.assigned_kam_id == current_user.id)
    
    result = await db.execute(query)
    interaction = result.scalar_one_or_none()
    
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")
    
    await db.delete(interaction)
    await db.commit()
    
    return {"message": "Interaction deleted"}


@router.patch("/{interaction_id}/move", response_model=InteractionResponse)
async def move_interaction(
    interaction_id: int,
    data: MoveRequest,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Move interaction to another stage."""
    query = select(Interaction).where(Interaction.id == interaction_id)
    if current_user.role == "user":
        query = query.where(Interaction.assigned_kam_id == current_user.id)
    
    result = await db.execute(query)
    interaction = result.scalar_one_or_none()
    
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")
    
    # Verify new stage exists
    stage_query = select(WorkflowStage).where(WorkflowStage.id == data.new_stage_id)
    stage_result = await db.execute(stage_query)
    new_stage = stage_result.scalar_one_or_none()
    
    if not new_stage:
        raise HTTPException(status_code=404, detail="Stage not found")
    
    old_stage_id = interaction.current_stage_id
    interaction.current_stage_id = data.new_stage_id
    
    await db.commit()
    await db.refresh(interaction)
    
    # Send email notification asynchronously
    if interaction.assigned_kam and interaction.assigned_kam.email:
        background_tasks.add_task(
            send_status_change_notification,
            interaction=interaction,
            new_stage=new_stage,
            recipient_email=interaction.assigned_kam.email,
        )
    
    return interaction
