"""Explicit public YOLO research helpers; never an automatic customer trainer.

Original CVUT member identities are observed hashes, not publisher attestations.
The third-party reference is Ultralytics8.1.29 (AGPL-3.0), kept external. No
serialized Ultralytics object is executed: extract primitive tensors first.
"""
from collections import OrderedDict
from hashlib import sha256
from io import BytesIO


PUBLIC_RGB = {
    'n': (6806691, 'e464ffde55d91727b19c8690706d79b70a3deb2398d7d564bb7a0a2656fea6e6', 3274981),
    's': (23896931, '549c6d78ba9e44cfd3936062fa74510468ae57bdb91c5fa9116a5662d999674f', 11811541),
}


class _Passive:
    def __setstate__(self, state):
        if type(state) is not dict:
            raise ValueError('Passive dictionary state required')
        self.__dict__.update(state)


def _unused_forward(*args, **kwargs):
    raise ValueError('Serialized model methods must never execute')


def _guarded_getattr(obj, name):
    if obj is not _Passive or name != 'forward':
        raise ValueError('Unexpected serialized attribute lookup')
    return _unused_forward


def _passive_tensor_state(data, torch):
    """Restricted loading with inert aliases, then explicit tensor dictionaries.

    Never call state_dict(), hooks or forward() on a deserialized object. Shared
    weightless activations are legitimate; ancestor cycles remain forbidden.
    """
    if type(data) is not bytes or not 1 <= len(data) <= 30_000_000:
        raise ValueError('Bounded public checkpoint bytes required')
    names = ('nn.modules.block.Bottleneck', 'nn.modules.block.C2f', 'nn.modules.block.DFL',
        'nn.modules.block.Proto', 'nn.modules.block.SPPF', 'nn.modules.conv.Concat',
        'nn.modules.conv.Conv', 'nn.modules.head.Detect', 'nn.modules.head.Segment',
        'nn.tasks.SegmentationModel', 'utils.IterableSimpleNamespace', 'utils.loss.BboxLoss',
        'utils.loss.v8SegmentationLoss', 'utils.tal.TaskAlignedAssigner')
    allowed = [(_Passive, 'ultralytics.'+name) for name in names]
    allowed += [(_guarded_getattr, 'builtins.getattr'), set, torch.nn.SiLU,
        torch.nn.BatchNorm2d, torch.nn.ModuleList, torch.nn.Sequential, torch.nn.Conv2d,
        torch.nn.ConvTranspose2d, torch.nn.BCEWithLogitsLoss, torch.nn.MaxPool2d, torch.nn.Upsample]
    with torch.serialization.safe_globals(allowed):
        checkpoint = torch.load(BytesIO(data), map_location='cpu', weights_only=True)
    if type(checkpoint) is not dict or type(checkpoint.get('model')) is not _Passive:
        raise ValueError('Known passive public checkpoint required')
    state, ancestors, total = OrderedDict(), set(), 0
    def visit(obj, prefix='', depth=0):
        nonlocal total
        if (depth > 32 or id(obj) in ancestors
                or not isinstance(obj, (_Passive, torch.nn.Module))):
            raise ValueError('Invalid or cyclic passive module graph')
        ancestors.add(id(obj))
        fields = vars(obj)
        for field in ('_parameters', '_buffers'):
            items = fields.get(field, {})
            if type(items) not in (dict, OrderedDict):
                raise ValueError('Primitive tensor dictionaries required')
            for name, value in items.items():
                if not isinstance(name, str) or not name or '.' in name:
                    raise ValueError('Invalid tensor name')
                if value is None or field == '_buffers' and name in fields.get('_non_persistent_buffers_set', set()):
                    continue
                if (type(value) not in (torch.Tensor, torch.nn.Parameter)
                        or value.device.type != 'cpu' or value.numel() > 20_000_000):
                    raise ValueError('Bounded primitive CPU tensors required')
                total += value.numel()
                if (total > 20_000_000 or value.dtype not in (torch.float16, torch.float32, torch.int64)
                        or not torch.isfinite(value).all()):
                    raise ValueError('Public tensor types or values differ')
                state[prefix+name] = value.detach().clone()
        children = fields.get('_modules', {})
        if type(children) not in (dict, OrderedDict):
            raise ValueError('Primitive child dictionaries required')
        for name, child in children.items():
            if not isinstance(name, str) or not name or '.' in name:
                raise ValueError('Invalid passive child name')
            if child is not None:
                visit(child, prefix+name+'.', depth+1)
        ancestors.remove(id(obj))
    visit(checkpoint['model'])
    metadata = dict(version=checkpoint.get('version'), names=vars(checkpoint['model']).get('names'),
        tensor_keys=len(state), tensor_elements=total)
    return state, metadata


def published_rgb_state(data, torch, variant='n'):
    if variant not in PUBLIC_RGB:
        raise ValueError('Declared public RGB variant required')
    size, expected, elements = PUBLIC_RGB[variant]
    if len(data) != size or sha256(data).hexdigest() != expected:
        raise ValueError('Observed public RGB member identity differs')
    state, meta = _passive_tensor_state(data, torch)
    if (meta['version'] != '8.1.29' or meta['names'] != {0: 'module'}
            or meta['tensor_keys'] != 417 or meta['tensor_elements'] != elements):
        raise ValueError('Public RGB module architecture metadata differs')
    return state


def reference_model(torch, state, variant='n'):
    """Build the known reference architecture and load only verified tensors."""
    from pathlib import Path
    import ultralytics
    from ultralytics.nn.tasks import SegmentationModel
    from ultralytics.utils import yaml_load
    if (variant not in PUBLIC_RGB or ultralytics.__version__ != '8.1.29'
            or torch.__version__ != '2.15.0+cpu' or torch.version.cuda is not None):
        raise ValueError('Qualified explicit public YOLO CPU reference required')
    cfg = yaml_load(Path(ultralytics.__file__).parent/'cfg/models/v8/yolov8-seg.yaml')
    cfg.update(scale=variant, nc=1)
    model = SegmentationModel(cfg, ch=3, nc=1, verbose=False).cpu().float().eval()
    expected = model.state_dict()
    if (type(state) not in (dict, OrderedDict) or set(state) != set(expected)
            or any(type(v) is not torch.Tensor or v.device.type != 'cpu'
                   or v.shape != expected[k].shape
                   or v.dtype not in ((torch.int64,) if k.endswith('num_batches_tracked')
                                      else (torch.float16, torch.float32))
                   or not torch.isfinite(v).all() for k, v in state.items())):
        raise ValueError('Public YOLO tensor shapes, types or values differ')
    model.load_state_dict(state, strict=True)
    return model


def configure_public_training(torch, model, first_block):
    """Allow staged unfreezing; retain fixed DFL projection and BatchNorm."""
    if type(first_block) is not int or first_block not in (0, 10, 22):
        raise ValueError('Declared bounded public adaptation stage required')
    for name, parameter in model.named_parameters():
        parameter.requires_grad_(int(name.split('.')[1]) >= first_block and '.dfl.' not in name)
    for layer in model.modules():
        if isinstance(layer, torch.nn.BatchNorm2d):
            for parameter in layer.parameters():
                parameter.requires_grad_(False)
    public_training_mode(torch, model)


def public_training_mode(torch, model):
    model.eval()
    model.model[-1].train()
    for layer in model.modules():
        if isinstance(layer, torch.nn.BatchNorm2d):
            layer.eval()


def known_pixel_loss(torch, model):
    """Standard YOLO losses with explicit conservative known-pixel support.

    Classification/assignment ignore unknown anchor cells. Segmentation takes
    its mean only over known pixels in each object box. CNN context can still
    depend on surrounding pixels; this verifies direct output gradients only.
    """
    from ultralytics.utils.loss import v8SegmentationLoss
    from ultralytics.utils.ops import crop_mask
    F = torch.nn.functional
    class KnownPixelLoss(v8SegmentationLoss):
        def __init__(self, model):
            super().__init__(model)
            original, owner = self.assigner, self
            class KnownBCE(torch.nn.Module):
                def forward(self, scores, targets):
                    return F.binary_cross_entropy_with_logits(scores, targets,
                        reduction='none')*owner.known_anchors.unsqueeze(-1)
            class KnownAssigner:
                def __call__(self, scores, *args):
                    result = list(original(scores*owner.known_anchors.unsqueeze(-1), *args))
                    result[2] = result[2]*owner.known_anchors.unsqueeze(-1)
                    result[3] = result[3] & owner.known_anchors
                    return tuple(result)
            self.bce, self.assigner = KnownBCE(), KnownAssigner()

        def __call__(self, predictions, batch):
            valid = batch.get('valid_pixels')
            features, coefficients, prototype = predictions
            if (not isinstance(valid, torch.Tensor) or valid.dtype != torch.bool
                    or valid.ndim != 3 or valid.shape[0] != 1
                    or valid.shape[-2:] != batch['img'].shape[-2:]):
                raise ValueError('Explicit single-image validity mask required')
            x = valid[:, None].float()
            self.known_proto = F.adaptive_avg_pool2d(x, prototype.shape[-2:]).eq(1)[0, 0]
            self.known_grids = [F.adaptive_avg_pool2d(x, f.shape[-2:]).eq(1) for f in features]
            self.known_anchors = torch.cat([g.flatten(1) for g in self.known_grids], dim=1)
            return super().__call__(predictions, batch)

        def single_mask_loss(self, gt_mask, pred, prototype, xyxy, area):
            logits = torch.einsum('in,nhw->ihw', pred, prototype)
            losses = F.binary_cross_entropy_with_logits(logits, gt_mask, reduction='none')
            known = crop_mask(self.known_proto.expand_as(losses).float(), xyxy)
            return ((losses*known).sum((1, 2))/known.sum((1, 2)).clamp_min(1)).sum()
    return KnownPixelLoss(model)
