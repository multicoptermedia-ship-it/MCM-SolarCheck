# SolarCheck online product architecture

Status: architecture checkpoint before concrete GUI implementation.

This document records product decisions that affect the online shell, access
control, ordering flow, and application-service boundaries. It deliberately
does not select a compute provider or define final prices.

## 1. Shared application, product profiles

SolarCheck Online uses one application/codebase. Product differences are
represented by server-authoritative product/entitlement profiles rather than
forked GUI implementations.

Initial profiles:

### Promotional trial

- maximum accepted plant size: 20 kWp;
- intended for promotional use and new users;
- analysis/review workflow remains available within the permitted scope;
- report download is unavailable;
- export is unavailable.

The 20 kWp limit and download/export restrictions must be enforced by the
backend/application boundary. Hiding or disabling GUI controls alone is not an
access-control mechanism.

Report/export capabilities may remain visible as unavailable features so the
user can understand the full-product workflow, provided the UI clearly explains
the restriction.

### Full online product

The full product uses the normal SolarCheck workflow and can provide report and
export operations when all existing workflow/review/release gates permit them.

Commercial entitlement never bypasses technical, review, provenance, or report
release gates.

## 2. Help and user guide

The application Help menu includes **User guide** as a first-class command.

The login/start page contains a short note telling new users that the user guide
is available through **Help -> User guide**.

The guide should open inside the SolarCheck help experience where practical.
Context-sensitive links may later focus the relevant guide section without
creating a second source of documentation truth.

## 3. Quote before upload/processing

For the full online product, the order/start experience accepts a plant-size
input based on:
- installed plant power (kWp); or
- module count where the commercial tariff supports that basis.

Fixed commercial bands map this input to a displayed evaluation price.

The concrete bands, prices, taxes, payment-provider behavior, and relationship
between module count and kWp remain part of the later pricing workstream.

The price shown to the user must come from an authoritative pricing service or
configuration, not duplicated constants in the GUI.

## 4. Uploaded-scope verification and price escalation

The initially selected tariff band is provisional until SolarCheck can compare
it with the uploaded/project scope using authoritative information available to
the application.

If the verified scope exceeds the purchased band, processing that would incur
the higher charge is paused before the additional commercial commitment.

The user is shown a confirmation dialog containing at least:
- originally selected scope/band;
- verified scope used for the commercial comparison;
- next applicable tariff band;
- additional/final price information available from the pricing service;
- explicit accept and decline actions.

No higher price is silently applied.

### Accept

Acceptance is persisted as an auditable commercial decision before the
application proceeds. The accepted higher tariff becomes the order tariff.

Any online payment/charge is performed through the later payment boundary. A
successful UI click is not equivalent to a successful charge.

### Decline

Declining terminates/cancels the affected evaluation order in a controlled
state. Further chargeable processing does not continue.

The user receives a clear cancellation/termination confirmation. The
application itself is not forcibly closed.

## 5. Pricing/application boundary

GUI code must not calculate commercial totals independently.

A future pricing service should expose concepts such as:
- product profile;
- submitted scope;
- applicable tariff band;
- quoted price;
- verified scope;
- escalation requirement;
- accepted commercial revision.

The exact data model is deferred until the pricing workstream, but the GUI and
workflow implementation must leave this boundary available.

## 6. Payment boundary

Payment-provider selection is deferred.

The application architecture must distinguish:
1. user acceptance of a quote/revised quote;
2. payment authorization/collection;
3. payment success/failure;
4. permission to continue chargeable processing.

This prevents a GUI confirmation from being treated as proof of payment.

## 7. Compute and hosting boundary

Compute-provider selection remains open. IONOS pay-per-use and other options
will be evaluated later using measured SolarCheck workloads and cost per
evaluation.

The online application therefore must submit processing through a
provider-neutral job/worker boundary. Web UI, commercial ordering, project
storage, and image-analysis compute must not depend on a hard-coded cloud
vendor.

A later infrastructure decision can then choose one provider without requiring
a product-workflow redesign.

## 8. Data retention and project archive

Online evaluation data is temporary by product policy. The exact operational
retention/deletion implementation and legal/privacy wording require a separate
deployment/privacy review.

The target product behavior is:
- no promise of permanent cloud project storage;
- a bounded temporary retention period;
- downloadable project archive/ZIP for authorized offline retention;
- deletion after the applicable retention policy.

The archive format should be designed so that a future offline SolarCheck
edition can consume the same authoritative project/evidence package where
feasible.

## 9. Implementation guardrails

Before and during GUI implementation:
- product entitlements are backend-derived;
- pricing is service-derived;
- payment state is not inferred from button clicks;
- trial restrictions cannot be bypassed by client changes;
- pricing/entitlements cannot bypass review/report gates;
- compute remains provider-neutral;
- online and offline core inspection behavior stays aligned;
- final pricing and compute-provider selection remain deferred.
