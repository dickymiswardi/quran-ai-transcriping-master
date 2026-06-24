"""
Transcription Alignment Step
(Bypassed)
"""
from app.pipeline.base import PipelineStep, PipelineContext
class TranscriptionAlignmentStep(PipelineStep):
    def __init__(self): super().__init__()
    def validate_input(self, context: PipelineContext) -> bool: return True
    def process(self, context: PipelineContext) -> PipelineContext: return context
