from fastapi import APIRouter, UploadFile, File
from typing import List
from app.services.multi_prescription import analyze_multiple_images

router = APIRouter()

@router.post("/analyze-multiple")
async def analyze_multiple(files: List[UploadFile] = File(...)):

    image_bytes_list = []

    for file in files:
        image_bytes = await file.read()
        image_bytes_list.append(image_bytes)

    result = analyze_multiple_images(image_bytes_list)

    return result