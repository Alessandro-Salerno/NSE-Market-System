from unet.command import UNetCommand, NoSuchUNetCommandException, UNetCommandIncompatibleArgumentException
import inspect


def unet_command(name: str, *aliases):
    def inner(handler):
        handler._unet_command_handler = True
        handler._unet_command_name = name
        handler._unet_command_argc = len(inspect.signature(handler).parameters) - 2
        handler._unet_command_aliases = list()
        for alias in aliases:
            handler._unet_command_aliases.append(alias)
        return handler
    
    return inner


class UNetCommandHandler:
    def __init__(self) -> None:
        self._aliases = dict()
        self._commands = dict()
        self._parent = None
        self._top = None

        for attr in dir(self):
            concrete = getattr(self, attr)
            if hasattr(concrete, '_unet_command_handler'):
                self._commands.__setitem__(concrete._unet_command_name, concrete)
                for alias in concrete._unet_command_aliases:
                    self._aliases.__setitem__(alias, concrete)

    def get_command(self, name: str) -> any:
        if name in self._commands:
            return self._commands[name]
        
        if name in self._aliases:
            return self._aliases[name]
        
        raise NoSuchUNetCommandException(name)
    
    def call_command(self, command: UNetCommand) -> any:
        handler = self.get_command(command.command_name)
        
        if handler._unet_command_argc != len(command.arguments):
            raise UNetCommandIncompatibleArgumentException(command.command_name, handler._unet_command_argc, len(command.arguments))
        
        return handler(command, *command.arguments)
    
    @property
    def parent(self):
        return self._parent

    @property
    def top(self):
        return self._top
