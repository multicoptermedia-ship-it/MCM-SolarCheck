"""Fixed public comparison: isolate outline policy from network input scale."""
CHECK = 'solarcheck-cvut-yolo-native-comparison-1'
METRICS = ('legacy256_raw','legacy256_outlines','projective256_outlines',
    'common512_raw_from256','common512_outlines_from256','native512_raw','native512_outlines')


def reference_geometry(labels):
    """Audit restrictions separately; never use this information in decoding."""
    import cv2
    import numpy as np
    rejected,total = 0,0
    for identity in np.unique(labels[labels>0]):
        y,x = np.nonzero(labels==identity)
        a,b = cv2.minAreaRect(np.column_stack((x,y)).astype(np.float32))[1]
        total+=1
        rejected+=int(min(a,b)<=0 or not 1.25<=max(a,b)/min(a,b)<=2.8)
    return dict(reference_instances=total,old_aspect_rejected=rejected)


def compare(torch,model,rgb,targets,samples,*,should_cancel=lambda:False):
    import numpy as np
    from ..vision import cvut_yolo_validation as old
    from ..vision import cvut_yolo_outlines as outlines
    from ..vision.pvis_instance_decoding import aggregate
    rows=[]
    for index,sample in samples:
        if should_cancel():
            raise KeyboardInterrupt
        boxes,masks,confidence = old.infer(torch,model,rgb[index])
        legacy = old.module_masks(boxes,masks,confidence)
        projected,_,diagnostics = outlines.projective_outlines(boxes,masks,confidence)
        if should_cancel():
            raise KeyboardInterrupt
        boxes512,masks512,confidence512 = old.infer(torch,model,sample.rgb,size=512)
        projected512,_,diagnostics512 = outlines.projective_outlines(
            boxes512,masks512,confidence512,size=512)
        def up(mask):
            return np.repeat(np.repeat(mask,2,axis=1),2,axis=2)
        rows.append(dict(source_record_sha256=sample.record['record_sha256'],
            legacy256_raw=old.score_masks(targets[index],masks),
            legacy256_outlines=old.score_masks(targets[index],legacy),
            projective256_outlines=old.score_masks(targets[index],projected),
            common512_raw_from256=old.score_masks(sample.instances,up(masks),size=512),
            common512_outlines_from256=old.score_masks(sample.instances,up(projected),size=512),
            native512_raw=old.score_masks(sample.instances,masks512,size=512),
            native512_outlines=old.score_masks(sample.instances,projected512,size=512),
            projective256_diagnostics=diagnostics,projective512_diagnostics=diagnostics512,
            reference_geometry=reference_geometry(targets[index])))
    if len(rows)!=24:
        raise ValueError('Complete24-crop comparison required before publication')
    return dict(crops=rows,metrics={k:aggregate([row[k] for row in rows]) for k in METRICS},
        reference_geometry={k:sum(r['reference_geometry'][k] for r in rows)
                            for k in ('reference_instances','old_aspect_rejected')},
        outline_profile=outlines.PROFILE,
        common_grid='native512_reference_for_both_inputs_nearest2x256_prediction',
        original_grid='saved256_reference_for_original_and_projective256_outlines')
