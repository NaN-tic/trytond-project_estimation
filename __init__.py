# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from .work import *


def register():
    Pool.register(
        Work,
        ProjectEstimation,
        ProjectEstimationLine,
        PredecessorSuccessor,
        CreateTaskStart,
        module='project_estimation', type_='model')
    Pool.register(
        CreateTask,
        module='project_estimation', type_='wizard')
