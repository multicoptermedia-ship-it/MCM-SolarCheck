(() => {
  "use strict";

  const entry = document.querySelector("[data-solarcheck-online-entry]");
  if (!entry) return;

  const configuredUrl = document.documentElement.dataset.solarcheckOnlineUrl || "";
  let target;
  try {
    target = new URL(configuredUrl);
  } catch {
    target = null;
  }

  if (target && (target.protocol === "https:" || target.protocol === "http:")) {
    entry.href = target.href;
    entry.setAttribute("aria-label", "SolarCheck Online öffnen");
    return;
  }

  entry.setAttribute("aria-disabled", "true");
  entry.title = "SolarCheck Online wird nach Bereitstellung freigeschaltet.";
  entry.addEventListener("click", (event) => event.preventDefault());
})();
