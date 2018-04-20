"""
PragmaDoc - Pragmatical Text Editor

Pragmatics: meaning is derrived from both semantics and context

1. Read meta and content
2. Identify blueprint nodes
4. Map asset and template to each node
5. Preprocess each node with Jinja2
6. Assemble final stream
7. Use Pandoc academic markdown + citeproc to convert to final format

Requires:
Mistune (MD loadeer)
Jinja2 preprocessor
Pandoc Academic Markdown

Create RST for sphinx
Create doc for sharing/pdfing

"""

import yaml, logging, time, collections, os, re
from argparse import ArgumentParser
from glob import glob
from pprint import pformat
import pypandoc as pd
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
import dateutil.parser as dateparser
from subprocess import check_output
import datetime
from loader import ContentLoader

def read_yml(fp):
    with open(fp, 'rU') as f:
        return yaml.load(f)

def read_blueprints():
    bps = {}
    for fp in glob(os.path.join(pdoc_loc, "blueprints/*.yml")):
        bps.update(read_yml(fp))
    return bps

def read_content(fp):
    r, e = os.path.splitext(fp)
    if e == ".yml":
        return read_yml(fp)
    elif r.endswith('md') and e == '.j2':
        return ContentLoader().load(fp)

# Can't merge arrays with this (but how would you?)
def deep_update(d, u):
    # logging.debug(pformat(d))
    # logging.debug(pformat(u))
    for k, v in u.iteritems():
        if isinstance(v, collections.Mapping):
            # logging.debug(d)
            d[k] = deep_update(d.get(k, {}), v)
        else:
            d[k] = v
    return d

def prerender_content(env, content, content_dir):

    def render(item):
        # logging.debug('type of item {}'.format(type(item)))
        if type(item) is list:
            for i, subitem in enumerate(item):
                # logging.debug('looking at {}'.format(i))
                item[i] = render(subitem)
            return item
        if type(item) is dict:
            for key in item.keys():
                # logging.debug('looking at ' + key)
                item[key] = render(item[key])
            return item
        if type(item) is str:
            # logging.debug("rendering " + item)
            m = env.from_string(item)
            return m.render(content)

    content['blocks'] = render(content['blocks'])

    # prerender budget if it exists
    if os.path.exists(os.path.join(content_dir, "budget.csv")):
        budget = check_output(
            [os.path.join(py3_loc, "python3"),
             os.path.join(py3_loc, "csvtomd"),
             os.path.join(content_dir, "budget.csv")])
        content['blocks']['budget'] = budget
        # logging.debug(budget)


def render_template(env, name, content):

    template_fn = "{}.md.j2".format(name)
    # logging.debug(env.list_templates())
    try:
        template = env.get_template(template_fn)
        return template.render(content) + '\n\n'
    except TemplateNotFound:
        logging.warn("Template {} not found!".format(template_fn))
        return ''


def render_pdoc(blueprint, content, content_dir):

    # Create env
    env = Environment(loader=FileSystemLoader(
        [os.path.join(pdoc_loc, 'templates'), content_dir]))

    def j2_strftime(date):
        date = dateparser.parse(date)
        native = date.replace(tzinfo=None)
        format = '%B %d, %Y'
        return native.strftime(format)

    def j2_sortkeys(keys):

        def get_year(k):
            nums = re.sub('[^0-9]', '', k)
            nums = nums[-4:]
            # logging.debug(nums)
            return nums

        keys.sort(key=get_year, reverse=True)
        return keys

    def j2_bystart(items, reverse=False):
        items.sort(key=lambda k: k['startdate'] or k['enddate'], reverse=reverse)
        return items

    def j2_ongoing(items):
        """
        Returns list of items with no enddate, or enddate in the future
        """
        # logging.debug(items)
        ret = []
        for item in items:
            if not item.get('enddate') or \
                    item['enddate'] > datetime.datetime.now().date():
                ret.append(item)
        return ret

    def j2_completed(items):
        """
        Returns list of items with enddate in the past
        """
        # logging.debug(items)
        ret = []
        for item in items:
            if item.get('enddate') and \
                    item['enddate'] < datetime.datetime.now().date():
                ret.append(item)
        return ret

    # Register some useful filters
    env.filters['strftime'] = j2_strftime
    env.filters['sortkeys'] = j2_sortkeys
    env.filters['bystart'] = j2_bystart
    env.filters['ongoing'] = j2_ongoing
    env.filters['completed'] = j2_completed

    env.globals['now'] = datetime.datetime.utcnow
    env.globals.update(zip=zip)

    # Anything loaded under "blocks" gets pre-processed for Jinja
    if content.get('blocks'):
        prerender_content(env, content, content_dir)
    # logging.debug(pformat(content))

    # Go through each blueprint and append output to stream
    md = u""
    for item in blueprint:
        md += render_template(env, item, content)
    return md

def assemble_pdoc(blueprint_name, content_fp, global_fp=None):
    blueprint = read_blueprints()[blueprint_name]
    content = read_content(content_fp)
    if global_fp and os.path.exists(global_fp):
        globals = read_content(global_fp)
        content = deep_update(globals, content)

    return blueprint, content


def parse_args():

    p = ArgumentParser()
    p.add_argument("input")
    p.add_argument("blueprint")
    p.add_argument("--bibliography", "-b", default="/Users/derek/MyLibrary.yaml")
    p.add_argument("--globals",   "-g", default="globals.yml")
    p.add_argument("--format",    "-f", default="markdown_github")
    p.add_argument("--outfile",   "-o")

    opts = p.parse_args()
    return opts


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)

    py3_loc = "/Users/derek/anaconda/envs/python3/bin"
    py2_loc = "'/Users/derek/anaconda/envs/testing27/bin/"
    pdoc_loc = os.path.dirname(os.path. realpath(__file__))

    opts = parse_args()

    blueprint, content = assemble_pdoc(opts.blueprint, opts.input, opts.globals)
    md = render_pdoc(blueprint, content, os.path.split(opts.input)[0])

    # time.sleep(0.5)
    print(md)

    filters = ['pandoc-fignos',
               'pandoc-mermaid',
               'pandoc-citeproc']
    pdoc_args = ['--mathjax',
                 '--bibliography={}'.format(opts.bibliography)]

    if md.lower().find("suppress-bibliography") >= 0:
        # This is an inline bib
        csl_path = os.path.join(pdoc_loc, "_static/chicago-syllabus_plus.csl")
        pdoc_args.append('--csl={}'.format(csl_path))
    else:
        # Let's use reference links for readability
        pdoc_args += [
        '--reference-links',
        '--reference-location=section',
        # '--metadata link-citations=true'
        ]

    _format = opts.format
    if _format.startswith("markdown"):
        _format = "{}-shortcut_reference_links+multiline_tables".format(_format)
        _format = "{}-citations+multiline_tables".format(_format)

    # _format = "docx"
    # opts.outfile = "merck_cv.docx"

    # logging.debug(pdoc_args)

    output = pd.convert_text(source=md,
                             format='md',
                             to=_format,
                             extra_args=pdoc_args,
                             filters=filters,
                             outputfile=opts.outfile)

    print output

    build_dir = "_build/md"

    if not os.path.isdir(build_dir):
        os.makedirs(build_dir)

    basename = os.path.splitext(os.path.basename(opts.input))[0]
    if basename.endswith(".md"):  # was .md.j2
        basename = basename[:-3]
    pdoc_out = os.path.join( build_dir, "{}.md".format(basename) )

    with open(pdoc_out, 'w') as f:
        f.write(output.encode('utf-8'))

# TODO: rst: If there are long captions in figures, need to add double-space at front
# TODO: csv: confirm tables have no rows that start w comma!  (Or fix csv->md plugin)






