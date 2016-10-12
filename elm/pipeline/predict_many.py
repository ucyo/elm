from functools import partial
import copy
import datetime
import itertools
import logging
import os

import dask
import numpy as np
import xarray as xr


from elm.config import import_callable, parse_env_vars
from elm.model_selection.util import get_args_kwargs_defaults
from elm.config.dask_settings import (wait_for_futures,
                                        no_client_submit)
from elm.sample_util.sample_pipeline import create_sample_from_data_source
from elm.pipeline.serialize import (load_models_from_tag,
                                    serialize_prediction)
from elm.readers import (flatten,
                         inverse_flatten,
                         ElmStore,)
from elm.sample_util.samplers import make_one_sample_part

logger = logging.getLogger(__name__)

__all__ = ['predict_many',]

_predict_idx = 0

def _next_name():
    global _predict_idx
    n = 'predict-{}'.format(_predict_idx)
    _predict_idx += 1
    return n


def _predict_one_sample_one_arg(pipe,
                                transform_model,
                                serialize,
                                to_cube,
                                tag,
                                models,
                                filename,
                                sample=None):
    logger.info('Predict {}'.format(filename))
    pipe_copy = copy.deepcopy(pipe)
    pipe_copy[0][-1]['filename'] = filename
    out = []
    for idx, (name, model) in enumerate(models):
        if idx == 0:
            sample, sample_y, sample_weight = run_sample_pipeline(pipe,
                                         sample=sample,
                                         transform_model=transform_model)
            if not hasattr(sample, 'flat'):
                raise ValueError('Expected "sample" to have an attribute "flat".  Adjust sample pipeline to use {"flatten": "C"}')
        prediction = model.predict(sample.flat.values)
        if prediction.ndim == 1:
            prediction = prediction[:, np.newaxis]
            ndim = 2
        elif prediction.ndim == 2:
            pass
        else:
            raise ValueError('Expected 1- or 2-d output of model.predict but found ndim of prediction: {}'.format(prediction.ndim))

        bands = ['predict']

        attrs = copy.deepcopy(sample.attrs)
        attrs.update(copy.deepcopy(sample.flat.attrs))
        attrs['elm_predict_date'] = datetime.datetime.utcnow().isoformat()
        prediction = ElmStore({'flat': xr.DataArray(prediction,
                                         coords=[('space', sample.flat.space),
                                                 ('band', bands)],
                                         dims=('space', 'band'),
                                         attrs=attrs)},
                                 attrs=attrs)
        if to_cube:
            new_es = inverse_flatten(prediction)
        else:
            new_es = prediction
        if serialize:
            new_es = serialize(new_es, sample, tag)
        out.append(new_es)
    return out



def predict_many(sample_pipeline,
                 data_source,
                 config=None,
                 step=None,
                 client=None,
                 samples_per_batch=1,
                 models=None,
                 serialize=serialize_prediction,
                 to_cube=True,
                 transform_model=None,
                 transform_dict=None,
                 tag=None,
                 sample=None,
                 **sample_pipeline_kwargs):
    if hasattr(client, 'map'):
        map_function = client.map
    else:
        map_function = map
    if hasattr(client, 'submit'):
        submit_func = client.submit
    else:
        submit_func = no_client_submit
    get_results = partial(wait_for_futures, client=client)
    pipe = create_sample_from_data_source(sample_pipeline,
                                                  config=config, step=step,
                                                  data_source=data_source,
                                                  **sample_pipeline_kwargs)
    sampler_kwargs = pipe[0][-1]
    env = parse_env_vars()
    tag = tag or step['predict']
    if config and not serialize:
        serialize = serialize_prediction
    if serialize == serialize_prediction:
        serialize = partial(serialize, config)
    if models is None:
        if not config:
            etp = env.get('ELM_TRAIN_PATH')
            if not etp or not os.path.exists(etp):
                raise IOError('Expected ELM_TRAIN_PATH in environment variables')
        else:
            etp = config.ELM_TRAIN_PATH
        logger.info('Load pickled models from {} {}'.format(etp, tag))
        models, meta = load_models_from_tag(etp,
                                            tag)
    generated_args = sampler_kwargs['generated_args']

    predict_dsk = {}
    keys = []
    last_file_name = None
    for idx, arg in enumerate(generated_args):
        name = _next_name()
        predict_dsk[name] = (_predict_one_sample_one_arg,
                             pipe,
                             transform_model,
                             serialize,
                             to_cube,
                             tag,
                             models,
                             arg,
                             sample)


        keys.append(name)
    preds = []
    if client is None:
        new = dask.get(predict_dsk, keys)
    else:
        new = client.get(predict_dsk, keys)
    return tuple(itertools.chain.from_iterable(new))