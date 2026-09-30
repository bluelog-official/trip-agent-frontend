import { describe, expect, it } from "vitest";
import { continentPaths, projectLatLng } from "./flatMap";

describe("flat map projection", () => {
  it("lays cities out from longitude and latitude", () => {
    const paris = projectLatLng(48.8566, 2.3522);
    const tokyo = projectLatLng(35.6762, 139.6503);
    const sydney = projectLatLng(-33.8688, 151.2093);
    const newYork = projectLatLng(40.7128, -74.006);
    expect(tokyo.x).toBeGreaterThan(paris.x);
    expect(paris.x).toBeGreaterThan(newYork.x);
    expect(sydney.y).toBeGreaterThan(paris.y);
    const shapes = continentPaths();
    expect(shapes.length).toBeGreaterThan(4);
    expect(shapes.every((shape) => shape.d.startsWith("M") && shape.d.endsWith("Z"))).toBe(true);
  });
});
