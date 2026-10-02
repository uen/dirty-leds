"""Where each LED is in the room, for effects that sweep across strips

Strips with a "path" in the config (a list of [x, y, z] points in metres, as
in rooms/*.json) get their LEDs spaced evenly along it by length, the same way
the web interface's 3D view places them. room_positions() then gives every
LED a 0-1 position along the room's longest horizontal side, the same scale
for every strip, so something travelling from 0 to 1 crosses the whole room.
"""
import numpy as np

import config


def led_points(path, count):
    """`count` points evenly spaced along a polyline, at the middle of each LED's share"""
    vertices = np.asarray(path, dtype=float)
    lengths = np.linalg.norm(np.diff(vertices, axis=0), axis=1)
    total = lengths.sum()
    if count <= 0 or total <= 0:
        return np.repeat(vertices[:1], max(count, 0), axis=0)
    distance = (np.arange(count) + 0.5) / count * total
    ends = np.cumsum(lengths)
    segment = np.minimum(np.searchsorted(ends, distance), len(lengths) - 1)
    start = ends[segment] - lengths[segment]
    t = (distance - start) / np.maximum(lengths[segment], 1e-9)
    return vertices[segment] + (vertices[segment + 1] - vertices[segment]) * t[:, np.newaxis]


def _room_axis():
    """Index of the room's longest horizontal side (x or z) and its length"""
    room = config.settings.get("room") or {}
    size = room.get("size")
    if size:
        axis = 0 if size[0] >= size[2] else 2
        return axis, float(size[axis])
    return 0, None


def room_positions(device_name, count):
    """0-1 position of each LED along the room, or None when the strip has no layout"""
    device = config.settings["devices"].get(device_name, {})
    path = device.get("layout")
    if not path or len(path) < 2:
        return None
    points = led_points(path, count)
    axis, length = _room_axis()
    if length is None:
        # No room size: use the span of all laid-out strips instead
        spans = [np.asarray(d["layout"], dtype=float)[:, axis] for d in config.settings["devices"].values()
                 if d.get("layout")]
        low = min(s.min() for s in spans)
        length = max(max(s.max() for s in spans) - low, 1e-9)
        return np.clip((points[:, axis] - low) / length, 0, 1)
    return np.clip(points[:, axis] / length, 0, 1)
