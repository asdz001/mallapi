from _typeshed import Incomplete
from logging import Logger

from oauthlib.common import Request

from ..tokens import TokenBase
from .base import GrantTypeBase

log: Logger

def code_challenge_method_s256(verifier: str, challenge: str) -> bool: ...
def code_challenge_method_plain(verifier: str, challenge: str) -> bool: ...

class AuthorizationCodeGrant(GrantTypeBase):
    default_response_mode: str
    response_types: list[str]
    def create_authorization_code(self, request: Request) -> dict[str, str]: ...
    def create_authorization_response(
        self, request: Request, token_handler: TokenBase
    ) -> tuple[dict[str, str], None, int | None]: ...
    def create_token_response(self, request: Request, token_handler: TokenBase) -> tuple[dict[str, str], str, int | None]: ...
    def validate_authorization_request(self, request: Request) -> tuple[Incomplete, dict[str, Incomplete]]: ...
    def validate_token_request(self, request: Request) -> None: ...
    def validate_code_challenge(self, challenge: str, challenge_method: str, verifier: str) -> bool: ...
