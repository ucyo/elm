import pytest

from elm.sample_util.filename_selection import get_args_list
from elm.example_data import EXAMPLE_FILES
from elm.readers.hdf4 import load_hdf4_array, load_hdf4_meta
from elm.sample_util.band_selection import select_from_file

EXAMPLE_BAND_SPECS = [['long_name', 'Band 1 ', 'band_1',],
                      ['long_name', 'Band 2',  'band_2']]

@pytest.mark.needs_examples
def test_get_args_list():

    def filenames_gen(**kwargs):
        for f in EXAMPLE_FILES['hdf']:
            yield f
    files = get_args_list(filenames_gen,
                               EXAMPLE_BAND_SPECS,
                               select_from_file,
                               load_meta=load_hdf4_meta,
                               load_array=load_hdf4_array)
    assert files
