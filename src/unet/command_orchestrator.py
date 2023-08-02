from unet.command import UNetCommand, NoSuchUNetCommandException, UNetCommandIncompatibleArgumentException
from mcom.protocol import MComProtocol
from unet.command_handler import UNetCommandHandler


class UNetCommandOrchestrator:
    def __init__(self, local_handler: UNetCommandHandler, remote: MComProtocol) -> None:
        self._local_handler = local_handler
        self._remote = remote
    
    def call_command(self, command: UNetCommand) -> any:
        if command.local:
            return self._local_handler.call_command(command)
        
        return self._remote.send(command.command_stirng)

    @property
    def local_handler(self):
        return self._local_handler
    
    @property
    def remote(self):
        return self._remote
