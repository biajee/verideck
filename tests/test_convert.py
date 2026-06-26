"""Unit tests for LibreOffice invocation details (no LibreOffice needed)."""

from pathlib import PurePosixPath, PureWindowsPath

from verideck.convert import _user_installation_arg


def test_user_installation_arg_windows_path_is_valid_file_url():
    # Regression: f"file://{path}" produced file://C:\... on Windows, which
    # LibreOffice rejects with "bootstrap.ini is corrupt".
    arg = _user_installation_arg(PureWindowsPath(r"C:\Users\me\data\job\pdf\.lo_profile"))
    assert arg == "-env:UserInstallation=file:///C:/Users/me/data/job/pdf/.lo_profile"
    assert "\\" not in arg
    assert arg.startswith("-env:UserInstallation=file:///")


def test_user_installation_arg_posix_path():
    arg = _user_installation_arg(PurePosixPath("/home/me/data/job/pdf/.lo_profile"))
    assert arg == "-env:UserInstallation=file:///home/me/data/job/pdf/.lo_profile"


def test_user_installation_arg_encodes_spaces():
    arg = _user_installation_arg(PureWindowsPath(r"C:\My Files\verideck\.lo_profile"))
    assert " " not in arg
    assert "%20" in arg
