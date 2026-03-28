from app.models.schemas import AnalysisResponse, Medication, Warning


async def get_mock_analysis() -> AnalysisResponse:
    """
    Returns a realistic mock prescription analysis response.
    OCR and file processing are intentionally not implemented.
    This mock data is designed to match the frontend's expected structure exactly.
    """
    return AnalysisResponse(
        summary="Mild fever with bacterial infection. Patient presents with elevated temperature "
                "and signs of upper respiratory tract infection requiring antibiotic therapy.",
        medications=[
            Medication(
                name="Paracetamol",
                dosage="500mg",
                purpose="Reduce fever and relieve pain",
                frequency="Twice daily (every 12 hours)",
            ),
            Medication(
                name="Amoxicillin",
                dosage="250mg",
                purpose="Treat bacterial infection",
                frequency="Three times daily (every 8 hours)",
            ),
            Medication(
                name="Cetirizine",
                dosage="10mg",
                purpose="Relieve allergy symptoms and nasal congestion",
                frequency="Once daily at bedtime",
            ),
        ],
        warnings=[
            Warning(
                type="high",
                title="Antibiotic Allergy Risk",
                description="Check for penicillin or amoxicillin allergy before administration. "
                            "Discontinue immediately and seek medical help if rash, swelling, "
                            "or difficulty breathing occurs.",
            ),
            Warning(
                type="moderate",
                title="Avoid Alcohol",
                description="Do not consume alcohol while taking these medications. "
                            "Alcohol may intensify drowsiness caused by Cetirizine and "
                            "reduce the effectiveness of Amoxicillin.",
            ),
            Warning(
                type="low",
                title="Drowsiness Advisory",
                description="Cetirizine may cause mild drowsiness in some patients. "
                            "Avoid driving or operating heavy machinery until you know "
                            "how this medication affects you.",
            ),
        ],
        instructions=[
            "Take all medications with a full glass of water.",
            "Complete the full course of Amoxicillin (7 days) even if symptoms improve earlier.",
            "Paracetamol should not exceed 4 doses in 24 hours.",
            "Store medications at room temperature, away from direct sunlight and moisture.",
            "Take Cetirizine at the same time each day for best results.",
            "Consult your doctor immediately if symptoms worsen after 48 hours.",
            "Do not crush or chew the tablets; swallow them whole.",
        ],
    )
