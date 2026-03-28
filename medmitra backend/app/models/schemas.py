from pydantic import BaseModel
from typing import Literal


class Medication(BaseModel):
    name: str
    dosage: str
    purpose: str
    frequency: str


class Warning(BaseModel):
    type: Literal["high", "moderate", "low"]
    title: str
    description: str


class AnalysisResponse(BaseModel):
    summary: str
    medications: list[Medication]
    warnings: list[Warning]
    instructions: list[str]


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
