"""Files API router."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.core.security import get_current_user, CurrentUser
from app.models.attached_file import AttachedFile
from app.models.interaction import Interaction
from app.schemas.attached_file import AttachedFileResponse

router = APIRouter()


@router.get("/{interaction_id}/files", response_model=List[AttachedFileResponse])
async def get_files(
    interaction_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all files for an interaction."""
    query = select(AttachedFile).where(AttachedFile.interaction_id == interaction_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/{interaction_id}/files", response_model=AttachedFileResponse)
async def upload_file(
    interaction_id: int,
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload file to interaction."""
    # Verify interaction exists
    interaction_query = select(Interaction).where(Interaction.id == interaction_id)
    interaction_result = await db.execute(interaction_query)
    interaction = interaction_result.scalar_one_or_none()
    
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")
    
    # Validate file type (basic check)
    allowed_types = [
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "image/jpeg",
        "image/png",
    ]
    
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"File type {file.content_type} not allowed")
    
    # Read file content (in production, save to S3/MinIO)
    content = await file.read()
    
    attached_file = AttachedFile(
        filename=file.filename,
        content_type=file.content_type,
        file_data=content,  # Store as bytes (in production, store path to S3)
        interaction_id=interaction_id,
    )
    
    db.add(attached_file)
    await db.commit()
    await db.refresh(attached_file)
    
    return attached_file


@router.delete("/{file_id}")
async def delete_file(
    file_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete file."""
    query = select(AttachedFile).where(AttachedFile.id == file_id)
    result = await db.execute(query)
    file_obj = result.scalar_one_or_none()
    
    if not file_obj:
        raise HTTPException(status_code=404, detail="File not found")
    
    await db.delete(file_obj)
    await db.commit()
    
    return {"message": "File deleted"}
