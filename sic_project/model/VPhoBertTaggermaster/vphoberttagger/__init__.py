__version__ = '1.0.0'
__author__ = ''

from .constant import LOGGER

from model.VPhoBertTaggermaster.vphoberttagger import trainer as Trainer
# import vphoberttagger.predictor as Predictor
from model.VPhoBertTaggermaster.vphoberttagger import predictor as Predictor



__all__ = ['Trainer', 'Predictor', 'LOGGER']