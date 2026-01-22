"""State machine for URL to PDF conversion process."""

from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional


class JobState(Enum):
    """States of URL to PDF conversion."""

    PENDING = auto()
    EXTRACTING = auto()
    DOWNLOADING_IMAGES = auto()
    GENERATING_PDF = auto()
    COMPLETED = auto()
    FAILED = auto()


@dataclass
class ConversionProgress:
    """Progress information for conversion."""

    state: JobState
    progress: float  # 0.0-100.0
    current_step: str = ""
    images_downloaded: int = 0
    images_total: int = 0
    error: Optional[str] = None


class ConversionStateMachine:
    """State machine for conversion process."""

    # Stage weights for progress calculation
    STAGE_WEIGHTS = {
        JobState.EXTRACTING: 20.0,
        JobState.DOWNLOADING_IMAGES: 50.0,
        JobState.GENERATING_PDF: 30.0,
    }

    def __init__(self):
        self.state = JobState.PENDING
        self.progress = ConversionProgress(state=JobState.PENDING, progress=0.0)

    def transition_to(self, new_state: JobState, step_description: str = ""):
        """Transition to a new state.

        Args:
            new_state: The state to transition to
            step_description: Description of the current step

        Raises:
            ValueError: If the transition is invalid
        """
        # Valid state transitions
        valid_transitions = {
            JobState.PENDING: [JobState.EXTRACTING, JobState.FAILED],
            JobState.EXTRACTING: [JobState.DOWNLOADING_IMAGES, JobState.FAILED],
            JobState.DOWNLOADING_IMAGES: [JobState.GENERATING_PDF, JobState.FAILED],
            JobState.GENERATING_PDF: [JobState.COMPLETED, JobState.FAILED],
        }

        if new_state not in valid_transitions.get(self.state, []):
            raise ValueError(f"Invalid transition: {self.state} -> {new_state}")

        self.state = new_state
        self.progress.state = new_state
        self.progress.current_step = step_description

        # Update base progress
        self._update_base_progress()

    def _update_base_progress(self):
        """Update base progress based on current state."""
        base_progress = {
            JobState.PENDING: 0.0,
            JobState.EXTRACTING: 0.0,
            JobState.DOWNLOADING_IMAGES: 20.0,
            JobState.GENERATING_PDF: 70.0,
            JobState.COMPLETED: 100.0,
            JobState.FAILED: 0.0,
        }
        self.progress.progress = base_progress.get(self.state, 0.0)

    def update_images_progress(self, downloaded: int, total: int):
        """Update progress for image downloading stage.

        Args:
            downloaded: Number of images downloaded so far
            total: Total number of images to download
        """
        if self.state != JobState.DOWNLOADING_IMAGES:
            return

        self.progress.images_downloaded = downloaded
        self.progress.images_total = total

        # Calculate progress: 20% (base) + 50% * (downloaded/total)
        if total > 0:
            stage_progress = (downloaded / total) * 50.0
            self.progress.progress = 20.0 + stage_progress

    def mark_failed(self, error: str):
        """Mark conversion as failed.

        Args:
            error: Error message describing the failure
        """
        self.state = JobState.FAILED
        self.progress.state = JobState.FAILED
        self.progress.error = error
