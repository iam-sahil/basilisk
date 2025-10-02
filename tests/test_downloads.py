import os
import tempfile
import types
import importlib
import builtins


def test_download_scripts_invokes_download(monkeypatch, tmp_path):
    module = importlib.import_module('debloat_components.debloat_download_scripts')

    downloaded = {}

    def fake_download(url, dest_name=None, dest_dir=None, retries=3):
        nonlocal downloaded
        downloaded[(url, dest_name, dest_dir)] = True
        # simulate writing a file
        if dest_dir and dest_name:
            os.makedirs(dest_dir, exist_ok=True)
            with open(os.path.join(dest_dir, dest_name), 'wb') as f:
                f.write(b'OK')
        return True

    # ensure scripts do not exist so path goes to download
    monkeypatch.setattr(module, 'SCRIPTS_DIR', tmp_path.as_posix())
    monkeypatch.setattr(module, 'MEDIA_DIR', tmp_path.joinpath('media').as_posix())

    # monkeypatch the function where it is used (module namespace) to avoid network
    monkeypatch.setattr(module, 'download_file', fake_download)
    # avoid opening error dialogs and exiting during tests
    monkeypatch.setattr(module, 'show_error_popup', lambda *a, **k: True)

    # prevent sys.exit on failure paths
    monkeypatch.setattr(module, 'sys', types.SimpleNamespace(exit=lambda code: (_ for _ in ()).throw(AssertionError("sys.exit called"))))

    module.main()

    # Verify that at least one script and one media file were attempted
    assert any('scripts' in u for (u, _, _) in downloaded.keys())
    assert any('media' in u for (u, _, _) in downloaded.keys())


def test_downloads_to_temp_basilisk_dir(monkeypatch, tmp_path):
    module = importlib.import_module('debloat_components.debloat_download_scripts')
    monkeypatch.setenv('TEMP', tmp_path.as_posix())

    created_paths = []

    def fake_download(url, dest_name=None, dest_dir=None, retries=3):
        created_paths.append(dest_dir)
        return True

    monkeypatch.setattr(module, 'download_file', fake_download)
    monkeypatch.setattr(module, 'show_error_popup', lambda *a, **k: True)
    # Point both script and media dirs to a clean, test-specific location
    scripts_dir = tmp_path.joinpath('basilisk').as_posix()
    media_dir = tmp_path.joinpath('basilisk', 'media').as_posix()
    monkeypatch.setattr(module, 'SCRIPTS_DIR', scripts_dir)
    monkeypatch.setattr(module, 'MEDIA_DIR', media_dir)
    module.main()

    assert scripts_dir in created_paths
    assert media_dir in created_paths


