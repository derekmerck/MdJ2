"""
PragmaDoc - Pragmatical Text Editor

Pragmatics: meaning is derrived from both semantics and context

1. Read meta data
2. Read asset data
3. Recursively parse blueprint nodes
4. Map asset and template to each node
5. Preprocess each node with Jinja2
6. Assemble final stream
7. Use Pandoc academic markdown + citeproc to convert to final format

Requires:
Jinja2 preprocessor
Pandoc Academic Markdown

Create RST for sphinx
Create doc for sharing/pdfing

"""

import yaml, logging, time, collections, os
from argparse import ArgumentParser
from glob import glob
from pprint import pformat
import pypandoc as pd
from jinja2 import Environment, FileSystemLoader
import dateutil.parser as dateparser
from subprocess import check_output

def read_yml(fp):
    with open(fp, 'rU') as f:
        return yaml.load(f)

def read_blueprints():
    bps = {}
    for fp in glob(os.path.join(pdoc_loc, "blueprints/*.yml")):
        bps.update(read_yml(fp))
    return bps

def read_content(fp):
    return read_yml(fp)

def deep_update(d, u):
    for k, v in u.iteritems():
        if isinstance(v, collections.Mapping):
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

    content['content'] = render(content['content'])

    # prerender budget if it exists
    if os.path.exists(os.path.join(content_dir, "budget.csv")):
        budget = check_output(
            [os.path.join(py3_loc, "python3"),
             os.path.join(py3_loc, "csvtomd"),
             os.path.join(content_dir, "budget.csv")])
        content['content']['budget'] = budget
        logging.debug(budget)


def render_template(env, name, content):

    template_fn = "{}.md.j2".format(name)
    # logging.debug(env.list_templates())
    try:
        template = env.get_template(template_fn)
    except:
        logging.warn("Template {} not found!".format(template_fn))
        return ''
    return template.render(content) + '\n\n'

def render_pdoc(blueprint, content, content_dir):

    def j2_strftime(date):
        date = dateparser.parse(date)
        native = date.replace(tzinfo=None)
        format = '%B %d, %Y'
        return native.strftime(format)

    env = Environment(loader=FileSystemLoader(
        [os.path.join(pdoc_loc, 'templates'), content_dir]))
    env.filters['strftime'] = j2_strftime

    prerender_content(env, content, content_dir)
    logging.debug(pformat(content))


    md = u""
    for item in blueprint:
        md += render_template(env, item, content)
    return md

def assemble_pdoc(blueprint_name, content_fp, global_fp=None):
    blueprint = read_blueprints()[blueprint_name]
    globals = read_content(global_fp)
    content = read_content(content_fp)
    content = deep_update(globals, content)

    return blueprint, content


def parse_args():

    p = ArgumentParser()
    p.add_argument("input")
    p.add_argument("blueprint")
    p.add_argument("--bibliography", "-b", default="/Users/derek/MyLibrary.yaml")
    p.add_argument("--globals",   "-g", default="content/globals.yml")
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

    time.sleep(0.5)
    print(md)

    filters = ['pandoc-fignos',
               'pandoc-mermaid',
               'pandoc-citeproc']
    pdoc_args = ['--mathjax',
                 '--bibliography={}'.format(opts.bibliography)]
    output = pd.convert_text(source=md,
                             format='md',
                             to=opts.format,
                             extra_args=pdoc_args,
                             filters=filters,
                             outputfile=opts.outfile)

    time.sleep(0.5)
    print output

    # with open('test.rst', 'w') as f:
    #     f.write(output.encode('utf-8'))


# TODO: If there are long captions in figures, need to add double-space at front
# TODO: confirm tables are properly formatted






