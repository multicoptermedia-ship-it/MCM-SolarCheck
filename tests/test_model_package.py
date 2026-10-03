import pytest

from mcm_solarcheck.review.model_lineage import TrainingRun, TrainedModelArtifact
from mcm_solarcheck.review.model_package import build_model_package_manifest, require_model_distribution
from mcm_solarcheck.review.model_release import ModelRelease


def _values():
    run=TrainingRun("d"*64,"s"*64,"ultralytics","8.3","rendered_rgb",{"seed":42})
    artifact=TrainedModelArtifact(run.run_id,"a"*64,"pt")
    release=ModelRelease("r"*64,run.run_id,artifact.weights_sha256,"validator","e"*64)
    return run,artifact,release


def test_model_package_manifest_is_reproducible_and_rights_gated():
    run,artifact,release=_values()
    a=build_model_package_manifest(release,run,artifact,distribution_rights_verified=False)
    b=build_model_package_manifest(release,run,artifact,distribution_rights_verified=False)
    assert a.package_id==b.package_id
    assert not a.distributable
    with pytest.raises(PermissionError,match="rights"):
        require_model_distribution(a)


def test_model_package_distribution_requires_explicit_rights():
    run,artifact,release=_values()
    package=build_model_package_manifest(release,run,artifact,distribution_rights_verified=True)
    require_model_distribution(package)
    assert package.distributable


def test_model_package_rejects_release_weight_mismatch():
    run,artifact,release=_values()
    bad=ModelRelease(release.release_id,run.run_id,"b"*64,"validator",release.evaluation_id)
    with pytest.raises(ValueError,match="weights"):
        build_model_package_manifest(bad,run,artifact,distribution_rights_verified=True)
