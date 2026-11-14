from typing import Optional


class FinkernelError(Exception):
    pass


class PSLSyntaxError(FinkernelError):
    def __init__(self, message: str, line: Optional[int] = None, column: Optional[int] = None):
        super().__init__(message)
        self.line = line
        self.column = column


class PSLTypeError(FinkernelError):
    pass


class PSLValidationError(FinkernelError):
    pass
