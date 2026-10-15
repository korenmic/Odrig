"""Writes the small GIF that the walk-through imports: ten pictures of 40 x 30, each one
flat colour, shown for a tenth of a second each, in red, green, blue, yellow, magenta, cyan,
white, grey, orange and sky blue. The file is stored here as it was once drawn, so that
nothing outside Python's own library is needed.

    python make_gif.py OUT.gif
"""

import base64
import sys

GIF = base64.b64decode(
    "R0lGODlhKAAeAIEAAP8AAAAAAAAAAAAAACH/C05FVFNDQVBFMi4wAwEAAAAh+QQACgAAACwAAAAAKAAeAAAI"
    "OgABCBxIsKDBgwgTKlzIsKHDhxAjSpxIsaLFixgzatzIsaPHjyBDihxJsqTJkyhTqlzJsqXLlzAxBgQAIfkE"
    "AQoAAQAsAAAAACgAHgCBAP8AAAAAAAAAAAAACDoAAQgcSLCgwYMIEypcyLChw4cQI0qcSLGixYsYM2rcyLGj"
    "x48gQ4ocSbKkyZMoU6pcybKly5cwMQYEACH5BAEKAAEALAAAAAAoAB4AgQAA/wAAAAAAAAAAAAg6AAEIHEiw"
    "oMGDCBMqXMiwocOHECNKnEixosWLGDNq3Mixo8ePIEOKHEmypMmTKFOqXMmypcuXMDEGBAAh+QQBCgABACwA"
    "AAAAKAAeAIH//wAAAAAAAAAAAAAIOgABCBxIsKDBgwgTKlzIsKHDhxAjSpxIsaLFixgzatzIsaPHjyBDihxJ"
    "sqTJkyhTqlzJsqXLlzAxBgQAIfkEAQoAAQAsAAAAACgAHgCB/wD/AAAAAAAAAAAACDoAAQgcSLCgwYMIEypc"
    "yLChw4cQI0qcSLGixYsYM2rcyLGjx48gQ4ocSbKkyZMoU6pcybKly5cwMQYEACH5BAEKAAEALAAAAAAoAB4A"
    "gQD//wAAAAAAAAAAAAg6AAEIHEiwoMGDCBMqXMiwocOHECNKnEixosWLGDNq3Mixo8ePIEOKHEmypMmTKFOq"
    "XMmypcuXMDEGBAAh+QQBCgABACwAAAAAKAAeAIH///8AAAAAAAAAAAAIOgABCBxIsKDBgwgTKlzIsKHDhxAj"
    "SpxIsaLFixgzatzIsaPHjyBDihxJsqTJkyhTqlzJsqXLlzAxBgQAIfkEAQoAAQAsAAAAACgAHgCBgICAAAAA"
    "AAAAAAAACDoAAQgcSLCgwYMIEypcyLChw4cQI0qcSLGixYsYM2rcyLGjx48gQ4ocSbKkyZMoU6pcybKly5cw"
    "MQYEACH5BAEKAAEALAAAAAAoAB4Agf+AAAAAAAAAAAAAAAg6AAEIHEiwoMGDCBMqXMiwocOHECNKnEixosWL"
    "GDNq3Mixo8ePIEOKHEmypMmTKFOqXMmypcuXMDEGBAAh+QQBCgABACwAAAAAKAAeAIEAgP8AAAAAAAAAAAAI"
    "OgABCBxIsKDBgwgTKlzIsKHDhxAjSpxIsaLFixgzatzIsaPHjyBDihxJsqTJkyhTqlzJsqXLlzAxBgQAOw=="
)


def write(path):
    with open(path, "wb") as file:
        file.write(GIF)


if __name__ == "__main__":
    write(sys.argv[1])
