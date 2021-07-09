from typing import List
import requests
from bs4 import BeautifulSoup


COORDINATE_PANEL_CLASS = 'panel-with-coords'


def get_coords_lines(url: str) -> List[str]:
    request = requests.get(url)
    if request.status_code != 200:
        return []

    html_data = BeautifulSoup(request.text, 'html.parser')

    main_div = html_data.find(name='div',
                              attrs={'class': COORDINATE_PANEL_CLASS})
    if not main_div:
        return []

    lists_coords = main_div.find_all(name='ul')
    if not lists_coords:
        return []

    result = []
    for current_list in lists_coords:
        list_items = current_list.find_all(name='li')
        if not list_items:
            continue

        for item in list_items:
            spans = item.findAll(name='span')
            result.append(spans[1].text)
    return result
