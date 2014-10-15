# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.

from trytond.model import ModelSQL, ModelView, fields
from trytond.pyson import Eval
from trytond.transaction import Transaction
from trytond.pool import Pool, PoolMeta
from trytond.wizard import Wizard, StateView, StateTransition, Button

__all__ = ['Work', 'ProjectEstimation', 'ProjectEstimationLine',
    'PredecessorSuccessor', 'CreateTaskStart', 'CreateTask']

__metaclass__ = PoolMeta


class Work:
    __name__ = 'project.work'
    procedure = fields.Text('Procedure', readonly=True)


class ProjectEstimation(ModelSQL, ModelView):
    '''Project Estimation'''
    __name__ = 'project.estimation'

    name = fields.Char('Name', required=True)
    hours = fields.Float('Hours', digits=(16, 2))
    lines = fields.One2Many('project.estimation.line', 'project', 'Lines')

    def create_task(self, name, parent, effort):
        TimesheetWork = Pool().get('timesheet.work')
        PredecessorSuccessors = Pool().get('project.predecessor_successor')
        Work = Pool().get('project.work')
        tasks = {}

        def create_timesheet_work(name, parent):
            timesheet = TimesheetWork()
            timesheet.name = name
            if parent:
                timesheet.parent = parent.work.id
            timesheet.save()
            return timesheet

        def create_work(timesheet_work, line):
            work = Work()
            work.work = timesheet_work.id
            work.party = parent.party.id
            work.effort = effort*line.percentage
            work.type = line.type
            work.project_invoice_method = 'manual'
            work.tracker = line.tracker
            work.save()
            tasks[line] = work

        def create_dependencies(start, end):
            p = PredecessorSuccessors()
            p.predecessor = start
            p.successor = end
            p.save()

        project = Work()
        project.work = create_timesheet_work(name, parent).id
        project.party = parent.party.id
        project.type = 'project'
        project.save()

        for line in self.lines:
            tname = "[%s] %s" % (line.name, name)
            tw = create_timesheet_work(tname, project)
            create_work(tw, line)

        for line, task in tasks.iteritems():
            if line.parent:
                parent_task = tasks[line.parent]
                task.work.parent = parent_task.work.id
                task.save()

            for predecessor in line.predecessors:
                pred = tasks[predecessor]
                create_dependencies(pred, task)

            for successor in line.successors:
                suc = tasks[successor]
                create_dependencies(task, suc)


class ProjectEstimationLine(ModelSQL, ModelView):
    '''Project Estimation Line'''

    __name__ = 'project.estimation.line'

    name = fields.Char('Name', required=True)
    project = fields.Many2One('project.estimation', 'Project', required=True,
        select=True)
    tracker = fields.Many2One('project.work.tracker', 'Tracker', required=True)
    type = fields.Selection([
            ('project', 'Project'),
            ('task', 'Task')
            ], 'Type', required=True, select=True)
    description = fields.Text('Description')
    percentage = fields.Float('Percentage',
        digits=(16, Eval('unit_digits', 2)), required=True)
    parent = fields.Many2One('project.estimation.line', 'Parent')
    predecessors = fields.Many2Many('project.estimation.predecessor_successor',
        'successor', 'predecessor', 'Predecessors')
    successors = fields.Many2Many('project.estimation.predecessor_successor',
        'predecessor', 'successor', 'Successors')
    hours = fields.Function(fields.Float('Hours',
        digits=(16, 2)), 'get_hours')
    procedure = fields.Text('Procedure')

    def get_hours(self, name):
        if not self.project or self.project and not self.project.hours:
            return 0
        return self.project.hours * self.percentage


class PredecessorSuccessor(ModelSQL):
    'Predecessor - Successor'
    __name__ = 'project.estimation.predecessor_successor'
    predecessor = fields.Many2One('project.estimation.line', 'Predecessor',
            ondelete='CASCADE', required=True, select=True)
    successor = fields.Many2One('project.estimation.line', 'Successor',
            ondelete='CASCADE', required=True, select=True)


class CreateTaskStart(ModelView):
    'Create Task Start'
    __name__ = 'project_estimation.create_task_start'

    name = fields.Char('Name', help='Name of the new project/task to create.',
        required=True)
    project = fields.Many2One('project.work', 'Project', required=True)
    effort = fields.Float('Effort', help='Total effort of the project/task.',
        required=True)


class CreateTask(Wizard):
    'Create Task'
    __name__ = 'project_estimation.create_task'
    start = StateView('project_estimation.create_task_start',
        'project_estimation.create_task_start', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Create Project', 'creatework', 'tryton-ok', default=True),
            ])
    creatework = StateTransition()

    def transition_creatework(self):
        Estimation = Pool().get('project.estimation')
        estimations = Estimation.browse(Transaction().context['active_ids'])
        for estimation in estimations:
            estimation.create_task(self.start.name, self.start.project,
                self.start.effort)
        return 'end'
