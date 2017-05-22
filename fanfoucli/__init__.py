import sys

__version__ = '0.1.12'

__all__ = [
    'cstring', 'cprint', 'clear_screen', 'open_in_browser', 'get_input']

ATTRIBUTES = {
    'bold': 1,
    'dark': 2,
    'underline': 4,
    'blink': 5,
    'reverse': 7,
    'concealed': 8
}

HIGHLIGHTS = {
    'on_grey': 40,
    'on_red': 41,
    'on_green': 42,
    'on_yellow': 43,
    'on_blue': 44,
    'on_magenta': 45,
    'on_cyan': 46,
    'on_white': 47
}

COLORS = {
    'grey': 30,
    'red': 31,
    'green': 32,
    'yellow': 33,
    'blue': 34,
    'magenta': 35,
    'cyan': 36,
    'white': 37,
}
RESET = '\033[0m'


def clear_screen():
    print('\n' * 100)


def get_input(prompt=None):
    try:
        return input(prompt).strip()
    except EOFError:
        sys.exit(0)


def open_in_browser(url):
    import webbrowser
    webbrowser.open_new_tab(url)


def cstring(text, color=None, on_color=None, attrs=None, **kwargs):
    fmt_str = '\033[%dm%s'
    if color is not None:
        text = fmt_str % (COLORS[color], text)

    if on_color is not None:
        text = fmt_str % (HIGHLIGHTS[on_color], text)

    if attrs is not None:
        for attr in attrs:
            text = fmt_str % (ATTRIBUTES[attr], text)

    text += RESET
    return text


def cprint(text, color=None, on_color=None, attrs=None, **kwargs):
    text = cstring(text, color, on_color, attrs)
    print(text, **kwargs)
