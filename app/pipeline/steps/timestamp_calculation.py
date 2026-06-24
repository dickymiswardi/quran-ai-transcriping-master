"""
Timestamp Calculation Step - Step 8 of the pipeline.

(OBSOLETE - Bypassed since VerseMatchingStep now handles boundaries directly)
"""

from app.pipeline.base import PipelineStep, PipelineContext

class TimestampCalculationStep(PipelineStep):
    def __init__(self):
        super().__init__()
    
    def validate_input(self, context: PipelineContext) -> bool:
        return True
    
    def process(self, context: PipelineContext) -> PipelineContext:
        self.logger.info("Bypassing TimestampCalculationStep as timestamps are already calculated per Ayah.")
        return context
