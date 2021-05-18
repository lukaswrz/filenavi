class GeneralError(Exception):
    def __init__(self, status_code, message):
        super().__init__(self)
        self.message = message


class Unauthorized(GeneralError):
    def __init__(self):
        super().__init__(401, "Unauthorized")


class NotAuthenticated(GeneralError):
    def __init__(self):
        super().__init__(403, "Not authenticated")


class AuthenticationFailure(GeneralError):
    def __init__(self):
        super().__init__(403, "Authentication failure")


class MalformedRequest(GeneralError):
    def __init__(self):
        super().__init__(400, "Malformed request")
