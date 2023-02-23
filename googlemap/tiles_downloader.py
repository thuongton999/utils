import os
import hashlib
import math
import cgi
import argparse
from urllib.request import urlopen, urlretrieve

TILE_SIZE = 256
ZOOM = 3
SCALE = 1 << ZOOM

def generate_html_viewer(
        folder: str,
        top_left_src: str,
        top_src: str,
        top_right_src: str,
        left_src: str,
        current_src: str,
        right_src: str,
        bottom_left_src: str,
        bottom_src: str,
        bottom_right_src: str):
    print("Generating HTML Viewer")
    style = '<style>main{display:grid;grid-template-areas:"tl t tr" "l c r" "bl b br";width:fit-content;height:fit-content;}#top_left{grid-area:tl}#top{grid-area:t}#top_right{grid-area:tr}#left{grid-area:l}#current{grid-area:c}#right{grid-area:r}#bottom_left{grid-area:bl}#bottom{grid-area:b}#bottom_right{grid-area:br}</style>'
    __meta = f"""
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Viewer</title>
    {style}
</head>

<body>
    <main>
        <img src="{top_left_src}" alt="." id="top_left">
        <img src="{top_src}" alt="." id="top">
        <img src="{top_right_src}" alt="." id="top_right">
        <img src="{left_src}" alt="." id="left">
        <img src="{current_src}" alt="." id="current">
        <img src="{right_src}" alt="." id="right">
        <img src="{bottom_left_src}" alt="." id="bottom_left">
        <img src="{bottom_src}" alt="." id="bottom">
        <img src="{bottom_right_src}" alt="." id="bottom_right">
    </main>
</body>
</html>
"""
    with open(os.path.join(folder, "map_viewer.html"), 'w', encoding='utf-8') as viewer:
        viewer.write(__meta)


class Point:
    x: float
    y: float

    def __init__(self) -> None:
        self.x = 0
        self.y = 0

    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def __str__(self) -> str:
        return f"({self.x}, {self.y})"

    def __add__(self, intNum: float):
        return Point(self.x + intNum, self.y + intNum)


class MercatorProjection:
    def deg_to_rad(deg: float):
        return deg * (math.pi / 180)

    def rad_to_deg(rad: float):
        return rad / (math.pi / 180)

    def from_lat_lng_to_point(pt: Point) -> Point:
        siny = math.sin(MercatorProjection.deg_to_rad(pt.x))
        siny = min(max(siny, -0.9999), 0.9999)

        lat = TILE_SIZE * (0.5 + pt.y / 360)
        lng = TILE_SIZE * (0.5 - math.log((1 + siny) /
                           (1 - siny)) / (4 * math.pi))
        return Point(lat, lng)

    def from_point_to_lat_lng(lat_lng: Point) -> Point:
        px_origin = Point(TILE_SIZE / 2, TILE_SIZE / 2)
        px_per_deg = TILE_SIZE / 360
        px_per_rad = TILE_SIZE / (2 * math.pi)

        x = lat_lng.x / SCALE
        y = lat_lng.y / SCALE

        lng = (x - px_origin.x) / px_per_deg
        lat_rad = (y - px_origin.y) / -px_per_rad
        lat = MercatorProjection.rad_to_deg(
            2 * math.atan(math.exp(lat_rad)) - math.pi / 2)
        return Point(lat, lng)


class Tile(Point):
    def get_center_pixel_coord(self) -> Point:
        top_left_pixel_coord = Point(self.x * TILE_SIZE, self.y * TILE_SIZE)
        offset = math.floor(TILE_SIZE / 2)
        center_pixel_coord = top_left_pixel_coord + offset
        return center_pixel_coord

    def get_center_world_coord(self) -> Point:
        center_pixel_coord = self.get_center_pixel_coord()
        return Point(center_pixel_coord.x >> ZOOM, center_pixel_coord.y >> ZOOM)

    def get_center_lat_lng(self) -> Point:
        return MercatorProjection.from_point_to_lat_lng(self.get_center_pixel_coord())


class Coordinate(Point):
    def get_world_coord(self) -> Point:
        return MercatorProjection.from_lat_lng_to_point(Point(self.x, self.y))

    def get_pixel_coord(self) -> Point:
        world_coord = self.get_world_coord()
        return Point(
            math.floor(world_coord.x * SCALE),
            math.floor(world_coord.y * SCALE)
        )

    def get_tile(self) -> Tile:
        pixel_coord = self.get_pixel_coord()
        return Tile(
            math.floor(pixel_coord.x / TILE_SIZE),
            math.floor(pixel_coord.y / TILE_SIZE)
        )

    def __str__(self) -> str:
        return f"(lat:\t{self.x},\tlng:\t{self.y})"


def download_file_from_url(url: str, folder: str, filename=None):
    remotefile = urlopen(url)
    filetype = remotefile.info()['Content-Type'].split('/')[-1]
    print(f'Downloading {filename}.{filetype}')
    if filename:
        abs_path = os.path.join(folder, f"{filename}.{filetype}")
        urlretrieve(url, abs_path)
        return abs_path
    contentdisposition = remotefile.info()['Content-Disposition']
    if contentdisposition:
        _, params = cgi.parse_header(contentdisposition)
        filename = params["filename"]
    else:
        filename = f"{hashlib.md5(url.encode('utf-8')).hexdigest()}.{filetype}"
    abs_path = os.path.join(folder, filename)
    urlretrieve(url, abs_path)
    return abs_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--lat', type=float, help='Latitude')
    parser.add_argument('--lng', type=float, help='Longtitude')
    parser.add_argument('--zoom', type=int, default=3, help='Zoom')
    parser.add_argument('--size', type=int, default=256, help='Tile size')
    parser.add_argument(
        '--folder', type=str, default=os.path.abspath(os.getcwd()), help="Folder to save image")
    args = parser.parse_args()
    if not os.path.exists(args.folder):
        os.makedirs(args.folder)
    if not args.lat or not args.lng:
        raise Exception("Lat/Lng is required")

    ZOOM = args.zoom
    TILE_SIZE = args.size
    SCALE = 1 << ZOOM
    
    coord = Coordinate(args.lat, args.lng)
    tile = coord.get_tile()

    API_KEY = "YOUR_API_KEY"
    static_map_url = f"https://maps.googleapis.com/maps/api/staticmap?key={API_KEY}&zoom={ZOOM}&format=png&maptype=roadmap&size={TILE_SIZE}x{TILE_SIZE}"

    region = [
        [[-1, -1],   [0, -1],    [1, -1]],
        [[-1, 0],    [0, 0],     [1, 0]],
        [[-1, 1],    [0, 1],     [1, 1]]
    ]

    name = {
        -1: {
            -1: 'top_left',
            0: 'left',
            1: 'bottom_left'
        },
        0: {
            -1: 'top',
            0: 'current',
            1: 'bottom'
        },
        1: {
            -1: 'top_right',
            0: 'right',
            1: 'bottom_right'
        }
    }

    urls = {
        'top_left': '',
        'left': '',
        'bottom_left': '',
        'top': '',
        'current': '',
        'bottom': '',
        'top_right': '',
        'right': '',
        'bottom_right': ''
    }

    for y in region:
        for x in y:
            center_lat_lng = Tile(
                tile.x + x[0], tile.y + x[1]).get_center_lat_lng()
            map_url = static_map_url + \
                f"&center={center_lat_lng.x}%2c{center_lat_lng.y}"
            filename = f"{name[x[0]][x[1]]}"
            urls[filename] = download_file_from_url(
                map_url, folder=args.folder, filename=filename)

    generate_html_viewer(
        args.folder,
        urls['top_left'],
        urls['top'],
        urls['top_right'],
        urls['left'],
        urls['current'],
        urls['right'],
        urls['bottom_left'],
        urls['bottom'],
        urls['bottom_right']
    )
