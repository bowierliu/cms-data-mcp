"""Ordinary tests must not contact the network; explicit live demos are separate."""

import socket

import pytest


@pytest.fixture(autouse=True)
def offline_network_boundary(monkeypatch):
    def reject(*args, **kwargs):
        raise AssertionError("External network access is forbidden in the offline suite")

    monkeypatch.setattr(socket.socket, "connect", reject)
    monkeypatch.setattr(socket.socket, "connect_ex", reject)
    monkeypatch.setattr(socket, "getaddrinfo", reject)
