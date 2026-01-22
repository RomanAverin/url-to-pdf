"""Progress reporter using rich library."""

from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn

from .state_machine import ConversionStateMachine, JobState


class ProgressReporter:
    """Progress reporter with rich progress bar."""

    def __init__(self, url: str):
        """Initialize progress reporter.

        Args:
            url: The URL being converted
        """
        self.url = url
        self.console = Console()
        self.progress = Progress(
            TextColumn("[bold blue]{task.fields[status]}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console,
        )
        self.task_id = None
        self.state_machine = ConversionStateMachine()

    def start(self):
        """Start displaying progress."""
        self.progress.start()
        self.task_id = self.progress.add_task(
            description="", total=100.0, status="Starting..."
        )

    def stop(self):
        """Stop displaying progress."""
        self.progress.stop()

    def update_state(self, new_state: JobState, step_description: str = ""):
        """Update state machine state.

        Args:
            new_state: The new state to transition to
            step_description: Optional description of the step
        """
        self.state_machine.transition_to(new_state, step_description)
        self._refresh_display()

    def update_images_progress(self, downloaded: int, total: int):
        """Update image download progress.

        Args:
            downloaded: Number of images downloaded
            total: Total number of images to download
        """
        self.state_machine.update_images_progress(downloaded, total)
        self._refresh_display()

    def mark_failed(self, error: str):
        """Mark conversion as failed.

        Args:
            error: Error message
        """
        self.state_machine.mark_failed(error)
        self._refresh_display()

    def _refresh_display(self):
        """Refresh progress bar display."""
        if self.task_id is None:
            return

        prog = self.state_machine.progress

        # Format status text
        status_text = self._format_status(prog.state)
        if prog.state == JobState.DOWNLOADING_IMAGES and prog.images_total > 0:
            status_text += f" ({prog.images_downloaded}/{prog.images_total})"

        self.progress.update(self.task_id, completed=prog.progress, status=status_text)

    def _format_status(self, state: JobState) -> str:
        """Format state for display.

        Args:
            state: The current job state

        Returns:
            Formatted status string
        """
        status_map = {
            JobState.PENDING: "Pending...",
            JobState.EXTRACTING: "Extracting article...",
            JobState.DOWNLOADING_IMAGES: "Downloading images",
            JobState.GENERATING_PDF: "Generating PDF...",
            JobState.COMPLETED: "Completed",
            JobState.FAILED: "Failed",
        }
        return status_map.get(state, "Unknown")

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
