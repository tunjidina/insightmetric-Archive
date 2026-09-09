"""
A deliberately coarse world map, defined in code.

The Signal Map logo needs a recognisable world at a very small size and nothing more.
Rather than take a dependency on geopandas, cartopy or a shapefile, the continents are
stored here as coarse lon/lat outlines and sampled onto a dot grid — which is also the
look the brand asks for.

This is a design asset, not a data source. It is wrong at every coastline and should
never be used for anything that claims to be geography.
"""
from __future__ import annotations

# Coarse outlines, (longitude, latitude), degrees. Ordered, closed implicitly.
OUTLINES: dict[str, list[tuple[float, float]]] = {
    "eurasia": [
        (-10, 36), (-9, 43), (-2, 48), (2, 51), (5, 53), (8, 55), (11, 58), (18, 60),
        (22, 65), (21, 70), (30, 71), (40, 68), (55, 70), (70, 73), (80, 75), (100, 77),
        (113, 74), (130, 73), (145, 72), (160, 70), (175, 68), (180, 66), (180, 62),
        (170, 60), (163, 58), (160, 53), (155, 50), (142, 46), (135, 44), (130, 40),
        (126, 35), (122, 31), (117, 24), (110, 20), (107, 10), (104, 1), (98, 8),
        (95, 16), (90, 21), (87, 21), (80, 13), (77, 8), (73, 18), (69, 23), (66, 25),
        (60, 25), (56, 26), (58, 22), (53, 17), (45, 13), (43, 17), (39, 21), (36, 28),
        (34, 31), (35, 36), (30, 36), (26, 40), (22, 40), (19, 42), (14, 42), (12, 45),
        (6, 44), (3, 42), (-1, 38), (-6, 36),
    ],
    "africa": [
        (-17, 15), (-16, 20), (-12, 28), (-6, 36), (10, 37), (20, 33), (32, 31),
        (35, 24), (37, 15), (43, 12), (51, 12), (48, 5), (41, -2), (40, -10),
        (35, -20), (33, -27), (28, -33), (20, -35), (15, -28), (12, -18), (9, -1),
        (9, 4), (3, 6), (-8, 4), (-13, 8),
    ],
    "north_america": [
        (-168, 66), (-160, 71), (-140, 70), (-125, 70), (-110, 68), (-95, 68),
        (-85, 70), (-80, 73), (-70, 70), (-65, 60), (-60, 55), (-55, 52), (-64, 45),
        (-70, 42), (-75, 36), (-80, 30), (-80, 25), (-85, 30), (-94, 29), (-97, 26),
        (-95, 18), (-90, 15), (-84, 10), (-79, 9), (-83, 15), (-88, 20), (-97, 20),
        (-105, 20), (-110, 24), (-117, 32), (-124, 40), (-124, 48), (-133, 55),
        (-145, 60), (-152, 58), (-165, 60),
    ],
    "south_america": [
        (-79, 9), (-75, 10), (-72, 12), (-62, 10), (-52, 5), (-44, -2), (-35, -6),
        (-38, -13), (-40, -20), (-48, -25), (-53, -33), (-58, -38), (-62, -40),
        (-65, -45), (-68, -52), (-71, -54), (-73, -45), (-73, -37), (-71, -30),
        (-70, -20), (-76, -14), (-81, -5), (-80, 0), (-78, 5),
    ],
    "australia": [
        (113, -22), (114, -26), (115, -34), (120, -34), (129, -32), (135, -35),
        (140, -38), (147, -38), (150, -35), (153, -28), (153, -25), (146, -19),
        (143, -11), (136, -12), (130, -11), (125, -14), (122, -17),
    ],
    "greenland": [
        (-45, 60), (-42, 65), (-30, 68), (-22, 70), (-20, 76), (-30, 82), (-45, 83),
        (-58, 82), (-65, 78), (-55, 70), (-50, 65),
    ],
    "british_isles": [
        (-10, 52), (-6, 55), (-5, 58), (-2, 58), (0, 53), (1, 51), (-5, 50),
    ],
    "japan": [
        (130, 32), (132, 34), (136, 35), (140, 36), (141, 41), (145, 44), (142, 45),
        (139, 38), (135, 33),
    ],
    "madagascar": [
        (43, -12), (50, -15), (48, -25), (45, -25), (43, -20),
    ],
    "new_zealand": [
        (167, -46), (170, -46), (176, -39), (178, -37), (174, -35), (172, -40),
    ],
}


def _inside(x: float, y: float, poly: list[tuple[float, float]]) -> bool:
    """Ray-casting point-in-polygon. No shapely dependency."""
    hit = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) / (y2 - y1) * (x2 - x1):
            hit = not hit
    return hit


def land_dots(step: float = 3.0,
              lon_range: tuple[float, float] = (-170, 180),
              lat_range: tuple[float, float] = (-56, 78)) -> list[tuple[float, float]]:
    """Sample the outlines onto a lon/lat grid, returning the land points.

    Under an equirectangular projection a regular lon/lat grid crowds towards the poles,
    which reads as a rendering fault rather than a design. Longitude spacing is therefore
    scaled by 1/cos(latitude) so the dots sit at an even distance on the drawn map, and
    alternate rows are offset by half a step for hexagonal packing.
    """
    from math import cos, radians

    polys = list(OUTLINES.values())
    dots: list[tuple[float, float]] = []
    lat = lat_range[0]
    row = 0
    while lat <= lat_range[1]:
        lon_step = step / max(cos(radians(lat)), 0.25)      # cap the stretch near the poles
        lon = lon_range[0] + (lon_step / 2 if row % 2 else 0)
        while lon <= lon_range[1]:
            if any(_inside(lon, lat, p) for p in polys):
                dots.append((lon, lat))
            lon += lon_step
        lat += step
        row += 1
    return dots
