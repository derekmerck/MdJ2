# MarkdownJinjaifier

Merck, Spring 2018

## Dependencies

- Pandoc
- pandoc-citeproc
- pandoc-fignos (filter)
- dateutil
- Jinja2
- pypandoc

## Overview

Parses a text format that I commonly use for semi-automatic documentation.

```yaml
---
yaml_header: true
enables: !include files.yml
---
# Markdown Content Blocks

With {{ "jinja" }} pre-processing.
```

I use the extension `.mdj2` for this format.  

This parser reads markdown level 1 headers into a dictionary 
and stores them as pandoc AST/JSON in a meta variable called
`blocks`.

The entire meta data structure can then be passed to fairly 
complicated jinja templates.  I use this framework for automatically
generating my CV and formatting short and long version of grant 
proposals, reports, abstracts, and manuscripts.

## Usage

### Multipass Jijna

This expands `{{ foo }}` and parses the AST blocks for `bar`.

```python
>>> from MarkdownJinjafier import MdJ2
>>> meta = MdJ2.loads(u"---\nfoo: bar\n---\n# {{ foo }}\n\neggs eggs eggs\n\n## {{ foo*2 }}")
```

Now the block `bar` can be used in any template and rendered with the filter
`render_blocks(level)`, where level is the desired top header level.

```python
>>> output = MdJ2.render(u'{{ blocks.bar | render_blocks(level=3) }}', meta)
>>> assert(output==u'### bar\n\neggs eggs eggs\n\n#### barbar\n')
```

A convenience function, `render_mdj2(content_fp, template_fp)` combines loading
and rendering into a single function.

### Boilerplate and Pandoc

Using an instance enables boilerplate blocks and bibliographies. This inserts
the boilerplate "spam spam spam" at the end of any block named "bar".

```python
    output = MdJ2().render(u"{{ blocks.bar | boilerplate('spam', 'bar') | render_blocks(level=3) }}\n\n{{ boilerplate('spam') }}\n", meta)
    assert(output == u'### bar\n\neggs eggs eggs\n\n'
                     u'Spam spam spam spam\n\n'
                     u'#### barbar\n\n\nSpam spam spam spam\n')
```

Finally, sending the output to the `call_pandoc()` function will compile
bibliographies, figure numbers, mermaid, etc.

A convenience function `render_md()` wraps the entire pipeline.