# MCM-SolarCheck: no recurring model-license fees, legal compliance first

Product goal: commercially usable AI training and inference without ongoing model license charges. This is a procurement and architecture target, **not** a guarantee that all software, datasets or weights are legally cleared or that compute/storage are free.

Milestone 22 removes `ultralytics` from default `requirements.txt`. No Ultralytics import, installation, download or training is introduced by this block. Review all remaining source and deployment paths before claiming total dependency elimination. Existing YOLO-format dataset validators remain usable because a label file format is not itself an Ultralytics runtime dependency.

Official RT-DETR implementation https://github.com/lyuwenyu/RT-DETR is published under Apache-2.0. It is a **candidate**, not an integrated backend. Verify actual version, all transitive libraries, training scripts, checkpoint provenance, weight licensing, attribution/NOTICE obligations, dataset rights and distribution before commercial approval.

The public Solar Hotspot candidate https://universe.roboflow.com/thermal-images-of-solar-panels/solar-hotspot-gu8ap remains UNREVIEWED. Provider-reported MIT license and image count are not proof of ownership or transferable commercial rights. No downloads or training in this block.

Customer inspection imagery may be used for model improvement only after separately recorded, freely given opt-in consent, appropriate privacy notices, and expert validation. Refusal must not affect paid service. Withdrawals and retention must be enforced in a future implementation. No customer data moved.

Next: scan the repository for any remaining Ultralytics imports; implement explicit detector adapter and verified dependency inventory; check original thermal dataset license evidence; implement consent/revocation and evaluation of negative images. Legal counsel must review final deployment.
