"""VLT-01: Proposed Desktop-to-Vault interface (requires team approval).

This module defines contracts only. It does not implement cryptography,
storage, authentication, or session policy.
"""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CredentialCreate:
    """Yeni kasa kaydi icin gerekli bilgiler."""

    title: str
    username: str
    password: str
    url: str = ""
    notes: str = ""


@dataclass(frozen=True, slots=True)
class CredentialUpdate:
    """Tam kayit guncellemesi; kismi guncelleme degildir."""

    title: str
    username: str
    password: str
    url: str = ""
    notes: str = ""


@dataclass(frozen=True, slots=True)
class CredentialItem:
    """Yetkili okuma sonrasi donen cozulmus kayit."""

    record_id: UUID
    title: str
    username: str
    password: str
    url: str = ""
    notes: str = ""


@dataclass(frozen=True, slots=True)
class CredentialSummary:
    """Listeleme modeli: parola ve not gibi hassas alanlari icermez."""

    record_id: UUID
    title: str
    username: str
    url: str = ""


class VaultLifecycleService(Protocol):
    """Kasa olusturma, acma ve kilitleme sozlesmesi."""

    def create_vault(self, master_password: str) -> UUID:
        """Yeni yerel kasa olusturur; kasa kimligini dondurur."""
        ...

    def unlock_vault(self, master_password: str) -> None:
        """Ana parola ile kasanin kilidini acar."""
        ...

    def lock_vault(self) -> None:
        """Kasayi kilitler ve cozulmus anahtar referanslarini birakir."""
        ...


class CredentialManagerService(Protocol):
    """Kilidi acik kasadaki kimlik bilgisi islemleri sozlesmesi."""

    def add_credential(self, data: CredentialCreate) -> UUID:
        """Yeni kayit ekler; kayit kimligini dondurur."""
        ...

    def get_credential(self, record_id: UUID) -> CredentialItem:
        """Yetkili erisimde tek kaydin tum alanlarini dondurur."""
        ...

    def update_credential(self, record_id: UUID, data: CredentialUpdate) -> None:
        """Var olan kaydi tam olarak gunceller."""
        ...

    def delete_credential(self, record_id: UUID) -> None:
        """Kaydi siler."""
        ...

    def list_credentials(self) -> list[CredentialSummary]:
        """Parolalari aciga cikarmadan kayit ozetlerini listeler."""
        ...


class VaultService(VaultLifecycleService, CredentialManagerService, Protocol):
    """Tum Vault islemlerine ihtiyac duyan istemciler icin bilesik arayuz."""

    pass
