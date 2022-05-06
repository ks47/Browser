

import urllib.parse
import dukpy
from htmlParser import Element, Text, HTMLParser
from cssParser import cascade_priority, resolve_url, style, tree_to_list, CSSParser
from layoutEngine import DocumentLayout
from network import request, url_origin
from jsContext import JSContext
from display import HEIGHT, SCROLL_STEP, CHROME_PX


class Tab:
    def __init__(self):
        self.history = []
        self.focus = None
        self.url = None

        # parser goes through file and returns a list of styles as
        # [(selectorObject1, {p1: v1, p2: v2}), (selector2, {....})]
        with open("browser8.css") as f:
            self.default_style_sheet = CSSParser(f.read()).parse()

    def allowed_request(self, url):
        return self.allowed_origins == None or \
            url_origin(url) in self.allowed_origins

    # request header & body from url
    # check headers to confirm security policy
    # create html tree from body & store all scripts & styles needed
    # then finally render the page
    def load(self, url, body=None):
        headers, body = request(url, self.url, payload=body)
        self.scroll = 0
        self.url = url
        self.history.append(url)

        self.allowed_origins = None
        if "content-security-policy" in headers:
            csp = headers["content-security-policy"].split()
            if len(csp) > 0 and csp[0] == "default-src":
                self.allowed_origins = csp[1:]

        # create tree from html file's contents & returns root
        self.nodes = HTMLParser(body).parse()

        self.js = JSContext(self)
        # store src for node where tag is script
        scripts = [node.attributes["src"] for node
                   # all nodes of html tree added to list in DFS order
                   in tree_to_list(self.nodes, [])
                   if isinstance(node, Element)
                   and node.tag == "script"
                   and "src" in node.attributes]
        # resolve and execute each script
        for script in scripts:
            script_url = resolve_url(script, url)
            if not self.allowed_request(script_url):
                print("Blocked script", script, "due to CSP")
                continue
            header, body = request(script_url, url)
            try:
                print("Script returned: ", self.js.run(body))
            except dukpy.JSRuntimeError as e:
                print("Script", script, "crashed", e)

        self.rules = self.default_style_sheet.copy()

        # store href of each element with tag link & rel stylesheet
        links = [node.attributes["href"]
                 for node in tree_to_list(self.nodes, [])
                 if isinstance(node, Element)
                 and node.tag == "link"
                 and "href" in node.attributes
                 and node.attributes.get("rel") == "stylesheet"]

        for link in links:
            # resolve each href, then call cssParser
            style_url = resolve_url(link, url)
            if not self.allowed_request(style_url):
                print("Blocked style", link, "due to CSP")
                continue
            try:
                header, body = request(style_url, url)
            except:
                continue
            # rules contains all parsed rules of form
            # [(selectorObj1, {}), (selectorObj2, {}), ...]
            self.rules.extend(CSSParser(body).parse())

        self.render()

    def render(self):
        # add style dictionary to each node and its children with
        # appropriate values for each {prop, val}
        # node.style = {p1: v1, p2: v2...}
        style(self.nodes, sorted(self.rules, key=cascade_priority))

        # from root to end of tree
        # makes each node block or input object
        # decides their size and position
        # then lays them onto the canvas with paint method
        self.document = DocumentLayout(self.nodes)
        self.document.layout()
        self.display_list = []

        # calls inline or block object's paint method
        # From root node to end node
        # decides styles based on node's style property
        # (eg. node.style[background-color: "red"])
        # draws each node on the canvas accordingly

        # WHAT IS DISPLAY_LIST?
        self.document.paint(self.display_list)

    # called by browser to draw contents
    def draw(self, canvas):
        for cmd in self.display_list:
            if cmd.top > self.scroll + HEIGHT - CHROME_PX:
                continue
            if cmd.bottom < self.scroll:
                continue
            cmd.execute(self.scroll - CHROME_PX, canvas)

        if self.focus:
            obj = [obj for obj in tree_to_list(self.document, [])
                   if obj.node == self.focus][0]
            text = self.focus.attributes.get("value", "")
            x = obj.x + obj.font.measure(text)
            y = obj.y - self.scroll + CHROME_PX
            canvas.create_line(x, y, x, y + obj.height)

    def scrolldown(self):
        max_y = self.document.height - (HEIGHT - CHROME_PX)
        self.scroll = min(self.scroll + SCROLL_STEP, max_y)

    def scrollup(self):
        if self.scroll <= 0:
            return
        self.scroll -= SCROLL_STEP

    def on_mousewheel(self, e):
        max_y = self.document.height - (HEIGHT - CHROME_PX)
        if (self.scroll <= 0 and e.delta > 0) or (self.scroll >= max_y and e.delta < 0):
            return
        self.scroll += -5*(e.delta)

    def click(self, x, y):
        self.focus = None
        y += self.scroll
        objs = [obj for obj in tree_to_list(self.document, [])
                if obj.x <= x < obj.x + obj.width
                and obj.y <= y < obj.y + obj.height]
        if not objs:
            return
        elt = objs[-1].node
        if elt and self.js.dispatch_event("click", elt):
            return
        while elt:
            if isinstance(elt, Text):
                pass
            elif elt.tag == "a" and "href" in elt.attributes:
                url = resolve_url(elt.attributes["href"], self.url)
                return self.load(url)
            elif elt.tag == "input":
                elt.attributes["value"] = ""
                self.focus = elt
                return
            elif elt.tag == "button":
                while elt:
                    if elt.tag == "form" and "action" in elt.attributes:
                        return self.submit_form(elt)
                    elt = elt.parent
            elt = elt.parent

    def submit_form(self, elt):
        if self.js.dispatch_event("submit", elt):
            return
        inputs = [node for node in tree_to_list(elt, [])
                  if isinstance(node, Element)
                  and node.tag == "input"
                  and "name" in node.attributes]

        body = ""
        for input in inputs:
            name = input.attributes["name"]
            value = input.attributes.get("value", "")
            name = urllib.parse.quote(name)
            value = urllib.parse.quote(value)
            body += "&" + name + "=" + value
        body = body[1:]

        url = resolve_url(elt.attributes["action"], self.url)
        self.load(url, body)

    def keypress(self, char):
        if self.focus:
            if self.js.dispatch_event("keydown", self.focus):
                return
            self.focus.attributes["value"] += char
        self.document.paint(self.display_list)  # TODO: is this necessary?

    def go_back(self):
        if len(self.history) > 1:
            self.history.pop()
            back = self.history.pop()
            self.load(back)
