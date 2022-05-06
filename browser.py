
import tkinter
import tkinter.font
from tabs import Tab
from display import get_font, WIDTH, HEIGHT, CHROME_PX


class Browser:
    def __init__(self):
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window,
            width=WIDTH,
            height=HEIGHT,
            bg="white",
        )
        self.canvas.pack()

        self.window.bind("<Down>", self.handle_down)
        self.window.bind("<Up>", self.handle_up)
        self.window.bind("<MouseWheel>", self.handle_on_mousewheel)
        self.window.bind("<Button-1>", self.handle_click)
        self.window.bind("<Key>", self.handle_key)
        self.window.bind("<Return>", self.handle_enter)

        self.window.title("Karan's Browser")

        self.tabs = []
        self.active_tab = None
        self.focus = None
        self.address_bar = ""

    def handle_down(self, e):
        self.tabs[self.active_tab].scrolldown()
        self.draw()

    def handle_up(self, e):
        self.tabs[self.active_tab].scrollup()
        self.draw()

    def handle_on_mousewheel(self, e):
        self.tabs[self.active_tab].on_mousewheel(e)
        self.draw()

    def handle_click(self, e):
        if e.y < CHROME_PX:
            self.focus = None
            if 40 <= e.x < 40 + 80 * len(self.tabs) and 0 <= e.y < 40:
                self.active_tab = int((e.x - 40) / 80)
            elif 10 <= e.x < 30 and 10 <= e.y < 30:
                self.load("https://browser.engineering/")
            elif 10 <= e.x < 35 and 40 <= e.y < 90:
                self.tabs[self.active_tab].go_back()
            elif 50 <= e.x < WIDTH - 10 and 40 <= e.y < 90:
                self.focus = "address bar"
                self.address_bar = ""
        else:
            self.focus = "content"
            self.tabs[self.active_tab].click(e.x, e.y - CHROME_PX)
        self.draw()

    def handle_key(self, e):
        if len(e.char) == 0:
            return
        if not (0x20 <= ord(e.char) < 0x7f):
            return
        if self.focus == "address bar":
            self.address_bar += e.char
            self.draw()
        elif self.focus == "content":
            self.tabs[self.active_tab].keypress(e.char)
            self.draw()

    def handle_enter(self, e):
        if self.focus == "address bar":
            self.tabs[self.active_tab].load(self.address_bar)
            self.focus = None
            self.draw()

    # call new_tabs load method, add it to tabs list
    def load(self, url="file://browser.html"):
        new_tab = Tab()
        new_tab.load(url)
        self.active_tab = len(self.tabs)
        self.tabs.append(new_tab)
        self.draw()

    # call draw method of active tab, then draw the browser's UI
    def draw(self):

        self.window.title = "Karan's Browser"
        self.canvas.delete("all")
        # calls active tab's draw method
        self.tabs[self.active_tab].draw(self.canvas)
        # Here onwards: draw browser's UI
        bgcolor = "#00123b"
        bgsecondary = "#16407a"
        linewhite = "#f2f2f3"
        linegrey = "#969696"

        # search and tabs area
        self.canvas.create_rectangle(0, 0, WIDTH, CHROME_PX,
                                     fill=bgcolor, outline=bgcolor)

        # tab box
        tabfont = get_font(18, "normal", "roman")
        for i, tab in enumerate(self.tabs):
            name = "Tab {}".format(i)
            x1, x2 = 40 + 80 * i, 120 + 80 * i
            # active tab
            if i == self.active_tab:
                self.canvas.create_rectangle(x1, 0, x2, 40, fill=bgsecondary,
                                             outline=bgsecondary)
            else:
                # vertical lines and tab name
                self.canvas.create_line(x1, 10, x1, 30, fill=linegrey)
                self.canvas.create_line(x2, 10, x2, 30, fill=linegrey)
            self.canvas.create_text(x1 + 10, 10, anchor="nw", text=name,
                                    font=tabfont, fill=linewhite)

        #  + button
        buttonfont = get_font(22, "normal", "roman")
        self.canvas.create_text(13, 6, anchor="nw", text="+",
                                font=buttonfont, fill=linewhite)

        self.canvas.create_rectangle(0, 41, WIDTH, CHROME_PX,
                                     fill=bgsecondary, outline=bgsecondary)
        # search box
        searchfont = get_font(16, "normal", "roman")
        # self.canvas.create_rectangle(40, 50, WIDTH - 10, 90, fill="#101010",
        #                              outline="#101010", width=1)

        def round_rectangle(x1, y1, x2, y2, radius=25, **kwargs):
            points = [x1+radius, y1,
                      x1+radius, y1,
                      x2-radius, y1,
                      x2-radius, y1,
                      x2, y1,
                      x2, y1+radius,
                      x2, y1+radius,
                      x2, y2-radius,
                      x2, y2-radius,
                      x2, y2,
                      x2-radius, y2,
                      x2-radius, y2,
                      x1+radius, y2,
                      x1+radius, y2,
                      x1, y2,
                      x1, y2-radius,
                      x1, y2-radius,
                      x1, y1+radius,
                      x1, y1+radius,
                      x1, y1]

            return self.canvas.create_polygon(points, **kwargs, smooth=True)

        round_rectangle(40, 50, WIDTH - 120, 90, radius=50, fill="#101010",
                        outline=bgsecondary, width=1)
        if self.focus == "address bar":
            # search bar while searching
            self.canvas.create_text(
                55, 60, anchor='nw', text=self.address_bar,
                font=searchfont, fill=linewhite)
            w = searchfont.measure(self.address_bar)
            # search cursor
            self.canvas.create_line(55 + w, 57, 55 + w, 80, fill=linewhite)
        else:
            # search bar view when it is not clicked on
            url = self.tabs[self.active_tab].url
            self.canvas.create_text(55, 60, anchor='nw', text=url,
                                    font=searchfont, fill=linewhite)

        # back arrow
        self.canvas.create_line(
            15, 70, 30, 70, arrow=tkinter.FIRST, fill=linewhite)


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 2:
        Browser().load(sys.argv[1])
    else:
        Browser().load()
    tkinter.mainloop()
