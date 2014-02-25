import os
import shutil
import tempfile
from project_manager import is_subdir

def touch(path):
    with open(path, 'a'):
        os.utime(path, None)

def test_is_subdir():
    # prep
    tmp = tempfile.mkdtemp()
    os.chdir(tmp)
    os.makedirs('test/day')
    os.makedirs('test/night')
    touch('test/day/red')
    touch('test/day/yellow')
    touch('test/night/blue')
    touch('test/lunch')
    touch('cyan')
    os.symlink('test/day/red', 'magenta')
    os.symlink('test/day/yellow', 'test/orange')
    os.symlink('test/night/blue', 'test/night/purple')

    # test
    assert(is_subdir(tmp, 'test'))
    assert(is_subdir(tmp, 'test/day'))
    assert(is_subdir(tmp, 'test/night/blue'))
    assert(is_subdir('test', 'test/day'))
    assert(is_subdir('test', 'test/day/red'))
    assert(is_subdir('test/night', 'test/night/blue'))
    assert(is_subdir('test', 'magenta'))
    assert(not is_subdir('test', 'cyan'))
    assert(is_subdir('test', 'test/orange'))
    assert(is_subdir('test/night', 'test/night/purple'))
    assert(is_subdir('test', 'test/../magenta'))
    assert(not is_subdir('test', 'test/../cyan'))
    assert(is_subdir('test/..', './magenta'))
    assert(not is_subdir('test/day', './test/night/../'))

    # cleanup
    shutil.rmtree(tmp)
