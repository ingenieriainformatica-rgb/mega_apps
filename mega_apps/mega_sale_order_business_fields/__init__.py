# -*- coding: utf-8 -*-
from . import models
from .hooks import sync_mega_descripcion_from_studio


def post_init_hook(env):
    sync_mega_descripcion_from_studio(env.cr)
