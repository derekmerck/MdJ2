"""
From https://davidchall.github.io/yaml-includes.html with minor modifications**

** result += ... to result.append()

```
education:    !include education.yaml

activities:   !include [schools.yaml, conferences.yaml, workshops.yaml]

publications: !include {peer_reviewed: publications/peer_reviewed.yaml, internal: publications/internal.yaml}
```

```
with open('document.yaml', 'r') as f:
    data = yaml.load(f, Loader=IncludeLoader)
```
"""
import yaml, logging, os.path
import pprint


class IncludeLoader(yaml.Loader):
    def __init__(self, stream):
        self._root = os.path.split(stream.name)[0]
        super(IncludeLoader, self).__init__(stream)
        IncludeLoader.add_constructor('!include', IncludeLoader.include)
        IncludeLoader.add_constructor('!import',  IncludeLoader.include)
        IncludeLoader.add_constructor('!include_raw', IncludeLoader.include_raw)

    def include_raw(self, node):
        return self.include(node, func=self.read_raw)

    def include(self, node, func=None):
        if func == None:
            func=self.read_yml

        if isinstance(node, yaml.ScalarNode):
            return func(self.construct_scalar(node))

        elif isinstance(node, yaml.SequenceNode):
            result = []
            for filename in self.construct_sequence(node):
                result.append(func(filename))
            return result

        elif isinstance(node, yaml.MappingNode):
            result = {}
            for k,v in self.construct_mapping(node).iteritems():
                result[k] = func(v)
            return result

        else:
            print "Error:: unrecognised node type in !include statement"
            raise yaml.constructor.ConstructorError

    def read_yml(self, filename):
        filepath = os.path.join(self._root, filename)
        with open(filepath, 'r') as f:
            return yaml.load(f, IncludeLoader)

    def read_raw(self, filename):
        filepath = os.path.join(self._root, filename)
        with open(filepath, 'r') as f:
            return f.read()


def test():

    with open("test/yaml_extras/base.yml") as f:
        res = yaml.load(f, Loader=IncludeLoader)
        assert( res == {'raw': '@baz [baz baz] -baz ---', 'scalar': ['foo', 'fooo', 'foooo'], 'dict': {'foo': ['foo', 'fooo', 'foooo'], 'bar': {'bar': ['foo', 'fooo', 'foooo']}}, 'array': [['foo', 'fooo', 'foooo'], {'bar': ['foo', 'fooo', 'foooo']}]} )


    s = \
"""
foo: [1,2,3]
bar: {foo: bar}    
"""
    import StringIO
    stio = StringIO.StringIO(s)
    stio.name = os.getcwd()
    res = yaml.load(stio, Loader=IncludeLoader)
    assert(res == {'foo': [1, 2, 3], 'bar': {'foo': 'bar'}} )


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)
    test()