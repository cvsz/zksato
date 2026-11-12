"""Tests for zksato-core IDs module."""

import pytest

from zksato_core.ids import (
    new_ulid,
    new_uuid,
    new_idempotency_key,
    new_correlation_id,
    parse_ulid,
    ulid_to_str,
    uuid_to_str,
)
from ulid import ULID
from uuid import UUID


def test_new_ulid():
    ulid = new_ulid()
    assert isinstance(ulid, ULID)
    assert len(str(ulid)) == 26


def test_new_uuid():
    uuid = new_uuid()
    assert isinstance(uuid, UUID)
    assert uuid.version == 4


def test_new_idempotency_key():
    key = new_idempotency_key("test")
    assert key.startswith("test_")
    assert len(key) > 10


def test_new_correlation_id():
    corr = new_correlation_id("test")
    assert corr.startswith("test_")
    assert "_" in corr


def test_parse_ulid():
    ulid = new_ulid()
    parsed = parse_ulid(str(ulid))
    assert parsed == ulid


def test_ulid_to_str():
    ulid = new_ulid()
    s = ulid_to_str(ulid)
    assert isinstance(s, str)
    assert len(s) == 26


def test_uuid_to_str():
    uuid = new_uuid()
    s = uuid_to_str(uuid)
    assert isinstance(s, str)
    assert len(s) == 36


def test_ulid_uniqueness():
    ulids = {new_ulid() for _ in range(100)}
    assert len(ulids) == 100


def test_uuid_uniqueness():
    uuids = {new_uuid() for _ in range(100)}
    assert len(uuids) == 100