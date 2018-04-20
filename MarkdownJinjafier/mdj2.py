"""
MarkdownJinjafier

Merck, Spring 2018
"""

import jinja2, re, yaml, logging, pypandoc, json, os, time, StringIO, datetime, collections
from yaml_extras import IncludeLoader
import jinja_filters
from pprint import pprint, pformat

# Can't merge arrays with this (but how would you?)
def deep_update(d, u):
    for k, v in u.iteritems():
        if isinstance(v, collections.Mapping):
            d[k] = deep_update(d.get(k, {}), v)
        else:
            d[k] = v
    return d

class MdJ2(object):

    pd_api = None     # Pandoc api version
    module_path = os.path.dirname(os.path.realpath(__file__)) # Module directory
    bp_blocks = None  # Boilerplate

    def __init__(self, **kwargs):
        self.bibliography = kwargs.get('bibliograpy', "/Users/derek/MyLibrary.yaml")
        boilerplate_fp = kwargs.get('boilerplate',
                     os.path.join(self.module_path, "_templates/boilerplate.mdj2"))
        with open(boilerplate_fp, "rU") as f:
            bp = f.read()
            self.__class__.bp_blocks = self.blockify(bp)

        globals_fp = kwargs.get('globals')
        if globals_fp:
            with open(globals_fp, "rU") as f:
                self.global_vars = yaml.load(f)
        else:
            self.global_vars = {}


    def call_pandoc(self, md, fmt="markdown_github", outfile=None):

        filters = ['pandoc-fignos',
                   #'pandoc-mermaid',
                   'pandoc-citeproc']
        pdoc_args = [#'--mathjax',
                     '--bibliography={}'.format(self.bibliography)]

        if fmt.startswith("markdown"):
            fmt = "{}-shortcut_reference_links+multiline_tables-citations".format(fmt)

        if md.lower().find("suppress-bibliography") >= 0:
            # This is an inline bib
            csl_path = os.path.join(self.module_path, "_static/chicago-syllabus_plus.csl")
            pdoc_args.append('--csl={}'.format(csl_path))
            # format = fmt + "-citations"
        else:
            # Let's use reference links for readability
            pdoc_args += [
                '--reference-links',
                '--reference-location=section',
                # '--metadata link-citations=true'
            ]

        pd = pypandoc.convert_text(source=md,
                                 format='md',
                                 to=fmt,
                                 extra_args=pdoc_args,
                                 filters=filters,
                                 outputfile=outfile)
        return pd

    def render_md(self, fp_content, fp_format, fp_globals=None, fmt=None, outfile=None):

        intermediate = self.render_mdj2(fp_content, fp_format, global_vars=self.global_vars, fp_globals=fp_globals)
        output = self.call_pandoc(intermediate, fmt=fmt, outfile=outfile)

        return output

    # ------------------------------
    # Class methods, no boilerplate or pandoc
    # ------------------------------

    @classmethod
    def blockify(cls, content):
        # Separates out top-level blocks for use with templates
        pd = pypandoc.convert_text(source=content,
                                   format='md',
                                   to="json")
        cd = json.loads(pd)
        cls.pd_api = cd.get('pandoc-api-version')
        pd_blocks = {}

        for b in cd.get('blocks'):
            if b['t'] == "Header" and b['c'][0] == 1:
                key = b['c'][1][0]
                pd_blocks[key] = []
            pd_blocks[key].append(b)
        return pd_blocks

    @classmethod
    def render(cls, md, meta):

        def render_blocks(blocks, level=1):

            def offset_headers(blocks, offset):
                for b in blocks:
                    if b['t'] == "Header":
                        b['c'][0] = b['c'][0] + offset
                return blocks

            offset = 0
            if blocks[0]['t'] == "Header":
                cardinal_level = blocks[0]['c'][0]
                offset = level - cardinal_level

            if offset != 0:
                blocks = offset_headers(blocks, offset)

            input_ = {'blocks': blocks,
                      'meta': {},
                      u'pandoc-api-version': cls.pd_api}
            input = json.dumps(input_)

            pd = pypandoc.convert_text(source=input,
                                       format='json',
                                       to="md")
            return pd

        def render_boilerplate(type, active=True):
            if not active:
                return
            return render_blocks([cls.bp_blocks[type][1]])

        def block_boilerplate(blocks, type, section=None, active=True):

            if not active:
                return blocks
            inblock = False
            i = None
            for i, b in enumerate(blocks):
                if b['t'] == "Header" and (b['c'][1][0] == section or not section):
                    # logging.debug("found opening for {} at {}".format(type, i))
                    inblock = True
                elif b['t'] == "Header":
                    if inblock:
                        break

            if inblock:
                # logging.debug("found closing for {} at {}".format(type, i))
                blocks.insert(i, cls.bp_blocks[type][1])

            return blocks

        env = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.join(cls.module_path, '_templates')))
        env.filters['sortkeys'] = jinja_filters.j2_sortkeys
        env.filters['strftime'] = jinja_filters.j2_strftime
        env.filters['bystart'] = jinja_filters.j2_bystart
        env.filters['ongoing'] = jinja_filters.j2_ongoing
        env.filters['completed'] = jinja_filters.j2_completed
        env.filters['csv2table'] = jinja_filters.j2_csv2table

        env.globals['now'] = datetime.datetime.utcnow
        env.globals['zip'] = zip

        # All of these are for merging, once the pre-pass has been done, they don't appear in MD
        env.filters['render_blocks'] = render_blocks
        env.filters['boilerplate'] = block_boilerplate
        env.globals['boilerplate'] = render_boilerplate

        # Takes jinjafied-markdown and metadata, produces markdown
        template = env.from_string(md)
        output = template.render(meta)
        return output

    @classmethod
    def render_mdj2(cls, fp_content, fp_format, global_vars=None, fp_globals=None):

        meta = MdJ2.load(fp_content)

        if not global_vars and fp_globals:
            with open(fp_globals, 'rU') as f:
                global_vars = yaml.load(f)
        if global_vars:
            meta = deep_update(global_vars, meta)

        with open(fp_format, "rU") as f:
            template = f.read()

        return MdJ2.render(template, meta)

    @classmethod
    def loads(cls, s, fp=None):
        # load string or stream

        # check for multidocument
        if not re.match("^---$", s, flags=re.MULTILINE):
            stio = StringIO.StringIO(s)
            stio.name = fp or cls.module_path
            meta = yaml.load( stio, Loader=IncludeLoader)
        else:
            _, y_s, md_s = re.split("^---$", s, flags=re.MULTILINE, maxsplit=2)
            stio = StringIO.StringIO(y_s)
            stio.name = fp or cls.module_path
            meta = yaml.load( stio, Loader=IncludeLoader )
            if md_s:
                md_ss = cls.render(md_s, meta)
                meta['blocks'] = cls.blockify( md_ss )
        return meta

    @classmethod
    def load(cls, fp):
        with open(fp, 'rU') as f:
            s = f.read()
        return cls.loads(s, fp)


def test_loaders():
    # Test with strings
    meta = MdJ2.loads(u"---\nfoo: bar\n---\n# {{ foo }}\n\neggs eggs eggs\n\n## {{ foo*2 }}")
    output = MdJ2.render(u"{{ blocks.bar | render_blocks(level=3) }}", meta)
    assert(output==u'### bar\n\neggs eggs eggs\n\n#### barbar\n')

    # Test with files
    fp_content = os.path.join(MdJ2.module_path, "test/content.mdj2")
    fp_format =  os.path.join(MdJ2.module_path, "test/format.mdj2" )
    meta = MdJ2.load(fp_content)
    with open(fp_format, "rU") as f:
        template = f.read()
    output = MdJ2.render(template, meta)
    assert(output==u'### bar\n\neggs eggs eggs\n\n#### barbar\n')

    # Test with file loader
    output = MdJ2.render_mdj2(fp_content, fp_format)
    assert(output==u'### bar\n\neggs eggs eggs\n\n#### barbar\n')


def test_boilerplate():
    # In order to use boilerplate, must have an instance
    meta = MdJ2.loads(u"---\nfoo: bar\n---\n# {{ foo }}\n\neggs eggs eggs\n\n## {{ foo*2 }}")
    output = MdJ2().render(u"{{ blocks.bar | boilerplate('spam', 'bar') | render_blocks(level=3) }}\n\n{{ boilerplate('spam') }}\n", meta)
    assert(output == u'### bar\n\neggs eggs eggs\n\n'
                     u'Spam spam spam spam\n\n'
                     u'#### barbar\n\n\nSpam spam spam spam\n')

    fp_content = os.path.join(MdJ2.module_path, "test/content.mdj2")
    fp_format =  os.path.join(MdJ2.module_path, "test/format_bp.mdj2" )
    output = MdJ2().render_mdj2(fp_content, fp_format)
    assert(output == u'### bar\n\neggs eggs eggs\n\n'
                     u'Spam spam spam spam\n\n'
                     u'#### barbar\n\n\nSpam spam spam spam\n')


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)
    # test_loaders()
    # test_boilerplate()
