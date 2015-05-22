COLOR_BLUE = '\033[94m'
COLOR_GREEN = '\033[92m'
COLOR_WARNING = '\033[93m'
COLOR_FAIL = '\033[91m'
END_COLOR = '\033[0m'

def colored_text(txt, color=COLOR_BLUE):
    return "%s%s%s" % (color, txt, END_COLOR)

def green_text(txt):
    return colored_text(txt, color=COLOR_GREEN)

def blue_text(txt):
    return colored_text(txt, color=COLOR_BLUE)

def red_text(txt):
	return colored_text(txt, color=COLOR_FAIL)

def warning_text(txt):
	return colored_text(txt, color=COLOR_WARNING)
