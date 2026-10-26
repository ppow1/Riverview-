# Riverview~ Controlled Source
# File: src/riverview_core/institutional_authority/service_principal_credentials.py
# Component: INSTITUTIONAL-AUTHORITY
# Revision: 1.0.0
# Purpose: Persist the ChatGPT service principal's one-time credential without browser delivery
# Execution Model: Fixed-path, local service account storage
# Observability: Sanitized availability errors; credential bytes are never logged
# Dependencies: A private service-owned directory and POSIX file semantics
# Authority: One fixed `service:chatgpt` credential destination
"""Protected one-time credential storage for the fixed ChatGPT service principal."""

from __future__ import annotations

from contextlib import contextmanager
import fcntl
import os
from pathlib import Path
import secrets
import stat


CHATGPT_PRINCIPAL_ID = "service:chatgpt"
CHATGPT_CREDENTIAL_PATH = Path(
    "/var/lib/riverview-status-dashboard/identity-credentials/service-chatgpt.credential"
)


class CredentialDestinationUnavailable(RuntimeError):
    """The fixed protected destination is absent, unsafe, or unwritable."""


class ProtectedChatGPTCredentialStore:
    """Fixed destination; no path or credential is accepted from an HTTP caller."""

    def __init__(self, path: str | Path = CHATGPT_CREDENTIAL_PATH):
        self.path = Path(path)
        if not self.path.is_absolute() or self.path.name != "service-chatgpt.credential":
            raise CredentialDestinationUnavailable("credential_destination_invalid")

    def _directory_fd(self, *, write: bool):
        directory = self.path.parent
        try:
            if directory.is_symlink() or not directory.is_dir():
                raise CredentialDestinationUnavailable("credential_destination_unavailable")
            metadata = directory.stat(follow_symlinks=False)
            if (not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.geteuid()
                    or stat.S_IMODE(metadata.st_mode) != 0o700):
                raise CredentialDestinationUnavailable("credential_destination_unavailable")
            if write and not os.access(directory, os.W_OK | os.X_OK, effective_ids=True):
                raise CredentialDestinationUnavailable("credential_destination_unavailable")
            flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
            return os.open(directory, flags | getattr(os, "O_CLOEXEC", 0))
        except CredentialDestinationUnavailable:
            raise
        except OSError:
            raise CredentialDestinationUnavailable("credential_destination_unavailable") from None

    @staticmethod
    def _read_at(directory_fd: int, name: str) -> str:
        try:
            descriptor = os.open(name, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                                 | getattr(os, "O_CLOEXEC", 0), dir_fd=directory_fd)
        except FileNotFoundError:
            raise
        except OSError:
            raise CredentialDestinationUnavailable("credential_destination_unavailable") from None
        try:
            metadata = os.fstat(descriptor)
            if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.geteuid()
                    or stat.S_IMODE(metadata.st_mode) != 0o400):
                raise CredentialDestinationUnavailable("credential_destination_unavailable")
            value = os.read(descriptor, 4096).decode("ascii").strip()
            if len(value) < 32 or len(value) > 512:
                raise CredentialDestinationUnavailable("credential_destination_unavailable")
            return value
        except (OSError, UnicodeError):
            raise CredentialDestinationUnavailable("credential_destination_unavailable") from None
        finally:
            os.close(descriptor)

    def available(self) -> bool:
        try:
            directory_fd = self._directory_fd(write=True)
            try:
                try:
                    self._read_at(directory_fd, self.path.name)
                except FileNotFoundError:
                    pass
            finally:
                os.close(directory_fd)
            return True
        except CredentialDestinationUnavailable:
            return False

    @contextmanager
    def registration_lock(self):
        directory_fd = self._directory_fd(write=True)
        descriptor = None
        try:
            try:
                descriptor = os.open(".service-chatgpt-registration.lock",
                    os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
                    | getattr(os, "O_CLOEXEC", 0), 0o600, dir_fd=directory_fd)
                metadata = os.fstat(descriptor)
                if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.geteuid()
                        or stat.S_IMODE(metadata.st_mode) != 0o600):
                    raise CredentialDestinationUnavailable("credential_destination_unavailable")
                fcntl.flock(descriptor, fcntl.LOCK_EX)
                yield
            except CredentialDestinationUnavailable:
                raise
            except OSError:
                raise CredentialDestinationUnavailable("credential_destination_unavailable") from None
        finally:
            if descriptor is not None:
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_UN)
                finally:
                    os.close(descriptor)
            os.close(directory_fd)

    def load_or_create(self) -> str:
        """Prepare a write-ahead token; retry reuses it until the registry commits."""
        directory_fd = self._directory_fd(write=True)
        try:
            try:
                return self._read_at(directory_fd, self.path.name)
            except FileNotFoundError:
                pass
            token = secrets.token_urlsafe(32)
            temporary = ".service-chatgpt-" + secrets.token_hex(16) + ".tmp"
            descriptor = None
            try:
                descriptor = os.open(temporary,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0)
                    | getattr(os, "O_CLOEXEC", 0), 0o600, dir_fd=directory_fd)
                payload = (token + "\n").encode("ascii")
                offset = 0
                while offset < len(payload):
                    offset += os.write(descriptor, payload[offset:])
                os.fchmod(descriptor, 0o400)
                os.fsync(descriptor)
                os.close(descriptor)
                descriptor = None
                # link() is an atomic no-overwrite install on the same filesystem.
                os.link(temporary, self.path.name, src_dir_fd=directory_fd,
                        dst_dir_fd=directory_fd, follow_symlinks=False)
                os.unlink(temporary, dir_fd=directory_fd)
                os.fsync(directory_fd)
                return token
            except FileExistsError:
                try:
                    os.unlink(temporary, dir_fd=directory_fd)
                except FileNotFoundError:
                    pass
                return self._read_at(directory_fd, self.path.name)
            except OSError:
                try:
                    os.unlink(temporary, dir_fd=directory_fd)
                except OSError:
                    pass
                raise CredentialDestinationUnavailable("credential_destination_unavailable") from None
            finally:
                if descriptor is not None:
                    os.close(descriptor)
        finally:
            os.close(directory_fd)
