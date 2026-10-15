"""Reference server: one shared copy of the project's decisions, with revisions, roles and a hash-chained record. See SERVER.md."""
from .store import GENESIS, Person, ServerError, Store, canon, sha256

__all__ = ["GENESIS", "Person", "ServerError", "Store", "canon", "sha256"]
