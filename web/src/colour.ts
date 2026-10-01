export type RGB = [number, number, number];

/** Average colour of a strip frame (packed RGB bytes) */
export function averageColour(bytes: Uint8Array): RGB {
  const count = Math.floor(bytes.length / 3);
  if (!count) return [0, 0, 0];
  let r = 0, g = 0, b = 0;
  for (let i = 0; i < count * 3; i += 3) {
    r += bytes[i];
    g += bytes[i + 1];
    b += bytes[i + 2];
  }
  return [r / count, g / count, b / count];
}

export function cssRgb([r, g, b]: RGB): string {
  return `rgb(${Math.round(r)} ${Math.round(g)} ${Math.round(b)})`;
}
