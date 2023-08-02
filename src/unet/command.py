class UNetCommand:
    def __init__(self, command_string: str, command_name: str, *args, local=False) -> None:
        self._command_string = command_string
        self._command_name = command_name
        self._arguments = args
        self._local = local

    @property
    def command_stirng(self):
        return self._command_string

    @property
    def command_name(self):
        return self._command_name
    
    @property
    def arguments(self):
        return self._arguments
    
    @property
    def local(self):
        return self._local


class NoSuchUNetCommandException(Exception):
    def __init__(self, name: str) -> None:
        self.message = f'No matching command could be found for \'{name}\''
        self.command_name = name
        super().__init__(self.message)


class UNetCommandIncompatibleArgumentException(Exception):
    def __init__(self, name: str, argc: int, given_argc: int) -> None:
        self.message = f'UNet Command \'{name}\' requires {argc} positional argument(s). {given_argc} given'
        self.command_name = name
        self.required_arguments = argc
        self.given_arguments = given_argc
        super().__init__(self.message)
