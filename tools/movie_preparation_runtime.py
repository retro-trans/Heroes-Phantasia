"""Fingerprint the executable and native raster libraries used by movie preparation."""
import hashlib,sys,shutil
from pathlib import Path
import PIL,numpy
from PIL import features

def fingerprint():
    files={Path(sys.executable).resolve()}
    for package in (PIL,numpy):
        root=Path(package.__file__).parent
        files.add(Path(package.__file__).resolve())
        files.update(p.resolve() for p in root.rglob('*.pyd'))
        files.update(p.resolve() for p in root.rglob('*.dll'))
        libs=root.parent/(root.name+'.libs')
        if libs.exists():files.update(p.resolve() for p in libs.rglob('*.dll'))
    for name in ('ffmpeg','ffprobe'):
        p=shutil.which(name)
        if not p:raise RuntimeError(name+' unavailable')
        files.add(Path(p).resolve())
    return dict(python_version=sys.version,pillow_version=PIL.__version__,
        freetype_version=features.version('freetype2'),numpy_version=numpy.__version__,
        executable_and_native_library_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)})
