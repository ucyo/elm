import glob
import os
import pickle

import numpy as np
import rasterio as rio

from sklearn.externals import joblib

def get_paths_for_tag(elm_pickle_path, tag):
    model_root = os.path.join(elm_pickle_path, tag + '_{}.pkl')
    meta_path = os.path.join(elm_pickle_path, tag + '_meta.pkl')
    return model_root, meta_path

def mkdir_p(path):
    if not os.path.exists(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))

def dump(data, path):
    joblib.dump(data, path)

def save_models_with_meta(models, elm_pickle_path, tag, meta):
    model_root, meta_path = get_paths_for_tag(elm_pickle_path, tag)
    paths = []
    for idx, model in enumerate(models):
        paths.append(model_root.format(idx))
        mkdir_p(paths[-1])
        dump(model, paths[-1])
    mkdir_p(meta_path)
    dump(meta, meta_path)
    return (paths, meta_path)

def load(path):
    return joblib.load(path)

def load_models_from_tag(elm_pickle_path, tag):
    model_root, meta_path = get_paths_for_tag(elm_pickle_path, tag)
    models = []
    for path in glob.glob(model_root.format('*')):
        models.append(load(path))
    return (models, load(meta_path))

def predict_to_netcdf():
    pass

def band_to_tif(band, filename):
    kwargs = dict(
                driver='GTiff',
                dtype=rio.float32,
                count=1,
                compress='lzw',
                nodata=0,
                bigtiff='YES', # Output will be larger than 4GB
                width=band.shape[0],
                height=band.shape[1],

            )
    raise NotImplementedError('This band_to_tif function is not working - hanging '
                              'indefinitely')
    if 'crs' in band.attrs['MetaData']:
        kwargs['crs'] = band.attrs['MetaData']['crs']
    kwargs['transform'] = band.attrs['GeoTransform']
    mkdir_p(filename)
    print(filename)
    with rio.drivers():
        with rio.open(filename, 'w', **kwargs) as f:
            data = band.astype(rio.float32)
            f.write_band(1, data, window=((0, band.y.size), (0, band.x.size)))