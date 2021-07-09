from typing import Tuple


DELIMITERS = {'°', '′', '″', '|'}


def convert_to_decimal_angle(grads: float, minutes: float, seconds: float):
    return round(grads + minutes / 60 + seconds / 3600, 6)


def line_parse(line: str) -> Tuple[float, float]:
    result = []
    num_src = ''
    for symbol in line:
        if symbol.isdigit() or symbol == '.':
            num_src += symbol
        elif symbol in DELIMITERS:
            try:
                result.append(float(num_src))
            except ValueError:
                pass
            num_src = ''
    latitude = convert_to_decimal_angle(*result[:3])
    longitude = convert_to_decimal_angle(*result[3:])
    return longitude, latitude
