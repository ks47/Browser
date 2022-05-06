
from htmlParser import Text, Element
from layoutParser import layout_mode, DrawRect


# convert variable to absolute path
def resolve_url(url, current):
    if "://" in url:
        return url
    elif url.startswith("/"):
        scheme, hostpath = current.split("://", 1)
        host, oldpath = hostpath.split("/", 1)
        return scheme + "://" + host + url
    else:
        scheme, hostpath = current.split("://", 1)
        if "/" not in hostpath:
            current = current + "/"
        dir, _ = current.rsplit("/", 1)
        while url.startswith("../"):
            url = url[3:]
            if dir.count("/") == 2:
                continue
            dir, _ = dir.rsplit("/", 1)
        return dir + "/" + url

# nodes of html tree added to list in DFS order


# DFS to get items of html tree in a list
def tree_to_list(tree, list):
    list.append(tree)
    for child in tree.children:
        tree_to_list(child, list)
    return list


# contents of css file as input s, i is index of current char being read
#
class CSSParser:
    def __init__(self, s):
        self.s = s
        self.i = 0

    # is current char is whitespace, move forward
    def whitespace(self):
        while self.i < len(self.s) and self.s[self.i].isspace():
            self.i += 1

    # if current char literal like :, move forward
    def literal(self, literal):
        assert self.i < len(self.s) and self.s[self.i] == literal
        self.i += 1

    # if current char is alphanumeric or in "#-.%", include it in word
    # once invalid char encoutered, return word built until now
    def word(self):
        start = self.i
        while self.i < len(self.s):
            if self.s[self.i].isalnum() or self.s[self.i] in "#-.%":
                self.i += 1
            else:
                break
        assert self.i > start
        return self.s[start:self.i]

    # save current word in prop variable
    # skip whitespace and :
    # save next word in val variable
    # return them as (prop, val pair)
    def pair(self):
        prop = self.word()
        self.whitespace()
        self.literal(":")
        self.whitespace()
        val = self.word()
        return prop.lower(), val

    # ignore until desired chars are seen
    def ignore_until(self, chars):
        while self.i < len(self.s):
            if self.s[self.i] in chars:
                return self.s[self.i]
            else:
                self.i += 1

    # goes through a css selector in file, eg. pre{..:..; ..:..}
    # returns dictionary of prop: value pairs from it
    def body(self):
        pairs = {}
        while self.i < len(self.s) and self.s[self.i] != "}":
            try:
                prop, val = self.pair()
                pairs[prop.lower()] = val
                self.whitespace()
                self.literal(";")
                self.whitespace()
            except AssertionError:
                why = self.ignore_until([";", "}"])
                if why == ";":
                    self.literal(";")
                    self.whitespace()
                else:
                    break
        return pairs

    def selector(self):
        word = self.word().lower()
        if word[0] == '.':
            out = ClassSelector(word)
        else:
            out = TagSelector(word)
        self.whitespace()
        while self.i < len(self.s) and self.s[self.i] != "{":
            tag = self.word()
            descendant = TagSelector(tag.lower())
            out = DescendantSelector(out, descendant)
            self.whitespace()
        return out

    # creates list of form: [(selectorObject, {p1: v1, p2: v2})], eg. [(.title, {color: blue, ...})]
    def parse(self):
        rules = []
        while self.i < len(self.s):
            try:
                self.whitespace()
                selector = self.selector()
                self.literal("{")
                self.whitespace()
                body = self.body()
                self.literal("}")
                rules.append((selector, body))
            except AssertionError:
                why = self.ignore_until(["}"])
                if why == "}":
                    self.literal("}")
                    self.whitespace()
                else:
                    break
        return rules


# converts input word into a tagselector object
# later we can pass other nodes to match method to see if they have
# the same tag
class TagSelector:
    def __init__(self, tag):
        self.tag = tag
        self.priority = 1

    def matches(self, node):
        return isinstance(node, Element) and self.tag == node.tag

    def __repr__(self):
        return "TagSelector(tag={}, priority={})".format(
            self.tag, self.priority)


class ClassSelector:
    def __init__(self, cls):
        self.cls = cls
        self.priority = 10

    # wont work since nodes dont have cls property
    def matches(self, node):
        return isinstance(node, Element) and self.cls == node.cls

    def __repr__(self):
        return "ClassSelector(class={}, priority={})".format(
            self.cls, self.priority)


class DescendantSelector:
    def __init__(self, ancestor, descendant):
        self.ancestor = ancestor
        self.descendant = descendant
        self.priority = ancestor.priority + descendant.priority

    def matches(self, node):
        if not self.descendant.matches(node):
            return False
        while node.parent:
            if self.ancestor.matches(node.parent):
                return True
            node = node.parent
        return False

    def __repr__(self):
        return ("DescendantSelector(ancestor={}, descendant={}, priority={}") \
            .format(self.ancestor, self.descendant, self.priority)


INHERITED_PROPERTIES = {
    "font-size": "16px",
    "font-style": "normal",
    "font-weight": "normal",
    "font-family": "roman",
    "color": "black",
}


# style depends on it, compute each property: value pair, eg. font-size: 16px
def compute_style(node, property, value):
    if property == "font-size":
        if value.endswith("px"):
            return value
        elif value.endswith("%"):
            if node.parent:
                parent_font_size = node.parent.style["font-size"]
            else:
                parent_font_size = INHERITED_PROPERTIES["font-size"]
            node_pct = float(value[:-1]) / 100
            parent_px = float(parent_font_size[:-2])
            return str(node_pct * parent_px) + "px"
        else:
            return None
    else:
        return value

# for nodes passed, adds a style dictionary {prop1: v1}


def style(node, rules):
    node.style = {}
    # for item in inherited_properties
    # if parent has a specific value then inherit it,
    # else get the default value for that property
    for property, default_value in INHERITED_PROPERTIES.items():
        if node.parent:
            node.style[property] = node.parent.style[property]
        else:
            node.style[property] = default_value
    # for each property in browser.css: compute its style for this element
    for selector, body in rules:
        # skip if property is not for this element
        if not selector.matches(node):
            continue
        # if property for this element, eg. class="title",
        # then compute all styles for the element
        for property, value in body.items():
            computed_value = compute_style(node, property, value)
            if not computed_value:
                continue
            node.style[property] = computed_value
    # support for "style property"
    if isinstance(node, Element) and "style" in node.attributes:
        pairs = CSSParser(node.attributes["style"]).body()
        for property, value in pairs.items():
            computed_value = compute_style(node, property, value)
            node.style[property] = computed_value
    if isinstance(node, Element) and node.tag == "pre":
        node.style["font-family"] = "Courier"
    # apply same style rules on each child as well
    for child in node.children:
        style(child, rules)


def cascade_priority(rule):
    selector, body = rule
    return selector.priority


class DrawText:
    def __init__(self, x1, y1, text, font, color):
        self.top = y1
        self.left = x1
        self.text = text
        self.font = font
        self.color = color

        self.bottom = y1 + font.metrics("linespace")

    def execute(self, scroll, canvas):
        canvas.create_text(
            self.left, self.top - scroll,
            text=self.text,
            font=self.font,
            anchor='nw',
            fill=self.color,
        )

    def __repr__(self):
        return "DrawText(text={})".format(self.text)
