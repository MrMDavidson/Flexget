from __future__ import unicode_literals, division, absolute_import
import logging

from flexget.event import event
from flexget.plugin import register_plugin,  priority
from flexget.utils.tools import console

log = logging.getLogger('dump')


def dump(entries, debug=False, eval_lazy=False, trace=False):
    """
    Dump *entries* to stdout

    :param list entries: Entries to be dumped.
    :param bool debug: Print non printable fields as well.
    :param bool eval_lazy: Evaluate lazy fields.
    :param bool trace: Display trace information.
    """
    def sort_key(field):
        # Sort certain fields above the rest
        if field == 'title':
            return 0
        if field == 'url':
            return 1
        if field == 'original_url':
            return 2
        return field

    for entry in entries:
        for field in sorted(entry, key=sort_key):
            if entry.is_lazy(field) and not eval_lazy:
                value = '<LazyField - value will be determined when it is accessed>'
            else:
                value = entry[field]
            if isinstance(value, basestring):
                try:
                    console('%-17s: %s' % (field, value.replace('\r', '').replace('\n', '')))
                except Exception:
                    console('%-17s: %r (warning: unable to print)' % (field, value))
            elif isinstance(value, list):
                console('%-17s: %s' % (field, '[%s]' % ', '.join(unicode(v) for v in value)))
            elif isinstance(value, (int, float, dict)):
                console('%-17s: %s' % (field, value))
            elif value is None:
                console('%-17s: %s' % (field, value))
            else:
                if debug:
                    console('%-17s: [not printable] (%r)' % (field, value))
        if trace:
            console('-- Processing trace:')
            for item in entry.traces:
                console('%-10s %-7s %s' % (item[0], '' if item[1] is None else item[1], item[2]))
        console('')


class OutputDump(object):
    """
    Outputs all entries to console
    """

    schema = {'type': 'boolean'}

    @priority(0)
    def on_task_output(self, task, config):
        if not config and not task.manager.options.dump_entries:
            return

        eval_lazy = task.manager.options.dump_entries == 'eval'
        trace = task.manager.options.dump_entries == 'trace'
        undecided = [entry for entry in task.all_entries if entry.undecided]
        if undecided:
            console('-- Undecided: --------------------------')
            dump(undecided, task.manager.options.debug, eval_lazy, trace)
        if task.accepted:
            console('-- Accepted: ---------------------------')
            dump(task.accepted, task.manager.options.debug, eval_lazy, trace)
        if task.rejected:
            console('-- Rejected: ---------------------------')
            dump(task.rejected, task.manager.options.debug, eval_lazy, trace)


register_plugin(OutputDump, 'dump', builtin=True, api_ver=2)


@event('register_parser_arguments')
def register_parser_arguments(core_parser):
    core_parser.get_subparser('exec').add_argument('--dump', nargs='?', choices=['eval', 'trace'], dest='dump_entries',
                                                   const=True, help='display all entries in task with fields they '
                                                                    'contain, use `--dump eval` to evaluate all lazy '
                                                                    'fields')
