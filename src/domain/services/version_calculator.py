from src.domain.value_objects import VersionNumber


class VersionCalculator:
    def calculate_next_version(
        self,
        current_version: VersionNumber,
        change_type: str,
    ) -> VersionNumber:
        if change_type == "breaking":
            return current_version.increment_major()
        elif change_type == "feature":
            return current_version.increment_minor()
        else:
            return current_version.increment_patch()
