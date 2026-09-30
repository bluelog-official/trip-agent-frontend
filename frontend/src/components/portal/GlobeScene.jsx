import { useCallback, useEffect, useRef, useState } from "react";
import Globe from "react-globe.gl";
import { createCityPin } from "../../lib/globePins";

const EARTH_IMAGE = "https://unpkg.com/three-globe@2.45.3/example/img/earth-blue-marble.jpg";
const EARTH_BUMP = "https://unpkg.com/three-globe@2.45.3/example/img/earth-topology.png";

const RING_SPEED = {
  "1w": 2,
  "2w": 1.45,
  "1m": 1,
  "1y": 0.55,
  all: 0.35,
};

const RING_RADIUS = {
  "1w": 4.2,
  "2w": 3.6,
  "1m": 3,
  "1y": 2.3,
  all: 1.8,
};

function narrowScreen() {
  return typeof window !== "undefined" && window.matchMedia?.("(max-width: 720px)")?.matches;
}

export default function GlobeScene({ cities, onOpenCity, onHover, onReady, reducedMotion, lowPower, period }) {
  const globeRef = useRef(null);
  const wrapRef = useRef(null);
  const [size, setSize] = useState({ width: 0, height: 420 });
  const posed = useRef(false);
  const hoverRef = useRef(false);
  const reducedRef = useRef(reducedMotion);
  const lowRef = useRef(lowPower);
  const handlers = useRef({ open: onOpenCity, hover: () => {} });
  reducedRef.current = reducedMotion;
  lowRef.current = lowPower;
  handlers.current.open = onOpenCity;
  handlers.current.hover = (point, event) => {
    hoverRef.current = Boolean(point);
    const controls = globeRef.current?.controls?.();
    if (controls) {
      controls.autoRotate = !point && !reducedRef.current && document.visibilityState !== "hidden";
    }
    onHover?.(point, event);
  };

  const htmlElement = useCallback((point) => createCityPin(point, handlers), []);

  const applyControls = useCallback((resetView) => {
    const globe = globeRef.current;
    if (!globe) return;
    const controls = globe.controls?.();
    if (controls) {
      controls.autoRotate = !reducedRef.current && !hoverRef.current && document.visibilityState !== "hidden";
      controls.autoRotateSpeed = lowRef.current ? 0.28 : 0.4;
      controls.enablePan = false;
      controls.enableZoom = false;
      controls.enableRotate = !narrowScreen();
    }
    const renderer = globe.renderer?.();
    if (renderer) {
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, lowRef.current ? 1 : 1.5));
    }
    if (resetView && !posed.current) {
      globe.pointOfView({ lat: 22, lng: 18, altitude: lowRef.current ? 2.45 : 2.15 }, 0);
      posed.current = true;
    }
  }, []);

  const api = useRef({ flyTo() {} });
  api.current.flyTo = (city) => {
    const globe = globeRef.current;
    if (!globe || city?.lat == null || city?.lng == null) return;
    const controls = globe.controls?.();
    if (controls) controls.autoRotate = false;
    const motion = reducedRef.current;
    globe.pointOfView(
      {
        lat: Number(city.lat),
        lng: Number(city.lng),
        altitude: lowRef.current ? 1.45 : 1.15,
      },
      motion ? 0 : 1400,
    );
    window.setTimeout(() => {
      const next = globeRef.current?.controls?.();
      if (next && !reducedRef.current && !hoverRef.current && document.visibilityState !== "hidden") {
        next.autoRotate = true;
      }
    }, motion ? 0 : 1550);
  };

  useEffect(() => {
    onReady?.(api.current);
  }, [onReady]);

  useEffect(() => {
    const node = wrapRef.current;
    if (!node) return undefined;
    const measure = () => {
      const width = Math.max(280, node.clientWidth || 0);
      const height = Math.max(300, Math.min(520, Math.round(width * (narrowScreen() ? 0.78 : 0.72))));
      setSize((current) => (current.width === width && current.height === height ? current : { width, height }));
    };
    measure();
    if (typeof ResizeObserver === "undefined") return undefined;
    const observer = new ResizeObserver(measure);
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    applyControls(false);
  }, [applyControls, reducedMotion, lowPower, size.width]);

  useEffect(() => {
    const onVisibility = () => applyControls(false);
    document.addEventListener("visibilitychange", onVisibility);
    return () => document.removeEventListener("visibilitychange", onVisibility);
  }, [applyControls]);

  const rings = reducedMotion ? [] : cities.filter((city) => city.is_top);
  const { width, height } = size;

  return (
    <div ref={wrapRef} className="globe-canvas" data-period={period}>
      {width > 0 ? (
        <Globe
          ref={globeRef}
          width={width}
          height={height}
          backgroundColor="rgba(0,0,0,0)"
          globeImageUrl={EARTH_IMAGE}
          bumpImageUrl={EARTH_BUMP}
          showAtmosphere
          atmosphereColor="#9ae6d8"
          atmosphereAltitude={0.16}
          animateIn={!reducedMotion && !lowPower}
          rendererConfig={{
            antialias: !lowPower,
            alpha: true,
            powerPreference: lowPower ? "low-power" : "default",
          }}
          onGlobeReady={() => applyControls(true)}
          pointsData={cities}
          pointLat="lat"
          pointLng="lng"
          pointColor={(city) => (city.is_top ? "#f6c453" : "#5eead4")}
          pointAltitude={0.012}
          pointRadius={(city) => (city.is_top ? 0.46 : 0.28) * (Number(city.pinScale) || 1)}
          pointsMerge={false}
          ringsData={rings}
          ringLat="lat"
          ringLng="lng"
          ringColor={() => (amount) => `rgba(251, 113, 133, ${Math.max(0, 0.8 - amount)})`}
          ringMaxRadius={RING_RADIUS[period] || RING_RADIUS.all}
          ringPropagationSpeed={RING_SPEED[period] || RING_SPEED.all}
          ringRepeatPeriod={period === "1w" ? 900 : period === "all" ? 2200 : 1400}
          htmlElementsData={cities}
          htmlLat="lat"
          htmlLng="lng"
          htmlAltitude={0.01}
          htmlElement={htmlElement}
        />
      ) : null}
    </div>
  );
}
