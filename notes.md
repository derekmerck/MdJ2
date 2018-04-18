pandoc filters

assembler -> pandoc -> ast -> jinja processor -> pandoc -> output format



assembler:

(format template)
[front] + [aims] + [bg] + [approach]   \
                                         --> md + jinja  -> use a pandoc filter to handle jinja
 front  +  aims  +  bg +   approach    / 
(use pandoc to disassemble the input document)

semiotext


MdJijnafier

mdj2 format w/ yaml and expansions
returns expanded md and (optionally) the meta

MdBlockify


Document
- template
- meta
- blocks (AST)
- copy