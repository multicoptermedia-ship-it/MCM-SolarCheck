# SolarCheck customer website integration

This directory captures the customer-facing SolarCheck landing-page entry boundary from the website ZIP supplied on 2026-10-03.

## Product boundary

- SolarCheck Online is the public customer product.
- SolarCheck Offline remains an internal MCM work/test product and MUST NOT receive a public link here.
- The Online tile stays fail-closed until a deployment supplies a real HTTP(S) application URL.
- No production/IONOS URL is invented or committed in source.

A deployment can set `data-solarcheck-online-url` on the root `<html>` element to the deployed SolarCheck Online entry URL. `online-entry-config.js` validates the URL and activates the existing SolarCheck tile only for HTTP(S).

## Source ZIP note

The supplied ZIP references `assets/images/MCM-Flightplan1.png`, `MCM-Solarcheck-app1.png`, and `MCM-Solarkataster1.png`, but the ZIP itself did not contain an `assets/` directory. Those assets must be supplied/verified before deployment; they are intentionally not fabricated here.

The remaining original static pages/styles/scripts are retained in the uploaded source ZIP and should be imported once their complete asset bundle is available. This directory currently establishes only the versioned SolarCheck customer-entry contract needed by the application repository.
