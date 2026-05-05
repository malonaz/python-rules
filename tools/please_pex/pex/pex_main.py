"""Zipfile entry point which supports auto-extracting itself based on zip-safety."""

import os
import runpy
import sys

# Put this pex on the path before anything else.
PEX = os.path.abspath(sys.argv[0])
# This might get overridden down the line if the pex isn't zip-safe.
PEX_PATH = PEX
sys.path = [PEX_PATH] + sys.path

# These will get templated in by the build rules.
MODULE_DIRS = [d for d in '__MODULE_DIR__'.split(',') if d]
ENTRY_POINT = '__ENTRY_POINT__'
ZIP_SAFE = __ZIP_SAFE__
PEX_STAMP = '__PEX_STAMP__'


def add_module_dir_to_sys_path(dirname, zip_safe=True):
    """Adds the given dirname to sys.path if it's nonempty."""
    import plz
    if dirname:
        sys.path.insert(1, os.path.join(sys.path[0], dirname))
        sys.meta_path.insert(0, plz.ModuleDirImport(dirname))


def add_so_import(module_dirs):
    """Adds the SoImport meta path finder for all module dirs."""
    import plz
    for module_dir in module_dirs:
        sys.meta_path.append(plz.SoImport(module_dir))


def pex_basepath(temp=False):
    if temp:
        import tempfile
        return tempfile.mkdtemp(dir=os.environ.get('TEMP_DIR'), prefix='pex_')
    else:
        return os.environ.get('PEX_CACHE_DIR',os.path.expanduser('~/.cache/pex'))


def pex_uniquedir():
    return 'pex-%s' % PEX_STAMP


def pex_paths():
    no_cache = os.environ.get('PEX_NOCACHE')
    no_cache = no_cache and no_cache.lower() == 'true'
    basepath, uniquedir = pex_basepath(no_cache), pex_uniquedir()
    pex_path = os.path.join(basepath, uniquedir)
    return pex_path, basepath, uniquedir, no_cache


def explode_zip():
    """Extracts the current pex to a temp directory where we can import everything from."""
    sys.path = [os.path.join(sys.path[0], '.bootstrap')] + sys.path[1:]
    import contextlib, portalocker, plz
    sys.path = sys.path[1:]

    @contextlib.contextmanager
    def pex_lockfile(basepath, uniquedir):
        lockfile_path = os.path.join(basepath, '.lock-%s' % uniquedir)
        with open(lockfile_path, "a+") as lockfile:
            portalocker.lock(lockfile, portalocker.LOCK_EX)
            lockfile.seek(0)
            yield lockfile
            portalocker.lock(lockfile, portalocker.LOCK_UN)

    @contextlib.contextmanager
    def _explode_zip():
        global PEX_PATH

        PEX_PATH, basepath, uniquedir, no_cache = pex_paths()
        os.makedirs(basepath, exist_ok=True)
        with pex_lockfile(basepath, uniquedir) as lockfile:
            if len(lockfile.read()) == 0:
                import compileall, zipfile

                os.makedirs(PEX_PATH, exist_ok=True)
                with plz.ZipFileWithPermissions(PEX, "r") as zf:
                    zf.extractall(PEX_PATH)

                if not no_cache:
                    compileall.compile_dir(PEX_PATH, optimize=2, quiet=1)

                lockfile.write("pex unzip completed")
        sys.path = [PEX_PATH] + [x for x in sys.path if x != PEX]
        try:
            yield
        finally:
            if no_cache:
                import shutil
                shutil.rmtree(basepath)

    return _explode_zip


def profile(filename):
    """Returns a context manager to perform profiling while the program runs."""
    import contextlib, cProfile

    @contextlib.contextmanager
    def _profile():
        profiler = cProfile.Profile()
        profiler.enable()
        yield
        profiler.disable()
        sys.stderr.write('Writing profiler output to %s\n' % filename)
        profiler.dump_stats(filename)

    return _profile


def start_debugger():
    pass


def main():
    """Runs the 'real' entry point of the pex."""
    if os.getenv("PLZ_DEBUG") is not None:
        start_debugger()

    runpy.run_module(ENTRY_POINT, run_name='__main__')
    return 0
