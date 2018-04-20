import re
import yaml
import mistune
from mistune_contrib.mdrenderer import MdRenderer
from anytree import Node, RenderTree, exporter, LevelOrderIter
from pprint import pprint

# MdRenderer Pull:
# Need to decorate get_text as an @classfunction
# Need to make ordered list marker a #. for pandoc

class Mdj2Renderer(MdRenderer):
    """
    Helper to teach the MdRenderer to preserve jinja markup
    """

    def jinja2(self, text, brackets):
        return brackets[0] + text + brackets[1]


class BlockMarkdown(mistune.Markdown):
    """
    This is a quick helper for enabling the mistune.Markdown class to
    render directly from block data.
    """
    def output_toks(self, tokens, rules=None):
        self.tokens = tokens
        self.tokens.reverse()
        self.inline.setup(self.block.def_links, self.block.def_footnotes)
        out = self.renderer.placeholder()
        while self.pop():
            out += self.tok()
        return out


class Jinja2Lexer(mistune.InlineLexer):
    def enable_jinja2(self):

        # Teach grammar to stop on braces
        self.grammar_class.text = \
            re.compile(r'^[\s\S]+?(?=[\\<!\[_*`~{}]|https?://| {2,}\n|$)')

        # Create a rule to collect tokens between braces
        self.rules.jinja2 = \
            re.compile(r'({[{#%])(.*)([#%}]})')

        # Want to look for this _way_ before emphasis (multiply) or
        # other markup that could be found in Jinja blocks
        self.default_rules.insert(5, 'jinja2')

    def output_jinja2(self, m):
        text = m.group(2)
        brackets = [m.group(1), m.group(3)]
        return self.renderer.jinja2(text, brackets)


class ContentLoader(object):

    def get_meta(self, y):
        return yaml.load(y)

    def get_md_content(self, md):
        """
        mistune renderer to a hierarchical dictionary
        """
        renderer = Mdj2Renderer()
        inline = Jinja2Lexer(renderer)
        inline.enable_jinja2()
        bmdj2 = BlockMarkdown(renderer=renderer, inline=inline)
        blocks = bmdj2.block.parse(md)

        # Tree the content
        root = Node("root", level=0, type="heading", text='')
        current_root = root
        for item in blocks:
            if item['type'] == "heading" and item['level'] > current_root.level:
                current_root = Node(item['text'], parent=current_root, level=item['level'], type=item['type'])
            elif item['type'] == "heading" and item['level'] <= current_root.level:
                while item['level'] <= current_root.level:
                    current_root = current_root.parent
                current_root = Node(item['text'], parent=current_root, level=item['level'], type=item['type'])
            else:
                Node(item['type'], parent=current_root, type=item['type'], block=item)

        # print( RenderTree(root) )

        # Flatten non-heading/leaf content
        for node in LevelOrderIter(root,
                                   filter_=lambda n: n.type == "heading"):
            blocks = []
            for child in node.children:
                if child.type == "heading":
                    continue
                blocks.append(child.block)
                child.parent = None
            node.text = bmdj2.output_toks(blocks)
            # print node.text

        # Hierarchical export by section
        d = exporter.DictExporter().export(root)

        # Compactify it into the nested dict format used here
        dd = []
        def handle_child(child):
            k = child['name']
            v = child['text']
            if child.get('children'):
                ddd = []
                if v:
                    ddd.append({"preamble": v})
                for grandchild in child['children']:
                    kk, vv = handle_child(grandchild)
                    ddd.append({kk: vv})
                return k, ddd
            return k, v

        for child in d['children']:
            k, v = handle_child(child)
            dd.append({k: v})

        return dd

    def load(self, fp):
        with open(fp, "rU") as f:
            doc = f.read()
        _, y, m = re.split("^---$", doc, flags=re.MULTILINE, maxsplit=2)

        content = self.get_meta(y)
        md_content = self.get_md_content(m)

        content['blocks'] = {}
        # Map top level instead of array
        for item in md_content:
            k = item.keys()[0]
            content['blocks'][k.lower().replace(" ", "_")]=item[k]

        return content


def test_loader():

    fp = "/Users/derek/dev/pragmatics/flex_ext/flex_ext.md.j2"
    content = ContentLoader().load(fp)
    pprint(content)

if __name__=="__main__":

    test_loader()





