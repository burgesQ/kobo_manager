"""Exit codes shared by every CLI. Packages re-export them from their own
``exit_codes.py``. Never return bare integers from CLI code."""

SUCCESS = 0
CLI_ERROR = 2  # argparse usage errors
DEVICE_NOT_FOUND = 3
PHASE_ERROR = 4
UNSAFE_FIRMWARE = 5
PROCESSING_ERROR = 6
HARDWARE_MISMATCH = 7
NOT_IMPLEMENTED = 64
