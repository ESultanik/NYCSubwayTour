from typing import Iterable

import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap
from matplotlib.animation import FuncAnimation


def animate(route: Iterable[tuple[float, float]], path: str):
    fig, ax = plt.subplots(figsize=(8, 8))

    lats, lons = zip(*route)

    min_lat = min(lats)
    max_lat = max(lats)
    min_lon = min(lons)
    max_lon = max(lons)

    lat_span = max_lat - min_lat
    lon_span = max_lon - min_lon

    if lat_span > lon_span:
        diff = lat_span - lon_span
        min_lon -= diff / 2
        max_lon += diff / 2
    elif lat_span < lon_span:
        diff = lon_span - lat_span
        min_lat -= diff / 2
        max_lat += diff / 2

    border = max(lat_span, lon_span) * 0.0618

    min_lat -= border
    max_lat += border
    min_lon -= border
    max_lon += border

    m = Basemap(projection='mill', llcrnrlat=min_lat, urcrnrlat=max_lat,
                llcrnrlon=min_lon, urcrnrlon=max_lon, resolution='f')

    m.drawmapboundary(fill_color='aqua')
    m.fillcontinents(color='lightgray', lake_color='aqua')
    m.drawcoastlines()
    m.drawrivers()

    scale_lat = max_lat - border
    scale_lon = min_lon + border

    m.drawmapscale(scale_lon, scale_lat, -73.7, 40.8, 10)

    x, y = m(lons, lats)

    # Plot the entire route as a background line
    m.plot(x, y, marker=None, color='gray')

    line, = m.plot([], [], 'go', markersize=3)

    def init():
        line.set_data([], [])
        return line,

    def anim(i):
        line.set_data(x[:i], y[:i])
        return line,

    # Animate the route
    ani = FuncAnimation(fig, anim, frames=len(route), init_func=init,
                        interval=50, blit=True)

    # Save the animation as a GIF or MP4
    ani.save(str(path), writer='pillow')

    return ani


if __name__ == '__main__':
    # Animate the route
    # Sample GPS coordinates (latitude, longitude)
    route = [
        (40.7128, -74.0060),  # NYC (start)
        (40.748817, -73.985428),  # Empire State Building
        (40.758896, -73.985130),  # Times Square
        (40.730610, -73.935242),  # East Village
        (40.752726, -73.977229),  # Grand Central
    ]

    # Save the animation as a GIF or MP4
    animate(route, 'nyc_route.gif')
