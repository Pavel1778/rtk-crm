"""Workflow stages API router."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.core.security import get_current_user, CurrentUser, require_role
from app.models.workflow_stage import WorkflowStage
from app.models.interaction import Interaction
from app.schemas.workflow_stage import (
    WorkflowStageCreate,
    WorkflowStageUpdate,
    WorkflowStageResponse,
    WorkflowStageReorder,
)

router = APIRouter()


@router.get("/stages", response_model=List[WorkflowStageResponse])
async def get_stages(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all workflow stages ordered by position."""
    query = select(WorkflowStage).order_by(WorkflowStage.order)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/stages", response_model=WorkflowStageResponse)
@require_role(["admin"])
async def create_stage(
    data: WorkflowStageCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create new workflow stage."""
    # Get max order
    max_order_query = select(func.max(WorkflowStage.order))
    max_order_result = await db.execute(max_order_query)
    max_order = max_order_result.scalar() or 0
    
    stage = WorkflowStage(
        **data.model_dump(),
        order=data.order or (max_order + 1)
    )
    db.add(stage)
    await db.commit()
    await db.refresh(stage)
    
    return stage


@router.patch("/stages/{stage_id}", response_model=WorkflowStageResponse)
@require_role(["admin"])
async def update_stage(
    stage_id: int,
    data: WorkflowStageUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update workflow stage."""
    query = select(WorkflowStage).where(WorkflowStage.id == stage_id)
    result = await db.execute(query)
    stage = result.scalar_one_or_none()
    
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")
    
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(stage, field, value)
    
    await db.commit()
    await db.refresh(stage)
    
    return stage


@router.delete("/stages/{stage_id}")
@require_role(["admin"])
async def delete_stage(
    stage_id: int,
    target_stage_id: Optional[int] = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete workflow stage. If stage has interactions, target_stage_id is required."""
    query = select(WorkflowStage).where(WorkflowStage.id == stage_id)
    result = await db.execute(query)
    stage = result.scalar_one_or_none()
    
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")
    
    # Check if stage has active interactions
    interactions_query = select(Interaction).where(Interaction.current_stage_id == stage_id)
    interactions_result = await db.execute(interactions_query)
    interactions = interactions_result.scalars().all()
    
    if interactions:
        if not target_stage_id:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete stage with active interactions. Provide target_stage_id to move them."
            )
        
        # Verify target stage exists
        target_query = select(WorkflowStage).where(WorkflowStage.id == target_stage_id)
        target_result = await db.execute(target_query)
        target_stage = target_result.scalar_one_or_none()
        
        if not target_stage:
            raise HTTPException(status_code=404, detail="Target stage not found")
        
        # Move interactions to target stage
        for interaction in interactions:
            interaction.current_stage_id = target_stage_id
    
    await db.delete(stage)
    await db.commit()
    
    return {"message": "Stage deleted"}


@router.post("/stages/reorder")
@require_role(["admin"])
async def reorder_stages(
    data: WorkflowStageReorder,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reorder workflow stages."""
    for item in data.stages:
        query = select(WorkflowStage).where(WorkflowStage.id == item.id)
        result = await db.execute(query)
        stage = result.scalar_one_or_none()
        
        if stage:
            stage.order = item.order
    
    await db.commit()
    
    return {"message": "Stages reordered"}
