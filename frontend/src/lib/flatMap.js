/** Equirectangular flat world. Pins use latitude and longitude, not a WebGL globe. */

export const MAP_WIDTH = 960;
export const MAP_HEIGHT = 480;

const CONTINENTS = {
  northAmerica: [
    [-168, 71], [-140, 70], [-105, 73], [-85, 73], [-68, 68], [-56, 52],
    [-66, 44], [-74, 35], [-81, 25], [-97, 26], [-106, 22], [-115, 32],
    [-124, 40], [-125, 49], [-140, 60], [-166, 54], [-168, 66],
  ],
  greenland: [
    [-68, 76], [-58, 83], [-22, 81], [-20, 70], [-44, 60], [-68, 70],
  ],
  southAmerica: [
    [-78, 10], [-68, 12], [-60, 8], [-50, 2], [-35, -8], [-39, -22],
    [-48, -28], [-62, -40], [-68, -55], [-76, -52], [-77, -18], [-81, -2],
  ],
  eurasia: [
    [-10, 36], [-8, 44], [-5, 58], [8, 62], [28, 71], [70, 72], [120, 72],
    [150, 68], [146, 50], [141, 35], [128, 33], [121, 31], [109, 20],
    [104, 1], [95, 16], [80, 22], [68, 25], [52, 30], [44, 13],
    [34, 28], [26, 36], [10, 37], [-6, 36],
  ],
  africa: [
    [-17, 21], [-16, 12], [-8, 5], [8, 4], [12, -6], [18, -34],
    [26, -34], [33, -28], [40, -16], [51, 12], [43, 12], [32, 31],
    [10, 37], [-6, 35], [-17, 28],
  ],
  australia: [
    [113, -22], [128, -14], [136, -12], [142, -11], [146, -15],
    [153, -26], [150, -38], [137, -35], [124, -33], [114, -34], [113, -28],
  ],
};

export function projectLatLng(lat, lng, width = MAP_WIDTH, height = MAP_HEIGHT) {
  const safeLat = Math.max(-90, Math.min(90, Number(lat) || 0));
  const safeLng = Math.max(-180, Math.min(180, Number(lng) || 0));
  return {
    x: ((safeLng + 180) / 360) * width,
    y: ((90 - safeLat) / 180) * height,
  };
}

function ringToPath(ring) {
  return `${ring
    .map((point, index) => {
      const projected = projectLatLng(point[1], point[0]);
      const command = index === 0 ? "M" : "L";
      return `${command}${projected.x.toFixed(1)} ${projected.y.toFixed(1)}`;
    })
    .join(" ")} Z`;
}

export function continentPaths() {
  return Object.entries(CONTINENTS).map(([id, ring]) => ({
    id,
    d: ringToPath(ring),
  }));
}

export function pinPlacement(lat, lng) {
  const point = projectLatLng(lat, lng);
  const left = (point.x / MAP_WIDTH) * 100;
  const top = (point.y / MAP_HEIGHT) * 100;
  return {
    ...point,
    left,
    top,
    openLeft: point.x > MAP_WIDTH * 0.62,
    openUp: point.y < MAP_HEIGHT * 0.22,
  };
}
