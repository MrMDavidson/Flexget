from flexget.ui.webui import manager, register_plugin, app
from flexget.feed import Feed
from flask import render_template, request, flash, redirect, Module
import yaml
import logging
from flask.helpers import url_for

configure = Module(__name__, url_prefix='/configure')

log = logging.getLogger('ui.configure')


@configure.route('/')
def index():
    return render_template('configure/configure.html')


@configure.route('/new/<root>', methods=['POST', 'GET'])
def new_text(root):
    if root not in ['feeds', 'presets']:
        flash('Invalid root.', 'error')
        return redirect(url_for('index'))
    config_type = root.rstrip('s')
    context = {'root': root,
               'config_type': config_type}
    if request.method == 'POST':
        context['config'] = request.form.get('config')
        name = request.form.get('name')
        if not name:
            flash('You must enter a name for this %s' % config_type, 'error')
        elif name in manager.config.get(root, []):
            flash('%s with name %s already exists' % (config_type.capitalize(), name), 'error')
        else:
            manager.config.setdefault(root, {})[name] = {}
            return redirect(url_for('edit_text', root=root, name=name))

    return render_template('configure/new.html', **context)


@configure.route('/delete/<root>/<name>')
def delete(root, name):
    if root in manager.config and name in manager.config[root]:
        log.info('Deleting %s %s' % (root, name))
        del manager.config[root][name]
        manager.save_config()
        flash('Deleted %s.' % name, 'delete')
    return redirect(url_for('index'))


@configure.route('/edit/text/<root>/<name>', methods=['POST', 'GET'])
def edit_text(root, name):
    from flexget.manager import FGDumper
    config_type = root.rstrip('s')
    context = {
        'name': name,
        'root': root,
        'config_type': config_type}

    if request.method == 'POST':
        context['config'] = request.form['config']
        try:
            config = yaml.load(request.form['config'])
        except yaml.scanner.ScannerError, e:
            flash('Invalid YAML document: %s' % e, 'error')
            log.exception(e)
        else:
            # valid yaml, now run validator
            errors = Feed.validate_config(config)
            if errors:
                for error in errors:
                    flash(error, 'error')
                context['config'] = request.form['config']
            else:
                manager.config[root][name] = config
                manager.save_config()
                context['config'] = yaml.dump(config, Dumper=FGDumper, default_flow_style=False)
                if request.form.get('name') != name:
                    # Renaming
                    new_name = request.form.get('name')
                    if new_name in manager.config[root]:
                        flash('%s with name %s already exists' % (config_type.capitalize(), new_name), 'error')
                    else:
                        # Do the rename
                        manager.config[root][new_name] = manager.config[root][name]
                        del manager.config[root][name]
                        manager.save_config()
                        flash('%s %s renamed to %s.' % (config_type.capitalize(), name, new_name), 'success')
                        return redirect(url_for('edit_text', root=root, name=new_name))
                else:
                    flash('Configuration saved', 'success')
    else:
        config = manager.config[root][name]
        if config:
            context['config'] = yaml.dump(config, Dumper=FGDumper, default_flow_style=False)
        else:
            context['config'] = ''
    context['related'] = get_related(root, name)
    return render_template('configure/edit_text.html', **context)


@configure.route('/edit/<root>/<name>', methods=['POST', 'GET'])
def edit(root, name):
    context = {'name': name}
    return render_template('configure/edit.html', **context)


@app.template_filter('other_type')
def other_type(root):
    if root == 'feeds':
        return 'presets'
    return 'feeds'


def get_related(root, name):
    """Returns a list of related feeds/presets for a given preset/feed"""
    if root == 'feeds':
        presets = manager.config[root][name].get('preset', [])
        if isinstance(presets, basestring):
            presets = [presets]
        return presets
    elif root == 'presets':
        feeds = []
        for feed, config in manager.config['feeds'].iteritems():
            if config.get('preset'):
                if name == config['preset'] or name in config['preset']:
                    feeds.append(feed)
        return feeds


register_plugin(configure, menu='Configure', order=10)