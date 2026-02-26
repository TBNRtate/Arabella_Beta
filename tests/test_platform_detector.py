from core_framework.platform.detector import PlatformDetector
from core_framework.platform.linux import LinuxPlatformLayer
from core_framework.platform.macos import MacOSPlatformLayer
from core_framework.platform.windows import WindowsPlatformLayer


def test_platform_override_linux():
    assert isinstance(PlatformDetector.detect("linux"), LinuxPlatformLayer)


def test_platform_override_macos():
    assert isinstance(PlatformDetector.detect("macos"), MacOSPlatformLayer)


def test_platform_override_windows():
    assert isinstance(PlatformDetector.detect("windows"), WindowsPlatformLayer)
