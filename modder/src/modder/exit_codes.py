"""Named exit codes. Never return bare integers from CLI code."""

from kobocore.exit_codes import (
    CLI_ERROR,
    DEVICE_NOT_FOUND,
    HARDWARE_MISMATCH,
    INVALID_PACKAGE,
    NOT_IMPLEMENTED,
    PHASE_ERROR,
    PROCESSING_ERROR,
    SUCCESS,
    UNSAFE_FIRMWARE,
    UPDATE_PENDING,
)

__all__ = [
    "CLI_ERROR",
    "DEVICE_NOT_FOUND",
    "HARDWARE_MISMATCH",
    "INVALID_PACKAGE",
    "NOT_IMPLEMENTED",
    "PHASE_ERROR",
    "PROCESSING_ERROR",
    "SUCCESS",
    "UNSAFE_FIRMWARE",
    "UPDATE_PENDING",
]
