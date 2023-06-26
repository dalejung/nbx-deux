"""
Mishmash of io logic stripped from jupyter code that isn't entangled with the
Configurable and ContentsManager.
"""
from datetime import datetime
from contextlib import contextmanager
import os.path
from fnmatch import fnmatch
from base64 import decodebytes, encodebytes
import json
from typing import cast

from jupyter_server.services.contents.fileio import (
    path_to_intermediate,
    path_to_invalid,
    replace_file,
    atomic_writing,
    _simple_writing,
)
from jupyter_server.services.contents.filemanager import FileContentsManager
import nbformat
from nbformat import ValidationError, sign
from nbformat import validate as validate_nb
from tornado.web import HTTPError
from jupyter_server import _tz as tz


def mark_trusted_cells(nb):
    """Mark cells as trusted if the notebook signature matches.

    Called as a part of loading notebooks.

    Parameters
    ----------
    nb : dict
        The notebook object (in current nbformat)
    path : str
        The notebook's path (for logging)
    """

    notary = sign.NotebookNotary()
    trusted = notary.check_signature(nb)
    notary.mark_cells(nb, trusted)


def get_hide_globs() -> list:
    """
    Seems like good way to get hide_globs defaults
    """
    fcm = FileContentsManager()
    hide_globs = cast(list, fcm.hide_globs)
    return hide_globs


FCM_HIDE_GLOBS = get_hide_globs()


def should_list(name, hide_globs):
    """Should this file/directory name be displayed in a listing?"""
    return not any(fnmatch(name, glob) for glob in hide_globs)


def _read_notebook(
    os_path,
    as_version=4,
    capture_validation_error=None,
    use_atomic_writing=True
):
    """Read a notebook from an os path."""
    with open(os_path, "r", encoding="utf-8") as f:
        try:
            return nbformat.read(
                f,
                as_version=as_version,
                capture_validation_error=capture_validation_error
            )
        except Exception as e:
            e_orig = e

        # If use_atomic_writing is enabled, we'll guess that it was also
        # enabled when this notebook was written and look for a valid
        # atomic intermediate.
        tmp_path = path_to_intermediate(os_path)

        if not use_atomic_writing or not os.path.exists(tmp_path):
            raise HTTPError(
                400,
                f"Unreadable Notebook: {os_path} {e_orig!r}",
            )

        # Move the bad file aside, restore the intermediate, and try again.
        invalid_file = path_to_invalid(os_path)
        replace_file(os_path, invalid_file)
        replace_file(tmp_path, os_path)
        return _read_notebook(
            os_path,
            as_version,
            capture_validation_error=capture_validation_error,
            use_atomic_writing=use_atomic_writing
        )


def _save_notebook(
    os_path,
    nb,
    capture_validation_error=None,
    use_atomic_writing=True
):
    """Save a notebook to an os_path."""
    with writing_cm(os_path, encoding="utf-8", use_atomic_writing=use_atomic_writing) as f:
        nbformat.write(
            nb,
            f,
            version=nbformat.NO_CONVERT,
            capture_validation_error=capture_validation_error,
        )


@contextmanager
def writing_cm(os_path, *args, use_atomic_writing=True, **kwargs):
    """wrapper around atomic_writing that turns permission errors to 403.
    Depending on flag 'use_atomic_writing', the wrapper perform an actual atomic writing or
    simply writes the file (whatever an old exists or not)"""
    if use_atomic_writing:
        with atomic_writing(os_path, *args, **kwargs) as f:
            yield f
    else:
        with _simple_writing(os_path, *args, **kwargs) as f:
            yield f


def _save_file(os_path, content, format, use_atomic_writing=True):
    """Save content of a generic file."""
    if format not in {"text", "base64"}:
        raise HTTPError(
            400,
            "Must specify format of file contents as 'text' or 'base64'",
        )

    try:
        if format == "text":
            bcontent = content.encode("utf8")
        else:
            b64_bytes = content.encode("ascii")
            bcontent = decodebytes(b64_bytes)

    except Exception as e:
        raise HTTPError(400, f"Encoding error saving {os_path}: {e}") from e

    with writing_cm(os_path, text=False, use_atomic_writing=use_atomic_writing) as f:
        f.write(bcontent)



def _read_file(os_path, format):
    """Read a non-notebook file.

    os_path: The path to be read.
    format:
      If 'text', the contents will be decoded as UTF-8.
      If 'base64', the raw bytes contents will be encoded as base64.
      If not specified, try to decode as UTF-8, and fall back to base64
    """
    if not os.path.isfile(os_path):
        raise HTTPError(400, "Cannot read non-file %s" % os_path)

    with open(os_path, "rb") as f:
        bcontent = f.read()

    if format is None or format == "text":
        # Try to interpret as unicode if format is unknown or if unicode
        # was explicitly requested.
        try:
            return bcontent.decode("utf8"), "text"
        except UnicodeError as e:
            if format == "text":
                raise HTTPError(
                    400,
                    "%s is not UTF-8 encoded" % os_path,
                    reason="bad format",
                ) from e
    return encodebytes(bcontent).decode("ascii"), "base64"


def ospath_is_writable(os_path):
    try:
        return os.access(os_path, os.W_OK)
    except OSError:
        return False


def get_ospath_metadata(os_path):
    info = os.lstat(os_path)

    size = None
    try:
        # size of file
        size = info.st_size
    except (ValueError, OSError):
        pass

    try:
        last_modified = tz.utcfromtimestamp(info.st_mtime)
    except (ValueError, OSError):
        # Files can rarely have an invalid timestamp
        # https://github.com/jupyter/notebook/issues/2539
        # https://github.com/jupyter/notebook/issues/2757
        # Use the Unix epoch as a fallback so we don't crash.
        last_modified = datetime(1970, 1, 1, 0, 0, tzinfo=tz.UTC)

    try:
        created = tz.utcfromtimestamp(info.st_ctime)
    except (ValueError, OSError):  # See above
        created = datetime(1970, 1, 1, 0, 0, tzinfo=tz.UTC)

    return {'size': size, 'last_modified': last_modified, 'created': created}


def validate_notebook_model(model, validation_error=None):
    """Add failed-validation message to model"""
    try:
        if validation_error is not None:
            e = validation_error.get("ValidationError")
            if isinstance(e, ValidationError):
                raise e
        else:
            validate_nb(model["content"])
    except ValidationError as e:
        model["message"] = "Notebook validation failed: {}:\n{}".format(
            str(e),
            json.dumps(e.instance, indent=1, default=lambda obj: "<UNKNOWN>"),
        )
    return model
