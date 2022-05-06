
class Text:
    def __init__(self, text, parent):
        self.text = text
        self.children = []
        self.parent = parent

    def __repr__(self):
        return repr(self.text)


class Element:
    def __init__(self, tag, attributes, parent, cls=None):
        self.tag = tag
        self.attributes = attributes
        self.children = []
        self.parent = parent
        self.cls = cls

    def __repr__(self):
        attrs = [" " + k + "=\"" + v + "\"" for k,
                 v in self.attributes.items()]
        return "<" + self.tag + "".join(attrs) + ">"


def print_tree(node, indent=0):
    print(" " * indent, node)
    for child in node.children:
        print_tree(child, indent + 2)

# get html files's contents as input, converts them into a tree of elements & text


class HTMLParser:
    def __init__(self, body):
        self.body = body
        self.unfinished = []

    # make html tree and return its root
    def parse(self):
        text = ""
        in_tag = False
        for c in self.body:
            if c == "<":
                in_tag = True
                # if any text encountered before <
                if text:
                    # make it text object and append to parent
                    self.add_text(text)
                text = ""
            elif c == ">":
                in_tag = False
                # when tags ends, make it element object & add node to its parent's children
                self.add_tag(text)
                text = ""
            else:
                # build a tag or text
                text += c
        if not in_tag and text:
            # add any remaining text to the tree
            self.add_text(text)
        return self.finish()

    # parses attributes and adds them in the
    # attributes property of respective Element object as a dictionary
    def get_attributes(self, text):
        parts = text.split()
        tag = parts[0].lower()
        attributes = {}
        for attrpair in parts[1:]:
            if "=" in attrpair:
                key, value = attrpair.split("=", 1)
                if len(value) > 2 and value[0] in ["'", "\""]:
                    value = value[1:-1]
                attributes[key.lower()] = value
            else:
                attributes[attrpair.lower()] = ""
        return tag, attributes

    # create text object and add it to parent's children list
    def add_text(self, text):
        if text.isspace():
            return
        self.implicit_tags(None)
        # appends item to previous unfinshed parent
        parent = self.unfinished[-1]
        node = Text(text, parent)
        parent.children.append(node)

    SELF_CLOSING_TAGS = [
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr",
    ]

    def add_tag(self, tag):
        tag, attributes = self.get_attributes(tag)
        if tag.startswith("!"):
            return
        # add closing tag if not added by developer
        self.implicit_tags(tag)

        cls = None
        if "class" in attributes:
            cls = "." + attributes["class"]
            print(cls)

        if tag.startswith("/"):
            if len(self.unfinished) == 1:
                return
            # if closing tag, add it to parent
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        elif tag in self.SELF_CLOSING_TAGS:
            parent = self.unfinished[-1]
            node = Element(tag, attributes, parent, cls)
            parent.children.append(node)
        else:
            parent = self.unfinished[-1] if self.unfinished else None
            node = Element(tag, attributes, parent, cls)
            self.unfinished.append(node)

    HEAD_TAGS = [
        "base", "basefont", "bgsound", "noscript",
        "link", "meta", "title", "style", "script",
    ]

    def implicit_tags(self, tag):
        # self close tags if not closed by developers
        # & adds html, head, body if not added by dev
        while True:
            open_tags = [node.tag for node in self.unfinished]
            if open_tags == [] and tag != "html":
                self.add_tag("html")
            elif open_tags == ["html"] \
                    and tag not in ["head", "body", "/html"]:
                if tag in self.HEAD_TAGS:
                    self.add_tag("head")
                else:
                    self.add_tag("body")
            elif open_tags == ["html", "head"] and \
                    tag not in ["/head"] + self.HEAD_TAGS:
                self.add_tag("/head")
            else:
                break

    def finish(self):
        # if everything parsed add html at the end
        # else add remaining alements to the tree
        if len(self.unfinished) == 0:
            self.add_tag("html")
        while len(self.unfinished) > 1:
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        # return the root of the tree
        return self.unfinished.pop()
