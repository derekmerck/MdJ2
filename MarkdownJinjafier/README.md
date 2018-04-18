# MarkdownJinjaifier

Merck, Spring 2018

## Overview

...

## Usage

Also supports yaml `!include` directive

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

Using an instance enables boilerplate blocks and bibliographies. This inserts the boilerplate "spam spam spam" at the end of any block named "bar".

```python
    output = MdJ2().render(u"{{ blocks.bar | boilerplate('spam', 'bar') | render_blocks(level=3) }}\n\n{{ boilerplate('spam') }}\n", meta)
    assert(output == u'### bar\n\neggs eggs eggs\n\n'
                     u'Spam spam spam spam\n\n'
                     u'#### barbar\n\n\nSpam spam spam spam\n')
```

Finally, sending the output to the `pandoc()` function will parse
bibliographies, figure numbers, mermaid, etc.

A convenience function `render_md()` wraps the entire pipeline.
