import sys

class DataPlatformException(Exception):
    def __init__(self, error_message: str, stage: str, error_details: sys):
        super().__init__(error_message)
        _, _, exc_tb = error_details.exc_info()
        self.lineno = exc_tb.tb_lineno if exc_tb else "Unknown"
        self.file_name = exc_tb.tb_frame.f_code.co_filename if exc_tb else "Unknown"
        self.stage = stage # New: identify if it was 'ETL_EXTRACTION' or 'ETL_LOADING'
        self.error_message = error_message

    def __str__(self):
        return f"Stage: [{self.stage}] | File: [{self.file_name}] | Line: [{self.lineno}] | Error: {self.error_message}"