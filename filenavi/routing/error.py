class GeneralError(Exception):
    def __init__(self, message):
        super().__init__(self)
        self.message = message


class NotAccessible(GeneralError):
    def __init__(self):
        super().__init__("Not accessible")


class Unauthorized(GeneralError):
    def __init__(self):
        super().__init__("Unauthorized")


class NotAuthenticated(GeneralError):
    def __init__(self):
        super().__init__("Not authenticated")


class AuthenticationFailure(GeneralError):
    def __init__(self):
        super().__init__("Authentication failure")


class MalformedRequest(GeneralError):
    def __init__(self):
        super().__init__("Malformed request")
