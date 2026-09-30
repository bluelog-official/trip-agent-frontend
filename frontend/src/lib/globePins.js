export function createCityPin(point, handlers) {
  const button = document.createElement("button");
  button.type = "button";
  const period = point.period || "all";
  const scale = Number(point.pinScale) || 1;
  const size = Math.max(16, Math.round(28 * scale));
  button.className = [
    "globe-pin",
    point.is_top ? "is-top" : "",
    point.active ? "is-focus" : "",
    `period-${period}`,
  ]
    .filter(Boolean)
    .join(" ");
  button.dataset.slug = point.slug || "";
  button.dataset.period = period;
  button.style.width = `${size}px`;
  button.style.height = `${size}px`;
  button.style.fontSize = `${Math.max(9, Math.round(size * 0.4))}px`;
  button.setAttribute("aria-label", point.label || point.city || point.slug || "city");
  const count = document.createElement("span");
  count.className = "globe-pin-count";
  count.textContent = String(point.published_count ?? "");
  button.append(count);
  button.addEventListener("pointerenter", (event) => handlers.current?.hover?.(point, event));
  button.addEventListener("pointerleave", () => handlers.current?.hover?.(null));
  button.addEventListener("focus", (event) => handlers.current?.hover?.(point, event));
  button.addEventListener("blur", () => handlers.current?.hover?.(null));
  button.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    handlers.current?.open?.(point);
  });
  return button;
}
