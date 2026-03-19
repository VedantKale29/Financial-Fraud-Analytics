import sys

class DataPlatformException(Exception):
    def __init__(self, error_message: str, error_details: sys, *, cause: Exception | None = None):
        super().__init__(error_message)
        self.error_message = error_message
        self.cause = cause

        _, _, exc_tb = error_details.exc_info()
        self.lineno = exc_tb.tb_lineno if exc_tb else None
        self.file_name = exc_tb.tb_frame.f_code.co_filename if exc_tb else None

    def __str__(self):
        base = f"Error in [{self.file_name}] at line [{self.lineno}] : {self.error_message}"
        if self.cause:
            return f"{base} | Cause: {repr(self.cause)}"
        return base